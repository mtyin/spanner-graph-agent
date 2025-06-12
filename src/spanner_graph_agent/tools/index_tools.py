import asyncio
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Union
from google.adk.tools import FunctionTool, ToolContext
from google.cloud import spanner
from google.cloud.spanner_v1.database import Database
from google.genai import types
from pydantic import BaseModel, Field, create_model
from spanner_graph_agent.utils.information_schema import Column, Index
from typing_extensions import override

logger = logging.getLogger('spanner_graph_agent.' + __name__)


# column AS alias
class ColumnWithAlias(BaseModel):
  column: Column
  alias: str


# search_function(tokenlist_column, @{tokenized_column.alias})
# score_function(tokenlist_column, @{tokenized_column.alias})
class SearchCriteria(BaseModel):
  tokenlist_column: Column
  tokenized_column: ColumnWithAlias
  search_function: str
  score_function: str


def _build_full_text_search_query(
    table_name: str,
    search_criterias: List[SearchCriteria],
    partition_columns: List[ColumnWithAlias],
    index_filter_expr: Optional[str],
    canonical_reference_columns: List[ColumnWithAlias],
) -> str:
  canonical_reference_aliases = ', '.join((
      col.column.name + ' AS ' + col.alias
      for col in canonical_reference_columns
  ))
  filter_conditions = [
      ''.join((
          criteria.search_function,
          '(',
          criteria.tokenlist_column.name,
          ', ',
          '@',
          criteria.tokenized_column.alias,
          ')',
      ))
      for criteria in search_criterias
  ]
  filter_conditions.extend([
      ''.join((col.column.name, ' = ', '@', col.alias))
      for col in partition_columns
  ])
  if index_filter_expr:
    filter_conditions.append(index_filter_expr)

  score_expr = ', '.join([
      # score_function(tokenlist_column, @tokenized_column.alias)
      # +
      # if(tokenized_column = @tokenized_column.alias, 1, 0)
      ''.join((
          criteria.score_function,
          '(',
          criteria.tokenlist_column.name,
          ', ',
          '@',
          criteria.tokenized_column.alias,
          ')',
          ' + ',
          'IF(',
          criteria.tokenized_column.column.name,
          '=',
          '@',
          criteria.tokenized_column.alias,
          ', 1., 0.)',
      ))
      for criteria in search_criterias
  ])
  filter_expr = ' AND '.join(filter_conditions)
  return f"""
    SELECT {canonical_reference_aliases}
    FROM {table_name}
    WHERE {filter_expr}
    ORDER BY {score_expr} DESC
    LIMIT 1
  """


def _build_example_query(
    table_name: str,
    search_criterias: List[SearchCriteria],
    partition_columns: List[ColumnWithAlias],
    index_filter_expr: Optional[str],
    canonical_reference_columns: List[ColumnWithAlias],
) -> str:
  example_aliases = ', '.join([
      col.column.name + ' AS ' + col.alias
      for col in (
          canonical_reference_columns
          + partition_columns
          + [criteria.tokenized_column for criteria in search_criterias]
      )
  ])
  filter_conditions = [
      ''.join((criteria.tokenized_column.column.name, ' IS NOT NULL'))
      for criteria in search_criterias
  ]
  if index_filter_expr:
    filter_conditions.append(index_filter_expr)
  filter_expr = ' AND '.join(filter_conditions)
  return f"""
    SELECT {example_aliases}
    FROM {table_name}
    TABLESAMPLE RESERVOIR (1 ROWS)
    WHERE {filter_expr}
  """


def _get_python_type_from_spanner_type(spanner_type: str):
  if spanner_type.startswith('STRING'):
    return str
  if spanner_type.startswith('BYTES'):
    return bytes
  if spanner_type in ['INT32', 'INT64']:
    return int
  if spanner_type in ['FLOAT32', 'FLOAT64', 'DOUBLE']:
    return float

  array_prefix, array_suffix = 'ARRAY<', '>'
  if spanner_type.startswith(array_prefix) and spanner_type.endswith(
      array_suffix
  ):
    return _get_python_type_from_spanner_type(
        spanner_type[len(array_prefix) : -len(array_suffix)]
    )
  return None


