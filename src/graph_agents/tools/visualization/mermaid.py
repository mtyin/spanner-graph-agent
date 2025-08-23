import json

def _format_properties_for_mermaid(properties: dict) -> list[str]:
    """
    (Helper Function)
    Formats a dictionary of properties into a list of strings for Mermaid.
    """
    if not properties:
        return []
    
    lines = []
    for key, value in properties.items():
        # Format and sanitize the value for display
        val_str = json.dumps(value).strip('"')
        lines.append(f"{key}: {val_str}")
    return lines

def convert_graph_json_to_mermaid(graph_json_str: str) -> str:
    """
    Converts a generic property graph from a JSON string into Mermaid syntax.

    This tool processes nodes and edges, displaying their labels and all
    their properties in a structured format within the diagram.

    Args:
        graph_json: A JSON string.

    Returns:
        A string containing the Mermaid syntax for the graph.
    """
    graph_json = json.loads(graph_json_str)
    
    if 'graph' not in graph_json:
        raise ValueError("Input JSON must have a 'graph' key.")

    graph = graph_json['graph']
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])

    mermaid_lines = ["graph TD;"]

    # --- Process Nodes ---
    for node in nodes:
        node_id = node['id']
        node_label = node.get('label', '')
        
        content_lines = [f"<strong>{node_label}</strong>"]
        content_lines.extend(_format_properties_for_mermaid(node.get('properties', {})))
        
        full_node_text = "<br>".join(content_lines)
        sanitized_text = json.dumps(full_node_text)
        
        mermaid_lines.append(f'    {node_id}[{sanitized_text}];')

    # --- Process Edges ---
    for edge in edges:
        source = edge['source']
        destination = edge['destination']
        
        content_lines = [edge.get('label', '')] if edge.get('label') else []
        content_lines.extend(_format_properties_for_mermaid(edge.get('properties', {})))

        full_edge_text = "<br>".join(content_lines)

        if full_edge_text:
            sanitized_text = json.dumps(full_edge_text)
            mermaid_lines.append(f'    {source} -- {sanitized_text} --> {destination};')
        else:
            mermaid_lines.append(f'    {source} --> {destination};')
            
    return "\n".join(mermaid_lines)