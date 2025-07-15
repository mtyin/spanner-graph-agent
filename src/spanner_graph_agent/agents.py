import asyncio
import json
import logging
from typing import Any, Optional, Union
from google.adk.agents import LlmAgent
from google.cloud import spanner
from google.cloud.spanner_v1.database import Database
from spanner_graph_agent.prompts import (
    SPANNER_GRAPH_AGENT_DEFAULT_DESCRIPTION,
    SPANNER_GRAPH_AGENT_DEFAULT_INSTRUCTIONS,
    SPANNER_GRAPH_QUERY_QA_TOOL_DEFAULT_DESCRIPTION_TEMPLATE,
)
from spanner_graph_agent.tools.index_tools import SpannerFullTextSearchTool
from spanner_graph_agent.tools.langchain_tools import SpannerGraphQueryQATool
from spanner_graph_agent.utils.information_schema import (
    Index,
    InformationSchema,
    PropertyGraph,
)

logger = logging.getLogger('spanner_graph_agent.' + __name__)


class SpannerGraphAgent(LlmAgent):

  gql_query_tool: SpannerGraphQueryQATool

  def __init__(
      self,
      instance_id: str,
      database_id: str,
      graph_id: str,
      model: str,
      project_id: Optional[str] = None,
      description: Optional[str] = None,
      instruction: Optional[str] = None,
      agent_config: dict[str, Any] = {},
  ):
    client = spanner.Client(project=project_id)
    database = client.instance(instance_id).database(database_id)
    self._config_log_level(agent_config)
    information_schema = InformationSchema(database)
    property_graph = information_schema.get_property_graph(graph_id)
    if property_graph is None:
      raise ValueError(f'No graph with name `{graph_id}` found')
    tools = self.build_index_tools(
        database, information_schema, property_graph, agent_config
    )
    gql_query_tool_description = (
        SPANNER_GRAPH_QUERY_QA_TOOL_DEFAULT_DESCRIPTION_TEMPLATE.format(
            node_labels=json.dumps(property_graph.get_node_labels(), indent=1),
            edge_labels=json.dumps(property_graph.get_edge_labels(), indent=1),
        )
    )
    gql_query_tool = SpannerGraphQueryQATool(
        instance_id,
        database_id,
        graph_id,
        model,
        gql_query_tool_description,
        client,
        agent_config,
    )

    for tool in tools:
      logger.info(
          f'Tool: {tool.name}\n' + f'Description: {tool.description}\n\n'
      )
    super().__init__(
        model=model,
        name='SpannerGraphAgent',
        description=description or SPANNER_GRAPH_AGENT_DEFAULT_DESCRIPTION,
        instruction=instruction or SPANNER_GRAPH_AGENT_DEFAULT_INSTRUCTIONS,
        gql_query_tool=gql_query_tool,
        tools=tools + [gql_query_tool],
    )

  def _config_log_level(self, agent_config: dict[str, Any]):
    log_level = agent_config.get(
        'log_level', 'DEBUG' if agent_config.get('verbose') else 'INFO'
    )
    logging.getLogger('spanner_graph_agent').setLevel(
        getattr(logging, log_level.upper())
    )

  def build_index_tools(
      self,
      database: Database,
      information_schema: InformationSchema,
      graph: PropertyGraph,
      agent_config: dict[str, Any],
  ):
    enabled_indexes = agent_config.get('indexes_as_tools')
    all_search_indexes = information_schema.get_search_indexes(enabled_indexes)
    properties_by_label = {
        label.name: label.property_declaration_names for label in graph.labels
    }
    label_with_aliases_by_table = {}
    for node in graph.nodes:
      for label in node.label_names:
        label_with_aliases_by_table.setdefault(
            node.table_name.casefold(), {}
        ).setdefault(
            label,
            {
                pdef.expr.casefold(): pdef.name
                for pdef in node.property_definitions
                if pdef.name.casefold() in properties_by_label[label]
            },
        )
    for edge in graph.edges:
      for label in edge.label_names:
        label_with_aliases_by_table.setdefault(
            edge.table_name.casefold(), {}
        ).setdefault(
            label,
            {
                pdef.expr.casefold(): pdef.name
                for pdef in edge.property_definitions
                if pdef.name.casefold() in properties_by_label[label]
            },
        )

    tools = []
    for index in all_search_indexes:
      label_with_aliases = label_with_aliases_by_table.get(
          index.table.name.casefold(), {}
      )
      if not label_with_aliases:
        logger.info(f'Skipped index: {index.name}')
        continue
      for label_name, column_aliases in label_with_aliases.items():
        tool = SpannerFullTextSearchTool.build_from_index(
            database,
            index,
            label_name,
            column_aliases,
        )
        if not tool:
          logger.info(f'Skipped index for label `{label_name}`: {index.name}')
          continue

        logger.info(
            f'Added a tool built for label `{label_name}` from the index:'
            f' {index.name}'
        )
        tools.append(tool)
    return tools
