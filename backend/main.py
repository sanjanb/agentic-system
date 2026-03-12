from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from database import get_conn
import uvicorn

app = FastAPI()

class AssignmentRequest(BaseModel):
    task_id: int
    worker_id: int

@app.post("/tasks/claim")
async def claim_task(req: AssignmentRequest):
    """
    ATOMIC DISPATCH:
    Checks if task is 'open' and worker is 'available' in ONE transaction.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1. Start Transaction
            cur.execute("BEGIN;")
            
            # 2. Try to update task status
            cur.execute(
                "UPDATE tasks SET assigned_worker_id = %s, status = 'assigned' "
                "WHERE id = %s AND status = 'open' RETURNING id",
                (req.worker_id, req.task_id)
            )
            task_updated = cur.fetchone()

            if not task_updated:
                cur.execute("ROLLBACK;")
                raise HTTPException(status_code=409, detail="Task already taken or closed.")

            # 3. Mark worker as busy
            cur.execute(
                "UPDATE workers SET status = 'busy' WHERE id = %s AND status = 'available' RETURNING id",
                (req.worker_id,)
            )
            worker_updated = cur.fetchone()

            if not worker_updated:
                cur.execute("ROLLBACK;")
                raise HTTPException(status_code=409, detail="Worker is no longer available.")

            # 4. Commit both if successful
            cur.execute("COMMIT;")
            return {"status": "success", "message": f"Task {req.task_id} assigned to Worker {req.worker_id}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)