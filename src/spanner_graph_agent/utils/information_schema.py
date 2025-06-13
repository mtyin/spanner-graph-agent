import asyncio
import logging
import re
from typing import List, Optional
from google.cloud.spanner_v1.database import Database
from pydantic import BaseModel

logger = logging.getLogger('spanner_graph_agent.' + __name__)


class JsonField(BaseModel):
  key: str
  type: str


class JsonSchema(BaseModel):
  schema_object_name: str
  json_object_name: str
  json_fields: List[JsonField]


class Column(BaseModel):
  name: str
  type: str
  expr: Optional[str] = None


class Table(BaseModel):
  name: str
  key_columns: List[str]
  columns: List[Column]


class Index(BaseModel):
  name: str
  type: str
  table: Table
  columns: List[Column]
  filter: Optional[str]
  search_partition_by: Optional[List[str]]
  search_order_by: Optional[List[str]]


class PropertyDeclaration(BaseModel):
  name: str
  type: str


class Label(BaseModel):
  name: str
  property_declaration_names: List[str]


class PropertyDefinition(BaseModel):
  name: str
  expr: str


class NodeReference(BaseModel):
  node_name: str


class GraphElement(BaseModel):
  name: str
  table_name: str
  key_column_names: List[str]
  label_names: List[str]
  property_definitions: List[PropertyDefinition]
  source_node_reference: Optional[NodeReference] = None
  dest_node_reference: Optional[NodeReference] = None


class PropertyGraph(BaseModel):
  name: str
  nodes: List[GraphElement]
  edges: List[GraphElement]
  labels: List[Label]
  property_declarations: List[PropertyDeclaration]

  def get_node_labels(self):
    return list({label for node in self.nodes for label in node.label_names})

  def get_edge_labels(self):
    node_labels = {
        node.name.casefold(): node.label_names for node in self.nodes
    }
    return list({
        (src_node_label, edge_label, dst_node_label)
        for edge in self.edges
        for edge_label in edge.label_names
        for src_node_label in node_labels[
            edge.source_node_reference.node_name.casefold()
        ]
        for dst_node_label in node_labels[
            edge.dest_node_reference.node_name.casefold()
        ]
    })


