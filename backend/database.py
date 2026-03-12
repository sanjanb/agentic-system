# backend/database.py
import psycopg
from pgvector.psycopg import register_vector

DATABASE_URL = "postgresql://dev_user:dev_password@localhost:5432/task_db"

def get_conn():
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    register_vector(conn)
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