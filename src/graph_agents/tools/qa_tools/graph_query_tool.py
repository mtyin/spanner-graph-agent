import logging
from typing import Any, Optional, Union

from google.adk.tools import BaseTool, ToolContext
from google.cloud import spanner
from google.cloud.spanner_v1.database import Database
from google.genai import types
from langchain_community.graphs.graph_store import GraphStore
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseLanguageModel
from langchain_core.vectorstores import VectorStore
from langchain_google_spanner import (
    SpannerGraphQAChain,
    SpannerGraphStore,
    SpannerVectorStore,
    TableColumn,
)
from typing_extensions import override

from graph_agents.utils.prompts import (
    DEFAULT_GQL_EXAMPLE_TEMPLATE,
    DEFAULT_GQL_FIX_TEMPLATE_PART2,
    DEFAULT_GQL_FIX_TEMPLATE_WITH_EXAMPLE_PREFIX,
    DEFAULT_GQL_GENERATION_WITH_EXAMPLE_PREFIX,
    DEFAULT_GQL_TEMPLATE_PART1,
)

logger = logging.getLogger("graph_agents." + __name__)


class SpannerGraphQueryQATool(BaseTool):

    def __init__(
        self,
        database: Database,
        graph_id: str,
        llm: Union[str, BaseLanguageModel],
        description: str,
        tool_config: dict[str, Any] = {},
    ):
        super().__init__(
            name="SpannerGraphQueryQATool",
            description=description,
        )
        config = tool_config.copy()
        config["database"] = database
        self.graph_store = SpannerGraphStore(
            instance_id=database._instance.instance_id,
            database_id=database.database_id,
            graph_name=graph_id,
            client=database._instance._client,
        )
        self.llm = self.get_llm(llm, config)
        self.example_store = self.get_example_store(config)
        self.qa_chain = self.get_qa_chain(
            self.graph_store,
            self.llm,
            self.example_store,
            config,
        )

    @staticmethod
    def get_llm(
        llm: Union[str, BaseLanguageModel], tool_config: dict[str, Any] = {}
    ) -> BaseLanguageModel:
        if isinstance(llm, str):
            from langchain_google_vertexai import ChatVertexAI

            return ChatVertexAI(model=llm)
        return llm

    @staticmethod
    def get_embedding_service(
        tool_config: dict[str, Any] = {},
    ) -> Optional[Embeddings]:
        embedding = tool_config.get("embedding", None)

        if isinstance(embedding, str):
            from langchain_google_vertexai.embeddings import VertexAIEmbeddings

            return VertexAIEmbeddings(model_name=embedding)

        return embedding

    @staticmethod
    def get_example_store(
        tool_config: dict[str, Any] = {},
    ) -> Optional[VectorStore]:
        spanner_example_table = tool_config.get("example_table", None)
        if isinstance(spanner_example_table, str):

            database = tool_config["database"]
            database_id = database.database_id
            instance_id = database._instance.instance_id
            client = database._instance._client
            SpannerVectorStore.init_vector_store_table(
                instance_id,
                database_id,
                spanner_example_table,
                content_column="user_query",
                client=client,
                metadata_columns=[
                    TableColumn(name="example", type="JSON"),
                ],
            )
            return SpannerVectorStore(
                instance_id,
                database_id,
                table_name=spanner_example_table,
                content_column="user_query",
                embedding_service=SpannerGraphQueryQATool.get_embedding_service(
                    tool_config
                ),
                metadata_json_column="example",
                client=client,
            )
        return None

    @staticmethod
    def get_qa_chain(
        graph_store: GraphStore,
        llm: BaseLanguageModel,
        example_store: Optional[VectorStore],
        tool_config: dict[str, Any],
    ):
        gql_prompt = None
        gql_fix_prompt = None
        if example_store is not None:
            from langchain_core.example_selectors import (
                MaxMarginalRelevanceExampleSelector,
            )
            from langchain_core.prompts import FewShotPromptTemplate
            from langchain_core.prompts.prompt import PromptTemplate

            example_selector = MaxMarginalRelevanceExampleSelector(
                vectorstore=example_store,
                k=tool_config.get("num_gql_examples", 3),
            )

            gql_generation_instruction_prompt = DEFAULT_GQL_TEMPLATE_PART1
            gql_fix_instruction_prompt = DEFAULT_GQL_FIX_TEMPLATE_PART2
            gql_prompt = FewShotPromptTemplate(
                example_selector=example_selector,
                example_prompt=PromptTemplate.from_template(
                    DEFAULT_GQL_EXAMPLE_TEMPLATE
                ),
                prefix=DEFAULT_GQL_GENERATION_WITH_EXAMPLE_PREFIX,
                suffix=gql_generation_instruction_prompt,
                input_variables=["user_query", "schema"],
            )

            gql_fix_prompt = FewShotPromptTemplate(
                example_selector=example_selector,
                example_prompt=PromptTemplate.from_template(
                    DEFAULT_GQL_EXAMPLE_TEMPLATE
                ),
                prefix=DEFAULT_GQL_FIX_TEMPLATE_WITH_EXAMPLE_PREFIX,
                suffix=gql_fix_instruction_prompt,
                input_variables=[
                    "user_query",
                    "generated_gql",
                    "err_msg",
                    "schema",
                ],
            )

        tool_config.setdefault("num_gql_fix_retries", 3)
        tool_config.setdefault("top_k", 100)
        return SpannerGraphQAChain.from_llm(
            llm,
            graph=graph_store,
            gql_prompt=gql_prompt,
            gql_fix_prompt=gql_fix_prompt,
            allow_dangerous_requests=True,
            **tool_config,
        )

    async def run_async(
        self, *, args: dict[str, Any], tool_context: ToolContext
    ) -> Any:
        try:
            user_query = args["user_query"]
            chain_input = {self.qa_chain.input_key: user_query}
            logger.debug(f"Input query: `{user_query}`")
            results = await self.qa_chain.ainvoke(chain_input)
            if self.qa_chain.output_key != "result":
                results["result"] = results[self.qa_chain.output_key]
                del results[self.qa_chain.output_key]
            return results
        except Exception as e:
            logger.error(f"Failed QA chain invocation: {e}")
            return {"result": f"I don't know due to the following error: `{e}`"}

    def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
        return types.FunctionDeclaration(
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "user_query": types.Schema(
                        type=types.Type.STRING,
                        description="User query",
                    ),
                },
                required=["user_query"],
            ),
            response=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "result": types.Schema(
                        type=types.Type.STRING,
                    ),
                },
                required=["result"],
            ),
            name=self.name,
            description=self.description,
        )

    def add_example(self, user_query: str, gql: str, schema: str = ""):
        if self.example_store is None:
            raise ValueError("No example store configured")

        self.example_store.add_texts(
            texts=[user_query],
            metadatas=[
                {
                    "question": user_query,
                    "gql": gql.replace("{", "{{").replace("}", "}}"),
                    "schema": schema,
                }
            ],
        )
