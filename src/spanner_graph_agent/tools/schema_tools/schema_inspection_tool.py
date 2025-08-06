import functools
import json
from spanner_graph_agent.utils.information_schema import InformationSchema, PropertyGraph


def build_schema_inspection_tools(
    info_schema: InformationSchema,
    property_graph: PropertyGraph,
):

  def to_json(f):

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
      result = f(*args, **kwargs)
      return json.dumps(result, default=lambda obj: obj.__dict__, indent=1)

    return wrapper

  @to_json
  def list_node_types():
    """List all node types in the knowledge graph."""
    return property_graph.get_node_labels()

  @to_json
  def list_edge_types():
    """List all edge types in the knowledge graph."""
    return property_graph.get_edge_labels()

  @to_json
  def list_triplet_types():
    """List all tripet types in the knowledge graph.

    Each triplet is defined by (source node type, edge type, target node type).
    """
    return property_graph.get_triplet_labels()

  @to_json
  def list_node_type_details(node_type: str):
    """Show detailed schema about a node type.

    E.g. properties (name and type) of given node type.
    """
    return property_graph.get_node_details(node_type)

  @to_json
  def list_edge_type_details(edge_type: str):
    """Show detailed schema about an edge type.

    E.g. properties (name and type) of given edge type.
    """
    return property_graph.get_edge_details(edge_type)

  @to_json
  def list_triplet_type_details(
      src_node_type: str, edge_type: str, dst_node_type: str
  ):
    """Show details about a (source_node_type, edge_type, target_node_type) triplet.

    E.g. properties (name and type) of given triplet.
    """
    return property_graph.get_triplet_details(
        src_node_type, edge_type, dst_node_type
    )

  @to_json
  def list_json_property_details(json_property_name: str):
    """Show details about a json property.

    E.g. possible sub-fields of the json property.
    """
    return info_schema.get_json_property_schema_in_property_graph(
        property_graph, [json_property_name]
    )

  return [
      list_node_types,
      list_edge_types,
      list_node_type_details,
      list_edge_type_details,
      list_json_property_details,
  ]