def _get_spanner_param_type_from_value(v: Any):
  if isinstance(v, str):
    return spanner.param_types.STRING
  if isinstance(v, bytes):
    return spanner.param_types.BYTES
  if isinstance(v, int):
    return spanner.param_types.INT64
  if isinstance(v, float):
    return spanner.param_types.FLOAT64
  return None


def _create_model(
    model_name: str,
    columns: List[ColumnWithAlias],
) -> Optional[BaseModel]:
  fields = {}
  for column in columns:
    t = _get_python_type_from_spanner_type(column.column.type)
    if t is None:
      logger.warning(
          f'Column {column.column.name} of type {column.column.type} is not'
          ' supported'
      )
      return None
    fields[column.alias] = (
        t,
        Field(description=f'{column.alias} of {model_name}'),
    )
  return create_model(model_name, **fields)


def _get_alias(
    name: str, aliases: Optional[Dict[str, str]] = None
) -> Optional[str]:
  if aliases is None:
    return name
  return aliases.get(name.casefold())


def _query(database, query, params=None):
  param_types = (
      {
          field_name: _get_spanner_param_type_from_value(val)
          for field_name, val in params.items()
      }
      if params
      else None
  )
  try:
    with database.snapshot() as snapshot:
      rows = snapshot.execute_sql(query, params=params, param_types=param_types)
      return [
          {
              column: value
              for column, value in zip(
                  [column.name for column in rows.fields], row
              )
          }
          for row in rows
      ]
  except Exception as e:
    logger.error(f'Query failed: `{e}`')
  return []


async def _aquery(database, query, params=None) -> List[Dict[str, Any]]:
  return await asyncio.to_thread(
      _query,
      database,
      query,
      params=params,
  )


def _get_example_reference(
    database, query, reference_model, canonical_reference_model
):
  example_reference, example_canonical_reference = None, None
  values = _query(database, query)
  if not values:
    logger.error('No example found by the query')
    return None, None

  value = values[0]
  try:
    example_reference, example_canonical_reference = (
        reference_model(
            **{name: value[name] for name in reference_model.model_fields}
        ),
        canonical_reference_model(**{
            name: value[name] for name in canonical_reference_model.model_fields
        }),
    )
    return example_reference, example_canonical_reference
  except Exception as e:
    logger.error(f'Failed to build example: `{e}`')
    return None, None


def _get_schema_repr(model):
  schema = model.model_json_schema()
  return '%s(%s)' % (
      schema['title'],
      ', '.join([
          '%s: %s' % (name, info['type'])
          for name, info in schema.get('properties', {}).items()
      ]),
  )


def _build_full_text_search_function_description(
    table_alias,
    input_model,
    output_model,
    input_model_example,
    output_model_example,
):
  reference_repr = _get_schema_repr(input_model)
  canonical_reference_repr = _get_schema_repr(output_model)
  input_fields = {name for name in input_model.model_fields}
  canonicalized_fields = {
      name
      for name in output_model.model_fields
      if name not in input_model.model_fields
  }
  input_fields_name = '_'.join(input_fields)
  canonicalized_fields_name = '_'.join(canonicalized_fields)
  function_name = f'resolve_{table_alias}_{canonicalized_fields_name}_by_{input_fields_name}'
  example_doc = ''
  if input_model_example and output_model_example:
    example_doc = """
    For example,
      Given %s, this tool may return a mapping to %s.
      %s should be used in subsequent queries to the knowledge graph.
    """ % (
        repr(input_model_example),
        repr(output_model_example),
        repr(output_model_example),
    )
  return (
      function_name,
      f"""
    Resolves the canonical {canonicalized_fields} of {table_alias} using given {input_fields}.

    Input: a list of reference in original query represented by {reference_repr};
    Output: a mapping to the corresponding canonical references represented by {canonical_reference_repr}.

    {example_doc}

    This tool convert user-provided references (names, descriptions, titles, etc.)
    into their corresponding canonical identifiers. The output of these tools
    (the canonical ID) must be used in subsequent queries to the knowledge graph.
  """,
  )


