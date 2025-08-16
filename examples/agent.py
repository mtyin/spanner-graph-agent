import os
from dotenv import load_dotenv
from spanner_graph_agent import SpannerGraphQueryAgent

# Load environment variables from .env
load_dotenv()

# root_agent = SpannerGraphQueryAgent(
#     instance_id=os.environ["GOOGLE_SPANNER_INSTANCE"],
#     database_id=os.environ["GOOGLE_SPANNER_DATABASE"],
#     graph_id=os.environ["GOOGLE_SPANNER_GRAPH"],
#     model="gemini-2.5-flash",
#     project_id=os.environ.get("GOOGLE_CLOUD_PROJECT", None),
#     agent_config={
#         "example_table": "gql_examples",
#         "embedding": "text-embedding-004",
#         "verify_gql": False,
#         "log_level": "DEBUG",
#     },
# )


# async def main():
#   from spanner_graph_agent.utils.agent_session import AgentSession
#   import uuid

#   user_id = str(uuid.uuid4())
#   with AgentSession(agent=root_agent, user_id=user_id) as session:
#     response = await session.ainvoke("How many nodes in the graph?")
#     if response:
#       print(response.content.parts[0].text)


# if __name__ == "__main__":
#   import asyncio

#   asyncio.run(main())


from spanner_graph_agent import GraphAgent

root_agent = GraphAgent(
    model="gemini-2.0-flash",
)
