import os
from spanner_graph_agent import SpannerGraphAgent

root_agent = SpannerGraphAgent(
    instance_id=os.environ["SPANNER_INSTANCE"],
    database_id=os.environ["SPANNER_DATABASE"],
    graph_id=os.environ["SPANNER_GRAPH"],
    model="gemini-2.5-flash",
    project_id=os.environ["GCP_PROJECT"],
    agent_config={
        "example_table": "gql_examples",
        "embedding": "text-embedding-004",
        "verify_gql": False,
        "verbose": True,
        "return_intermediate_steps": True,
    },
)

if __name__ == "__main__":
  from spanner_graph_agent.utils.agent_session import AgentSession
  import asyncio
  import uuid
  from dotenv import load_dotenv

  # Load environment variables from .env
  load_dotenv()

  user_id = str(uuid.uuid4())
  with AgentSession(agent=root_agent, user_id=user_id) as session:
    response = asyncio.run(session.ainvoke("How many nodes in the graph?"))
    if response:
      print(response.content.parts[0].text)
