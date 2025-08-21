import logging
from abc import abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("graph_agents." + __name__)


class QueryResult(BaseModel):
    results: List[Dict[str, Any]] = Field(description="Query results")
    error_message: Optional[str] = Field(
        default=None, description="Error messages resulted from invalid query"
    )


class Engine(object):

    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def _query(self, q: str, **kwargs: Any) -> List[Dict[str, Any]]:
        pass

    def query(self, q: str, **kwargs: Any) -> QueryResult:
        """
        Execute the graph query `q` to get query results.

        When query execution failed (e.g. due to incorrect graph query),
        error_message will be set.
        """

        try:
            results = self._query(q, **kwargs)
            return QueryResult(results=results)
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return QueryResult(results=[], error_message=str(e))

    @abstractmethod
    def apply_ddls(self, ddls: List[str], **kwargs: Any) -> None:
        """
        Apply the list of ddl statements.
        """
        pass

    @abstractmethod
    def insert_or_update(
        self, table: str, columns: List[str], values: List[List[Any]]
    ) -> None:
        """Insert or update the table.

        Parameters:
        - table: Spanner table name;
        - columns: list of column names;
        - values: list of values.
        """
        pass
