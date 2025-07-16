import asyncio
import json
import os
import random
from dotenv import load_dotenv
from google.adk.planners import BuiltInPlanner
from google.cloud import spanner
from google.cloud.spanner_v1 import param_types
from google.genai import types
from spanner_graph_agent import SpannerGraphAgent
from spanner_graph_agent.utils.dataset import Dataset
import yaml

# Load environment variables from .env
load_dotenv()

graph_id = "FinanceGraph"
instance, database, project = (
    os.environ["GOOGLE_SPANNER_INSTANCE"],
    os.environ["GOOGLE_SPANNER_DATABASE"],
    os.environ.get("GOOGLE_CLOUD_PROJECT", None),
)

spanner_db = (
    spanner.Client(project=project).instance(instance).database(database)
)


def query(db, q):
  with db.snapshot() as snapshot:
    rows = snapshot.execute_sql(q)
    return [
        {
            column: value
            for column, value in zip(
                [column.name for column in rows.fields], row
            )
        }
        for row in rows
    ]


dataset = Dataset("finance_data.tar.gz")
# Clean up the database if necessary.
# dataset.cleanup(instance, database, project)
dataset.load(instance, database, project)

sample = query(
    spanner_db,
    """
      GRAPH FinanceGraph
      MATCH (n:Person) -[w:worksAt]-> (c:Company),
            (n) -[o:ownsShare]-> (c),
            (mf:MutualFund) -[:ownsShare]-> (c),
            (n2:Person) -[:ownsShare]-> (c)
      WHERE n != n2
      LIMIT 1
      RETURN n.name AS person_name,
             c.name AS company_name,
             mf.name AS mutual_fund_name,
             w.job_title,
             n.name AS person_name_1,
             n2.name AS person_name_2,
             EXTRACT(YEAR FROM o.release_date) AS year
               """,
)[0]
for param_name, param_type in [
    ("person_name", param_types.STRING),
    ("company_name", param_types.STRING),
    ("mutual_fund_name", param_types.STRING),
    ("job_title", param_types.STRING),
    ("person_name_1", param_types.STRING),
    ("person_name_2", param_types.STRING),
    ("year", param_types.INT64),
]:
  print(
      f"Register parameter: {param_name}={repr(sample[param_name])} with"
      f" type={param_type}"
  )

  def make_provider(n, t):
    return lambda: (sample[n], t)

  dataset.register_parameter_provider(
      param_name, make_provider(n=param_name, t=param_type)
  )

agent = SpannerGraphAgent(
    instance_id=instance,
    database_id=database,
    graph_id=graph_id,
    model="gemini-2.5-flash",
    project_id=project,
    agent_config={
        "example_table": "gql_examples",
        "embedding": "text-embedding-004",
        "verify_gql": False,
        "log_level": None,
        "return_intermediate_steps": False,
    },
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    ),
)


async def evaluate(num_examples: int = 3):
  results = []
  async for topic, result in dataset.evaluate(
      agent, instance, database, project
  ):
    if len(results) > num_examples:
      break
    print(f"========= {topic} ===========")
    print(json.dumps(result, indent=1))
    results.append({"topic": topic, "result": result})

  with open("results", "w") as ofile:
    yaml.dump(results, ofile, default_flow_style=False)


asyncio.run(evaluate())
