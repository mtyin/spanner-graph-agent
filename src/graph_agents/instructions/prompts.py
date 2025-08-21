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
    "GRAPH_SCHEMA_AGENT_DESCRIPTION": "schema/GRAPH_SCHEMA_AGENT_DESCRIPTION.md",
    "GRAPH_SCHEMA_AGENT_INSTRUCTIONS": "schema/GRAPH_SCHEMA_AGENT_INSTRUCTIONS.md",
    # Schema Diagram2Model
    "GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_DESCRIPTION": "schema/GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_DESCRIPTION.md",
    "GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_INSTRUCTIONS": "schema/GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_INSTRUCTIONS.md",
    # Schema NL2Model
    "SPANNER_GRAPH_SCHEMA_GENERATION_AGENT_INSTRUCTIONS": "schema/SPANNER_GRAPH_SCHEMA_GENERATION_AGENT_INSTRUCTIONS.md",
    "SPANNER_GRAPH_SCHEMA_GENERATION_AGENT_INSTRUCTIONS": "schema/SPANNER_GRAPH_SCHEMA_GENERATION_AGENT_INSTRUCTIONS.md",
    # Schema SpannerSchema2Model
    "TABLE_TO_GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_DESCRIPTION": "schema/TABLE_TO_GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_DESCRIPTION.md",
    "TABLE_TO_GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_INSTRUCTIONS": "schema/TABLE_TO_GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_INSTRUCTIONS.md",
    # Schema Model2SpannerSchema
    "TABLE_TO_GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_DESCRIPTION": "schema/TABLE_TO_GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_DESCRIPTION.md",
    "TABLE_TO_GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_INSTRUCTIONS": "schema/TABLE_TO_GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_INSTRUCTIONS.md",
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
