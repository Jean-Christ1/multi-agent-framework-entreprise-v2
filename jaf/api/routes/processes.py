"""
JAF Process & Event API Routes
================================

REST endpoints for viewing persisted process data and event audit trails.

- GET  /api/v1/processes              → list all processes
- GET  /api/v1/processes/{id}         → get single process with plan
- GET  /api/v1/processes/{id}/events  → list events for a process
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from framework.persistence.database import create_session
from framework.persistence.process_repo import ProcessRepository
from framework.persistence.models import ProcessStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/processes", tags=["processes"])


@router.get("")
async def list_processes(
    status: Optional[str] = Query(None, description="Filter by status: pending, running, completed, failed"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all processes with optional status filter."""
    session = await create_session()
    try:
        repo = ProcessRepository(session)
        ps = None
        if status:
            try:
                ps = ProcessStatus(status)
            except ValueError:
                raise HTTPException(400, f"Invalid status: {status}. Valid: pending, running, completed, failed")

        processes = await repo.list_processes(status=ps, limit=limit, offset=offset)

        # Get event counts for each process
        result = []
        for p in processes:
            count_q = await session.execute(
                text("SELECT COUNT(*) FROM process_events WHERE process_id = :pid"),
                {"pid": p.id},
            )
            event_count = count_q.scalar() or 0

            # Extract goal from context or plan
            goal = ""
            if p.context and isinstance(p.context, dict):
                goal = p.context.get("goal", "")

            result.append({
                "id": str(p.id),
                "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                "goal": goal,
                "plan_steps": len(p.current_plan.steps) if hasattr(p.current_plan, "steps") else 0,
                "plan_status": p.current_plan.status if hasattr(p.current_plan, "status") else "unknown",
                "event_count": event_count,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            })

        return {"processes": result, "total": len(result), "limit": limit, "offset": offset}

    finally:
        await session.close()


@router.get("/{process_id}")
async def get_process(process_id: str):
    """Get a single process with its full plan."""
    session = await create_session()
    try:
        repo = ProcessRepository(session)
        try:
            proc_uuid = uuid.UUID(process_id)
            p = await repo.get_process(proc_uuid)
        except (ValueError, Exception) as e:
            raise HTTPException(404, f"Process not found: {e}")

        # Get event count
        count_q = await session.execute(
            text("SELECT COUNT(*) FROM process_events WHERE process_id = :pid"),
            {"pid": p.id},
        )
        event_count = count_q.scalar() or 0

        # Serialize plan steps
        plan_steps = []
        if hasattr(p.current_plan, "steps"):
            for step in p.current_plan.steps:
                plan_steps.append({
                    "id": step.id,
                    "actor_name": step.actor_name,
                    "tool_name": step.tool_name,
                    "parameters": step.parameters,
                    "status": step.status,
                })

        goal = ""
        if p.context and isinstance(p.context, dict):
            goal = p.context.get("goal", "")

        return {
            "id": str(p.id),
            "status": p.status.value if hasattr(p.status, "value") else str(p.status),
            "goal": goal,
            "plan": {
                "steps": plan_steps,
                "status": p.current_plan.status if hasattr(p.current_plan, "status") else "unknown",
            },
            "context": p.context,
            "event_count": event_count,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }

    finally:
        await session.close()


@router.get("/{process_id}/events")
async def get_process_events(process_id: str):
    """Get all events for a process, ordered chronologically."""
    session = await create_session()
    try:
        proc_uuid = uuid.UUID(process_id)

        # Verify process exists
        check = await session.execute(
            text("SELECT id FROM processes WHERE id = :pid"),
            {"pid": proc_uuid},
        )
        if not check.scalar():
            raise HTTPException(404, f"Process {process_id} not found")

        # Fetch events
        result = await session.execute(
            text("""
                SELECT id, process_id, agent_id, action_type, message, status, created_at
                FROM process_events
                WHERE process_id = :pid
                ORDER BY created_at ASC
            """),
            {"pid": proc_uuid},
        )
        rows = result.mappings().all()

        events = []
        for row in rows:
            events.append({
                "id": str(row["id"]),
                "process_id": str(row["process_id"]),
                "agent_id": row["agent_id"],
                "action_type": row["action_type"],
                "message": row["message"],
                "status": row["status"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            })

        return {"process_id": process_id, "events": events, "total": len(events)}

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(400, f"Invalid process ID format: {process_id}")
    finally:
        await session.close()
