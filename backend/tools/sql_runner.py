import os
import json
import duckdb

DATA_DIR = os.environ.get(
    "DATA_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "Sample Data"),
)

_con: duckdb.DuckDBPyConnection | None = None


def _get_connection() -> duckdb.DuckDBPyConnection:
    global _con
    if _con is not None:
        return _con

    _con = duckdb.connect(database=":memory:")

    _register_view(_con, "calendar", "calendar.csv")
    _register_view(_con, "listings", "listings.csv")
    _register_view(_con, "listings_summary", "listings_summary.csv")
    _register_view(_con, "reviews", "reviews.csv")
    _register_view(_con, "reviews_summary", "reviews_summary.csv")
    _register_view(_con, "neighbourhoods", "neighbourhoods.csv")

    return _con


def _register_view(con: duckdb.DuckDBPyConnection, name: str, filename: str) -> None:
    path = os.path.join(DATA_DIR, filename).replace("\\", "/")
    if not os.path.exists(path):
        return
    con.execute(
        f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_csv_auto('{path}', ignore_errors=true)"
    )


def get_schema_description() -> str:
    """Return a compact description of every registered view and its columns."""
    con = _get_connection()
    views = con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_type='VIEW'"
    ).fetchall()

    parts: list[str] = []
    for (view_name,) in views:
        cols = con.execute(
            f"SELECT column_name, data_type FROM information_schema.columns "
            f"WHERE table_name='{view_name}' ORDER BY ordinal_position"
        ).fetchall()
        col_list = ", ".join(f"{c} ({t})" for c, t in cols)
        parts.append(f"  {view_name}: {col_list}")

    return "Available tables:\n" + "\n".join(parts)


def run_sql(query: str, max_rows: int = 500) -> str:
    """Execute a read-only SQL query and return results as JSON."""
    con = _get_connection()
    upper = query.strip().upper()
    if any(upper.startswith(kw) for kw in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE")):
        return json.dumps({"error": "Only SELECT queries are allowed."})

    try:
        result = con.execute(query)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchmany(max_rows)
        data = [dict(zip(columns, row)) for row in rows]
        total = len(data)
        return json.dumps(
            {"columns": columns, "row_count": total, "data": data},
            default=str,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})
