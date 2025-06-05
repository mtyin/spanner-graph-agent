import logging
from typing import Any, Optional, Union
from google.adk.tools import BaseTool, ToolContext
from google.cloud import spanner
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
from spanner_graph_agent.prompts import (
    DEFAULT_GQL_EXAMPLE_TEMPLATE,
    DEFAULT_GQL_FIX_TEMPLATE_PART2,
    DEFAULT_GQL_FIX_TEMPLATE_WITH_EXAMPLE_PREFIX,
    DEFAULT_GQL_GENERATION_WITH_EXAMPLE_PREFIX,
    DEFAULT_GQL_TEMPLATE_PART1,
)
from typing_extensions import override


class SpannerGraphQueryQATool(BaseTool):

  def __init__(
      self,
      instance_id: str,
      database_id: str,
      graph_id: str,
      llm: Union[str, BaseLanguageModel],
      client: Optional[spanner.Client] = None,
      tool_config: dict[str, Any] = {},
  ):
    super().__init__(
        name='SpannerGraphQueryQATool',
        description=(
            'Answer user query by talking to the knowledge graph stored in'
            ' Spanner Graph.\n\nNOTE: This tool requires canonical references'
            ' for all entities and relationships (if any) mentioned in the user'
            ' query for optimal performance and accurate results. Always ensure'
            ' to use other tools to convert ALL entities AND relationships in'
            ' the user query (if any) to their canonical IDs before using this'
            ' tool.'
        ),
    )
    config = tool_config.copy()
    config['instance_id'] = instance_id
    config['database_id'] = database_id
    config['graph_id'] = graph_id
    config['spanner_client'] = client
    self.graph_store = SpannerGraphStore(
        instance_id=instance_id,
        database_id=database_id,
        graph_name=graph_id,
        client=client,
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
    embedding = tool_config.get('embedding', None)

    if isinstance(embedding, str):
      from langchain_google_vertexai.embeddings import VertexAIEmbeddings

      return VertexAIEmbeddings(model_name=embedding)

    return embedding

  @staticmethod
  def get_example_store(
      tool_config: dict[str, Any] = {},
  ) -> Optional[VectorStore]:
    spanner_example_table = tool_config.get('example_table', None)
    if isinstance(spanner_example_table, str):

      instance_id = tool_config['instance_id']
      database_id = tool_config['database_id']
      spanner_client = tool_config['spanner_client']
      SpannerVectorStore.init_vector_store_table(
          instance_id,
          database_id,
          spanner_example_table,
          content_column='user_query',
          client=spanner_client,
          metadata_columns=[
              TableColumn(name='example', type='JSON'),
          ],
      )
      return SpannerVectorStore(
          tool_config['instance_id'],
          tool_config['database_id'],
          table_name=spanner_example_table,
          content_column='user_query',
          embedding_service=SpannerGraphQueryQATool.get_embedding_service(
              tool_config
          ),
          metadata_json_column='example',
          client=tool_config['spanner_client'],
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
      from langchain_core.example_selectors import MaxMarginalRelevanceExampleSelector
      from langchain_core.prompts import FewShotPromptTemplate
      from langchain_core.prompts.prompt import PromptTemplate

      example_selector = MaxMarginalRelevanceExampleSelector(
          vectorstore=example_store,
          k=tool_config.get('num_gql_examples', 3),
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
          input_variables=['user_query', 'schema'],
      )

      gql_fix_prompt = FewShotPromptTemplate(
          example_selector=example_selector,
          example_prompt=PromptTemplate.from_template(
              DEFAULT_GQL_EXAMPLE_TEMPLATE
          ),
          prefix=DEFAULT_GQL_FIX_TEMPLATE_WITH_EXAMPLE_PREFIX,
          suffix=gql_fix_instruction_prompt,
          input_variables=[
              'user_query',
              'generated_gql',
              'err_msg',
              'schema',
          ],
      )

    tool_config.setdefault('num_gql_fix_retries', 3)
    tool_config.setdefault('top_k', 100)
    return SpannerGraphQAChain.from_llm(
        llm,
        graph=graph_store,
        gql_prompt=gql_prompt,
        gql_fix_prompt=gql_fix_prompt,
        allow_dangerous_requests=True,
        **tool_config,
    )

  @override
  async def run_async(
      self, *, args: dict[str, Any], tool_context: ToolContext
  ) -> dict[str, Any]:
    try:
      user_query = args['user_query']

      state_key = 'temp:reference_mappings'
      if state_key in tool_context.state:
        # TODO: QA agent should support structured context input instead of
        # making the context as part of the query.
        user_query = '\n'.join(
            [user_query, '\nCONTEXT:']
            + [str(rm) for rm in tool_context.state[state_key]]
        )

      chain_input = {self.qa_chain.input_key: user_query}
      results = await self.qa_chain.ainvoke(chain_input)
      if self.qa_chain.output_key != 'result':
        results['result'] = results[self.qa_chain.output_key]
        del results[self.qa_chain.output_key]
      return results
    except Exception as e:
      logging.error(f'Failed QA chain invocation: {e}')
      return {'result': f"I don't know due to the following error: `{e}`"}

  @override
  def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
    return types.FunctionDeclaration(
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                'user_query': types.Schema(
                    type=types.Type.STRING,
                    description='User query',
                ),
            },
            required=['user_query'],
        ),
        response=types.Schema(
            type=types.Type.OBJECT,
            properties={
                'result': types.Schema(
                    type=types.Type.STRING,
                ),
            },
            required=['result'],
        ),
        name=self.name,
        description=self.description,
    )

  def add_example(self, user_query: str, gql: str, schema: str = ''):
    if self.example_store is None:
      raise ValueError('No example store configured')

    self.example_store.add_texts(
        texts=[user_query],
        metadatas=[{
            'question': user_query,
            'gql': gql.replace('{', '{{').replace('}', '}}'),
            'schema': schema,
        }],
    )
