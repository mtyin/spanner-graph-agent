import asyncio
import functools
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools import FunctionTool, ToolContext
from pydantic import BaseModel, Field
from typing_extensions import override

from graph_agents.instructions.prompts import get_prompt
from graph_agents.tools import build_schema_inspection_tools
from graph_agents.tools.nl2gql.nl2gql import GraphQueryGenerationContextTool
from graph_agents.utils.database_context import Index, PropertyGraph
from graph_agents.utils.embeddings import Embeddings
from graph_agents.utils.engine import Engine
from graph_agents.utils.example_store import ExampleStore, QueryExample, QueryFixExample
from graph_agents.utils.information_schema import InformationSchema
from graph_agents.utils.json import to_json

logger = logging.getLogger("graph_agents." + __name__)


class QueryAgentConfig(BaseModel):
    num_gql_examples: int = Field(default=3, description="Num of GQL examples to show")
    max_iterations: int = Field(
        default=3, description="Max number trials to generate query and execute"
    )
    example_table: Optional[str] = Field(
        default="gql_examples",
        description="Table names that stores the gql examples",
    )
    query_example_paths: List[str] = Field(
        default=[],
        description="A list of paths to default query example files",
    )
    embedding_model: Optional[str] = Field(
        default="text-embedding-004", description="Embedding model to get gql examples"
    )
    enabled_indexes: Optional[List[str]] = Field(
        default=None, description="Enabled indexes"
    )
    enabled_index_types: Optional[List[str]] = Field(
        default=["SEARCH"], description="Enabled index types"
    )
    log_level: str = Field(default="INFO", description="Log level.")
    timeout: int = Field(
        default=30, description="Default timeout in seconds for engine APIs."
    )


def exit_loop(tool_context: ToolContext):
    """Call this function when we successfully generate and excutive a valid
    graph query and have sufficiently knowledge to answer the user query.
    """
    logger.info("Exit the loop...")
    tool_context.actions.escalate = True
    return []


class GraphQueryQAAgent(LlmAgent):

    def __init__(
        self,
        engine,
        query_generation_tool,
        model: str,
        name: str = "",
        description: Optional[str] = None,
        instruction: Optional[str] = None,
    ):
        super().__init__(
            model=model,
            name=name or "GraphQueryQAAgent",
            tools=[
                query_generation_tool,
                FunctionTool(to_json(engine.query)),
                exit_loop,
            ],
            description=description
            or get_prompt(
                "GRAPH_QUERY_QA_AGENT_DEFAULT_DESCRIPTION", product=engine.name()
            ),
            instruction=instruction
            or get_prompt("GRAPH_QUERY_QA_AGENT_DEFAULT_INSTRUCTIONS"),
        )


class GraphQueryAgent(LlmAgent):

    graph_id: str
    engine: Engine
    example_store: Optional[ExampleStore]
    agent_config: QueryAgentConfig
    gql_query_tool: Optional[GraphQueryGenerationContextTool] = None

    def __init__(
        self,
        graph_id: str,
        engine: Engine,
        model: str = "",
        description: Optional[str] = None,
        instruction: Optional[str] = None,
        agent_config: QueryAgentConfig = QueryAgentConfig(),
        name: str = "GraphQueryAgent",
        example_store: Optional[ExampleStore] = None,
        **kwargs: Any,
    ):
        if isinstance(agent_config, dict):
            agent_config = QueryAgentConfig(**agent_config)
        super().__init__(
            model=model,
            name=name,
            description=description
            or get_prompt(
                "GRAPH_QUERY_AGENT_DEFAULT_DESCRIPTION", product=engine.name()
            ),
            instruction=instruction
            or get_prompt("GRAPH_QUERY_AGENT_DEFAULT_INSTRUCTIONS"),
            graph_id=graph_id,
            engine=engine,
            example_store=example_store,
            agent_config=agent_config,
            tools=[],
            **kwargs,
        )
        self._config_log_level(agent_config)
        self.reload_tools()

    def reload_extra_tools(self):
        return []

    def build_graph_query_tool(self):
        return GraphQueryGenerationContextTool(
            self.engine,
            self.graph_id,
            self.example_store,
            num_gql_examples=self.agent_config.num_gql_examples,
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

    def build_schema_tools(self, information_schema: InformationSchema):
        return [
            FunctionTool(func)
            for func in build_schema_inspection_tools(information_schema, self.graph_id)
        ]

    def reload_tools(self):
        """Reload the agent tools."""
        # When model unspecified, we use the canonical model which can be
        # inferred from the parent or ancestor agent.
        self.model = self.model or self.canonical_model.model
        information_schema = InformationSchema(self.engine)
        property_graph = information_schema.get_property_graph(self.graph_id)
        if property_graph is None:
            raise ValueError(f"No graph with name `{self.graph_id}` found")

        self.gql_query_tool = self.build_graph_query_tool()
        tools = []
        tools.extend(self.build_schema_tools(information_schema))
        tools.extend(self.reload_extra_tools())
        tools.append(FunctionTool(self.reload_tools))
        if self.example_store:
            tools.append(FunctionTool(self.add_examples))
            tools.append(FunctionTool(self.add_fix_examples))
            if self.agent_config.query_example_paths:
                cnt = self.example_store.load_examples(
                    self.agent_config.query_example_paths
                )
                logger.info(
                    f"Loaded {cnt} examples from {self.agent_config.query_example_paths}"
                )
        self.sub_agents = [
            LoopAgent(
                name="GraphQueryQAWithRetryAgent",
                description="",
                max_iterations=self.agent_config.max_iterations,
                sub_agents=[
                    GraphQueryQAAgent(
                        self.engine, self.gql_query_tool, model=self.model
                    )
                ],
            )
        ]
        for tool in tools:
            logger.debug(
                f"Tool: {tool.name}\n" + f"Description: {tool.description}\n\n"
            )
        self.tools = tools

    def add_examples(self, examples: List[QueryExample]):
        """Add graph query examples that can be referred as contextual information during query generation."""
        if self.example_store is None:
            raise ValueError("No example store configured")
        self.example_store.add_examples(examples)

    def add_fix_examples(self, examples: List[QueryFixExample]):
        """Add graph query fix examples that can be referred as contextual information when try to fix an invalid graph query."""

        if self.example_store is None:
            raise ValueError("No example store configured")
        self.example_store.add_fix_examples(examples)
