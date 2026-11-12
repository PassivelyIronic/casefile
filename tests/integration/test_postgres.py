import psycopg
import pytest

from casefile.config import Settings


@pytest.mark.integration
def test_postgres_has_pgvector_and_schema() -> None:
    with psycopg.connect(Settings().postgres_dsn, connect_timeout=5) as conn:
        ext = conn.execute(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()
        schema = conn.execute(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'vectors'"
        ).fetchone()
        distance = conn.execute("SELECT '[1,0]'::vector <-> '[0,0]'::vector").fetchone()
    assert ext is not None
    assert schema is not None
    assert distance is not None
    assert distance[0] == 1.0
