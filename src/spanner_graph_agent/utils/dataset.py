import logging
import os
import shutil
import tarfile
import tempfile
from typing import Optional
from google.cloud import spanner
from google.cloud.spanner_v1.database import Database
import pandas as pd

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
          tar.extractall(self._temp_dir)
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
