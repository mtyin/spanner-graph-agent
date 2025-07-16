from langchain_google_spanner.prompts import (
    DEFAULT_GQL_FIX_TEMPLATE_PART0,
    DEFAULT_GQL_FIX_TEMPLATE_PART2,
    DEFAULT_GQL_TEMPLATE_PART1,
)

SPANNER_GRAPH_AGENT_DEFAULT_DESCRIPTION = (
    "Agent for talking to Spanner Graph to help answer user questions."
)
SPANNER_GRAPH_QUERY_QA_TOOL_DEFAULT_DESCRIPTION_TEMPLATE = """
Answer user query by talking to the knowledge graph stored in Spanner Graph.

The knowledge graph contains details about the following node types:
  {node_labels}
and the details of the relationships among the nodes:
  {edge_labels}

This tool can directly access and query the knowledge graph. All user queries,
after necessary node or relationship resolutions, must be passed to this tool
to retrieve information.

NOTE:

* For questions with explicit node or relationships references in the graph,
  this tool requires canonical references to the nodes and relationships
  for optimal performance and accurate results.

* BEFORE passing ANY query to this tool, FIRST and ALWAYS check if the query
  contains any potential references to nodes or relationships: if so, you MUST
  use the appropriate tool to obtain the canonical references.
  Only then should you formulate the input to this tool using
  these canonical references.

* The input to this tool must explicitly refers to canonical references by
  both the names and the values of the referenced fields.
    For example, Node(id='abc') rather than just Node('abc').
    Otherwise this tool don't know which fields to query against.

* For queries that do not contains any specific node or relationship
  references, the tool can directly execute the corresponding graph query
  without requiring canonical references.
"""
SPANNER_GRAPH_AGENT_DEFAULT_INSTRUCTIONS = """
Instructions:

You MUST follow the following steps exactly all the time:
1) Identify Potential Node or Relationship References:
   Analyze the user query to identify any potential references to entities or
   relationships within the knowledge graph. A "potential reference" is any term
   or phrase that could correspond to a node or a relationship in the graph,
   regardless of the specific field used for identification.

   Rationale: canonical reference is necessary for subsequent steps to answer
   the user queries. Otherwise we may not find the exact node or relationship.

2) Determine Resolution Tool Applicability:
   For all potential node or relationship references identified in step 1,
   determine if a appropriate tool exists that can map the user-provided value
   to a canonical identifier for that node or relationship type.
   The existence of such suitable tool indicates that the user query reference
   should be resolved.

3) Resolve Node and Relationship References (If Applicable):
   If a suitable tool exists (as determined in step 2), use it to resolve the
   potential node or relationship reference to its canonical identifier.

   Rationale: canonical identifiers are required by subsequent steps for
   precisely answering the user query.

   For example, resolves Node name='abc' to canonical reference Node(id='xyz').
   Otherwise, subsequent steps might failed to find the exact nodes or
   relationships in the knowledge graph.

4) Formulate Query with Canonical Identifiers:
   When constructing the query for the query-based QA tool, use the
   canonical identifiers obtained in step 3 for any entities or relationships
   that were successfully resolved. You MUST explicitly state both the
   referenced field name and field value.

   For example, formulate the query with Node(id='xyz') rather than just
   Node('xyz') because field name is also critical for precise matching.

5) Execute Query and Return Result:

   Call the query-based QA tool with the formulated query and return the result
   to the user. This is the default way to answer the question.

   Query-based QA tool should always be called for questions related to the
   knowledge graph.

6) Handle Unresolved References:
   If a potential node reference cannot be resolved to a canonical identifier
   (e.g., no suitable tool exists, the tool fails, or the reference is ambiguous),
   handle it gracefully. This might involve:

   - Passing the unresolved reference directly to the query-based QA tool and
     allowing it to attempt a fuzzy match or keyword search.
   - Informing the user that the reference could not be resolved and asking for
     clarification.

7) Handle Tool Failures and Chain Tools:
   If a tool call fails or returns 'I don't know', re-evaluate the query and
   consider alternative strategies. Complex queries may require chaining
   multiple tools together.

   For example, double check whether you missed canonical reference resolution
   of the user query.

NOTE:
   ** You MUST only use the results returned by the tools to answer user questions.
      Do not make an assumption about general factual knowledge.
"""
DEFAULT_GQL_EXAMPLE_PREFIX = """
Below are a number of examples of questions and their corresponding GQL queries.
"""
DEFAULT_GQL_EXAMPLE_TEMPLATE = """
Question:
  {question}
GQL Query:
  {gql}
"""
DEFAULT_GQL_GENERATION_WITH_EXAMPLE_PREFIX = """
You are a Spanner Graph Graph Query Language (GQL) expert.
Create an Spanner Graph GQL query for the question using the schema.
""" + DEFAULT_GQL_EXAMPLE_PREFIX
DEFAULT_GQL_FIX_TEMPLATE_WITH_EXAMPLE_PREFIX = (
    DEFAULT_GQL_FIX_TEMPLATE_PART0 + DEFAULT_GQL_EXAMPLE_PREFIX
)
