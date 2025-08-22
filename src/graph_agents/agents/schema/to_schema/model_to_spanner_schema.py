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

class Model2SpannerSchemaAgent(LlmAgent):
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
            name="Model2SpannerSchemaAgent",
            description="An agent that translates a graph model, provided in a specific JSON format, into a Spanner Graph schema.",
            instruction=get_prompt("model_to_spanner_schema"),
            tools=[],
        )