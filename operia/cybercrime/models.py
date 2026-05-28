from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from operia.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ExternalTool(Base, TimestampMixin):
    __tablename__ = "cybercrime_external_tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    category: Mapped[str] = mapped_column(String(80))
    executable_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    default_command: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_import_formats: Mapped[str] = mapped_column(String(255), default="CSV, JSON, TXT, HTML, PDF, Markdown")
    is_commercial_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    installed_status: Mapped[str] = mapped_column(String(40), default="no verificado")
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    documentation_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    safety_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ToolLaunchLog(Base, TimestampMixin):
    __tablename__ = "cybercrime_tool_launch_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tool_id: Mapped[int] = mapped_column(ForeignKey("cybercrime_external_tools.id"))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    command: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(80), default="registrado")
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class ForensicLabSession(Base, TimestampMixin):
    __tablename__ = "cybercrime_forensic_lab_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    tool_id: Mapped[int | None] = mapped_column(ForeignKey("cybercrime_external_tools.id"), nullable=True)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id"), nullable=True)
    technical_data_id: Mapped[int | None] = mapped_column(ForeignKey("technical_data.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    purpose: Mapped[str] = mapped_column(String(120), default="analisis forense")
    environment_mode: Mapped[str] = mapped_column(String(60), default="local")
    workspace_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    command: Mapped[str | None] = mapped_column(Text, nullable=True)
    command_status: Mapped[str] = mapped_column(String(80), default="pendiente")
    checklist: Mapped[str | None] = mapped_column(Text, nullable=True)
    safety_ack: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_level: Mapped[str] = mapped_column(String(40), default="medio")
    operator: Mapped[str] = mapped_column(String(160), default="Equipo Operia")
    status: Mapped[str] = mapped_column(String(60), default="preparada")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_as: Mapped[str | None] = mapped_column(String(80), nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)


class CTFEvent(Base, TimestampMixin):
    __tablename__ = "cybercrime_ctf_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    platform: Mapped[str] = mapped_column(String(120), default="Cloud CTF")
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    team_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(60), default="activo")


class CTFChallenge(Base, TimestampMixin):
    __tablename__ = "cybercrime_ctf_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("cybercrime_ctf_events.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(120), default="Misc")
    difficulty: Mapped[str] = mapped_column(String(60), default="media")
    points: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    flag_format: Mapped[str] = mapped_column(String(160), default="flag{.*}")
    status: Mapped[str] = mapped_column(String(60), default="no iniciado")
    assigned_to: Mapped[str | None] = mapped_column(String(160), nullable=True)
    solved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_flag: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CTFAnalysisStep(Base, TimestampMixin):
    __tablename__ = "cybercrime_ctf_analysis_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("cybercrime_ctf_challenges.id"))
    lab_session_id: Mapped[int | None] = mapped_column(ForeignKey("cybercrime_forensic_lab_sessions.id"), nullable=True)
    step_type: Mapped[str] = mapped_column(String(80), default="nota")
    tool: Mapped[str | None] = mapped_column(String(160), nullable=True)
    command: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    finding: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(160), default="Equipo Operia")


class DeepfakeAnalysis(Base, TimestampMixin):
    __tablename__ = "cybercrime_deepfake_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id"), nullable=True)
    media_type: Mapped[str] = mapped_column(String(80), default="video")
    checklist: Mapped[str] = mapped_column(Text, default="")
    metadata_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_results: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification: Mapped[str] = mapped_column(String(120), default="requiere analisis experto")
    warning: Mapped[str] = mapped_column(
        Text,
        default="Ninguna herramienta automatica prueba por si sola que un archivo sea deepfake.",
    )


class IoTDevice(Base, TimestampMixin):
    __tablename__ = "cybercrime_iot_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    device_type: Mapped[str] = mapped_column(String(120))
    manufacturer: Mapped[str | None] = mapped_column(String(160), nullable=True)
    model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    firmware: Mapped[str | None] = mapped_column(String(160), nullable=True)
    internal_ip: Mapped[str | None] = mapped_column(String(80), nullable=True)
    external_ip: Mapped[str | None] = mapped_column(String(80), nullable=True)
    mac: Mapped[str | None] = mapped_column(String(80), nullable=True)
    open_ports: Mapped[str | None] = mapped_column(Text, nullable=True)
    known_vulnerabilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    checklist: Mapped[str | None] = mapped_column(Text, nullable=True)


class BlockchainTransaction(Base, TimestampMixin):
    __tablename__ = "cybercrime_blockchain_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    source_wallet: Mapped[str | None] = mapped_column(String(255), nullable=True)
    destination_wallet: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tx_hash: Mapped[str] = mapped_column(String(255))
    blockchain: Mapped[str] = mapped_column(String(80))
    amount: Mapped[float] = mapped_column(Float, default=0)
    token: Mapped[str] = mapped_column(String(40), default="BTC")
    tx_datetime: Mapped[str | None] = mapped_column(String(80), nullable=True)
    explorer_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    approximate_value: Mapped[float] = mapped_column(Float, default=0)
    route_hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProofMatrixRow(Base, TimestampMixin):
    __tablename__ = "cybercrime_proof_matrix_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    technical_data_id: Mapped[int | None] = mapped_column(ForeignKey("technical_data.id"), nullable=True)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id"), nullable=True)
    finding_id: Mapped[int | None] = mapped_column(ForeignKey("findings.id"), nullable=True)
    hypothesis_id: Mapped[int | None] = mapped_column(ForeignKey("hypotheses.id"), nullable=True)
    defensible_conclusion: Mapped[str] = mapped_column(Text)
    legal_framing: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_damage: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_level: Mapped[str] = mapped_column(String(40), default="medio")
    weakness: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="borrador")
    risk_flag: Mapped[str | None] = mapped_column(Text, nullable=True)

