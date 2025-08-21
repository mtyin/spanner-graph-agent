import functools
import logging
from typing import Any, Optional

from typing_extensions import override

from graph_agents.agents.query.query_agent import GraphQueryAgent, QueryAgentConfig
from graph_agents.tools import (
    SpannerFullTextSearchTool,
    SpannerGraphVisualizationTool,
    build_schema_inspection_tools,
)
from graph_agents.utils.embeddings import Embeddings
from graph_agents.utils.information_schema import InformationSchema, PropertyGraph
from graph_agents.utils.spanner.engine import SpannerEngine
from graph_agents.utils.spanner.example_store import SpannerExampleStore

logger = logging.getLogger("graph_agents." + __name__)


class SpannerGraphQueryAgent(GraphQueryAgent):

    def __init__(
        self,
        instance_id: str,
        database_id: str,
        graph_id: str,
        project_id: Optional[str] = None,
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
        from google.cloud import spanner

        spanner_client = spanner.Client(project=project_id)
        instance = spanner_client.instance(instance_id)
        database = instance.database(database_id)
        engine = SpannerEngine(database, timeout=agent_config.timeout)
        example_store = None
        if agent_config.embedding_model:
            embeddings = Embeddings(agent_config.embedding_model, project=project_id)
            example_store = SpannerExampleStore(engine, embeddings)
        super().__init__(
            graph_id,
            engine,
            agent_config=agent_config,
            name=name,
            example_store=example_store,
            **kwargs,
        )

    @classmethod
    @functools.wraps(__init__, assigned=("__doc__",))
    def create_query_agent(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    @override
    def reload_extra_tools(self):
        information_schema = InformationSchema(self.engine)
        property_graph = information_schema.get_property_graph(self.graph_id)
        tools = self.infer_tools_from_indexes(
            information_schema, property_graph, self.agent_config
        )
        tools.append(SpannerGraphVisualizationTool(self.engine, property_graph.name))
        return tools

    def infer_tools_from_indexes(
        self,
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
                        self.engine,
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
