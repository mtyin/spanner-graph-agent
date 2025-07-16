import asyncio
import json
import os
import random
from google.adk.planners import BuiltInPlanner
from google.cloud.spanner_v1 import param_types
from google.genai import types
from spanner_graph_agent import SpannerGraphAgent
from spanner_graph_agent.utils.dataset import Dataset
import yaml

graph_id = "FinanceGraph"
instance, database, project = (
    os.environ["GOOGLE_SPANNER_INSTANCE"],
    os.environ["GOOGLE_SPANNER_DATABASE"],
    os.environ.get("GOOGLE_CLOUD_PROJECT", None),
)

dataset = Dataset("finance_data.tar.gz")
# Clean up the database if necessary.
# dataset.cleanup(instance, database, project)
dataset.load(instance, database, project)
dataset.register_parameter_provider(
    "person_name", lambda: ("Michelle Benton", param_types.STRING)
)
dataset.register_parameter_provider(
    "company_name", lambda: ("Cox LLC", param_types.STRING)
)
dataset.register_parameter_provider(
    "mutual_fund_name", lambda: ("Name Born Fund", param_types.STRING)
)
dataset.register_parameter_provider(
    "job_title", lambda: ("Clinical cytogeneticist", param_types.STRING)
)
dataset.register_parameter_provider(
    "person_name_1", lambda: ("Michelle Benton", param_types.STRING)
)
dataset.register_parameter_provider(
    "person_name_2", lambda: ("Marcus Wilson", param_types.STRING)
)
dataset.register_parameter_provider(
    "year", lambda: (random.choice(range(2022, 2025)), param_types.INT64)
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


async def evaluate(num_examples: int = 10):
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
