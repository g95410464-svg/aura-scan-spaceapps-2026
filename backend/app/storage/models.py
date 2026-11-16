import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, ForeignKey, JSON, Integer, Float, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid():
    return str(uuid.uuid4())


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Workspace(Base):
    __tablename__ = 'workspaces'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class BrowserSession(Base):
    __tablename__ = 'browser_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id'), index=True)
    csrf: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[int] = mapped_column(Integer, index=True)


class Capture(Base):
    __tablename__ = 'workspace_captures'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id'), index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    device_type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    is_demo: Mapped[bool] = mapped_column(default=False)
    result: Mapped[dict] = mapped_column(JSON)


class Measurement(Base):
    __tablename__ = 'workspace_measurements'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id'), index=True)
    capture_id: Mapped[str] = mapped_column(ForeignKey('workspace_captures.id'), unique=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    measured_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    subject_alias: Mapped[str] = mapped_column(String(80))
    device_type: Mapped[str] = mapped_column(String(30))
    is_demo: Mapped[bool] = mapped_column(default=False)
    readings: Mapped[list] = mapped_column(JSON)
    symptoms: Mapped[str] = mapped_column(Text, default='')
    assessment: Mapped[dict] = mapped_column(JSON)


class AuditEvent(Base):
    __tablename__ = 'workspace_audit_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id'), index=True)
    capture_id: Mapped[str] = mapped_column(ForeignKey('workspace_captures.id'))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    action: Mapped[str] = mapped_column(String(40))
    detail: Mapped[dict] = mapped_column(JSON)


class HealthContext(Base):
    __tablename__ = 'workspace_health_contexts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id'), index=True)
    subject_alias: Mapped[str] = mapped_column(String(80), index=True)
    is_demo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    environment: Mapped[str] = mapped_column(String(30))
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    mood: Mapped[str] = mapped_column(String(30))
    symptoms: Mapped[str] = mapped_column(Text, default='')
    medical_notes: Mapped[str] = mapped_column(Text, default='')
    red_flags: Mapped[list] = mapped_column(JSON, default=list)


class LiveSession(Base):
    __tablename__ = 'workspace_live_sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id'), index=True)
    subject_alias: Mapped[str] = mapped_column(String(80))
    device_type: Mapped[str] = mapped_column(String(30))
    is_demo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    expires_at: Mapped[int] = mapped_column(Integer)
    stopped_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[dict] = mapped_column(JSON, default=dict)


class LiveReading(Base):
    __tablename__ = 'workspace_live_readings'
    __table_args__ = (UniqueConstraint('session_id','sequence'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id'), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('workspace_live_sessions.id'), index=True)
    capture_id: Mapped[str] = mapped_column(ForeignKey('workspace_captures.id'), unique=True)
    sequence: Mapped[int] = mapped_column(Integer)
    subject_alias: Mapped[str] = mapped_column(String(80), index=True)
    device_type: Mapped[str] = mapped_column(String(30))
    is_demo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    readings: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default='pending')


class SimulationRun(Base):
    __tablename__ = 'workspace_simulation_runs'
    __table_args__ = (UniqueConstraint('owner_id','run_key'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('workspaces.id'), index=True)
    run_key: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
