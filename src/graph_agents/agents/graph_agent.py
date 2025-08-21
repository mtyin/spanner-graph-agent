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

import functools
from typing import Optional

from google.adk.agents import LlmAgent

from graph_agents.agents.model import GraphModellingAgent
from graph_agents.agents.query.spanner import SpannerGraphQueryAgent
from graph_agents.instructions.prompts import get_prompt


class GraphAgent(LlmAgent):
    """A root agent that triages and dispatches graph-related user requests.

    This agent serves as the central entry point for a suite of specialized graph
    agents operating on Google Cloud's Spanner Graph. Its primary responsibility
    is not to answer questions directly, but to analyze incoming user requests,
    determine their relevance to graph operations, and route them to the
    appropriate sub-agent for execution.

    ---
    ## Core Workflow

    The agent follows a strict **Triage and Dispatch** model:

    1.  **Triage for Relevance**: It first assesses whether a user's query is
        related to graph concepts (e.g., networks, connections, paths). If the
        query is out of scope (like asking for the weather), it declines the request.
    2.  **Dispatch to Sub-Agent**: For valid graph-related requests, it identifies
        the user's primary intent and dispatches the task to a specialized sub-agent.
    ---
    ## Sub-Agents Managed

    - `GraphModelingAgent`: Handles all requests related to designing, creating, or
    modifying the graph's **schema**.
    - `GraphQueryAgent`: Handles all requests for retrieving, counting, or asking
    questions about the **data** within the graph. When a query agent is not found,
    you can first use the tool to build a query agent that talks to a specific graph.
    """

    def __init__(
        self,
        model: str,
    ):
        super().__init__(
            model=model,
            name="GraphAgent",
            description=get_prompt("GRAPH_AGENT_DESCRIPTION"),
            instruction=get_prompt("GRAPH_AGENT_INSTRUCTIONS"),
            tools=[self.add_sub_agent(SpannerGraphQueryAgent.create_query_agent)],
            sub_agents=[GraphModellingAgent(model)],
        )

    def add_sub_agent(self, agent_factory):
        """
        Add or replace a new sub agent constructed by `agent_factory`.
        """

        @functools.wraps(agent_factory)
        def _add_sub_agent(*args, **kwargs):
            kwargs.setdefault("parent_agent", self)
            new_sub_agent = agent_factory(*args, **kwargs)
            sub_agents = []
            for sub_agent in self.sub_agents:
                if sub_agent.name == new_sub_agent.name:
                    # Replace existing agent with the same name.
                    sub_agents.append(new_sub_agent)
                    new_sub_agent = None
                else:
                    # Add back the existing sub agent.
                    sub_agents.append(sub_agent)

            if new_sub_agent is not None:
                # Add the new sub agent.
                sub_agents.append(new_sub_agent)
            self.sub_agents = sub_agents

        return _add_sub_agent
