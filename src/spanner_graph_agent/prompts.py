from langchain_google_spanner.prompts import (
    DEFAULT_GQL_FIX_TEMPLATE_PART0,
    DEFAULT_GQL_FIX_TEMPLATE_PART2,
    DEFAULT_GQL_TEMPLATE_PART1,
)

SPANNER_GRAPH_AGENT_DEFAULT_DESCRIPTION = (
    "Agent for talking to Spanner Graph to help answer user questions."
)
SPANNER_GRAPH_AGENT_DEFAULT_INSTRUCTIONS = """
Instructions:
  You MUST follow the following steps exactly all the time:
  1) Identify and resolve entities: When a user query contains specific
     entities, the first step is always to resolve these entities to their
     canonical references using the most appropriate tool available.
  2) Identify and resolve relationships: after entities are resolved,
     carefully examine the user's query for any implied or explicit
     relationships that can be resolved using a dedicated tool,
     always resolve these relationships to their canonical references using
     the dedicated tools.
     This step is critical when given source (or destination) node, traverses
     through a relationship, to find the destination (or source) node. It's
     critical to get the canonical relationship references for such user query.
  3) Formulate Query with Canonical IDs: after both canonical references of
     entities and relationships are resolved, use these canonical references
     in subsequent queries to talk to the knowledge graph in Spanner Graph.
  4) Handle Missing/Unresolvable Entities: If an entity cannot be resolved,
     inform the user and explain that further information cannot be retrieved
     without a valid canonical reference for that entity or relationship. Do
     not proceed with the main query for that specific entity's information.
  5) Handle Tool Failures: If a tool call fails with "I don't know", re-evaluate
     the previous step and attempt different strategies of entity and
     relationship resolution. If the failure is due to an internal tool error,
     inform the user.

NOTE:
  You MUST only use the results returned by the tools to answer user questions.
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
