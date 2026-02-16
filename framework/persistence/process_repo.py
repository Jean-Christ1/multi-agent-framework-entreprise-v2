import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from framework.persistence.models import ProcessStatus
from framework.persistence.schemas import ProcessSchema
from framework.types import Plan


class ProcessRepository:
    """Handles saving, loading, and querying processes in persistence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------------------------------------------------
    # CREATE PROCESS
    # ---------------------------------------------------
    async def create_process(
        self,
        process_id: uuid.UUID,
        plan: Plan | Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        status: ProcessStatus | str = ProcessStatus.PENDING,
    ) -> ProcessSchema:
        params = {
            "id": process_id,
            "status": self._normalize_status(status).value,
            "plan": self._plan_to_json(plan),
            "context": self._context_to_json(context),
        }

        query = text(
            """
            INSERT INTO processes (id, status, current_plan, context)
            VALUES (:id, :status, :plan, :context)
            RETURNING id, status, current_plan, context, created_at, updated_at
            """
        )

        result = await self.session.execute(query, params)
        row = result.mappings().one()
        await self.session.commit()
        return self._row_to_schema(row)

    # ---------------------------------------------------
    # UPDATE PROCESS STATE
    # ---------------------------------------------------
    async def update_process(
        self,
        process_id: uuid.UUID,
        plan: Plan | Dict[str, Any],
        context: Dict[str, Any],
        status: Optional[ProcessStatus | str] = None,
    ) -> ProcessSchema:
        set_clauses = [
            "current_plan = :plan",
            "context = :context",
            "updated_at = NOW()",
        ]
        params: Dict[str, Any] = {
            "id": process_id,
            "plan": self._plan_to_json(plan),
            "context": self._context_to_json(context),
        }

        if status is not None:
            params["status"] = self._normalize_status(status).value
            set_clauses.insert(0, "status = :status")

        query = text(
            f"""
            UPDATE processes
            SET {", ".join(set_clauses)}
            WHERE id = :id
            RETURNING id, status, current_plan, context, created_at, updated_at
            """
        )

        result = await self.session.execute(query, params)
        row = result.mappings().one_or_none()

        if row is None:
            await self.session.rollback()
            raise ValueError(f"Process {process_id} does not exist")

        await self.session.commit()
        return self._row_to_schema(row)

    # ---------------------------------------------------
    # FETCH SINGLE PROCESS
    # ---------------------------------------------------
    async def get_process(self, process_id: uuid.UUID) -> ProcessSchema:
        query = text(
            """
            SELECT id, status, current_plan, context, created_at, updated_at
            FROM processes
            WHERE id = :id
            """
        )

        result = await self.session.execute(query, {"id": process_id})
        row = result.mappings().one_or_none()

        if row is None:
            raise ValueError(f"Process {process_id} does not exist")

        return self._row_to_schema(row)

    # ---------------------------------------------------
    # LIST PROCESSES
    # ---------------------------------------------------
    async def list_processes(
        self,
        *,
        status: Optional[ProcessStatus | str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ProcessSchema]:
        where_clauses = []
        params: Dict[str, Any] = {"limit": limit, "offset": offset}

        if status is not None:
            params["status"] = self._normalize_status(status).value
            where_clauses.append("status = :status")

        if from_date is not None:
            params["from_date"] = from_date
            where_clauses.append("created_at >= :from_date")

        if to_date is not None:
            params["to_date"] = to_date
            where_clauses.append("created_at <= :to_date")

        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = text(
            f"""
            SELECT id, status, current_plan, context, created_at, updated_at
            FROM processes
            {where_clause}
            ORDER BY updated_at DESC
            LIMIT :limit OFFSET :offset
            """
        )

        result = await self.session.execute(query, params)
        rows = result.mappings().all()
        return [self._row_to_schema(row) for row in rows]

    # ---------------------------------------------------
    # DELETE PROCESS
    # ---------------------------------------------------
    async def delete_process(self, process_id: uuid.UUID) -> bool:
        """
        Delete a process from the database.

        Args:
            process_id: The UUID of the process to delete

        Returns:
            True if the process was deleted, False if it didn't exist
        """
        query = text(
            """
            DELETE FROM processes
            WHERE id = :id
            """
        )

        result = await self.session.execute(query, {"id": process_id})
        await self.session.commit()
        return result.rowcount > 0  # type: ignore[attr-defined]

    # ---------------------------------------------------
    # LEGACY API (wrappers for backward compatibility)
    # ---------------------------------------------------
    async def save_process(
        self,
        process_id: uuid.UUID,
        plan: Plan | Dict[str, Any],
        context: Dict[str, Any],
    ) -> None:
        await self.update_process(process_id, plan, context)

    async def load_process(
        self,
        process_id: uuid.UUID,
    ) -> Tuple[Plan, Dict[str, Any]]:
        process = await self.get_process(process_id)
        return process.current_plan, process.context

    # ---------------------------------------------------
    # INTERNAL HELPERS
    # ---------------------------------------------------
    @staticmethod
    def _normalize_status(status: ProcessStatus | str) -> ProcessStatus:
        if isinstance(status, ProcessStatus):
            return status
        return ProcessStatus(status)

    @staticmethod
    def _plan_to_json(plan: Plan | Dict[str, Any]) -> str:
        plan_obj = ProcessRepository._ensure_plan(plan)
        return plan_obj.model_dump_json()

    @staticmethod
    def _ensure_plan(plan: Plan | Dict[str, Any]) -> Plan:
        if isinstance(plan, Plan):
            return plan
        if isinstance(plan, dict):
            return Plan.model_validate(plan)
        raise TypeError("plan must be a Plan or dict")

    @staticmethod
    def _context_to_json(context: Optional[Dict[str, Any]]) -> str:
        return json.dumps(context or {})

    @staticmethod
    def _hydrate_plan(raw_plan: Any) -> Plan:
        if isinstance(raw_plan, Plan):
            return raw_plan
        if isinstance(raw_plan, dict):
            return Plan.model_validate(raw_plan)
        if isinstance(raw_plan, str):
            return Plan.model_validate_json(raw_plan)
        raise TypeError("Unsupported plan payload from database")

    @staticmethod
    def _hydrate_context(raw_context: Any) -> Dict[str, Any]:
        if raw_context is None:
            return {}
        if isinstance(raw_context, dict):
            return raw_context
        if isinstance(raw_context, str):
            return json.loads(raw_context)
        return dict(raw_context)

    def _row_to_schema(self, row: Any) -> ProcessSchema:
        plan = self._hydrate_plan(row["current_plan"])
        context = self._hydrate_context(row["context"])
        status = self._normalize_status(row["status"])

        return ProcessSchema(
            id=row["id"],
            status=status,
            current_plan=plan,
            context=context,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