def _build_search_criterias(
    tokenlist_cols: List[Column],
    table_cols: Dict[str, Column],
    column_aliases: Optional[Dict[str, str]] = None,
) -> Optional[List[SearchCriteria]]:
  search_criterias = []
  for col in tokenlist_cols:
    if col.expr is None:
      logger.warning(
          f'No expr found for tokenlist column definition: {col.name}'
      )
      return None
    match = re.match(
        r'(tokenize_substring|tokenize_fulltext|tokenize_ngrams)\((\w+)',
        col.expr,
        re.IGNORECASE,
    )
    if match is None:
      logger.warning(f'Tokenlist definition `{col.expr}` is not supported')
      return None

    token_function = match.group(1)
    if token_function.casefold() == 'tokenize_substring':
      search_function = 'search_substring'
      score_function = 'score_ngrams'
    elif token_function.casefold() == 'tokenize_fulltext':
      search_function = 'search'
      score_function = 'score'
    elif token_function.casefold() == 'tokenize_ngrams':
      search_function = 'search_ngrams'
      score_function = 'score_ngrams'
    else:
      logger.warning(f'Token function {token_function} is not supported')
      return None

    tokenized_column_name = match.group(2)
    tokenized_column = table_cols[tokenized_column_name.casefold()]
    alias = _get_alias(tokenized_column_name, column_aliases)
    if alias is None:
      logger.debug(
          f'No alias found for `{tokenized_column_name}` of `{table_alias}'
      )
      return None
    search_criterias.append(
        SearchCriteria(
            tokenlist_column=col,
            tokenized_column=ColumnWithAlias(
                column=tokenized_column, alias=alias
            ),
            search_function=search_function,
            score_function=score_function,
        )
    )
  return search_criterias


def _build_column_with_aliases(
    table_alias: str,
    columns: Optional[List[Union[str, Column]]],
    table_cols: Dict[str, Column],
    column_aliases: Optional[Dict[str, str]] = None,
) -> Optional[List[ColumnWithAlias]]:
  if not columns:
    return []
  column_with_aliases = []
  for column in columns:
    column_name = column if isinstance(column, str) else column.name
    column = table_cols[column_name.casefold()]
    alias = _get_alias(column_name, column_aliases)
    if alias is None:
      logger.debug(f'No alias found for `{column.name}` of `{table_alias}')
      return None
    column_with_aliases.append(
        ColumnWithAlias(
            column=column,
            alias=alias,
        )
    )
  return column_with_aliases


