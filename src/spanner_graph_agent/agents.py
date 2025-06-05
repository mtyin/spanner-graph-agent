import logging
from typing import Any, Optional, Union
from google.adk.agents import LlmAgent
from google.cloud import spanner
from google.cloud.spanner_v1.database import Database
from spanner_graph_agent.prompts import (
    SPANNER_GRAPH_AGENT_DEFAULT_DESCRIPTION,
    SPANNER_GRAPH_AGENT_DEFAULT_INSTRUCTIONS,
)
from spanner_graph_agent.tools.index_tools import SpannerFullTextSearchTool
from spanner_graph_agent.tools.langchain_tools import SpannerGraphQueryQATool
from spanner_graph_agent.utils.information_schema import (
    Index,
    InformationSchema,
    PropertyGraph,
)


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
    tools = self.build_index_tools(database, graph_id, agent_config)
    gql_query_tool = SpannerGraphQueryQATool(
        instance_id,
        database_id,
        graph_id,
        model,
        client,
        agent_config,
    )
    for tool in tools:
      logging.info(
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

  def build_index_tools(
      self,
      database: Database,
      graph_id: str,
      agent_config: dict[str, Any],
  ):
    information_schema = InformationSchema(database)
    graph = information_schema.get_property_graph(graph_id)
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
    for index in information_schema.get_search_indexes():
      label_with_aliases = label_with_aliases_by_table.get(
          index.table.name.casefold(), {}
      )
      if not label_with_aliases:
        logging.info(f'Skipped index: {index.name}')
        continue
      for label_name, column_aliases in label_with_aliases.items():
        tool = SpannerFullTextSearchTool.build_from_index(
            database,
            index,
            label_name,
            column_aliases,
        )
        if not tool:
          logging.info(f'Skipped index for label `{label_name}`: {index.name}')
          continue

        logging.info(
            f'Added a tool built for label `{label_name}` from the index:'
            f' {index.name}'
        )
        tools.append(tool)
    return tools
