import logging
from abc import abstractmethod
from typing import Any, Dict, Generator, List, Optional

from pydantic import BaseModel, Field

from graph_agents.utils.embeddings import Embeddings
from graph_agents.utils.engine import Engine

logger = logging.getLogger("graph_agents." + __name__)


class QueryExample(BaseModel):
    query: str = Field(description="Graph query.")
    description: str = Field(description="Description of the graph query semantic.")


class QueryFixExample(BaseModel):
    bad_query: str = Field(description="Bad graph query")
    correct_query: str = Field(description="Correct version of the graph query")
    description: str = Field(description="Description of the error", default=None)


class ExampleStore(object):

    def __init__(
        self,
        engine: Engine,
        embeddings: Embeddings,
        *args: Any,
        **kwargs: Any,
    ):
        self.engine = engine
        self.embeddings = embeddings

    def load_examples(self, query_example_paths: List[str] = []) -> int:
        count = 0
        examples = []
        fix_examples = []
        for example in self._load_examples(query_example_paths):
            if isinstance(example, QueryExample):
                examples.append(example)
            elif isinstance(example, QueryFixExample):
                fix_examples.append(example)
            else:
                logger.error(f"Unsupported example: {type(example)}")
                continue
            count += 1
        self.add_examples(examples)
        self.add_fix_examples(fix_examples)
        return count

    @abstractmethod
    def _load_examples(
        self, query_example_paths: List[str] = []
    ) -> Generator[QueryExample | QueryFixExample, None, None]:
        pass

    @abstractmethod
    def get_example_queries(
        self, user_query: str, schema: Any, k: int, *args: Any, **kwargs: Any
    ) -> List[QueryExample]:
        pass

    @abstractmethod
    def get_example_fix_queries(
        self,
        error_message: str,
        error_graph_query: str,
        schema: Any,
        k: int,
        *args: Any,
        **kwargs: Any,
    ) -> List[QueryFixExample]:
        pass

    @abstractmethod
    def add_examples(self, examples: List[QueryExample], *args: Any, **kwargs: Any):
        pass

    @abstractmethod
    def add_fix_examples(
        self,
        examples: List[QueryFixExample],
        *args: Any,
        **kwargs: Any,
    ):
        pass
