An agent that answer user query by talking to the knowledge graph stored in {{product}}.

The knowledge graph contains details about the following node types:
  {{node_labels}}
and the details of the relationships among the nodes:
  {{edge_labels}}

This agent can directly access and query the knowledge graph. All user queries,
after necessary node or relationship resolutions, must be passed to this agent
to retrieve information.

NOTE:

* For questions with explicit node or relationships references in the graph,
  this agent requires canonical references to the nodes and relationships
  for optimal performance and accurate results.

* BEFORE passing ANY query to this agent, FIRST and ALWAYS check if the query
  contains any potential references to nodes or relationships: if so, you MUST
  use the appropriate agent to obtain the canonical references.
  Only then should you formulate the input to this agent using
  these canonical references.

* The input to this agent must explicitly refers to canonical references by
  both the names and the values of the referenced fields.
    For example, Node(id='abc') rather than just Node('abc').
    Otherwise this agent don't know which fields to query against.

* For queries that do not contains any specific node or relationship
  references, the agent can directly execute the corresponding graph query
  without requiring canonical references.
