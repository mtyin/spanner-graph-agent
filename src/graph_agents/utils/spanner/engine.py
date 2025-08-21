from typing import Any, Dict, List

from google.cloud import spanner
from google.cloud.spanner_v1.database import Database
from typing_extensions import override

from graph_agents.utils.engine import Engine, QueryResult


def _get_spanner_param_type_from_value(v: Any):
    if isinstance(v, bool):
        return spanner.param_types.BOOL
    if isinstance(v, str):
        return spanner.param_types.STRING
    if isinstance(v, bytes):
        return spanner.param_types.BYTES
    if isinstance(v, int):
        return spanner.param_types.INT64
    if isinstance(v, float):
        return spanner.param_types.FLOAT32
    if isinstance(v, list):
        if len(v) == 0:
            raise ValueError("Unknown element type of empty array")
        return spanner.param_types.Array(_get_spanner_param_type_from_value(v[0]))
    raise ValueError(f"Unsupported parameter type: {type(v)}")


class SpannerEngine(Engine):

    def __init__(self, database: Database, **kwargs: Any):
        self._database = database
        self._default_timeout = kwargs.get("timeout", 30)

    @override
    def name(self):
        return "Spanner Graph"

    @override
    def _query(self, q: str, **kwargs: Any) -> List[Dict[str, Any]]:
        if "params" in kwargs and "param_types" not in kwargs:
            kwargs["param_types"] = {
                k: _get_spanner_param_type_from_value(v)
                for k, v in kwargs["params"].items()
            }
        if "timeout" not in kwargs and self._default_timeout is not None:
            kwargs["timeout"] = self._default_timeout
        with self._database.snapshot() as snapshot:
            rows = snapshot.execute_sql(q, **kwargs)
            return [
                {
                    column: value
                    for column, value in zip(
                        [column.name for column in rows.fields], row
                    )
                }
                for row in rows
            ]

    @override
    def apply_ddls(self, ddls: List[str], **kwargs: Any) -> None:
        if not ddls:
            return

        timeout = self._default_timeout
        if "timeout" in kwargs:
            timeout = kwargs.pop("timeout")
        op = self._database.update_ddl(ddl_statements=ddls, **kwargs)
        op.result(timeout=timeout)

    @override
    def insert_or_update(
        self, table: str, columns: List[str], values: List[List[Any]], **kwargs: Any
    ) -> None:
        """Insert or update the table.

        Parameters:
        - table: Spanner table name;
        - columns: list of column names;
        - values: list of values.
        """

        batch_size = kwargs.get("batch_size", 100)
        for i in range(0, len(values), batch_size):
            value_batch = values[i : i + batch_size]
            with self._database.batch(**kwargs) as batch:
                batch.insert_or_update(table=table, columns=columns, values=value_batch)
