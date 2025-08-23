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

class PGDiagram2DataAgent(LlmAgent):

    def __init__(
        self,
        model: str,
    ):
        super().__init__(
            model=model,
            name="PGDiagram2DataAgent",
            description="An agent that helps users translate a property graph diagram into property graph data.",
            instruction=get_prompt("pg_diagram_to_data"),
            tools=[],
        )
