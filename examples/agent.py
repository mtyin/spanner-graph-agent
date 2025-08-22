# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from dotenv import load_dotenv

from graph_agents import SpannerGraphQueryAgent

# Load environment variables from .env
# load_dotenv()

# root_agent = SpannerGraphQueryAgent(
#     instance_id=os.environ["GOOGLE_SPANNER_INSTANCE"],
#     database_id=os.environ["GOOGLE_SPANNER_DATABASE"],
#     graph_id=os.environ["GOOGLE_SPANNER_GRAPH"],
#     model="gemini-2.5-flash",
#     project_id=os.environ.get("GOOGLE_CLOUD_PROJECT", None),
#     agent_config={
#         "example_table": "gql_examples",
#         "embedding_model": "text-embedding-004",
#         "log_level": "DEBUG",
#     },
# )


# async def main():
#     import uuid

#     from graph_agents.utils.agent_session import AgentSession

#     user_id = str(uuid.uuid4())
#     with AgentSession(agent=root_agent, user_id=user_id) as session:
#         response = await session.ainvoke("How many nodes in the graph?")
#         if response:
#             print(response.content.parts[0].text)


# if __name__ == "__main__":
#     import asyncio

#     asyncio.run(main())


from graph_agents import GraphAgent

root_agent = GraphAgent(
    model="gemini-2.5-flash",
)