class InformationSchema(object):

  def __init__(
      self,
      database: Database,
  ):
    self.database = database

  def get_table(self, name: str) -> Optional[Table]:
    results = self._query(self._get_table_query(name))
    if len(results) == 0:
      return None
    table = results[0]
    return Table(
        name=table['name'],
        key_columns=table['key_columns'],
        columns=[
            Column(name=name, type=type) for (name, type) in table['columns']
        ],
    )

  def get_search_indexes(
      self, enabled_indexes: Optional[List[str]] = None
  ) -> List[Index]:
    indexes = []
    for index_config in self._query(
        self._get_search_index_query(enabled_indexes)
    ):
      columns = [
          Column(name=name, type=type, expr=expr)
          for (name, type, expr) in index_config['columns']
      ]
      table = self.get_table(index_config['table_name'])
      del index_config['columns']
      index = Index(
          name=index_config['name'],
          type=index_config['type'],
          table=table,
          columns=columns,
          **index_config['details'],
      )
      indexes.append(index)
    return indexes

  def get_json_property_schema_in_property_graph(
      self,
      graph: PropertyGraph,
      json_schema_included_properties: Optional[List[str]] = None,
  ) -> List[JsonSchema]:

    included_properties = (
        {name.casefold() for name in json_schema_included_properties}
        if json_schema_included_properties
        else None
    )
    property_types = {
        prop.name.casefold(): prop.type
        for prop in graph.property_declarations
        if included_properties is None
        or prop.name.casefold() in included_properties
    }
    label_properties = {
        label.name.casefold(): label.property_declaration_names
        for label in graph.labels
    }
    results = []
    for node in graph.nodes:
      for label_name in node.label_names:
        for property_name in label_properties.get(label_name.casefold(), []):
          if property_types.get(property_name.casefold()) != 'JSON':
            continue
          results.append(
              JsonSchema(
                  schema_object_name=label_name,
                  json_object_name=property_name,
                  json_fields=[
                      JsonField(**row)
                      for row in self._query(
                          self._get_node_json_property_schema_query(
                              graph.name, label_name, property_name
                          )
                      )
                  ],
              )
          )

    for edge in graph.edges:
      for label_name in edge.label_names:
        for property_name in label_properties.get(label_name.casefold(), []):
          if property_types.get(property_name.casefold()) != 'JSON':
            continue
          results.append(
              JsonSchema(
                  schema_object_name=label_name,
                  json_object_name=property_name,
                  json_fields=[
                      JsonField(**row)
                      for row in self._query(
                          self._get_edge_json_property_schema_query(
                              graph.name, label_name, property_name
                          )
                      )
                  ],
              )
          )
    return results

  def get_property_graph(self, name: str) -> Optional[PropertyGraph]:
    results = self._query(self._get_property_graph_query(name))
    if len(results) == 0:
      return None
    graph_json = results[0]['property_graph_metadata_json']

    property_declarations = [
        PropertyDeclaration(
            name=decl['name'],
            type=decl['type'],
        )
        for decl in graph_json.get('propertyDeclarations', [])
    ]
    labels = [
        Label(
            name=label['name'],
            property_declaration_names=label['propertyDeclarationNames'],
        )
        for label in graph_json.get('labels', [])
    ]
    nodes = [
        GraphElement(
            name=node['name'],
            table_name=node['baseTableName'],
            key_column_names=node['keyColumns'],
            label_names=node['labelNames'],
            property_definitions=[
                PropertyDefinition(
                    name=pdef['propertyDeclarationName'],
                    expr=pdef['valueExpressionSql'],
                )
                for pdef in node.get('propertyDefinitions', [])
            ],
        )
        for node in graph_json.get('nodeTables', [])
    ]
    edges = [
        GraphElement(
            name=edge['name'],
            table_name=edge['baseTableName'],
            key_column_names=edge['keyColumns'],
            label_names=edge['labelNames'],
            property_definitions=[
                PropertyDefinition(
                    name=pdef['propertyDeclarationName'],
                    expr=pdef['valueExpressionSql'],
                )
                for pdef in edge.get('propertyDefinitions', [])
            ],
            source_node_reference=NodeReference(
                node_name=edge['sourceNodeTable']['nodeTableName']
            ),
            dest_node_reference=NodeReference(
                node_name=edge['destinationNodeTable']['nodeTableName']
            ),
        )
        for edge in graph_json.get('edgeTables', [])
    ]

    return PropertyGraph(
        name=graph_json['name'],
        nodes=nodes,
        edges=edges,
        labels=labels,
        property_declarations=property_declarations,
    )

  def _get_property_graph_query(self, graph_name):
    return f"""
    SELECT property_graph_metadata_json
    FROM INFORMATION_SCHEMA.PROPERTY_GRAPHS
    WHERE property_graph_name = '{graph_name}'
    """

  def _get_table_query(self, table_name):
    return f"""
    SELECT TABLE_NAME AS name,
           ARRAY(
             SELECT COLUMN_NAME
             FROM INFORMATION_SCHEMA.INDEX_COLUMNS AS index_column
             WHERE index_column.table_name = table.TABLE_NAME
               AND index_column.INDEX_TYPE = 'PRIMARY_KEY'
             ORDER BY index_column.ORDINAL_POSITION
           ) AS key_columns,
           ARRAY(
             SELECT STRUCT(column.COLUMN_NAME, column.SPANNER_TYPE)
             FROM INFORMATION_SCHEMA.COLUMNS AS column
             WHERE column.TABLE_NAME = table.TABLE_NAME
           ) AS columns
    FROM INFORMATION_SCHEMA.TABLES AS table
    WHERE table.TABLE_NAME = '{table_name}'
    """

  def _get_search_index_query(
      self, enabled_indexes: Optional[List[str]] = None
  ):
    return """
  SELECT INDEX_NAME AS name,
         INDEX_TYPE AS type,
         TABLE_NAME AS table_name,
         ARRAY (
           SELECT STRUCT(
                     index_column.COLUMN_NAME AS name,
                     index_column.SPANNER_TYPE AS type,
                     (SELECT GENERATION_EXPRESSION
                     FROM INFORMATION_SCHEMA.COLUMNS AS column
                     WHERE index_column.TABLE_NAME = column.TABLE_NAME
                       AND index_column.COLUMN_NAME = column.COLUMN_NAME
                     LIMIT 1) AS expr)
           FROM INFORMATION_SCHEMA.INDEX_COLUMNS AS index_column
           WHERE index.TABLE_NAME = index_column.TABLE_NAME
             AND index.INDEX_NAME = index_column.INDEX_NAME
           ORDER BY index_column.ORDINAL_POSITION
         ) AS columns,
         JSON_OBJECT("filter", index.FILTER,
                     "search_partition_by", index.SEARCH_PARTITION_BY,
                     "search_order_by", index.SEARCH_ORDER_BY) AS details
  FROM INFORMATION_SCHEMA.INDEXES AS index
  WHERE index.INDEX_TYPE = 'SEARCH' AND index.IS_UNIQUE
    AND %s """ % (
        f'index.name IN UNNEST([{enabled_indexes}])'
        if enabled_indexes is not None
        else 'TRUE'
    )

  def _get_node_json_property_schema_query(
      self, graph_id: str, label_name: str, property_name: str
  ):
    return f"""
    GRAPH {graph_id}
    MATCH (n:{label_name})
    WHERE n.{property_name} IS NOT NULL
    LET j = n.{property_name}
    TABLESAMPLE RESERVOIR (1 ROWS)
    LET keys = JSON_KEYS(j, 1)
    FOR key IN keys
    LET v = j[key]
    LET type = json_type(v)
    RETURN key, type
    """

  def _get_edge_json_property_schema_query(
      self, graph_id: str, label_name: str, property_name: str
  ):
    return f"""
    GRAPH {graph_id}
    MATCH -[n:{label_name}]->
    WHERE n.{property_name} IS NOT NULL
    LET j = n.{property_name}
    TABLESAMPLE RESERVOIR (1 ROWS)
    LET keys = JSON_KEYS(j, 1)
    FOR key IN keys
    LET v = j[key]
    let type = json_type(v)
    RETURN key, type
    """

  def _query(self, q: str):
    with self.database.snapshot() as snapshot:
      rows = snapshot.execute_sql(q)
      return [
          {
              column: value
              for column, value in zip(
                  [column.name for column in rows.fields], row
              )
          }
          for row in rows
      ]

  async def _aquery(self, q: str):
    return await asyncio.to_thread(_query, self, q)
