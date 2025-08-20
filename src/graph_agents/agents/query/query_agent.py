# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import functools
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.cloud import spanner
from google.cloud.spanner_v1.database import Database
from pydantic import BaseModel, Field

from graph_agents.instructions.query.prompts import (
    SPANNER_GRAPH_AGENT_DEFAULT_DESCRIPTION,
    SPANNER_GRAPH_AGENT_DEFAULT_INSTRUCTIONS,
    SPANNER_GRAPH_QUERY_QA_TOOL_DEFAULT_DESCRIPTION_TEMPLATE,
)
from graph_agents.tools import (
    SpannerFullTextSearchTool,
    SpannerGraphQueryQATool,
    SpannerGraphVisualizationTool,
    build_schema_inspection_tools,
)
from graph_agents.utils.database_context import Index, PropertyGraph
from graph_agents.utils.information_schema import InformationSchema

logger = logging.getLogger("graph_agents." + __name__)


class QueryAgentConfig(BaseModel):
    num_gql_examples: Optional[int] = Field(
        default=3, description="Num of GQL examples to show"
    )
    example_table: Optional[str] = Field(
        default=None, description="Spanner table names that stores the gql examples"
    )
    embedding_model: Optional[str] = Field(
        default=None, description="Embedding model to get gql examples"
    )
    enabled_indexes: Optional[List[str]] = Field(
        default=None, description="Enabled indexes"
    )
    enabled_index_types: Optional[List[str]] = Field(
        default=None, description="Enabled index types"
    )
    log_level: str = Field(default="INFO", description="Log level.")


class SpannerGraphQueryAgent(LlmAgent):

    identifier: Tuple[Optional[str], str, str, str]
    agent_config: QueryAgentConfig
    gql_query_tool: Optional[SpannerGraphQueryQATool] = None

    def __init__(
        self,
        instance_id: str,
        database_id: str,
        graph_id: str,
        model: str = "",
        project_id: Optional[str] = None,
        description: Optional[str] = None,
        instruction: Optional[str] = None,
        agent_config: QueryAgentConfig = QueryAgentConfig(),
        name: str = "GraphQueryAgent",
        **kwargs: Any,
    ):
        """
        Build a GraphQueryAgent that talks with a Spanner Graph database
        identified by (project_id, instance_id, database_id, graph_id).

        Optional arguments:
        - name: the name of the agent, by default, `GraphQueryAgent`;
        - agent_config: detailed configuration of agent.

        By default, project id is inferred from the environment.
        """
        if isinstance(agent_config, dict):
            agent_config = QueryAgentConfig(**agent_config)
        super().__init__(
            model=model,
            name=name,
            description=description or SPANNER_GRAPH_AGENT_DEFAULT_DESCRIPTION,
            instruction=instruction or SPANNER_GRAPH_AGENT_DEFAULT_INSTRUCTIONS,
            tools=[],
            identifier=(project_id, instance_id, database_id, graph_id),
            agent_config=agent_config,
            **kwargs,
        )
        self._config_log_level(agent_config)
        self.reload_tools()

    @classmethod
    @functools.wraps(__init__, assigned=("__doc__"))
    def create_query_agent(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def build_graph_query_tool(
        self,
        database: Database,
        property_graph: PropertyGraph,
        model: str,
        agent_config: QueryAgentConfig,
    ):
        gql_query_tool_description = (
            SPANNER_GRAPH_QUERY_QA_TOOL_DEFAULT_DESCRIPTION_TEMPLATE.format(
                node_labels=json.dumps(property_graph.get_node_labels(), indent=1),
                edge_labels=json.dumps(property_graph.get_triplet_labels(), indent=1),
            )
        )
        return SpannerGraphQueryQATool(
            database,
            property_graph.name,
            model,
            gql_query_tool_description,
            agent_config.model_dump(),
        )

    def _config_log_level(self, agent_config: QueryAgentConfig):
        log_level = agent_config.log_level
        if not log_level:
            return
        if not isinstance(log_level, str):
            raise ValueError("log level must be valid strings: e.g. INFO, DEBUG")
        level = getattr(logging, log_level.upper())
        logging.basicConfig(
            level=level,
            format=(
                "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d -" " %(message)s"
            ),
        )
        logging.getLogger("graph_agents").setLevel(level)

    def infer_tools_from_indexes(
        self,
        database: Database,
        information_schema: InformationSchema,
        property_graph: PropertyGraph,
        agent_config: QueryAgentConfig,
    ):
        enabled_indexes = agent_config.enabled_indexes
        enabled_types = agent_config.enabled_index_types
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
                logger.debug(f"Skipped index: {index.name}")
                continue
            for label_name, column_aliases in label_with_aliases:
                tool = None
                if index.type == "SEARCH":
                    tool = SpannerFullTextSearchTool.build_from_index(
                        database,
                        index,
                        table_alias=label_name,
                        column_aliases=column_aliases,
                    )
                if not tool:
                    logger.info(f"Skipped index for label `{label_name}`: {index.name}")
                    continue

                logger.info(
                    f"Added a tool built for label `{label_name}` from the index:"
                    f" {index.name}"
                )
                tools.append(tool)
        return tools

    def build_schema_tools(
        self, information_schema: InformationSchema, property_graph: PropertyGraph
    ):
        return [
            FunctionTool(func)
            for func in build_schema_inspection_tools(
                information_schema, property_graph
            )
        ]

    def reload_tools(self):
        """Reload the agent tools.

        This is useful when the underlying schema changes.
        """
        # When model unspecified, we use the canonical model which can be
        # inferred from the parent or ancestor agent.
        self.model = self.model or self.canonical_model.model
        project_id, instance_id, database_id, graph_id = self.identifier
        client = spanner.Client(project=project_id)
        database = client.instance(instance_id).database(database_id)
        information_schema = InformationSchema(database)
        property_graph = information_schema.get_property_graph(graph_id)
        if property_graph is None:
            raise ValueError(f"No graph with name `{graph_id}` found")

        tools = self.infer_tools_from_indexes(
            database, information_schema, property_graph, self.agent_config
        )
        self.gql_query_tool = self.build_graph_query_tool(
            database, property_graph, self.model, self.agent_config
        )
        tools.append(self.gql_query_tool)
        tools.append(SpannerGraphVisualizationTool(database, property_graph.name))
        tools.extend(self.build_schema_tools(information_schema, property_graph))
        tools.append(FunctionTool(self.reload_tools))
        for tool in tools:
            logger.debug(
                f"Tool: {tool.name}\n" + f"Description: {tool.description}\n\n"
            )
        self.tools = tools
