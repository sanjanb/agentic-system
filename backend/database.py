# backend/database.py
import psycopg
from pgvector.psycopg import register_vector

DATABASE_URL = "postgresql://dev_user:dev_password@localhost:5432/task_db"


def get_conn():
    # autocommit=False (default) is required for `with conn:` transaction blocks
    conn = psycopg.connect(DATABASE_URL)

    try:
        register_vector(conn)
    except psycopg.ProgrammingError as exc:
        # Most likely the `vector` extension hasn't been created in the database yet.
        msg = str(exc)
        if 'vector type not found' in msg or 'vector type' in msg:
            help_msg = (
                "pgvector extension not found in the database.\n"
                "Please create the extension in your Postgres instance and restart the server.\n"
                "If you're using the provided Docker Compose, run:\n"
                "  docker exec -i local-vault-vdb psql -U dev_user -d task_db -c \"CREATE EXTENSION IF NOT EXISTS vector;\"\n"
                "Or connect to your DB and run: CREATE EXTENSION IF NOT EXISTS vector;\n"
            )
            conn.close()
            raise RuntimeError(help_msg) from exc
        # If it's a different programming error, re-raise
        conn.close()
        raise

    return conn

def claim_task_atomically(task_id: int, worker_id: int):
    with get_conn() as conn:
        # ATOMIC OPERATION: Only assign if the task is still 'open'
        result = conn.execute(
            "UPDATE tasks SET assigned_worker_id = %s, status = 'assigned' "
            "WHERE id = %s AND status = 'open' RETURNING id",
            (worker_id, task_id)
        ).fetchone()
        
        if result:
            # Set worker to busy
            conn.execute("UPDATE workers SET status = 'busy' WHERE id = %s", (worker_id,))
            return True
        return False