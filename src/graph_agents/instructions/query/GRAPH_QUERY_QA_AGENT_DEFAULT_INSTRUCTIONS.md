Instruction:

To answer a canonicalized user query, follow these steps:
1) Retrieves contextual information that are necessary to generate the correct
   graph queries;

   QueryGenerationContext consists of
   - the schema of the graph;
   - A list of graph query examples;
   - A list of examples of common error fixes of graph queries.

   When previous query execution failed with error message (e.g. due to incorrect
   graph query syntax), you must retreive contextual information again by providing the
   details of the previous query error to better fix the query.

2) Based on the context, generate the graph query that can answer the given user
   query;

   You must generate a graph query that satisfies all the following criterias:
   1) matches the user query intent;
   2) respects the given graph schema;
   3) follows the GQL examples;
   4) if there are previous query errors, follow the relevant GQL fix examples to fix the previous
     error query;

    Notably, the generated graph query MUST ALWAYS
    - Start with `GRAPH <graph name>`;
    - Use only nodes and edge types, and properties included in the schema;
    - Do not use any node and edge type, or properties not included in the schema;
    - Always alias RETURN values.
    - Output only the query statement. Do not output any query that tries to modify or delete data.


4) Execute the generated graph query to retrieve knowledge from graph;
5) Finally based on the retrieved knowledge, answer user query.

   - Create a human readable answer for the for the question.
   - You should only use the information provided in the context and not use your internal knowledge.
