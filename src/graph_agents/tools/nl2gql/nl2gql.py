from typing import Any, List, Optional

from google.adk.tools import BaseTool, FunctionTool, ToolContext
from pydantic import BaseModel, Field

from graph_agents.utils.database_context import PropertyGraphDescriptor
from graph_agents.utils.engine import Engine
from graph_agents.utils.example_store import ExampleStore, QueryExample, QueryFixExample
from graph_agents.utils.information_schema import InformationSchema


class QueryGenerationContext(BaseModel):

    graph_schema: PropertyGraphDescriptor = Field(description="Property graph schema")
    query_examples: List[QueryExample] = Field(
        default=[], description="A list of graph query examples"
    )
    query_fix_examples: List[QueryFixExample] = Field(
        default=[],
        description="A list of examples on how to fix incorrect graph queries",
    )


class PreviousQueryError(BaseModel):
    error_message: str = Field(description="Error message of query result")
    error_graph_query: str = Field(description="The graph query that causes the error")


def _build_graph_query_generation_context_tool(
    engine: Engine,
    graph_id: str,
    example_store: Optional[ExampleStore] = None,
    num_gql_examples: int = 3,
):

    def get_graph_query_generation_context(
        user_query: str,
        previous_query_error: Optional[PreviousQueryError] = None,
    ) -> QueryGenerationContext:
        """
        Retrieves contextual information that are necessary to generate the
        correct graph queries for given `user_query`.

        `previous_query_error` describes the last attempt query execution
        failure when ran the generated graph query. This is helpful during query
        generation try by retrieving examples on how to fix incorrect graph queries.
        """
        if isinstance(previous_query_error, dict):
            previous_query_error = PreviousQueryError(**previous_query_error)
        information_schema = InformationSchema(engine)
        graph_schema = information_schema.get_property_graph(graph_id)
        assert graph_schema is not None
        context = QueryGenerationContext(graph_schema=graph_schema.to_descriptor())
        if example_store:
            context.query_examples = example_store.get_example_queries(
                user_query,
                graph_schema,
                k=num_gql_examples,
            )
        if previous_query_error and example_store:
            context.query_fix_examples = example_store.get_example_fix_queries(
                previous_query_error.error_message,
                previous_query_error.error_graph_query,
                graph_schema,
                k=num_gql_examples,
            )
        return context

    return get_graph_query_generation_context


class GraphQueryGenerationContextTool(FunctionTool):

    def __init__(
        self,
        engine: Engine,
        graph_id: str,
        example_store: Optional[ExampleStore] = None,
        num_gql_examples: int = 3,
    ):
        super().__init__(
            _build_graph_query_generation_context_tool(
                engine, graph_id, example_store, num_gql_examples=num_gql_examples
            )
        )
