import functools
import json

from graph_agents.utils.information_schema import InformationSchema, PropertyGraph
from graph_agents.utils.json import to_json


def build_schema_inspection_tools(
    info_schema: InformationSchema,
    graph_id: str,
):
    @to_json
    def list_node_types():
        """List all node types in the knowledge graph."""
        property_graph = info_schema.get_property_graph(graph_id)
        if property_graph is None:
            return []
        return property_graph.get_node_labels()

    @to_json
    def list_edge_types():
        """List all edge types in the knowledge graph."""
        property_graph = info_schema.get_property_graph(graph_id)
        if property_graph is None:
            return []
        return property_graph.get_edge_labels()

    @to_json
    def list_triplet_types():
        """List all tripet types in the knowledge graph.

        Each triplet is defined by (source node type, edge type, target node type).
        """
        property_graph = info_schema.get_property_graph(graph_id)
        if property_graph is None:
            return []
        return property_graph.get_triplet_labels()

    @to_json
    def list_node_type_details(node_type: str):
        """Show detailed schema about a node type.

        E.g. properties (name and type) of given node type.
        """
        property_graph = info_schema.get_property_graph(graph_id)
        if property_graph is None:
            return None
        return property_graph.get_node_details(node_type)

    @to_json
    def list_edge_type_details(edge_type: str):
        """Show detailed schema about an edge type.

        E.g. properties (name and type) of given edge type.
        """
        property_graph = info_schema.get_property_graph(graph_id)
        if property_graph is None:
            return None
        return property_graph.get_edge_details(edge_type)

    @to_json
    def list_json_property_details(node_or_edge_type: str, json_property_name: str):
        """Show details about a json property of a certain node or edge type.

        E.g. possible sub-fields of the json property.
        """
        property_graph = info_schema.get_property_graph(graph_id)
        if property_graph is None:
            return None
        return info_schema.get_json_property_schema_in_property_graph(
            property_graph, node_or_edge_type, [json_property_name]
        )

    return [
        list_node_types,
        list_edge_types,
        list_node_type_details,
        list_edge_type_details,
        list_json_property_details,
    ]
