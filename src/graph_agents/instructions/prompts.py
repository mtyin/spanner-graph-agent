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

import importlib.resources
from typing import Any

from jinja2 import Template

PROMPT_FILES = {
    # Graph
    "GRAPH_AGENT_DESCRIPTION": "GRAPH_AGENT_DESCRIPTION.md",
    "GRAPH_AGENT_INSTRUCTIONS": "GRAPH_AGENT_INSTRUCTIONS.md",
    # schema Orchestrator
    "schema_orchestrator_description": "schema/orchestrator_description.md",
    "schema_orchestrator_instructions": "schema/orchestrator_instructions.md",
    # schema Diagram2Model
    "diagram_to_model_description": "schema/to_model/from_er_description.md",
    "diagram_to_model_instructions": "schema/to_model/from_er_instructions.md",
    # schema Ml2Model
    "nl_to_model_description": "schema/to_model/from_nl_description.md",
    "nl_to_model_instructions": "schema/to_model/from_nl_instructions.md",
    # schema SpannerSchema2Model
    "spanner_schema_to_model_description": "schema/to_model/from_spanner_schema_description.md",
    "spanner_schema_to_model_instructions": "schema/to_model/from_spanner_schema_instructions.md",
    # schema Model2SpannerSchema
    "model_to_spanner_schema_description": "schema/to_schema/model_to_spanner_schema_description.md",
    "model_to_spanner_schema_instructions": "schema/to_schema/model_to_spanner_schema_instructions.md",
    # construction Diagram2Data
    "diagram_to_data_description": "construction/diagram_to_data_description.md",
    "diagram_to_data_instructions": "construction/diagram_to_data_instructions.md",
}

def _load_template(filename: str) -> Template:
    return Template(
        importlib.resources.files("graph_agents.instructions")
        .joinpath(filename)
        .read_text()
    )


def get_prompt(topic: str, *args: Any, **kwargs: Any) -> str:
    fname = PROMPT_FILES.get(topic)
    if fname is None:
        raise ValueError(f"No topic `{topic}` found")
    t = _load_template(fname)
    return t.render(*args, **kwargs)
