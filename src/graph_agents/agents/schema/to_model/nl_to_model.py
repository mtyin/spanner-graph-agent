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

class NL2ModelAgent(LlmAgent):
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
            name="NL2ModelAgent",
            description="An agent that helps users translate natural languages into a graph model.",
            instruction=get_prompt("nl_to_model"),
            tools=[],
        )