import asyncio
import logging
import os
import shutil
import string
import tarfile
import tempfile
from typing import Any, Callable, Dict, List, Optional, Tuple

from google.adk.agents import BaseAgent
from google.cloud import spanner
from google.cloud.spanner_v1.database import Database
import pandas as pd
from spanner_graph_agent.utils.agent_session import AgentSession
import yaml

logger = logging.getLogger("spanner_graph_agent." + __name__)


class Dataset(object):
  """Loads a directory of csv files (or a gzip compressed file of such directory)

  to Spanner.

  The directory has the following structure:
    schema.ddl
    nodes/
      NodeA.csv
      NodeB.csv
    edges/
      EdgeA.csv
      EdgeB.csv
  """

  def __init__(self, path, delimiter: str = ","):
    self.path = path
    self.delimiter = delimiter
    self._is_compressed = self.path.endswith(".tar.gz")
    self._temp_dir = None
    self.parameter_providers = {}

  def is_compressed(self) -> bool:
    return self._is_compressed

  def get_schema(self) -> str:
    if self.is_compressed():
      with tarfile.open(self.path, "r:gz") as tar:
        schema_file = tar.extractfile("./schema.ddl")
        return schema_file.read().decode("utf-8")
    else:
      with open(os.path.join(self.path, "schema.ddl"), "r") as f:
        return f.read()

  def load(
      self,
      instance: str,
      database: str,
      project: Optional[str] = None,
      max_batch_size: int = 10000,
  ):
    logger.info(f"starting to load dataset from {self.path}")
    spanner_client = spanner.Client(project=project)
    instance = spanner_client.instance(instance)
    database = instance.database(database)

    logger.info("applying ddl from schema.ddl")
    ddl_statements = [
        statement.strip()
        for statement in self.get_schema().split(";")
        if statement.strip()
    ]
    if ddl_statements:
      operation = database.update_ddl(ddl_statements)
      operation.result()  # Wait for completion
    logger.info("finished applying ddl from schema.ddl")

    logger.info("loading nodes")
    self._load_nodes(database, max_batch_size)
    logger.info("finished loading nodes")

    logger.info("loading edges")
    self._load_edges(database, max_batch_size)
    logger.info("finished loading edges")
    logger.info(f"finished loading dataset from {self.path}")

  def _load_nodes(self, database: Database, max_batch_size: int):
    data_path = self._get_data_path("nodes")
    for file_name in os.listdir(data_path):
      if file_name.endswith(".csv"):
        table_name = os.path.splitext(file_name)[0]
        logger.info(f"loading nodes from {file_name} into table {table_name}")
        df = pd.read_csv(
            os.path.join(data_path, file_name), delimiter=self.delimiter
        )
        self._insert_data(database, table_name, df, max_batch_size)

  def _load_edges(self, database: Database, max_batch_size: int):
    data_path = self._get_data_path("edges")
    for file_name in os.listdir(data_path):
      if file_name.endswith(".csv"):
        table_name = os.path.splitext(file_name)[0]
        logger.info(f"loading edges from {file_name} into table {table_name}")
        df = pd.read_csv(
            os.path.join(data_path, file_name), delimiter=self.delimiter
        )
        self._insert_data(database, table_name, df, max_batch_size)

  def cleanup(
      self,
      instance: str,
      database: str,
      project: Optional[str] = None,
  ):
    logger.info(f"starting to cleanup dataset from {self.path}")
    spanner_client = spanner.Client(project=project)
    instance_obj = spanner_client.instance(instance)
    database_obj = instance_obj.database(database)

    logger.info("deleting edges")
    self._delete_all_rows(database_obj, "edges")
    logger.info("finished deleting edges")

    logger.info("deleting nodes")
    self._delete_all_rows(database_obj, "nodes")
    logger.info("finished deleting nodes")

    if self.is_compressed() and self._temp_dir is not None:
      shutil.rmtree(self._temp_dir)
      self._temp_dir = None

    logger.info(f"finished cleaning up dataset from {self.path}")

  def _delete_all_rows(self, database: Database, component: str):
    data_path = self._get_data_path(component)
    for file_name in os.listdir(data_path):
      if file_name.endswith(".csv"):
        table_name = os.path.splitext(file_name)[0]
        logger.info(f"deleting all rows from table {table_name}")
        with database.batch() as batch:
          batch.delete(table=table_name, keyset=spanner.KeySet(all_=True))

  def _get_data_path(self, component: str) -> str:
    if self.is_compressed():
      if self._temp_dir is None:
        self._temp_dir = tempfile.mkdtemp()
        with tarfile.open(self.path, "r:gz") as tar:
          tar.extractall(self._temp_dir, filter="tar")
      return os.path.join(self._temp_dir, component)
    else:
      return os.path.join(self.path, component)

  def _insert_data(
      self,
      database: Database,
      table_name: str,
      df: pd.DataFrame,
      max_batch_size: int,
  ):
    logger.info(f"inserting {len(df)} rows into {table_name}")
    for start in range(0, len(df), max_batch_size):
      end = min(start + max_batch_size, len(df))
      logger.info(f"inserting rows {start} to {end} into {table_name}")
      with database.batch() as batch:
        batch.insert_or_update(
            table=table_name,
            columns=df.columns.tolist(),
            values=df.iloc[start:end].values.tolist(),
        )

  def register_parameter_provider(
      self, name: str, provider: Callable[[], Tuple[Any, Any]]
  ):
    self.parameter_providers[name] = provider

  def instantiate_parameters(self, question_template: str) -> str:
    params = {}
    param_types = {}
    for _, param_name, _, _ in string.Formatter().parse(question_template):
      if not param_name:
        continue
      provider = self.parameter_providers.get(param_name)
      if provider is None:
        raise ValueError(f"Unable to provider param with name `{param_name}`")
      params[param_name], param_types[param_name] = provider()
    return params, param_types

  def load_evalution_templates(self) -> Dict[str, List[List[str]]]:
    return self._load_yaml_file("./evaluation/templates.yaml")

  def _load_yaml_file(self, file_path: str) -> Dict[str, Any]:
    if self.is_compressed():
      with tarfile.open(self.path, "r:gz") as tar:
        template_file = tar.extractfile(file_path)
        return yaml.safe_load(template_file)
    else:
      with open(os.path.join(self.path, file_path), "r") as f:
        return yaml.safe_load(f)

  async def get_agent_answers(
      self, agent: BaseAgent, questions: List[str]
  ) -> List[Any]:
    agent_answers = []
    for question in questions:
      with AgentSession(agent, user_id="evalution") as session:
        event = await session.ainvoke(question)
        answer = "n/a"
        if event and event.content and event.content.parts:
          answer = "".join((part.text or "" for part in event.content.parts))
        agent_answers.append({
            "question": question,
            "answer": answer,
        })
    return agent_answers

  async def get_answer(
      self,
      database: Database,
      answer_query_template: str,
      params: Dict[str, Any],
      param_types: Dict[str, Any],
  ) -> Any:
    if not answer_query_template:
      return []

    def _query():
      with database.snapshot() as snapshot:
        rows = snapshot.execute_sql(
            answer_query_template,
            params=params,
            param_types=param_types,
        )
        return [
            {
                column: value
                for column, value in zip(
                    [column.name for column in rows.fields], row
                )
            }
            for row in rows
        ]

    return await asyncio.to_thread(_query)

  async def evaluate_qa(
      self,
      agent: BaseAgent,
      database: Database,
      question_templates: List[str],
      answer_query_template: Optional[str],
  ) -> Dict:
    params, param_types = self.instantiate_parameters(question_templates[0])
    questions = [q.format_map(params) for q in question_templates]
    result = {}
    if answer_query_template:
      result["reference_answer"] = await self.get_answer(
          database, answer_query_template, params, param_types
      )
    result["agent_answers"] = await self.get_agent_answers(agent, questions)
    return result

  def validate_param_providers(self, all_templates):
    validated_params = set()
    for templates in all_templates.values():
      for template in templates:
        questions = template.get("Questions", [])
        for question in questions:
          for _, param_name, _, _ in string.Formatter().parse(question):
            if param_name is None:
              continue
            if param_name in validated_params:
              continue
            if param_name not in self.parameter_providers:
              raise ValueError(f"Missing param provider for `{param_name}`")
            validated_params.add(param_name)
    return validated_params

  async def evaluate(
      self,
      agent: BaseAgent,
      instance: str,
      database: str,
      project: Optional[str] = None,
  ):
    all_templates = self.load_evalution_templates()
    spanner_client = spanner.Client(project=project)
    instance = spanner_client.instance(instance)
    database = instance.database(database)

    self.validate_param_providers(all_templates)
    return {
        topic: await self.evaluate_qa(
            agent,
            database,
            template.get("Questions", []),
            template.get("Answer", None),
        )
        for topic, templates in all_templates.items()
        for template in templates
    }


