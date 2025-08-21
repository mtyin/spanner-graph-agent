import glob
import json
import logging
from typing import Any, Dict, Generator, List

from typing_extensions import override

from graph_agents.utils.embeddings import Embeddings
from graph_agents.utils.engine import Engine
from graph_agents.utils.example_store import ExampleStore, QueryExample, QueryFixExample

logger = logging.getLogger("graph_agents." + __name__)


class SpannerExampleStore(ExampleStore):

    def __init__(
        self, engine: Engine, embeddings: Embeddings, *args: Any, **kwargs: Any
    ):
        super().__init__(engine, embeddings, *args, **kwargs)
        self.example_table = kwargs.get("example_table", "gql_examples")
        self.engine.apply_ddls(
            [
                f"""CREATE TABLE IF NOT EXISTS {self.example_table} (
                      id INT64 NOT NULL AS (FARM_FINGERPRINT(description)) STORED,
                      description STRING(MAX) NOT NULL,
                      description_embeddings ARRAY<FLOAT32> NOT NULL,
                      graph_query STRING(MAX) NOT NULL,
                      schema STRING(MAX) NOT NULL,
                      error_graph_query STRING(MAX),
                    ) PRIMARY KEY (id)"""
            ],
            **kwargs,
        )

    @override
    def _load_examples(
        self, query_example_paths: List[str] = []
    ) -> Generator[QueryExample | QueryFixExample, None, None]:
        for path in query_example_paths:
            for file in glob.glob(path):
                with open(file, "r") as ifile:
                    for line in ifile:
                        result = json.loads(line)
                        if "bad_query" in result:
                            yield QueryFixExample(
                                **{f: result[f] for f in QueryFixExample.model_fields}
                            )
                        else:
                            yield QueryExample(
                                **{f: result[f] for f in QueryExample.model_fields}
                            )

    @override
    def get_example_queries(
        self, user_query: str, schema: Any, k: int, **kwargs: Any
    ) -> List[QueryExample]:
        embeddings = self.embeddings.get_embeddings([user_query])
        if not embeddings or embeddings[0] is None:
            logger.warning("Unable to generate embedding for the user query")
            return []
        query_results = self.engine.query(
            f"""
        SELECT description, graph_query, schema, COSINE_DISTANCE(description_embeddings, @embeddings) AS distance
        FROM {self.example_table}
        WHERE description_embeddings IS NOT NULL AND error_graph_query IS NULL
        ORDER BY distance
        LIMIT {k}""",
            params={"embeddings": embeddings[0]},
        )
        if query_results.error_message:
            logger.error(
                f"Unable to fetch example queries: {query_results.error_message}"
            )
            return []
        # TODO(mtyin): Consider fallback to public examples in Spanner Graph
        # query overview.
        return [
            QueryExample(
                query=result["graph_query"],
                description=result["description"],
            )
            for result in query_results.results
        ]

    @override
    def get_example_fix_queries(
        self,
        error_message: str,
        error_graph_query: str,
        schema: Any,
        k: int,
        *args: Any,
        **kwargs: Any,
    ) -> List[QueryFixExample]:
        embeddings = self.embeddings.get_embeddings([error_message])
        if not embeddings or embeddings[0] is None:
            logger.warning("Unable to generate embedding for the error message")
            return []
        query_results = self.engine.query(
            f"""
        SELECT error_graph_query,
               graph_query,
               description,
               COSINE_DISTANCE(description_embeddings, @embeddings) AS distance
        FROM {self.example_table}
        WHERE error_graph_query IS NOT NULL
        ORDER BY distance
        LIMIT {k}""",
            params={"embeddings": embeddings[0]},
        )
        if query_results.error_message:
            logger.error(
                f"Unable to fetch example fix queries: {query_results.error_message}"
            )
            return []
        # TODO(mtyin): Consider fallback to public examples in Spanner Graph
        # troubleshoot page.
        return [
            QueryFixExample(
                bad_query=result["error_graph_query"],
                correct_query=result["graph_query"],
                description=result["description"],
            )
            for result in query_results.results
        ]

    @override
    def add_examples(
        self,
        examples: List[QueryExample],
        *args: Any,
        **kwargs: Any,
    ):
        embeddings = self.embeddings.get_embeddings(
            [example.description for example in examples]
        )
        if not embeddings or not all(embeddings) or len(embeddings) != len(examples):
            logger.warning("Unable to generate embedding for the query example")
            return []
        self.engine.insert_or_update(
            self.example_table,
            [
                "description",
                "graph_query",
                "schema",
                "description_embeddings",
            ],
            [
                [example.description, example.query, "", embedding]
                for example, embedding in zip(examples, embeddings)
            ],
        )

    @override
    def add_fix_examples(
        self,
        examples: List[QueryFixExample],
        *args: Any,
        **kwargs: Any,
    ):
        embeddings = self.embeddings.get_embeddings(
            [example.description for example in examples]
        )
        if not embeddings or not all(embeddings) or len(embeddings) != len(examples):
            logger.warning("Unable to generate embedding for the fix example")
            return []
        self.engine.insert_or_update(
            self.example_table,
            [
                "description",
                "graph_query",
                "schema",
                "description_embeddings",
                "error_graph_query",
            ],
            [
                [
                    example.description,
                    example.correct_query,
                    "",
                    embedding,
                    example.bad_query,
                ]
                for example, embedding in zip(examples, embeddings)
            ],
        )
