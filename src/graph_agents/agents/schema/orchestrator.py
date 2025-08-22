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

from graph_agents.agents.schema.to_model.nl_to_model import NL2ModelAgent
from graph_agents.agents.schema.to_model.diagram_to_model import Diagram2ModelAgent
from graph_agents.agents.schema.to_model.spanner_schema_to_model import SpannerSchema2ModelAgent
from graph_agents.agents.schema.to_schema.model_to_spanner_schema import Model2SpannerSchemaAgent

from graph_agents.instructions.prompts import get_prompt

class GraphSchemaAgent(LlmAgent):

    def __init__(
        self,
        model: str,
    ):
        super().__init__(
            model=model,
            name="GraphSchemaAgent",
            description="An agent specialized in all graph schema-related operations",
            instruction=get_prompt("schema_orchestrator_instructions"),
            tools=[],
            sub_agents=[
                NL2ModelAgent(model),
                Diagram2ModelAgent(model),
                SpannerSchema2ModelAgent(model),
                Model2SpannerSchemaAgent(model),
            ],
        )