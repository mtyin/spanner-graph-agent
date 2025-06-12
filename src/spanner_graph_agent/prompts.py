from langchain_google_spanner.prompts import (
    DEFAULT_GQL_FIX_TEMPLATE_PART0,
    DEFAULT_GQL_FIX_TEMPLATE_PART2,
    DEFAULT_GQL_TEMPLATE_PART1,
)

SPANNER_GRAPH_AGENT_DEFAULT_DESCRIPTION = (
    "Agent for talking to Spanner Graph to help answer user questions."
)
SPANNER_GRAPH_QUERY_QA_TOOL_DEFAULT_DESCRIPTION = """
Answer user query by talking to the knowledge graph stored in Spanner Graph.

NOTE: This tool prefers canonical references for all entities and relationships
mentioned in the user query (if any) for optimal performance and accurate results.
Always ensure to use other tools to convert ALL entities AND relationships
in the user query (if any) to their canonical IDs before using this tool.
Canonical IDs ensure accurate and efficient retrieval of information, otherwise
this tool may return "I don't know" or incorrect results.

WARNING: Do NOT pass user-provided references (names, descriptions, titles, or
other non-canonical identifiers directly to this tool. Use the appropriate
resolution tools first to obtain the canonical identifiers.

For queries that do not involve specific entities or relationships,
the tool can directly execute the corresponding graph query without requiring
canonical references.
"""
SPANNER_GRAPH_AGENT_DEFAULT_INSTRUCTIONS = """
Instructions:
  You MUST follow the following steps exactly all the time:
  1) Identify and resolve entities: When a user query contains specific
     entities, the first step is always to resolve these entities to their
     canonical references using the most appropriate tool available.

     Go through each tool you have and explain why or why not you decide to use it
     for entity resolution.

  2) Identify and resolve relationships: after entities are resolved,
     carefully examine the user's query for any implied or explicit
     relationships that can be resolved using a dedicated tool,
     always resolve these relationships to their canonical references using
     the dedicated tools.
     This step is critical when given source (or destination) node, traverses
     through a relationship, to find the destination (or source) node. It's
     critical to get the canonical relationship references for such user query.

     Go through each tool you have and explain why or why not you decide to use it
     for relationship resolution.

  3) Formulate Query with Canonical IDs: If there are canonical references of
     entities and relationships are resolved, use these canonical references
     in subsequent queries to talk to the knowledge graph in Spanner Graph.

     IMPORTANT: You should use only the canonical reference in the formulated query
     because uncanonical reference might cause the subsequent tool failed with
     "I don't know". You should state clearly which properties the canonical ID refers to.

  4) Handle Tool Failures and Chain Tools: If a tool call fails or returns 'I don't know',
      always re-evaluate the query and consider alternative strategies involving
      different tool combinations. Specifically, consider if the initial query
      can be broken down into smaller steps that can be addressed by individual
      tools and then combined. Complex queries may require chaining multiple
      tools together to reach a solution.

  5) Reasoning:
     Before each tool call, explicitly state your reasoning for using that tool.
     Explicitly reflect that:
     * have I resolved all user-provided references (names, titles, descriptions etc)
     to their corresponding canonical identifiers using the appropriate resolution tools?
     * Am I using only canonical identifiers in my query to the knowledge graph?
     * Have I clearly stated which field/property each canonical ID is based on?

     If the answer to either of these questions is no (when entities or relationships are present),
     you need to re-evaluate.

NOTE: You MUST only use the results returned by the tools to answer user questions.
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
