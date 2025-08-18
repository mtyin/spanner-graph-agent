from typing import Optional

from google.adk.agents import LlmAgent

from graph_agents.agents.model import GraphModellingAgent
from graph_agents.agents.query import QueryAgentConfig, SpannerGraphQueryAgent
from graph_agents.instructions.prompts import (
    GRAPH_AGENT_DESCRIPTION,
    GRAPH_AGENT_INSTRUCTIONS,
)


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
            description=GRAPH_AGENT_DESCRIPTION,
            instruction=GRAPH_AGENT_INSTRUCTIONS,
            tools=[self._build_spanner_graph_query_agent],
            sub_agents=[GraphModellingAgent(model)],
        )

    def _build_spanner_graph_query_agent(
        self,
        instance_id: str,
        database_id: str,
        graph_id: str,
        model: Optional[str] = None,
        project_id: Optional[str] = None,
        query_agent_config: QueryAgentConfig = QueryAgentConfig(),
    ):
        """
        Builds a query agent with the given configuration.
        """
        query_agent = SpannerGraphQueryAgent(
            instance_id,
            database_id,
            graph_id,
            model or self.model,
            project_id=project_id,
            agent_config=query_agent_config,
        )
        self.sub_agents = [GraphModellingAgent(self.model), query_agent]
