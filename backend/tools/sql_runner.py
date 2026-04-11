import os
import threading
import duckdb

from models.schemas import ErrorResult, QueryResult

DATA_DIR = os.environ.get(
    "DATA_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "Sample Data"),
)

_DB_PATH = os.path.join(DATA_DIR, "airbnb.duckdb")

_con: duckdb.DuckDBPyConnection | None = None
_db_lock = threading.Lock()
_schema_json_cache: dict | None = None
_schema_desc_cache: str | None = None


def _persist_to_file() -> None:
    """Materialize CSVs into a persistent DuckDB file for fast startup."""
    dest = duckdb.connect(database=_DB_PATH)
    try:
        for table_name, filename in [
            ("listings", "listings.csv"),
            ("reviews", "reviews.csv"),
            ("neighbourhoods", "neighbourhoods.csv"),
        ]:
            path = os.path.join(DATA_DIR, filename).replace("\\", "/")
            if os.path.exists(path):
                dest.execute(
                    f"CREATE TABLE IF NOT EXISTS {table_name} AS "
                    f"SELECT * FROM read_csv_auto('{path}', ignore_errors=true)"
                )
    finally:
        dest.close()


def _get_connection() -> duckdb.DuckDBPyConnection:
    global _con
    if _con is not None:
        return _con

    # Fast path: open pre-built DuckDB file
    if os.path.exists(_DB_PATH):
        _con = duckdb.connect(database=_DB_PATH, read_only=True)
        return _con

    # Slow path: build from CSVs, persist for next time
    _persist_to_file()
    _con = duckdb.connect(database=_DB_PATH, read_only=True)
    return _con


TABLE_DESCRIPTIONS = {
    "listings": "~37K Airbnb listings with host info, location, pricing, amenities, reviews",
    "reviews": "~1M guest reviews with listing references, dates, and reviewer details",
    "neighbourhoods": "NYC neighbourhood and neighbourhood group geographic reference data",
}


def get_schema_json() -> dict:
    """Return structured schema for all registered DuckDB tables (cached after first call)."""
    global _schema_json_cache
    if _schema_json_cache is not None:
        return _schema_json_cache

    con = _get_connection()
    with _db_lock:
        tables = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name IN ('listings', 'reviews', 'neighbourhoods')"
        ).fetchall()

        schema = {}
        for (table_name,) in tables:
            cols = con.execute(
                f"SELECT column_name, data_type FROM information_schema.columns "
                f"WHERE table_name='{table_name}' ORDER BY ordinal_position"
            ).fetchall()
            row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            schema[table_name] = {
                "description": TABLE_DESCRIPTIONS.get(table_name, ""),
                "columns": [{"name": c, "type": t} for c, t in cols],
                "row_count": row_count,
            }
    _schema_json_cache = schema
    return schema


def get_schema_description() -> str:
    """Return a compact description of every registered table and its columns (cached)."""
    global _schema_desc_cache
    if _schema_desc_cache is not None:
        return _schema_desc_cache

    con = _get_connection()
    with _db_lock:
        tables = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name IN ('listings', 'reviews', 'neighbourhoods')"
        ).fetchall()

        parts: list[str] = []
        for (table_name,) in tables:
            cols = con.execute(
                f"SELECT column_name, data_type FROM information_schema.columns "
                f"WHERE table_name='{table_name}' ORDER BY ordinal_position"
            ).fetchall()
            col_list = ", ".join(f"{c} ({t})" for c, t in cols)
            parts.append(f"  {table_name}: {col_list}")

    _schema_desc_cache = "Available tables:\n" + "\n".join(parts)
    return _schema_desc_cache


def run_sql(query: str, max_rows: int = 500) -> str:
    """Execute a read-only SQL query and return results as JSON."""
    con = _get_connection()
    normalized_query = query.strip().rstrip(";")
    upper = normalized_query.upper()
    if any(upper.startswith(kw) for kw in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE")):
        return ErrorResult(error="Only SELECT queries are allowed.").model_dump_json()

    try:
        with _db_lock:
            result = con.execute(normalized_query)
            columns = [desc[0] for desc in result.description]
            rows = result.fetchmany(max_rows)
            total_rows = len(rows)
            if len(rows) == max_rows:
                total_rows = con.execute(
                    f"SELECT COUNT(*) FROM ({normalized_query}) AS result_set"
                ).fetchone()[0]
        data = [dict(zip(columns, row)) for row in rows]
        response = QueryResult(
            columns=columns,
            row_count=total_rows,
            returned_row_count=len(data),
            truncated=total_rows > len(data),
            data=data,
        )
        return response.model_dump_json()
    except Exception as e:
        return ErrorResult(error=str(e)).model_dump_json()
