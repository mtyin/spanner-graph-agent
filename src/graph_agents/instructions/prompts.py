import importlib.resources
from typing import Any

from jinja2 import Template

PROMPT_FILES = {
    "GRAPH_AGENT_DESCRIPTION": "GRAPH_AGENT_DESCRIPTION.md",
    "GRAPH_AGENT_INSTRUCTIONS": "GRAPH_AGENT_INSTRUCTIONS.md",
    "GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_INSTRUCTIONS": "model/GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_INSTRUCTIONS.md",
    "GRAPH_MODELLING_AGENT_DESCRIPTION": "model/GRAPH_MODELLING_AGENT_DESCRIPTION.md",
    "GRAPH_MODELLING_AGENT_INSTRUCTIONS": "model/GRAPH_MODELLING_AGENT_INSTRUCTIONS.md",
    "NEW_GRAPH_MODELLING_AGENT_DESCRIPTION": "model/NEW_GRAPH_MODELLING_AGENT_DESCRIPTION.md",
    "NEW_GRAPH_MODELLING_AGENT_INSTRUCTIONS": "model/NEW_GRAPH_MODELLING_AGENT_INSTRUCTIONS.md",
    "SPANNER_GRAPH_SCHEMA_GENERATION_AGENT_INSTRUCTIONS": "model/SPANNER_GRAPH_SCHEMA_GENERATION_AGENT_INSTRUCTIONS.md",
    "TABLE_TO_GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_DESCRIPTION": "model/TABLE_TO_GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_DESCRIPTION.md",
    "TABLE_TO_GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_INSTRUCTIONS": "model/TABLE_TO_GRAPH_LOGICAL_SCHEMA_MODELLING_AGENT_INSTRUCTIONS.md",
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
