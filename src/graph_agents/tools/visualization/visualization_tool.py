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

import json
import logging
from threading import Thread
from typing import Any, Dict, List, Optional

from google.adk.tools import FunctionTool, ToolContext
from google.genai import types
from pydantic import BaseModel, Field
from spanner_graphs.graph_server import GraphServer
from spanner_graphs.graph_visualization import generate_visualization_html
from typing_extensions import override

from graph_agents.utils.spanner.engine import SpannerEngine

logger = logging.getLogger("graph_agents." + __name__)

singleton_server_thread: Optional[Thread] = None


def _build_visualization_tool(engine: SpannerEngine, graph_id: str):

    class CanonicalNodeReference(BaseModel):
        referenced_node_type: str = Field(
            description="Node type of the canonical node reference"
        )
        canonical_node_reference: Dict[str, Any] = Field(
            description="Canonical reference of the node."
        )

    async def visualize_subgraph(
        canonical_node_references: List[CanonicalNodeReference],
        radius: int = 1,
        tool_context: ToolContext = None,
    ):
        """This tool visualizes a subgraph of the knowledge graph centered around the given nodes.

        canonical_node_references: A list of nodes to visualize.
        radius: Radius of the rendered graph, i.e. maximum hops from the center
                nodes. Radius is a non-negative integer. By default, radius is 1.
                Radius=0: only render the given nodes;
                Radius=1: also render the immediate neighbors of the given nodes.

        The tool returns the visualized results as a saved artifact.
        """

        global singleton_server_thread
        if not singleton_server_thread or not singleton_server_thread.is_alive():
            singleton_server_thread = GraphServer.init()

        radius = int(max(radius, 0))
        pieces = []
        for node_reference in canonical_node_references:
            if isinstance(node_reference, dict):
                node_reference = CanonicalNodeReference(**node_reference)
            predicate = (
                " AND ".join(
                    [
                        f"n.{pname} = {repr(pvalue)}"
                        for pname, pvalue in node_reference.canonical_node_reference.items()
                    ]
                )
                or "TRUE"
            )
            if radius == 0:
                pieces.append(
                    f"""
          MATCH p = (n:{node_reference.referenced_node_type})
          WHERE {predicate}
          RETURN SAFE_TO_JSON(p) AS p"""
                )
            elif radius == 1:
                pieces.append(
                    f"""
          MATCH p = (n:{node_reference.referenced_node_type})-()
          WHERE {predicate}
          RETURN SAFE_TO_JSON(p) AS p"""
                )
            elif radius > 1:
                # NOTE(mtyin): This query can potentially be very slow depends on
                # the exact schema.
                pieces.append(
                    f"""
          MATCH p = (n:{node_reference.referenced_node_type})-{{1, {radius}}}()
          WHERE {predicate}
          RETURN SAFE_TO_JSON(p) AS p"""
                )
        query = f"GRAPH {graph_id}\n" + "\nUNION ALL\n".join(pieces)
        logger.debug("Visualize the query:\n%s" % query)
        database = engine._database
        html = generate_visualization_html(
            query=query,
            port=GraphServer.port,
            params=json.dumps(
                {
                    "project": database._instance._client.project,
                    "instance": database._instance.instance_id,
                    "database": database.database_id,
                    "graph": graph_id,
                    "mock": False,
                }
            ),
        )
        fname = "visual-%s.html" % hash(query)
        await tool_context.save_artifact(
            fname,
            types.Part(
                inline_data=types.Blob(data=html.encode(), mime_type="text/html")
            ),
        )
        return f"See visualiztion in the attached artifact: {fname}"

    return visualize_subgraph


class SpannerGraphVisualizationTool(FunctionTool):

    def __init__(self, engine: SpannerEngine, graph_id: str):
        self.engine = engine
        self.graph_id = graph_id
        self.visualization_function = _build_visualization_tool(
            self.engine, self.graph_id
        )
        super().__init__(self.visualization_function)

    def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
        function_decl = super()._get_declaration()
        if function_decl is None:
            return None
        function_decl.description = self.visualization_function.__doc__
        return function_decl