def _build_full_text_search_function(
    database: Database,
    index: Index,
    table_alias: Optional[str] = None,
    column_aliases: Optional[Dict[str, str]] = None,
    include_all_index_fields=False,
) -> Optional[Callable[[BaseModel], BaseModel]]:

  table_alias = table_alias or index.table.name
  tokenlist_cols = [col for col in index.columns if col.type == 'TOKENLIST']
  table_cols = {col.name.casefold(): col for col in index.table.columns}
  search_criterias = _build_search_criterias(
      tokenlist_cols, table_cols, column_aliases
  )

  key_column_with_aliases = _build_column_with_aliases(
      table_alias, index.table.key_columns, table_cols, column_aliases
  )
  if key_column_with_aliases is None:
    return None

  partition_columns_with_aliases = _build_column_with_aliases(
      table_alias, index.search_partition_by, table_cols, column_aliases
  )
  Reference = _create_model(
      f'UserProvided{table_alias}Reference',
      partition_columns_with_aliases
      + [criteria.tokenized_column for criteria in search_criterias],
  )

  if Reference is None:
    logger.warning(
        f'Unable to build UserProvided{table_alias}Reference data model'
    )
    return None
  logger.debug(
      f'Built UserProvided{table_alias}Reference data model:\n'
      + str(Reference.model_json_schema())
      + '\n'
  )

  canonical_reference_fields = key_column_with_aliases
  if include_all_index_fields:
    for col in index.columns:
      if col.type == 'TOKENLIST':
        continue
      alias = _get_alias(col.name, column_aliases)
      if alias is None:
        continue
      canonical_reference_fields.append(
          ColumnWithAlias(column=col, alias=alias)
      )

  canonical_reference_fields = [
      field
      for field in canonical_reference_fields
      if field.alias not in Reference.model_fields
  ]
  CanonicalReference = _create_model(
      f'Canonical{table_alias}Reference', canonical_reference_fields
  )
  if CanonicalReference is None:
    logger.warning(
        f'Unable to build {table_alias}CanonicalReference data model'
    )
    return None
  logger.debug(
      f'Built {table_alias}CanonicalReference data model:\n'
      + str(CanonicalReference.model_json_schema())
      + '\n'
  )

  class ReferenceMapping(BaseModel):

    reference_in_user_query: Reference = Field(
        description=f'A reference of {table_alias} from user input query'
    )
    canonical_reference: CanonicalReference = Field(
        description=(
            f'A canonical reference of {table_alias} in the knowledge graph'
        )
    )

  search_query = _build_full_text_search_query(
      table_name=index.table.name,
      search_criterias=search_criterias,
      partition_columns=partition_columns_with_aliases,
      index_filter_expr=index.filter,
      canonical_reference_columns=canonical_reference_fields,
  )
  logger.debug(f'Built search query:\n\n{search_query}\n\n')

  example_query = _build_example_query(
      table_name=index.table.name,
      search_criterias=search_criterias,
      partition_columns=partition_columns_with_aliases,
      index_filter_expr=index.filter,
      canonical_reference_columns=canonical_reference_fields,
  )
  logger.debug(f'Built example query:\n\n{example_query}\n\n')

  async def resolve_canonical_reference(
      references: List[Reference],
      tool_context: ToolContext,
  ) -> List[ReferenceMapping]:
    try:
      for i in range(len(references)):
        if isinstance(references[i], dict):
          references[i] = Reference(**references[i])
      logger.debug(f'Resolving: {references}...')

      results = []
      for reference in references:
        params = {field_name: ref for field_name, ref in reference}
        values = await _aquery(database, search_query, params=params)
        if values:
          canonical_ref = CanonicalReference(**values[0])
          results.append(
              ReferenceMapping(
                  reference_in_user_query=reference,
                  canonical_reference=canonical_ref,
              )
          )
    except Exception as e:
      logger.error('Failed to find relevant entities: %s' % e)
      results = []

    key = 'temp:reference_mappings'
    if key in tool_context.state:
      tool_context.state[key].extend(results)
    else:
      tool_context.state[key] = results
    logger.debug(f'Resolved reference_mappings: {results}')
    return results

  example_reference, example_canonical_reference = _get_example_reference(
      database, example_query, Reference, CanonicalReference
  )
  fields = '_'.join(Reference.model_fields)
  resolve_canonical_reference.__name__, resolve_canonical_reference.__doc__ = (
      _build_full_text_search_function_description(
          table_alias,
          Reference,
          CanonicalReference,
          example_reference,
          example_canonical_reference,
      )
  )

  return resolve_canonical_reference


class SpannerFullTextSearchTool(FunctionTool):

  @staticmethod
  def build_from_index(
      database: Database,
      index: Index,
      table_alias: Optional[str] = None,
      column_aliases: Optional[Dict[str, str]] = None,
  ) -> Optional[FunctionTool]:
    function = _build_full_text_search_function(
        database, index, table_alias, column_aliases
    )
    if function is None:
      return None
    return SpannerFullTextSearchTool(database, index, function)

  def __init__(self, database: Database, index: Index, function: Callable):
    super().__init__(function)
    self.database = database
    self.index = index

  @override
  def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
    function_decl = super()._get_declaration()
    if function_decl is None:
      return None
    function_decl.description = self.description
    return function_decl
