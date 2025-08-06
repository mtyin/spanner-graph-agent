import json
import logging
from threading import Thread
from typing import Any, Dict, Optional
from google.adk.tools import FunctionTool, ToolContext
from google.cloud.spanner_v1.database import Database
from google.genai import types
from pydantic import BaseModel
from spanner_graphs.graph_server import GraphServer
from spanner_graphs.graph_visualization import generate_visualization_html
from typing_extensions import override

logger = logging.getLogger('spanner_graph_agent.' + __name__)

singleton_server_thread: Thread = None


def _build_visualization_tool(database: Database, graph_id: str):

  async def visualize_subgraph(
      referenced_node_type: str,
      canonical_node_reference: Dict[str, Any],
      tool_context: ToolContext,
  ):
    """This tool visualizes a subgraph of the knowledge graph centered around the given node.

    referenced_node_type: Node type of the canonical node reference.
    canonical_node_reference: Canonical reference of the node.

    The tool returns the visualized results as a saved artifact.
    """

    global singleton_server_thread
    if not singleton_server_thread or not singleton_server_thread.is_alive():
      singleton_server_thread = GraphServer.init()

    if isinstance(canonical_node_reference, BaseModel):
      canonical_node_reference = canonical_node_reference.model_dump_json()
    predicate = (
        ' AND '.join([
            f'n.{pname} = {repr(pvalue)}'
            for pname, pvalue in canonical_node_reference.items()
        ])
        or 'TRUE'
    )
    query = f"""
      GRAPH {graph_id}
      MATCH p = (n:{referenced_node_type})-()
      WHERE {predicate}
      RETURN SAFE_TO_JSON(p) AS p
    """
    html = generate_visualization_html(
        query=query,
        port=GraphServer.port,
        params=json.dumps({
            'project': database._instance._client.project,
            'instance': database._instance.instance_id,
            'database': database.database_id,
            'graph': graph_id,
            'mock': False,
        }),
    )
    fname = 'visual.html'
    await tool_context.save_artifact(
        fname,
        types.Part(
            inline_data=types.Blob(data=html.encode(), mime_type='text/html')
        ),
    )
    return f'See visualiztion in the attached artifact: {fname}'

  return visualize_subgraph


class SpannerGraphVisualizationTool(FunctionTool):

  def __init__(self, database: Database, graph_id: str):
    self.database = database
    self.graph_id = graph_id
    self.visualization_function = _build_visualization_tool(
        self.database, self.graph_id
    )
    super().__init__(self.visualization_function)

  @override
  def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
    function_decl = super()._get_declaration()
    if function_decl is None:
      return None
    function_decl.description = self.visualization_function.__doc__
    return function_decl
