import asyncio
import logging
import re
from typing import List, Optional

from graph_agents.utils.database_context import (
    Column,
    GraphElement,
    Index,
    JsonField,
    JsonSchema,
    Label,
    NodeReference,
    PropertyDeclaration,
    PropertyDefinition,
    PropertyGraph,
    Table,
)
from graph_agents.utils.engine import Engine

logger = logging.getLogger("graph_agents." + __name__)


class InformationSchema(object):

    def __init__(
        self,
        engine: Engine,
    ):
        self._engine = engine

    def get_table(self, name: str) -> Optional[Table]:
        results = self._engine.query(self._get_table_query(name)).results
        if len(results) == 0:
            return None
        table = results[0]
        return Table(
            name=table["name"],
            key_columns=table["key_columns"],
            columns=[Column(name=name, type=type) for (name, type) in table["columns"]],
        )

    def get_indexes(
        self,
        enabled_indexes: Optional[List[str]] = None,
        enabled_types: Optional[List[str]] = None,
    ) -> List[Index]:
        indexes = []
        for index_config in self._engine.query(
            self._get_index_query(enabled_indexes, enabled_types)
        ).results:
            columns = [
                Column(name=name, type=type, expr=expr)
                for (name, type, expr) in index_config["columns"]
            ]
            table = self.get_table(index_config["table_name"])
            del index_config["columns"]
            index = Index(
                name=index_config["name"],
                type=index_config["type"],
                table=table,
                columns=columns,
                **index_config["details"],
            )
            indexes.append(index)
        return indexes

    def get_property_graph(self, name: str) -> Optional[PropertyGraph]:
        results = self._engine.query(self._get_property_graph_query(name)).results
        if len(results) == 0:
            return None
        graph_json = results[0]["property_graph_metadata_json"]

        property_declarations = {
            decl["name"].casefold(): PropertyDeclaration(
                name=decl["name"],
                type=decl["type"],
            )
            for decl in graph_json.get("propertyDeclarations", [])
        }
        labels = {
            label["name"].casefold(): Label(
                name=label["name"],
                property_declaration_names=set(
                    {name.casefold() for name in label["propertyDeclarationNames"]}
                ),
            )
            for label in graph_json.get("labels", [])
        }
        nodes = {
            node["name"].casefold(): GraphElement(
                name=node["name"],
                table_name=node["baseTableName"],
                key_column_names=node["keyColumns"],
                label_names=[name.casefold() for name in node["labelNames"]],
                property_definitions={
                    pdef["propertyDeclarationName"].casefold(): PropertyDefinition(
                        name=pdef["propertyDeclarationName"],
                        expr=pdef["valueExpressionSql"],
                    )
                    for pdef in node.get("propertyDefinitions", [])
                },
            )
            for node in graph_json.get("nodeTables", [])
        }
        edges = {
            edge["name"].casefold(): GraphElement(
                name=edge["name"],
                table_name=edge["baseTableName"],
                key_column_names=edge["keyColumns"],
                label_names=[name.casefold() for name in edge["labelNames"]],
                property_definitions={
                    pdef["propertyDeclarationName"].casefold(): PropertyDefinition(
                        name=pdef["propertyDeclarationName"],
                        expr=pdef["valueExpressionSql"],
                    )
                    for pdef in edge.get("propertyDefinitions", [])
                },
                source_node_reference=NodeReference(
                    node_name=edge["sourceNodeTable"]["nodeTableName"]
                ),
                dest_node_reference=NodeReference(
                    node_name=edge["destinationNodeTable"]["nodeTableName"]
                ),
            )
            for edge in graph_json.get("edgeTables", [])
        }

        return PropertyGraph(
            name=graph_json["name"],
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

    def _get_index_query(
        self,
        enabled_indexes: Optional[List[str]] = None,
        enabled_types: Optional[List[str]] = None,
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
  WHERE TRUE
    AND %s
    AND %s """ % (
            (
                f"index.index_type IN UNNEST({enabled_types})"
                if enabled_types is not None
                else "TRUE"
            ),
            (
                f"index.index_name IN UNNEST({enabled_indexes})"
                if enabled_indexes is not None
                else "TRUE"
            ),
        )

    def _get_json_schema_query(self, table_name: str, json_expr: str):
        return f"""
        SELECT key, JSON_TYPE(j[key]) AS type
        FROM (
          SELECT ({json_expr}) AS j
          FROM {table_name}
          WHERE ({json_expr}) IS NOT NULL
          -- Ideally we should do TABLESAMPLE RESERVOIR (1 ROWS), but it can be slow
          LIMIT 1
        ) AS t, UNNEST(JSON_KEYS(j)) AS key
    """

    def get_json_property_schema_in_property_graph(
        self,
        graph: PropertyGraph,
        label_name: str,
        json_schema_included_properties: Optional[List[str]] = None,
    ) -> List[JsonSchema]:

        included_properties = (
            {name.casefold() for name in json_schema_included_properties}
            if json_schema_included_properties
            else None
        )
        label_name = label_name.casefold()
        label = graph.labels.get(label_name)
        if label is None:
            return []
        property_types = {
            pname: graph.property_declarations[pname].type
            for pname in label.property_declaration_names
            if included_properties is None or pname in included_properties
        }
        results = []
        for node in graph.nodes.values():
            if label_name in node.label_names:
                for pname, ptype in property_types.items():
                    if ptype != "JSON":
                        continue
                    results.append(
                        JsonSchema(
                            schema_object_name=label_name,
                            json_object_name=pname,
                            json_fields=[
                                JsonField(**row)
                                for row in self._engine.query(
                                    self._get_json_schema_query(
                                        node.table_name,
                                        node.property_definitions[pname].expr,
                                    )
                                ).results
                            ],
                        )
                    )

        for edge in graph.edges.values():
            if label_name in edge.label_names:
                for pname, ptype in property_types.items():
                    if ptype != "JSON":
                        continue
                    results.append(
                        JsonSchema(
                            schema_object_name=label_name,
                            json_object_name=pname,
                            json_fields=[
                                JsonField(**row)
                                for row in self._engine.query(
                                    self._get_json_schema_query(
                                        edge.table_name,
                                        edge.property_definitions[pname].expr,
                                    )
                                ).results
                            ],
                        )
                    )
        return results
