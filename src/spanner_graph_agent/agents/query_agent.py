import asyncio
import json
import logging
from typing import Any, Optional, Union
from google.adk.agents import LlmAgent
from google.cloud import spanner
from google.cloud.spanner_v1.database import Database
from spanner_graph_agent.tools import (
    SpannerFullTextSearchTool,
    SpannerGraphQueryQATool,
    SpannerGraphVisualizationTool,
)
from spanner_graph_agent.utils.information_schema import (
    Index,
    InformationSchema,
    PropertyGraph,
)
from spanner_graph_agent.utils.prompts import (
    SPANNER_GRAPH_AGENT_DEFAULT_DESCRIPTION,
    SPANNER_GRAPH_AGENT_DEFAULT_INSTRUCTIONS,
    SPANNER_GRAPH_QUERY_QA_TOOL_DEFAULT_DESCRIPTION_TEMPLATE,
)

logger = logging.getLogger('spanner_graph_agent.' + __name__)


class SpannerGraphQueryAgent(LlmAgent):

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
      **kwargs: Any,
  ):
    self._config_log_level(agent_config)

    client = spanner.Client(project=project_id)
    database = client.instance(instance_id).database(database_id)
    information_schema = InformationSchema(database)
    property_graph = information_schema.get_property_graph(graph_id)
    if property_graph is None:
      raise ValueError(f'No graph with name `{graph_id}` found')

    tools = self.infer_tools_from_indexes(
        database, information_schema, property_graph, agent_config
    )
    gql_query_tool = self.build_graph_query_tool(
        database, property_graph, model, agent_config
    )
    tools.append(gql_query_tool)
    tools.append(SpannerGraphVisualizationTool(database, property_graph.name))
    for tool in tools:
      logger.debug(
          f'Tool: {tool.name}\n' + f'Description: {tool.description}\n\n'
      )
    super().__init__(
        model=model,
        name='SpannerGraphQueryAgent',
        description=description or SPANNER_GRAPH_AGENT_DEFAULT_DESCRIPTION,
        instruction=instruction or SPANNER_GRAPH_AGENT_DEFAULT_INSTRUCTIONS,
        gql_query_tool=gql_query_tool,
        tools=tools + [gql_query_tool],
        **kwargs,
    )

  def build_graph_query_tool(
      self,
      database: Database,
      property_graph: PropertyGraph,
      model: str,
      agent_config: dict[str, Any],
  ):
    gql_query_tool_description = (
        SPANNER_GRAPH_QUERY_QA_TOOL_DEFAULT_DESCRIPTION_TEMPLATE.format(
            node_labels=json.dumps(property_graph.get_node_labels(), indent=1),
            edge_labels=json.dumps(property_graph.get_edge_labels(), indent=1),
        )
    )
    return SpannerGraphQueryQATool(
        database,
        property_graph.name,
        model,
        gql_query_tool_description,
        agent_config,
    )

  def _config_log_level(self, agent_config: dict[str, Any]):
    log_level = agent_config.get('log_level')
    if not log_level:
      return
    if not isinstance(log_level, str):
      raise ValueError('log level must be valid strings: e.g. INFO, DEBUG')
    level = getattr(logging, log_level.upper())
    agent_config['verbose'] = level < logging.INFO
    logging.basicConfig(
        level=level,
        format=(
            '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d -'
            ' %(message)s'
        ),
    )
    logging.getLogger('spanner_graph_agent').setLevel(level)

  def infer_tools_from_indexes(
      self,
      database: Database,
      information_schema: InformationSchema,
      property_graph: PropertyGraph,
      agent_config: dict[str, Any],
  ):
    enabled_indexes = agent_config.get('enabled_indexes')
    enabled_types = agent_config.get('enabled_index_types', ['SEARCH'])
    all_indexes = information_schema.get_indexes(
        enabled_indexes=enabled_indexes,
        enabled_types=enabled_types,
    )
    tools = []
    for index in all_indexes:
      label_with_aliases = property_graph.get_label_and_properties(
          index.table.name
      )
      if not label_with_aliases:
        logger.debug(f'Skipped index: {index.name}')
        continue
      for label_name, column_aliases in label_with_aliases:
        tool = None
        if index.type == 'SEARCH':
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
