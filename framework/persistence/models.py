from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Enum, TIMESTAMP, func
from datetime import datetime
import uuid
from enum import Enum as PyEnum


class Base(DeclarativeBase):
    pass


# ============================================================================
# ENUMS (ALIGNÉS AVEC POSTGRES)
# ============================================================================


class ProcessStatus(PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DRY_RUN = "dry_run"


class ProcessEventStatus(PyEnum):
    COMPLETE = "complete"
    ERROR = "error"


# ============================================================================
# PROCESS
# ============================================================================


class Process(Base):
    __tablename__ = "processes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    status: Mapped[ProcessStatus] = mapped_column(
        Enum(
            ProcessStatus,
            name="process_status",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=False,
        default=ProcessStatus.PENDING,
    )

    current_plan: Mapped[dict] = mapped_column(JSONB, nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


# ============================================================================
# PROCESS EVENT
# ============================================================================


class ProcessEvent(Base):
    __tablename__ = "process_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    process_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    agent_id: Mapped[str] = mapped_column(nullable=False)
    action_type: Mapped[str] = mapped_column(nullable=False)
    message: Mapped[str | None]

    status: Mapped[ProcessEventStatus] = mapped_column(
        Enum(
            ProcessEventStatus,
            name="process_event_status",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