if __name__ == "__main__":
  import os
  import yaml
  import asyncio
  from spanner_graph_agent import SpannerGraphAgent
  from google.cloud.spanner_v1 import param_types

  instance, database, project = (
      os.environ["GOOGLE_SPANNER_INSTANCE"],
      os.environ["GOOGLE_SPANNER_DATABASE"],
      os.environ.get("GOOGLE_CLOUD_PROJECT", None),
  )
  agent = SpannerGraphAgent(
      instance_id=instance,
      database_id=database,
      graph_id=os.environ["GOOGLE_SPANNER_GRAPH"],
      model="gemini-2.5-flash",
      project_id=project,
      agent_config={
          "example_table": "gql_examples",
          "embedding": "text-embedding-004",
          "verify_gql": False,
          "verbose": False,
          "return_intermediate_steps": False,
      },
  )
  dataset = Dataset("../../../datasets/finance/finance_data.tar.gz")
  dataset.cleanup(instance, database, project)
  dataset.load(instance, database, project)
  dataset.register_parameter_provider(
      "person_name", lambda: ("Dale Reeves", param_types.STRING)
  )
  dataset.register_parameter_provider(
      "company_name", lambda: ("Bauer-Guerrero", param_types.STRING)
  )
  dataset.register_parameter_provider(
      "mutual_fund_name", lambda: ("Option Spring Fund", param_types.STRING)
  )
  dataset.register_parameter_provider(
      "job_title", lambda: ("Engineer, production", param_types.STRING)
  )
  dataset.register_parameter_provider(
      "person_name_1", lambda: ("Dale Reeves", param_types.STRING)
  )
  dataset.register_parameter_provider(
      "person_name_2", lambda: ("Tina Chambers", param_types.STRING)
  )
  results = asyncio.run(dataset.evaluate(agent, instance, database, project))
  with open("results", "w") as ofile:
    yaml.dump(results, ofile, default_flow_style=False)
