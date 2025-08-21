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
    # Schema orchestrator
    "ORCHESTRATOR_DESCRIPTION": "schema/ORCHESTRATOR_DESCRIPTION.md",
    "ORCHESTRATOR_INSTRUCTIONS": "schema/ORCHESTRATOR_INSTRUCTIONS.md",
    # Schema Diagram2Model
    "DIAGRAM_TO_MODEL_DESCRIPTION": "schema/DIAGRAM_TO_MODEL_DESCRIPTION.md",
    "DIAGRAM_TO_MODEL_INSTRUCTIONS": "schema/DIAGRAM_TO_MODEL_INSTRUCTIONS.md",
    # Schema NL2Model
    "NL_TO_MODEL_DESCRIPTION": "schema/NL_TO_MODEL_DESCRIPTION.md",
    "NL_TO_MODEL_INSTRUCTIONS": "schema/NL_TO_MODEL_INSTRUCTIONS.md",
    # Schema SpannerSchema2Model
    "SPANNER_SCHEMA_TO_MODEL_DESCRIPTION": "schema/SPANNER_SCHEMA_TO_MODEL_DESCRIPTION.md",
    "SPANNER_SCHEMA_TO_MODEL_INSTRUCTIONS": "schema/SPANNER_SCHEMA_TO_MODEL_INSTRUCTIONS.md",
    # Schema Model2SpannerSchema
    "MODEL_TO_SPANNER_SCHEMA_AGENT_DESCRIPTION": "schema/MODEL_TO_SPANNER_SCHEMA_AGENT_DESCRIPTION.md",
    "MODEL_TO_SPANNER_SCHEMA_AGENT_INSTRUCTIONS": "schema/MODEL_TO_SPANNER_SCHEMA_AGENT_INSTRUCTIONS.md",
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
