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

from google.adk.agents import LlmAgent

from graph_agents.instructions.prompts import get_prompt


class GraphLogicalSchemaModellingAgent(LlmAgent):
    """An interactive agent for creating logical graph schemas from natural language.

    This agent manages a conversational workflow to help users design a logical
    graph schema. It translates ambiguous user requests into a structured JSON
    format (`graph_topology`) that defines the nodes, edges, and properties of a
    graph.

    The agent is designed to be fully interactive, guiding the user through the
    modeling process with the following workflow:

    Workflow:
        1.  **Assess Clarity:** Initially determines if a user's request is
            detailed enough to create a schema or if it's too vague.
        2.  **Clarify Ambiguity:** If the request is vague (e.g., "Model a
            financial graph"), it engages the user with targeted questions
            to identify the core entities (nodes) and their relationships
            (edges).
        3.  **Generate & Confirm:** Once enough detail is gathered, it produces
            a JSON representation of the logical schema and asks for the user's
            confirmation. It handles revision requests in a conversational
            loop until the user approves the final schema.

    Primary Input:
        - Natural language text from a user.

    Primary Output:
        - A `graph_topology` JSON object followed by a confirmation prompt.
    """

    def __init__(
        self,
        model: str,
    ):
        super().__init__(
            model=model,
            name="GraphLogicalSchemaModellingAgent",
            description="GraphLogicalSchemaModellingAgent",
            instruction=get_prompt("GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_INSTRUCTIONS"),
            tools=[],
        )


class SpannerGraphSchemaGenerationAgent(LlmAgent):
    """A non-interactive agent for generating Spanner Graph DDL from a logical schema.

    This agent acts as a specialized compiler, translating a logical graph
    schema, defined in a `graph_topology` JSON format, into a physical
    schema of executable DDL for Google Cloud Spanner Graph.

    It is designed to be a non-interactive, final step in the schema
    creation pipeline, operating solely on its structured JSON input. The
    agent follows a strict, two-step process:

    Workflow:
        1.  **Validate Input:** The agent's first action is to strictly
            validate that the input is a JSON object conforming to the
            expected `graph_topology` structure. It will reject any
            other input type, including natural language or malformed
            JSON, with a specific error message.
        2.  **Translate to DDL:** Upon successful validation, it systematically
            converts the logical model into physical DDL. This includes
            generating `CREATE TABLE` statements for nodes and edges, and a
            final `CREATE PROPERTY GRAPH` statement to define the graph
            semantics on Spanner.

    Primary Input:
        - A single `graph_topology` JSON object.

    Primary Output:
        - A single string containing the complete Spanner Graph DDL.
    """

    def __init__(
        self,
        model: str,
    ):
        super().__init__(
            model=model,
            name="SpannerGraphSchemaGenerationAgent",
            description="SpannerGraphSchemaGenerationAgent",
            instruction=get_prompt(
                "SPANNER_GRAPH_SCHEMA_GENERATION_AGENT_INSTRUCTIONS"
            ),
            tools=[],
        )


class TableToGraphLogicalSchemaModellingAgent(LlmAgent):

    def __init__(
        self,
        model: str,
    ):
        super().__init__(
            model=model,
            name="TableToGraphLogicalSchemaModellingAgent",
            description=get_prompt(
                "TABLE_TO_GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_DESCRIPTION"
            ),
            instruction=get_prompt(
                "TABLE_TO_GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_INSTRUCTIONS"
            ),
            tools=[],
        )


class NewGraphModellingAgent(LlmAgent):
    """An orchestrator agent that manages the end-to-end graph schema creation workflow.

    This agent acts as a high-level controller for a two-phase graph schema
    creation process. It coordinates the workflow between two specialized sub-agents:
    one for interactive logical modeling and another for automated physical
    schema generation.

    The agent's primary responsibility is to manage the conversation state and
    the handoff between these two phases, ensuring a seamless user experience
    from a natural language request to the final, executable DDL.

    ## Workflow

    The agent operates in two distinct phases:

    1.  **Logical Schema Modeling**: Upon receiving a user's initial request,
        this agent delegates the conversation to the
        `GraphLogicalSchemaModellingAgent`. It then silently monitors the
        interaction until the user explicitly confirms that the generated
        logical schema (JSON) is correct.

    2.  **Physical Schema Generation**: Once the user confirms the logical schema,
        this agent takes control. It retrieves the confirmed JSON and invokes the
        `SpannerGraphSchemaGenerationAgent` to produce the final Spanner Graph DDL,
        which it then presents to the user.

    ## Sub-Agents Managed

    - `GraphLogicalSchemaModellingAgent`: Handles the interactive, natural
      language-to-JSON logical modeling.
    - `SpannerGraphSchemaGenerationAgent`: Handles the non-interactive,
      JSON-to-DDL physical schema generation.
    """

    def __init__(
        self,
        model: str,
    ):
        super().__init__(
            model=model,
            name="NewGraphModellingAgent",
            description=get_prompt("NEW_GRAPH_MODELLING_AGENT_DESCRIPTION"),
            instruction=get_prompt("NEW_GRAPH_MODELLING_AGENT_INSTRUCTIONS"),
            tools=[],
            sub_agents=[
                GraphLogicalSchemaModellingAgent(model),
                SpannerGraphSchemaGenerationAgent(model),
            ],
        )


class GraphModellingAgent(LlmAgent):

    def __init__(
        self,
        model: str,
    ):
        super().__init__(
            model=model,
            name="GraphModellingAgent",
            description=get_prompt("GRAPH_MODELLING_AGENT_DESCRIPTION"),
            instruction=get_prompt("GRAPH_MODELLING_AGENT_INSTRUCTIONS"),
            tools=[],
            sub_agents=[
                NewGraphModellingAgent(model),
                TableToGraphLogicalSchemaModellingAgent(model),
            ],
        )
