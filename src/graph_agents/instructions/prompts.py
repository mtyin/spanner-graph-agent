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
    "graph_agent_description": "GRAPH_AGENT_DESCRIPTION.md",
    "graph_agent_instructions": "GRAPH_AGENT_INSTRUCTIONS.md",
    # Schema Orchestrator
    "schema_orchestrator": "schema/orchestrator.md",
    # Schema ERDiagram2Model
    "er_diagram_to_model": "schema/to_model/er_diagram_to_model.md",
    # Schema NL2Model
    "nl_to_model": "schema/to_model/nl_to_model.md",
    # Schema SpannerSchema2Model
    "spanner_schema_to_model": "schema/to_model/spanner_schema_to_model.md",
    # Schema Model2SpannerSchema
    "model_to_spanner_schema": "schema/to_schema/model_to_spanner_schema.md",
    # Construction Flowchart2Data
    "flowchart_to_data": "construction/flowchart_to_data.md",
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
