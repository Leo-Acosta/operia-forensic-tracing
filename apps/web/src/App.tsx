import { FormEvent, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  BarChart3,
  BookOpen,
  Bot,
  BrainCircuit,
  Briefcase,
  CheckCircle2,
  Download,
  FileCheck2,
  FileText,
  Fingerprint,
  Gavel,
  Globe2,
  History,
  Map,
  Navigation,
  RefreshCcw,
  Save,
  Search,
  Settings,
  Shield,
  Trash2,
  Upload,
  Users,
  Wrench
} from "lucide-react";
import { API_BASE, apiDelete, apiGet, apiPost, apiPostForm, apiPut, getAuthToken, setAuthToken } from "./api";
import { externalToolsCatalog, type InventoryCyberTool } from "./externalToolsCatalog";

type ModuleKey =
  | "workflow"
  | "dashboard"
  | "caseDetail"
  | "cases"
  | "evidence"
  | "reports"
  | "legalKnowledge"
  | "ai"
  | "cybercrime"
  | "deepfakeMedia"
  | "blockchainForensics"
  | "iotForensics"
  | "externalTools"
  | "aiSecurity"
  | "geoTrace"
  | "geoProximity"
  | "identity"
  | "exports"
  | "history"
  | "settings";

type CaseItem = {
  id: number;
  case_code: string;
  title: string;
  description: string;
  incident_type: string;
  status: string;
  created_at?: string;
  updated_at?: string;
};

type EvidenceItem = {
  id: number;
  case_id: number;
  evidence_type: string;
  description: string;
  sha256_hash: string;
  md5_hash?: string;
  integrity_status: string;
  file_location?: string;
  source?: string;
  responsible?: string;
  custodian?: string;
  preservation_method?: string;
  tool_used?: string;
  confidence_level?: string;
};

type CustodyAction = {
  id: number;
  case_id: number;
  evidence_id?: number;
  action_type: string;
  detailed_description: string;
  hash_after?: string;
  user_responsible?: string;
  tool_used?: string;
  command_or_procedure?: string;
  result_obtained?: string;
  legal_observations?: string;
  status: string;
};

type CaseParticipant = {
  id: number;
  case_id: number;
  participant_type: string;
  person_type: string;
  display_name: string;
  document_type: string;
  document_number: string;
  tax_id: string;
  email: string;
  phone: string;
  address?: string;
  role_description: string;
  relationship_to_case: string;
  notes?: string;
  sensitivity_level: string;
};

type ReportItem = {
  id: number;
  case_id: number;
  title: string;
  version: string;
  status: string;
  author: string;
  review_score: number;
  observations?: string;
};

type ReportPreview = {
  report_id: number;
  title: string;
  author: string;
  status: string;
  review_score: number;
  executive_summary: string;
  can_export_final: boolean;
  exportability: {
    level: string;
    score: number;
    missing_items: string[];
  };
  contradictions: {
    blocking: boolean;
    count: number;
    risk_level: string;
    issues: Array<{ severity: string; norm_reference: string; legal_element: string; message: string; recommended_action: string }>;
  };
  final_checklist: {
    ready: boolean;
    score: number;
    missing: string[];
    items: Array<{ key: string; label: string; ok: boolean; message: string }>;
  };
  annexes: {
    count: number;
    items: Array<{ type: string; title: string; sha256?: string; detail?: string; integrity_status?: string; rows?: number; score?: number }>;
  };
  final_seal?: {
    sealed: boolean;
    seal_id: string;
    observations: string;
    report_version: string;
  } | null;
  sections: Array<{ title: string; word_count: number; excerpt: string; has_tables: boolean }>;
  warnings: string[];
};

type ReportReviewResult = {
  score: number;
  status: string;
  critical_errors: string[];
  warnings: string[];
  suggestions: string[];
  incomplete_sections: string[];
  unsupported_conclusions: string[];
};

type AiEnrichmentResult = {
  status: string;
  report_id?: number;
  message: string;
  observations?: string;
};

type LegalArticle = {
  id: number;
  code: string;
  article_number: string;
  subsection: string;
  title: string;
  text?: string;
  objective_elements: string;
  subjective_elements?: string;
  evidentiary_requirements: string;
  official_url: string;
};

type LegalRecommendation = {
  article_id: number;
  reference: string;
  title: string;
  legal_role: string;
  text: string;
  why: string;
  subjective_elements: string;
  evidence_needed: string;
  applicability_to_case: string;
  probatory_limits: string;
  incident_relations?: string;
  sensitive?: boolean;
  warning?: string;
  confidence: string;
  source_title?: string;
  source_citation?: string;
  source_verified?: boolean;
  source_url: string;
  precedents: unknown[];
  doctrine: unknown[];
};

type LegalRecommendationResponse = {
  profile?: {
    key: string;
    label: string;
    legal_theory: string;
    required_evidence: string[];
    recommended_measures: string[];
  };
  recommendations: LegalRecommendation[];
  disclaimer?: string;
};

type LegalTypificationResult = {
  case_id: number;
  case_code: string;
  profile?: LegalRecommendationResponse["profile"];
  principal_typification?: LegalRecommendation;
  connected_typifications: LegalRecommendation[];
  confidence: string;
  readiness_score: number;
  decision_level: string;
  evidence_snapshot: {
    evidence_count: number;
    custody_actions: number;
    approved_legal_mappings: number;
  };
  missing_for_stronger_typification: string[];
  recommended_measures: string[];
  suggested_mapping_ids: number[];
  registered_sources_only: boolean;
  human_review_required: boolean;
  external_api_used: boolean;
};

type CaseAnalysisResult = {
  case_id?: number;
  incident_type?: string;
  legal_profile?: LegalRecommendationResponse["profile"];
  recommended_articles?: LegalRecommendation[];
  operational_next_steps?: string[];
  human_review_required?: boolean;
  external_api_used?: boolean;
  status?: string;
  response?: string;
  safety_notes?: string;
};

type LegalMapping = {
  id: number;
  case_id: number;
  article_id?: number;
  legal_area: string;
  norm_reference: string;
  analysis: string;
  verification_status: string;
  confidence_level: string;
  decision_status: string;
  analyst_name: string;
  analyst_rationale: string;
  legal_role: string;
  applicability_to_case: string;
  probatory_limits: string;
  decided_at: string;
};

type LegalMappingEvidence = {
  id: number;
  case_id: number;
  legal_mapping_id: number;
  evidence_id: number;
  linked_by: string;
  link_rationale: string;
  legal_element: string;
  probatory_strength: string;
  element_status: string;
  missing_evidence: string;
  contradiction_risk: string;
  recommended_measure: string;
};

type LegalProbatoryMatrix = {
  case_id: number;
  rows: Array<{
    mapping_id: number;
    article_id?: number;
    norm_reference: string;
    legal_role: string;
    legal_element: string;
    element_status: string;
    evidence_id?: number;
    evidence_description: string;
    evidence_hash: string;
    probatory_strength: string;
    missing_evidence: string;
    contradiction_risk: string;
    recommended_measure: string;
  }>;
  summary: Record<string, number>;
};

type LegalQualityControl = {
  case_id: number;
  score: number;
  risk_level: string;
  conclusion_impact: string;
  issues: Array<{ severity: string; code: string; message: string; recommended_action: string }>;
  matrix_summary: Record<string, number>;
};

type RubricSection = {
  key: string;
  label: string;
  weight: number;
  criteria: string[];
  expected_components: string[];
  minimum_fields: string[];
  status: "incompleto" | "parcial" | "completo";
  estimated_score: number;
  max_score: number;
  completion_ratio: number;
  missing: string[];
  recommendations: string[];
};

type RubricEvaluation = {
  id: number;
  case_id: number;
  rubric_key: string;
  rubric_title: string;
  total_score: number;
  max_score: number;
  percentage: number;
  status: "incompleto" | "parcial" | "completo";
  sections: RubricSection[];
  missing: string[];
  recommendations: string[];
  summary: string;
  evaluated_by: string;
  created_at: string;
  updated_at: string;
};

type DashboardPayload = {
  metrics?: Record<string, number>;
  alerts?: string[];
  cases_by_status?: Record<string, number>;
  report_readiness?: Array<{ report_id: number; title: string; status: string; review_score: number; ready_for_final: boolean }>;
};

type ClosureStatus = {
  case_id: number;
  status: string;
  ready_to_close: boolean;
  already_closed: boolean;
  missing: string[];
  requirements: Record<string, boolean>;
  counts: Record<string, number>;
  message?: string;
  closure_warnings?: string[];
  closure_mode?: string;
};

type AuditLog = {
  id: number;
  case_id?: number;
  action: string;
  module: string;
  entity_type: string;
  entity_id: string;
  severity: string;
  details: string;
  created_at: string;
};

type ExportManifest = {
  id: number;
  case_id?: number;
  report_id?: number;
  export_type: string;
  filename: string;
  sha256_hash: string;
  created_at: string;
};

type IdentitySession = {
  authenticated: boolean;
  user?: {
    id: number;
    organization_id?: number;
    name: string;
    email?: string;
    role: string;
  } | null;
};

type PermissionPayload = Record<string, string[]>;
type CaseDetailTab = "summary" | "participants" | "evidence" | "custody" | "legal" | "reports" | "audit";

type CybercrimeDashboard = {
  open_cases: number;
  closed_cases: number;
  evidence_count: number;
  tools_available: number;
  tools_missing: number;
  lab_sessions: number;
  ctf_events: number;
  ctf_challenges: number;
  deepfake_analyses: number;
  iot_devices: number;
  blockchain_transactions: number;
  proof_matrix_rows: number;
};

type CyberIndicatorResult = {
  indicator: string;
  indicator_type: string;
  risk_level: string;
  confidence: string;
  findings: string[];
  observables: Record<string, unknown>;
  recommended_actions: string[];
  legal_relevance: string;
  human_review_required: boolean;
};

type CyberTool = {
  id: number;
  name: string;
  category: string;
  executable_path?: string;
  default_command?: string;
  result_import_formats?: string;
  is_commercial_optional?: boolean;
  installed_status: string;
  notes?: string;
  website_url?: string;
  documentation_url?: string;
  safety_notes?: string;
};

type CyberLabSession = {
  id: number;
  session_code: string;
  case_id?: number;
  tool_id?: number;
  title: string;
  purpose: string;
  command_status: string;
  risk_level: string;
  operator: string;
  status: string;
  result_summary?: string;
};

type CyberProofRow = {
  id: number;
  case_id: number;
  defensible_conclusion: string;
  legal_framing?: string;
  confidence_level: string;
  weakness?: string;
  status: string;
  risk_flag?: string;
};

type DeepfakeAnalysisItem = {
  id: number;
  case_id: number;
  evidence_id?: number;
  evidence_description?: string;
  finding_id?: number;
  media_type: string;
  source_origin: string;
  evidence_hash: string;
  metadata_summary: string;
  checklist: Array<{ key: string; label: string; ok: boolean; note: string }>;
  tool_used: string;
  findings: string;
  limitations: string;
  classification: string;
  legal_relevance: string;
  legal_mapping_ids: number[];
  analyst_name: string;
  warning: string;
};

type BlockchainTransactionItem = {
  id: number;
  case_id: number;
  evidence_id?: number;
  evidence_description?: string;
  finding_id?: number;
  source_wallet: string;
  destination_wallet: string;
  tx_hash: string;
  blockchain: string;
  token: string;
  amount: number;
  approximate_value: number;
  tx_datetime: string;
  explorer_url: string;
  route_hypothesis: string;
  wallet_classification: string;
  evidence_hash: string;
  tool_used: string;
  limitations: string;
  recommended_measures: string[];
  legal_mapping_ids: number[];
  analyst_name: string;
  warning: string;
};

type IoTDeviceItem = {
  id: number;
  case_id: number;
  evidence_id?: number;
  evidence_description?: string;
  finding_id?: number;
  device_type: string;
  manufacturer: string;
  model: string;
  firmware: string;
  internal_ip: string;
  external_ip: string;
  mac: string;
  open_ports: string;
  known_vulnerabilities: string;
  logs_available: string;
  evidence_hash: string;
  checklist: Array<{ key: string; label: string; ok: boolean; note: string }>;
  tool_used: string;
  limitations: string;
  recommended_measures: string[];
  legal_mapping_ids: number[];
  analyst_name: string;
  warning: string;
};

const modules: Array<{ key: ModuleKey; label: string; icon: typeof BarChart3 }> = [
  { key: "workflow", label: "Flujo Operativo", icon: CheckCircle2 },
  { key: "dashboard", label: "Dashboard", icon: BarChart3 },
  { key: "caseDetail", label: "Detalle del Caso", icon: FileCheck2 },
  { key: "cases", label: "Casos", icon: Briefcase },
  { key: "evidence", label: "Evidencia", icon: Fingerprint },
  { key: "reports", label: "Informes", icon: FileText },
  { key: "legalKnowledge", label: "Biblioteca Legal", icon: BookOpen },
  { key: "ai", label: "Asistente IA", icon: Bot },
  { key: "cybercrime", label: "Cybercrime", icon: Shield },
  { key: "deepfakeMedia", label: "Deepfake / Medios", icon: FileCheck2 },
  { key: "blockchainForensics", label: "Blockchain Forensics", icon: Globe2 },
  { key: "iotForensics", label: "IoT Forensics", icon: Shield },
  { key: "externalTools", label: "Herramientas Externas", icon: Wrench },
  { key: "aiSecurity", label: "AI Security", icon: BrainCircuit },
  { key: "geoTrace", label: "Geo Trace", icon: Map },
  { key: "geoProximity", label: "Geo Proximity", icon: Navigation },
  { key: "identity", label: "Usuarios", icon: Users },
  { key: "exports", label: "Exportaciones", icon: Download },
  { key: "history", label: "Historial", icon: History },
  { key: "settings", label: "Configuracion", icon: Settings }
];

const emptyCase = {
  case_code: "",
  title: "",
  description: "",
  incident_type: "phishing / fraude digital",
  responsible: "",
  client_or_victim: "",
  status: "abierto",
  jurisdiction: "Argentina",
  general_observations: ""
};

const attackTypes = [
  { value: "phishing / fraude digital", label: "Phishing / fraude digital", query: "phishing fraude acceso datos consumidor" },
  { value: "ransomware", label: "Ransomware", query: "ransomware extorsión daño informático preservación" },
  { value: "acceso ilegitimo", label: "Acceso ilegítimo", query: "acceso ilegítimo sistema dato informático" },
  { value: "fraude digital", label: "Fraude digital", query: "fraude estafa manipulación informática consumidor" },
  { value: "dano informatico", label: "Daño informático", query: "daño informático sistemas datos" },
  { value: "filtracion de datos", label: "Filtración de datos", query: "filtración datos personales confidencialidad" },
  { value: "extorsion", label: "Extorsión", query: "extorsión intimidación datos ransomware" },
  { value: "deepfake", label: "Deepfake / autenticación de medios", query: "deepfake autenticación medios imagen voz identidad propiedad intelectual" },
  { value: "blockchain", label: "Blockchain / criptoactivos", query: "blockchain criptoactivos wallet fraude estafa extorsión" },
  { value: "iot", label: "IoT / dispositivos conectados", query: "iot dispositivos conectados acceso ilegítimo comunicaciones daño informático" },
  { value: "falsedad documental digital", label: "Falsedad documental digital", query: "falsedad documental digital documento falso uso certificado firma" },
  { value: "otro", label: "Otro", query: "incidente informático evidencia digital" }
];

const deepfakeChecklist = [
  { key: "source_origin", label: "Origen del archivo" },
  { key: "original_preserved", label: "Preservación de original" },
  { key: "hash", label: "Hash" },
  { key: "metadata", label: "Metadatos EXIF/media" },
  { key: "compression", label: "Compresión" },
  { key: "visual_inconsistencies", label: "Inconsistencias visuales" },
  { key: "audio_inconsistencies", label: "Inconsistencias de audio" },
  { key: "lip_sync", label: "Sincronización labial" },
  { key: "frame_analysis", label: "Análisis frame-by-frame" },
  { key: "known_source_comparison", label: "Comparación con fuente conocida" },
  { key: "publication_traceability", label: "Trazabilidad de publicación" },
  { key: "external_tool_used", label: "Herramienta externa usada" },
  { key: "limitations", label: "Limitaciones" }
];

const emptyDeepfakeChecklist = Object.fromEntries(deepfakeChecklist.map((item) => [item.key, false])) as Record<string, boolean>;

const emptyDeepfakeForm = {
  evidence_id: "",
  media_type: "video",
  source_origin: "",
  metadata_summary: "",
  tool_used: "OPERIA Deepfake Lab",
  findings: "",
  limitations: "Resultado preliminar sujeto a pericia especializada y corroboración independiente.",
  classification: "no concluyente"
};

const walletClassifications = [
  "wallet personal no verificada",
  "exchange",
  "mixer",
  "bridge",
  "contrato inteligente",
  "wallet receptora",
  "wallet intermediaria",
  "desconocido"
];

const emptyBlockchainForm = {
  evidence_id: "",
  source_wallet: "",
  destination_wallet: "",
  tx_hash: "",
  blockchain: "Bitcoin",
  token: "BTC",
  amount: "",
  approximate_value: "",
  tx_datetime: "",
  explorer_url: "",
  route_hypothesis: "",
  wallet_classification: "desconocido",
  tool_used: "OPERIA Blockchain Forensics",
  limitations: "Una wallet no identifica por sí sola a una persona sin evidencia externa corroborante."
};

const iotChecklist = [
  { key: "physical_identification", label: "Identificación física" },
  { key: "photo_capture", label: "Fotografía/captura" },
  { key: "evidence_hash", label: "Hash de evidencia" },
  { key: "firmware", label: "Firmware" },
  { key: "configuration", label: "Configuración" },
  { key: "logs", label: "Logs" },
  { key: "ports", label: "Puertos" },
  { key: "default_credentials", label: "Credenciales por defecto" },
  { key: "network_connection", label: "Conexión a red" },
  { key: "timeline", label: "Línea temporal" },
  { key: "state_preservation", label: "Preservación de estado" },
  { key: "alteration_risk", label: "Riesgo de alteración" }
];

const emptyIoTChecklist = Object.fromEntries(iotChecklist.map((item) => [item.key, false])) as Record<string, boolean>;

const emptyIoTForm = {
  evidence_id: "",
  device_type: "cámara IP",
  manufacturer: "",
  model: "",
  firmware: "",
  internal_ip: "",
  external_ip: "",
  mac: "",
  open_ports: "",
  known_vulnerabilities: "",
  logs_available: "",
  tool_used: "OPERIA IoT Forensics",
  limitations: "No se ejecutaron escaneos reales. Requiere autorización, preservación de estado y correlación externa."
};

function prettySpanish(value = "") {
  return value
    .replace(/\bDano\b/g, "Daño")
    .replace(/\bdano\b/g, "daño")
    .replace(/\bdanino\b/g, "dañino")
    .replace(/\bDanino\b/g, "Dañino")
    .replace(/\bengano\b/g, "engaño")
    .replace(/\bEngano\b/g, "Engaño")
    .replace(/\bilegitimo\b/g, "ilegítimo")
    .replace(/\binformatico\b/g, "informático")
    .replace(/\binformaticos\b/g, "informáticos")
    .replace(/\bpublicos\b/g, "públicos")
    .replace(/\brapida\b/g, "rápida")
    .replace(/\balmacenados\b/g, "almacenados")
    .replace(/\bpreservacion\b/g, "preservación")
    .replace(/\bcuantificacion\b/g, "cuantificación")
    .replace(/\bvictima\b/g, "víctima")
    .replace(/\bdisposicion\b/g, "disposición")
    .replace(/\bdefraudacion\b/g, "defraudación")
    .replace(/\beconomica\b/g, "económica")
    .replace(/\btecnica\b/g, "técnica")
    .replace(/\bjuridica\b/g, "jurídica")
    .replace(/\bcriticas\b/g, "críticas");
}

function professionalReportStatus(status = "") {
  const normalized = status.toLowerCase();
  if (normalized.includes("cerrado") || normalized.includes("final")) return "Caso Cerrado";
  if (normalized.includes("investigativo") || normalized.includes("enriquecido") || normalized.includes("ia")) return "En Proceso Investigativo";
  if (normalized.includes("analisis") || normalized.includes("análisis")) return "En Proceso de Análisis";
  return "Caso en Proceso de Inicio de Investigación";
}

function reportExportabilitySnapshot(
  selectedCase: CaseItem | undefined,
  evidence: EvidenceItem[],
  custody: CustodyAction[],
  legalMappings: LegalMapping[],
  legalProbatoryMatrix: LegalProbatoryMatrix | null,
  legalQualityControl: LegalQualityControl | null,
  latestReport?: ReportItem
) {
  const checklist = {
    analyst_present: Boolean(latestReport?.author),
    case_narrative: Boolean(selectedCase?.description),
    evidence_present: evidence.length > 0,
    hashes_present: evidence.length > 0 && evidence.every((item) => Boolean(item.sha256_hash)),
    custody_present: custody.length > 0,
    approved_legal_mapping: legalMappings.some((item) => item.decision_status !== "descartado"),
    matrix_has_support: Boolean(legalProbatoryMatrix?.rows.some((row) => row.evidence_id || row.evidence_description)),
    critical_gaps_absent: Boolean(legalQualityControl && legalQualityControl.risk_level === "bajo"),
    human_review_score: Boolean(latestReport && latestReport.review_score >= 80)
  };
  const weights: Record<keyof typeof checklist, number> = {
    analyst_present: 8,
    case_narrative: 8,
    evidence_present: 14,
    hashes_present: 12,
    custody_present: 12,
    approved_legal_mapping: 16,
    matrix_has_support: 14,
    critical_gaps_absent: 10,
    human_review_score: 6
  };
  const score = Object.entries(checklist).reduce((total, [key, value]) => total + (value ? weights[key as keyof typeof checklist] : 0), 0);
  const level =
    score >= 86 && checklist.critical_gaps_absent && checklist.human_review_score
      ? "Apto para presentación"
      : score >= 68 && checklist.approved_legal_mapping && checklist.evidence_present
        ? "Listo para revisión"
        : score >= 38 && checklist.evidence_present
          ? "Informe preliminar"
          : "Borrador técnico";
  const missing = [
    !checklist.analyst_present && "Analista",
    !checklist.case_narrative && "Narrativa",
    !checklist.evidence_present && "Evidencia",
    !checklist.hashes_present && "Hashes",
    !checklist.custody_present && "Custodia",
    !checklist.approved_legal_mapping && "Mapeo legal",
    !checklist.matrix_has_support && "Vínculo norma-evidencia",
    !checklist.critical_gaps_absent && "Semáforo legal bajo",
    !checklist.human_review_score && "Revisión humana"
  ].filter(Boolean);
  return { score, level: prettySpanish(level), missing };
}

function MetricGrid({ metrics }: { metrics: Record<string, number> }) {
  return (
    <div className="metric-grid">
      {Object.entries(metrics).map(([key, value]) => (
        <div className="metric" key={key}>
          <span>{key.replace(/_/g, " ")}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}

function JsonPanel({ data }: { data: unknown }) {
  return <pre>{data ? JSON.stringify(data, null, 2) : "Sin resultados todavia."}</pre>;
}

function StepCard({
  number,
  title,
  done,
  children
}: {
  number: number;
  title: string;
  done?: boolean;
  children: ReactNode;
}) {
  return (
    <section className={`step-card ${done ? "done" : ""}`}>
      <div className="step-title">
        <span className="step-number">{number}</span>
        <h3>{title}</h3>
        {done && (
          <span className="step-state">
            <CheckCircle2 size={14} />
            Completado
          </span>
        )}
      </div>
      {children}
    </section>
  );
}

export function App() {
  const [active, setActive] = useState<ModuleKey>("workflow");
  const [caseDetailTab, setCaseDetailTab] = useState<CaseDetailTab>("summary");
  const [dashboard, setDashboard] = useState<DashboardPayload>({});
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<number | "">("");
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [participants, setParticipants] = useState<CaseParticipant[]>([]);
  const [custody, setCustody] = useState<CustodyAction[]>([]);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [manifests, setManifests] = useState<ExportManifest[]>([]);
  const [legalMappings, setLegalMappings] = useState<LegalMapping[]>([]);
  const [legalMappingEvidence, setLegalMappingEvidence] = useState<LegalMappingEvidence[]>([]);
  const [legalProbatoryMatrix, setLegalProbatoryMatrix] = useState<LegalProbatoryMatrix | null>(null);
  const [legalQualityControl, setLegalQualityControl] = useState<LegalQualityControl | null>(null);
  const [legalEvidenceSelection, setLegalEvidenceSelection] = useState<Record<number, string>>({});
  const [legalElementSelection, setLegalElementSelection] = useState<Record<number, string>>({});
  const [legalLinkDrafts, setLegalLinkDrafts] = useState<Record<number, Partial<LegalMappingEvidence>>>({});
  const [articles, setArticles] = useState<LegalArticle[]>([]);
  const [modulePayload, setModulePayload] = useState<unknown>(null);
  const [authToken, setAuthTokenState] = useState(getAuthToken());
  const [identitySession, setIdentitySession] = useState<IdentitySession>({ authenticated: false });
  const [permissions, setPermissions] = useState<PermissionPayload>({});
  const [loginForm, setLoginForm] = useState({ email: "", password: "" });
  const [bootstrapForm, setBootstrapForm] = useState({
    organization_name: "OPERIA Local",
    organization_slug: "operia-local",
    name: "OPERIA Admin",
    email: "admin@operia.local",
    password: "operia-admin-change-me"
  });
  const [caseForm, setCaseForm] = useState(emptyCase);
  const [participantForm, setParticipantForm] = useState({
    participant_type: "damnificado",
    person_type: "persona_fisica",
    display_name: "",
    document_type: "",
    document_number: "",
    tax_id: "",
    email: "",
    phone: "",
    address: "",
    role_description: "",
    relationship_to_case: "",
    notes: "",
    sensitivity_level: "reservado"
  });
  const [editingParticipant, setEditingParticipant] = useState<CaseParticipant | null>(null);
  const [evidenceForm, setEvidenceForm] = useState({ description: "", responsible: "", custodian: "" });
  const [editingEvidence, setEditingEvidence] = useState<EvidenceItem | null>(null);
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [custodyForm, setCustodyForm] = useState({ action_type: "revision", detailed_description: "", user_responsible: "" });
  const [editingCustody, setEditingCustody] = useState<CustodyAction | null>(null);
  const [indicator, setIndicator] = useState("https://secure-login.example.com/verify");
  const [indicatorResult, setIndicatorResult] = useState<CyberIndicatorResult | null>(null);
  const [indicatorFindingState, setIndicatorFindingState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [indicatorFindingMessage, setIndicatorFindingMessage] = useState("");
  const [cyberDashboard, setCyberDashboard] = useState<CybercrimeDashboard | null>(null);
  const [cyberTools, setCyberTools] = useState<CyberTool[]>([]);
  const [cyberLabSessions, setCyberLabSessions] = useState<CyberLabSession[]>([]);
  const [cyberProofRows, setCyberProofRows] = useState<CyberProofRow[]>([]);
  const [deepfakeAnalyses, setDeepfakeAnalyses] = useState<DeepfakeAnalysisItem[]>([]);
  const [deepfakeForm, setDeepfakeForm] = useState(emptyDeepfakeForm);
  const [deepfakeChecklistState, setDeepfakeChecklistState] = useState<Record<string, boolean>>(emptyDeepfakeChecklist);
  const [deepfakeState, setDeepfakeState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [deepfakeMessage, setDeepfakeMessage] = useState("");
  const [blockchainTransactions, setBlockchainTransactions] = useState<BlockchainTransactionItem[]>([]);
  const [blockchainForm, setBlockchainForm] = useState(emptyBlockchainForm);
  const [blockchainState, setBlockchainState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [blockchainMessage, setBlockchainMessage] = useState("");
  const [iotDevices, setIotDevices] = useState<IoTDeviceItem[]>([]);
  const [iotForm, setIotForm] = useState(emptyIoTForm);
  const [iotChecklistState, setIotChecklistState] = useState<Record<string, boolean>>(emptyIoTChecklist);
  const [iotState, setIotState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [iotMessage, setIotMessage] = useState("");
  const [cyberToolForm, setCyberToolForm] = useState({ name: "", category: "osint", executable_path: "", default_command: "", notes: "", website_url: "", documentation_url: "", safety_notes: "" });
  const [externalToolQuery, setExternalToolQuery] = useState("");
  const [externalToolCategory, setExternalToolCategory] = useState("Todas");
  const [externalToolOs, setExternalToolOs] = useState("Todos");
  const [externalToolDifficulty, setExternalToolDifficulty] = useState("Todas");
  const [externalToolOnlineOnly, setExternalToolOnlineOnly] = useState(false);
  const [externalToolGithubOnly, setExternalToolGithubOnly] = useState(false);
  const [externalToolSpecialArea, setExternalToolSpecialArea] = useState("Todas");
  const [cyberLabForm, setCyberLabForm] = useState({ title: "", purpose: "analisis de indicador", risk_level: "medio", operator: "" });
  const [cyberProofForm, setCyberProofForm] = useState({
    defensible_conclusion: "",
    legal_framing: "",
    confidence_level: "medio",
    weakness: ""
  });
  const [legalQuery, setLegalQuery] = useState("phishing fraude acceso datos");
  const [legalRecommendation, setLegalRecommendation] = useState<LegalRecommendationResponse | null>(null);
  const [aiPrompt, setAiPrompt] = useState("Analiza el caso, evidencia cargada, riesgos y proximos pasos. No inventes normas legales.");
  const [aiResult, setAiResult] = useState<unknown>(null);
  const [aiEnrichmentResult, setAiEnrichmentResult] = useState<AiEnrichmentResult | null>(null);
  const [legalTypification, setLegalTypification] = useState<LegalTypificationResult | null>(null);
  const [legalApplyState, setLegalApplyState] = useState<"idle" | "applying" | "applied" | "error">("idle");
  const [legalApplyMessage, setLegalApplyMessage] = useState("");
  const [analystName, setAnalystName] = useState(localStorage.getItem("operia_analyst_name") || "");
  const [reviewResult, setReviewResult] = useState<unknown>(null);
  const [reviewAudit, setReviewAudit] = useState<ReportReviewResult | null>(null);
  const [reportPreview, setReportPreview] = useState<ReportPreview | null>(null);
  const [rubricEvaluation, setRubricEvaluation] = useState<RubricEvaluation | null>(null);
  const [rubricState, setRubricState] = useState<"idle" | "updating" | "updated" | "error">("idle");
  const [rubricMessage, setRubricMessage] = useState("");
  const [executiveSummaryDraft, setExecutiveSummaryDraft] = useState("");
  const [exportFinalResult, setExportFinalResult] = useState<unknown>(null);
  const [closureStatus, setClosureStatus] = useState<ClosureStatus | null>(null);
  const [closureNote, setClosureNote] = useState("Cierre operativo con evidencia preservada, informe revisado y PDF exportado.");
  const [aiSecurityResult, setAiSecurityResult] = useState<unknown>(null);
  const [ctfDashboardState, setCtfDashboardState] = useState<"idle" | "working" | "success" | "error">("idle");
  const [ctfDashboardMessage, setCtfDashboardMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedCase = useMemo(() => cases.find((item) => item.id === Number(selectedCaseId)), [cases, selectedCaseId]);
  const chronologicalCases = useMemo(
    () => [...cases].sort((a, b) => caseTimestamp(b) - caseTimestamp(a)),
    [cases]
  );
  const latestReport = reports[0];
  const latestEvidence = evidence[0];
  const exportabilitySnapshot = useMemo(
    () => reportExportabilitySnapshot(selectedCase, evidence, custody, legalMappings, legalProbatoryMatrix, legalQualityControl, latestReport),
    [selectedCase, evidence, custody, legalMappings, legalProbatoryMatrix, legalQualityControl, latestReport]
  );

  async function refreshCaseCollections(caseId: number | "") {
    if (!caseId) {
      setEvidence([]);
      setParticipants([]);
      setReports([]);
      setCustody([]);
      setAuditLogs([]);
      setManifests([]);
      setLegalMappings([]);
      setLegalMappingEvidence([]);
      setDeepfakeAnalyses([]);
      setBlockchainTransactions([]);
      setIotDevices([]);
      setLegalProbatoryMatrix(null);
      setLegalQualityControl(null);
      setRubricEvaluation(null);
      setRubricState("idle");
      setRubricMessage("");
      setLegalElementSelection({});
      setLegalLinkDrafts({});
      setReportPreview(null);
      setExecutiveSummaryDraft("");
      setClosureStatus(null);
      return;
    }
    const [
      participantData,
      evidenceData,
      reportData,
      custodyData,
      auditData,
      manifestData,
      mappingData,
      mappingEvidenceData,
      probatoryMatrixData,
      qualityControlData,
      deepfakeData,
      blockchainData,
      iotData,
      rubricData
    ] = await Promise.all([
      apiGet<CaseParticipant[]>(`/cases/${caseId}/participants`),
      apiGet<EvidenceItem[]>(`/evidence/case/${caseId}`),
      apiGet<ReportItem[]>(`/reports/case/${caseId}`),
      apiGet<CustodyAction[]>(`/evidence/case/${caseId}/custody-actions`),
      apiGet<AuditLog[]>(`/audit/logs?case_id=${caseId}`),
      apiGet<ExportManifest[]>(`/exports/manifests?case_id=${caseId}`),
      apiGet<LegalMapping[]>(`/legal-knowledge/case/${caseId}/mappings`),
      apiGet<LegalMappingEvidence[]>(`/legal-knowledge/case/${caseId}/mapping-evidence`),
      apiGet<LegalProbatoryMatrix>(`/legal-knowledge/case/${caseId}/probatory-matrix`),
      apiGet<LegalQualityControl>(`/legal-knowledge/case/${caseId}/quality-control`),
      apiGet<DeepfakeAnalysisItem[]>(`/cybercrime/deepfake/case/${caseId}`).catch(() => []),
      apiGet<BlockchainTransactionItem[]>(`/cybercrime/blockchain/case/${caseId}`).catch(() => []),
      apiGet<IoTDeviceItem[]>(`/cybercrime/iot/case/${caseId}`).catch(() => []),
      apiGet<RubricEvaluation>(`/rubrics/case/${caseId}/score`).catch(() => null)
    ]);
    setParticipants(participantData);
    setEvidence(evidenceData);
    setReports(reportData);
    setCustody(custodyData);
    setAuditLogs(auditData);
    setManifests(manifestData);
    setLegalMappings(mappingData);
    setLegalMappingEvidence(mappingEvidenceData);
    setDeepfakeAnalyses(deepfakeData);
    setBlockchainTransactions(blockchainData);
    setIotDevices(iotData);
    setLegalProbatoryMatrix(probatoryMatrixData);
    setLegalQualityControl(qualityControlData);
    setRubricEvaluation(rubricData);
    setReportPreview(null);
    setExecutiveSummaryDraft("");
    setClosureStatus(await apiGet<ClosureStatus>(`/cases/${caseId}/closure-status`));
  }

  async function refreshCore() {
    setError("");
    const [dashboardData, casesData] = await Promise.all([
      apiGet<DashboardPayload>("/dashboard/"),
      apiGet<CaseItem[]>("/cases")
    ]);
    setDashboard(dashboardData);
    setCases(casesData);
    const nextCaseId = selectedCaseId || casesData[0]?.id || "";
    setSelectedCaseId(nextCaseId);
    await refreshCaseCollections(nextCaseId);
  }

  async function loadModule(key: ModuleKey) {
    setLoading(true);
    setError("");
    try {
      if (["workflow", "dashboard", "cases", "evidence", "reports"].includes(key)) {
        await refreshCore();
        return;
      }
      if (key === "legalKnowledge") {
        setArticles(await apiGet<LegalArticle[]>(`/legal-knowledge/articles?q=${encodeURIComponent(legalQuery)}`));
        return;
      }
      if (key === "identity") {
        await refreshIdentity();
        return;
      }
      if (key === "cybercrime") {
        await refreshCybercrime();
        return;
      }
      if (key === "deepfakeMedia") {
        await refreshCybercrime();
        return;
      }
      if (key === "blockchainForensics") {
        await refreshCybercrime();
        return;
      }
      if (key === "iotForensics") {
        await refreshCybercrime();
        return;
      }
      if (key === "externalTools") {
        setModulePayload({ tools: externalToolsCatalog.length, mode: "external_inventory" });
        return;
      }
      const paths: Partial<Record<ModuleKey, string>> = {
        ai: "/ai/",
        aiSecurity: "/ai-security/",
        geoTrace: "/geo/trace/",
        geoProximity: "/geo/proximity/",
        identity: "/identity/",
        exports: "/exports/",
        settings: "/settings/readiness"
      };
      if (paths[key]) setModulePayload(await apiGet(paths[key]));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo conectar con la API.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadModule(active);
  }, [active]);

  useEffect(() => {
    refreshIdentity().catch(() => undefined);
  }, [authToken]);

  useEffect(() => {
    refreshCaseCollections(selectedCaseId).catch((err: Error) => setError(err.message));
  }, [selectedCaseId]);

  async function refreshIdentity() {
    const [session, permissionData] = await Promise.all([
      apiGet<IdentitySession>("/identity/me"),
      apiGet<PermissionPayload>("/identity/permissions")
    ]);
    setIdentitySession(session);
    setPermissions(permissionData);
    setModulePayload({ session, permissions: permissionData });
  }

  function caseTimestamp(item: CaseItem) {
    const value = item.updated_at || item.created_at || "";
    const parsed = value ? new Date(value).getTime() : 0;
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function formatHistoryDate(value?: string) {
    if (!value) return "Sin fecha registrada";
    const date = new Date(value);
    if (!Number.isFinite(date.getTime())) return "Sin fecha registrada";
    return date.toLocaleString("es-AR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  }

  function openCaseFromHistory(caseId: number, destination: ModuleKey = "workflow") {
    setSelectedCaseId(caseId);
    setActive(destination);
    if (destination === "caseDetail") setCaseDetailTab("summary");
    setModulePayload({ status: "historial_caso_abierto", case_id: caseId });
  }

  async function refreshCybercrime() {
    const caseParam = selectedCaseId ? `?case_id=${selectedCaseId}` : "";
    const [dashboardData, toolsData, labData, proofRowsData, deepfakeData, blockchainData, iotData] = await Promise.all([
      apiGet<CybercrimeDashboard>("/cybercrime/dashboard"),
      apiGet<CyberTool[]>("/cybercrime/tools"),
      apiGet<CyberLabSession[]>(`/cybercrime/lab/sessions${caseParam}`),
      selectedCaseId ? apiGet<CyberProofRow[]>(`/cybercrime/proof-matrix${caseParam}`) : Promise.resolve([]),
      selectedCaseId ? apiGet<DeepfakeAnalysisItem[]>(`/cybercrime/deepfake/case/${selectedCaseId}`) : Promise.resolve([]),
      selectedCaseId ? apiGet<BlockchainTransactionItem[]>(`/cybercrime/blockchain/case/${selectedCaseId}`) : Promise.resolve([]),
      selectedCaseId ? apiGet<IoTDeviceItem[]>(`/cybercrime/iot/case/${selectedCaseId}`) : Promise.resolve([])
    ]);
    setCyberDashboard(dashboardData);
    setCyberTools(toolsData);
    setCyberLabSessions(labData);
    setCyberProofRows(proofRowsData);
    setDeepfakeAnalyses(deepfakeData);
    setBlockchainTransactions(blockchainData);
    setIotDevices(iotData);
    setModulePayload({ dashboard: dashboardData, tools: toolsData.length, lab_sessions: labData.length, proof_rows: proofRowsData.length, deepfake_analyses: deepfakeData.length, blockchain_transactions: blockchainData.length, iot_devices: iotData.length });
  }

  async function login(event: FormEvent) {
    event.preventDefault();
    const result = await apiPost<{ access_token: string; user: IdentitySession["user"] }>("/identity/login", loginForm);
    setAuthToken(result.access_token);
    setAuthTokenState(result.access_token);
    setIdentitySession({ authenticated: true, user: result.user });
    setLoginForm({ email: "", password: "" });
  }

  async function bootstrapAdmin(event: FormEvent) {
    event.preventDefault();
    const result = await apiPost<{ access_token: string; user: IdentitySession["user"] }>("/identity/bootstrap-admin", bootstrapForm);
    setAuthToken(result.access_token);
    setAuthTokenState(result.access_token);
    setIdentitySession({ authenticated: true, user: result.user });
  }

  async function logout() {
    await apiPost("/identity/logout", { token: authToken }).catch(() => undefined);
    setAuthToken("");
    setAuthTokenState("");
    setIdentitySession({ authenticated: false });
  }

  function startNewCaseDraft() {
    setSelectedCaseId("");
    setCaseForm({ ...emptyCase });
    setParticipantForm({
      participant_type: "damnificado",
      person_type: "persona_fisica",
      display_name: "",
      document_type: "",
      document_number: "",
      tax_id: "",
      email: "",
      phone: "",
      address: "",
      role_description: "",
      relationship_to_case: "",
      notes: "",
      sensitivity_level: "reservado"
    });
    setEditingParticipant(null);
    setEvidenceForm({ description: "", responsible: "", custodian: "" });
    setEditingEvidence(null);
    setEvidenceFile(null);
    setCustodyForm({ action_type: "revision", detailed_description: "", user_responsible: "" });
    setEditingCustody(null);
    setIndicator("https://secure-login.example.com/verify");
    setIndicatorResult(null);
    setIndicatorFindingState("idle");
    setIndicatorFindingMessage("");
    setLegalQuery("phishing fraude acceso datos");
    setLegalRecommendation(null);
    setLegalTypification(null);
    setLegalApplyState("idle");
    setLegalApplyMessage("");
    setAiResult(null);
    setAiEnrichmentResult(null);
    setReviewResult(null);
    setReviewAudit(null);
    setReportPreview(null);
    setExecutiveSummaryDraft("");
    setExportFinalResult(null);
    setClosureStatus(null);
    setClosureNote("Cierre operativo con evidencia preservada, informe revisado y PDF exportado.");
    setModulePayload({ status: "nuevo_caso", message: "Formulario limpio. Los casos existentes permanecen guardados." });
    setError("");
    refreshCaseCollections("").catch((err: Error) => setError(err.message));
  }

  async function createCase(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    try {
      const created = await apiPost<CaseItem>("/cases", caseForm);
      setCaseForm(emptyCase);
      setSelectedCaseId(created.id);
      await refreshCore();
    } finally {
      setLoading(false);
    }
  }

  async function uploadEvidence(event: FormEvent) {
    event.preventDefault();
    if (!selectedCaseId || !evidenceFile) return;
    const params = new URLSearchParams({
      description: evidenceForm.description,
      responsible: evidenceForm.responsible,
      custodian: evidenceForm.custodian
    });
    const form = new FormData();
    form.append("file", evidenceFile);
    await apiPostForm<EvidenceItem>(`/evidence/case/${selectedCaseId}/upload?${params.toString()}`, form);
    setEvidenceForm({ description: "", responsible: "", custodian: "" });
    setEvidenceFile(null);
    await refreshCaseCollections(selectedCaseId);
  }

  async function createParticipant(event: FormEvent) {
    event.preventDefault();
    if (!selectedCaseId) return;
    await apiPost<CaseParticipant>(`/cases/${selectedCaseId}/participants`, participantForm);
    setParticipantForm({
      participant_type: "damnificado",
      person_type: "persona_fisica",
      display_name: "",
      document_type: "",
      document_number: "",
      tax_id: "",
      email: "",
      phone: "",
      address: "",
      role_description: "",
      relationship_to_case: "",
      notes: "",
      sensitivity_level: "reservado"
    });
    await refreshCaseCollections(selectedCaseId);
  }

  async function saveParticipant(event: FormEvent) {
    event.preventDefault();
    if (!editingParticipant) return;
    await apiPut<CaseParticipant>(`/cases/participants/${editingParticipant.id}`, editingParticipant);
    setEditingParticipant(null);
    await refreshCaseCollections(selectedCaseId);
  }

  async function deleteParticipant(id: number) {
    if (!confirm("Eliminar participante del caso?")) return;
    await apiDelete(`/cases/participants/${id}`);
    await refreshCaseCollections(selectedCaseId);
  }

  async function saveEvidence(event: FormEvent) {
    event.preventDefault();
    if (!editingEvidence) return;
    await apiPut<EvidenceItem>(`/evidence/${editingEvidence.id}`, {
      case_id: editingEvidence.case_id,
      evidence_type: editingEvidence.evidence_type,
      description: editingEvidence.description,
      source: editingEvidence.source || "",
      responsible: editingEvidence.responsible || "",
      custodian: editingEvidence.custodian || "",
      sha256_hash: editingEvidence.sha256_hash || "",
      md5_hash: editingEvidence.md5_hash || null,
      file_location: editingEvidence.file_location || null,
      preservation_method: editingEvidence.preservation_method || "",
      tool_used: editingEvidence.tool_used || "",
      evidence_nature: "copia forense",
      was_altered: false,
      alteration_justification: "",
      custody_observations: "",
      integrity_status: editingEvidence.integrity_status || "pendiente de validacion",
      confidence_level: editingEvidence.confidence_level || "medio"
    });
    setEditingEvidence(null);
    await refreshCaseCollections(selectedCaseId);
  }

  async function deleteEvidence(id: number) {
    if (!confirm("Eliminar evidencia? Esta accion debe quedar reservada a correcciones controladas.")) return;
    await apiDelete(`/evidence/${id}`);
    await refreshCaseCollections(selectedCaseId);
  }

  async function createCustodyAction(event: FormEvent) {
    event.preventDefault();
    if (!selectedCaseId) return;
    await apiPost("/evidence/custody-actions", {
      ...custodyForm,
      case_id: Number(selectedCaseId),
      evidence_id: latestEvidence?.id,
      hash_after: latestEvidence?.sha256_hash || ""
    });
    setCustodyForm({ action_type: "revision", detailed_description: "", user_responsible: "" });
    await refreshCaseCollections(selectedCaseId);
  }

  async function saveCustodyAction(event: FormEvent) {
    event.preventDefault();
    if (!editingCustody) return;
    await apiPut<CustodyAction>(`/evidence/custody-actions/${editingCustody.id}`, {
      case_id: editingCustody.case_id,
      evidence_id: editingCustody.evidence_id || null,
      user_responsible: editingCustody.user_responsible || "",
      action_type: editingCustody.action_type,
      detailed_description: editingCustody.detailed_description,
      tool_used: editingCustody.tool_used || "",
      command_or_procedure: editingCustody.command_or_procedure || "",
      result_obtained: editingCustody.result_obtained || "",
      altered_evidence: false,
      hash_before: "",
      hash_after: editingCustody.hash_after || "",
      validated_by: "",
      legal_observations: editingCustody.legal_observations || "",
      status: editingCustody.status || "registrada"
    });
    setEditingCustody(null);
    await refreshCaseCollections(selectedCaseId);
  }

  async function deleteCustodyAction(id: number) {
    if (!confirm("Eliminar accion de custodia? Usar solo para correcciones controladas.")) return;
    await apiDelete(`/evidence/custody-actions/${id}`);
    await refreshCaseCollections(selectedCaseId);
  }

  async function analyzeIndicator() {
    setIndicatorFindingState("idle");
    setIndicatorFindingMessage("");
    setIndicatorResult(await apiPost("/cybercrime/analyze-indicator", { case_id: selectedCaseId || undefined, indicator }));
    if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
    await refreshCybercrime();
  }

  async function saveIndicatorAsFinding() {
    if (!selectedCaseId || !indicatorResult) return;
    setIndicatorFindingState("saving");
    setIndicatorFindingMessage("Guardando hallazgo tecnico en el caso...");
    try {
      const saved = await apiPost<{ id: number }>(`/cases/${selectedCaseId}/findings`, {
        case_id: selectedCaseId,
        evidence_id: latestEvidence?.id,
        title: `Indicador ${prettySpanish(indicatorResult.indicator_type)} analizado`,
        technical_finding: indicatorResult.findings.join("\n"),
        explanation: `El indicador ${indicatorResult.indicator} fue clasificado con riesgo ${prettySpanish(indicatorResult.risk_level)} y confianza ${prettySpanish(indicatorResult.confidence)}.`,
        confidence_level: indicatorResult.confidence,
        weaknesses_or_limitations: "El analisis de indicador no prueba autoria por si solo; requiere correlacion con evidencia preservada, fuentes externas verificables y revision humana.",
        tools_used: "OPERIA Cybercrime Indicator Analyzer",
        supporting_evidence: latestEvidence ? `Evidencia #${latestEvidence.id}: ${latestEvidence.description}` : "Pendiente de vincular con evidencia preservada.",
        preliminary_legal_relevance: indicatorResult.legal_relevance,
        status: "validado"
      });
      await refreshCaseCollections(selectedCaseId);
      setIndicatorFindingState("saved");
      setIndicatorFindingMessage(`Hallazgo #${saved.id} incorporado al caso y disponible para informe.`);
      setModulePayload({ status: "hallazgo_guardado", finding_id: saved.id, indicator: indicatorResult.indicator, case_id: selectedCaseId });
    } catch (error) {
      const message = error instanceof Error ? error.message : "No se pudo guardar el hallazgo.";
      setIndicatorFindingState("error");
      setIndicatorFindingMessage(message);
    }
  }

  async function createCyberTool(event: FormEvent) {
    event.preventDefault();
    await apiPost<CyberTool>("/cybercrime/tools", cyberToolForm);
    setCyberToolForm({ name: "", category: "osint", executable_path: "", default_command: "", notes: "", website_url: "", documentation_url: "", safety_notes: "" });
    await refreshCybercrime();
  }

  async function verifyCyberTool(toolId: number) {
    await apiPost<CyberTool>(`/cybercrime/tools/${toolId}/verify`);
    await refreshCybercrime();
  }

  async function seedForensicToolSet() {
    await apiPost("/cybercrime/tools/seed-forensic-set");
    await refreshCybercrime();
  }

  async function createCyberLabSession(event: FormEvent) {
    event.preventDefault();
    if (!selectedCaseId) {
      setError("Selecciona un caso antes de crear una sesión cybercrime.");
      return;
    }
    await apiPost<CyberLabSession>("/cybercrime/lab/sessions", {
      ...cyberLabForm,
      case_id: Number(selectedCaseId),
      operator: cyberLabForm.operator || analystName || identitySession.user?.name || "Analista local",
      title: cyberLabForm.title || `Análisis cybercrime - ${indicator}`
    });
    setCyberLabForm({ title: "", purpose: "analisis de indicador", risk_level: "medio", operator: "" });
    await refreshCybercrime();
  }

  async function createCyberProofRow(event: FormEvent) {
    event.preventDefault();
    if (!selectedCaseId) {
      setError("Selecciona un caso antes de guardar una conclusión cybercrime.");
      return;
    }
    await apiPost<CyberProofRow>("/cybercrime/proof-matrix", {
      ...cyberProofForm,
      case_id: Number(selectedCaseId),
      defensible_conclusion:
        cyberProofForm.defensible_conclusion ||
        `El indicador ${indicator} fue clasificado como ${indicatorResult?.indicator_type || "dato técnico"} con riesgo ${indicatorResult?.risk_level || "medio"}.`,
      legal_framing: cyberProofForm.legal_framing || "Requiere vinculación con evidencia preservada y encuadre legal aprobado por analista."
    });
    setCyberProofForm({ defensible_conclusion: "", legal_framing: "", confidence_level: "medio", weakness: "" });
    await refreshCybercrime();
  }

  async function saveDeepfakeAnalysis(event: FormEvent) {
    event.preventDefault();
    if (!selectedCaseId) {
      setDeepfakeState("error");
      setDeepfakeMessage("Selecciona un caso antes de guardar el análisis.");
      return;
    }
    setDeepfakeState("saving");
    setDeepfakeMessage("Guardando análisis de medio...");
    try {
      const selectedEvidence = evidence.find((item) => item.id === Number(deepfakeForm.evidence_id));
      await apiPost<DeepfakeAnalysisItem>("/cybercrime/deepfake", {
        ...deepfakeForm,
        case_id: Number(selectedCaseId),
        evidence_id: deepfakeForm.evidence_id ? Number(deepfakeForm.evidence_id) : undefined,
        evidence_hash: selectedEvidence?.sha256_hash || "",
        source_origin: deepfakeForm.source_origin || selectedEvidence?.source || selectedEvidence?.file_location || "",
        checklist: deepfakeChecklistState,
        analyst_name: analystName || identitySession.user?.name || "Analista local"
      });
      setDeepfakeForm(emptyDeepfakeForm);
      setDeepfakeChecklistState(emptyDeepfakeChecklist);
      setDeepfakeState("saved");
      setDeepfakeMessage("Análisis guardado y vinculado al caso.");
      await refreshCaseCollections(selectedCaseId);
      await refreshCybercrime();
    } catch (error) {
      setDeepfakeState("error");
      setDeepfakeMessage(error instanceof Error ? error.message : "No se pudo guardar el análisis.");
    }
  }

  async function createDeepfakeFinding(analysisId: number) {
    setDeepfakeState("saving");
    setDeepfakeMessage("Creando hallazgo técnico...");
    try {
      const result = await apiPost<{ id: number; message: string }>(`/cybercrime/deepfake/${analysisId}/finding`);
      setDeepfakeState("saved");
      setDeepfakeMessage(result.message || `Hallazgo #${result.id} creado.`);
      if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
      await refreshCybercrime();
    } catch (error) {
      setDeepfakeState("error");
      setDeepfakeMessage(error instanceof Error ? error.message : "No se pudo crear el hallazgo.");
    }
  }

  async function applyDeepfakeLegal(analysis: DeepfakeAnalysisItem) {
    setDeepfakeState("saving");
    setDeepfakeMessage("Aplicando normas sugeridas...");
    try {
      const text = `${analysis.media_type} ${analysis.findings} ${analysis.legal_relevance}`.toLowerCase();
      const result = await apiPost<{ applied: Array<{ norm_reference: string }> }>(`/cybercrime/deepfake/${analysis.id}/apply-legal`, {
        analyst_name: analystName || identitySession.user?.name || "Analista local",
        fraud: text.includes("fraude") || text.includes("estafa") || text.includes("transferencia"),
        document_falsity: analysis.media_type === "documento" || text.includes("documento") || text.includes("certificado"),
        honor_affectation: text.includes("honor") || text.includes("reputación") || text.includes("reputacion"),
        personal_data: true,
        intellectual_property: true
      });
      setDeepfakeState("saved");
      setDeepfakeMessage(`Normas aplicadas: ${result.applied.map((item) => item.norm_reference).join(", ") || "sin nuevas normas"}.`);
      if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
      await refreshCybercrime();
    } catch (error) {
      setDeepfakeState("error");
      setDeepfakeMessage(error instanceof Error ? error.message : "No se pudieron aplicar las normas.");
    }
  }

  async function saveBlockchainTransaction(event: FormEvent) {
    event.preventDefault();
    if (!selectedCaseId) {
      setBlockchainState("error");
      setBlockchainMessage("Selecciona un caso antes de registrar la transacción.");
      return;
    }
    setBlockchainState("saving");
    setBlockchainMessage("Registrando transacción blockchain...");
    try {
      const selectedEvidence = evidence.find((item) => item.id === Number(blockchainForm.evidence_id));
      await apiPost<BlockchainTransactionItem>("/cybercrime/blockchain", {
        ...blockchainForm,
        case_id: Number(selectedCaseId),
        evidence_id: blockchainForm.evidence_id ? Number(blockchainForm.evidence_id) : undefined,
        amount: Number(blockchainForm.amount || 0),
        approximate_value: Number(blockchainForm.approximate_value || 0),
        evidence_hash: selectedEvidence?.sha256_hash || "",
        analyst_name: analystName || identitySession.user?.name || "Analista local"
      });
      setBlockchainForm(emptyBlockchainForm);
      setBlockchainState("saved");
      setBlockchainMessage("Transacción registrada con límites de atribución.");
      await refreshCaseCollections(selectedCaseId);
      await refreshCybercrime();
    } catch (error) {
      setBlockchainState("error");
      setBlockchainMessage(error instanceof Error ? error.message : "No se pudo registrar la transacción.");
    }
  }

  async function createBlockchainFinding(transactionId: number) {
    setBlockchainState("saving");
    setBlockchainMessage("Creando hallazgo blockchain...");
    try {
      const result = await apiPost<{ id: number; message: string }>(`/cybercrime/blockchain/${transactionId}/finding`);
      setBlockchainState("saved");
      setBlockchainMessage(result.message || `Hallazgo #${result.id} creado.`);
      if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
      await refreshCybercrime();
    } catch (error) {
      setBlockchainState("error");
      setBlockchainMessage(error instanceof Error ? error.message : "No se pudo crear el hallazgo.");
    }
  }

  async function applyBlockchainLegal(transaction: BlockchainTransactionItem) {
    setBlockchainState("saving");
    setBlockchainMessage("Aplicando normas registradas...");
    try {
      const text = `${transaction.route_hypothesis} ${transaction.wallet_classification} ${transaction.blockchain}`.toLowerCase();
      const result = await apiPost<{ applied: Array<{ norm_reference: string }> }>(`/cybercrime/blockchain/${transaction.id}/apply-legal`, {
        analyst_name: analystName || identitySession.user?.name || "Analista local",
        fraud: text.includes("estafa") || text.includes("fraude") || text.includes("phishing"),
        computer_manipulation: text.includes("manipulación") || text.includes("manipulacion") || text.includes("contrato inteligente"),
        extortion: text.includes("extorsión") || text.includes("extorsion") || text.includes("ransomware"),
        blackmail: text.includes("chantaje"),
        personal_data: text.includes("exchange") || text.includes("cuenta") || text.includes("kyc")
      });
      setBlockchainState("saved");
      setBlockchainMessage(`Normas aplicadas: ${result.applied.map((item) => item.norm_reference).join(", ") || "sin nuevas normas"}.`);
      if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
      await refreshCybercrime();
    } catch (error) {
      setBlockchainState("error");
      setBlockchainMessage(error instanceof Error ? error.message : "No se pudieron aplicar las normas.");
    }
  }

  async function saveIoTDevice(event: FormEvent) {
    event.preventDefault();
    if (!selectedCaseId) {
      setIotState("error");
      setIotMessage("Selecciona un caso antes de registrar el dispositivo.");
      return;
    }
    setIotState("saving");
    setIotMessage("Registrando dispositivo IoT...");
    try {
      const selectedEvidence = evidence.find((item) => item.id === Number(iotForm.evidence_id));
      await apiPost<IoTDeviceItem>("/cybercrime/iot", {
        ...iotForm,
        case_id: Number(selectedCaseId),
        evidence_id: iotForm.evidence_id ? Number(iotForm.evidence_id) : undefined,
        evidence_hash: selectedEvidence?.sha256_hash || "",
        checklist: iotChecklistState,
        analyst_name: analystName || identitySession.user?.name || "Analista local"
      });
      setIotForm(emptyIoTForm);
      setIotChecklistState(emptyIoTChecklist);
      setIotState("saved");
      setIotMessage("Dispositivo IoT registrado con metodología y límites.");
      await refreshCaseCollections(selectedCaseId);
      await refreshCybercrime();
    } catch (error) {
      setIotState("error");
      setIotMessage(error instanceof Error ? error.message : "No se pudo registrar el dispositivo.");
    }
  }

  async function createIoTFinding(deviceId: number) {
    setIotState("saving");
    setIotMessage("Creando hallazgo IoT...");
    try {
      const result = await apiPost<{ id: number; message: string }>(`/cybercrime/iot/${deviceId}/finding`);
      setIotState("saved");
      setIotMessage(result.message || `Hallazgo #${result.id} creado.`);
      if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
      await refreshCybercrime();
    } catch (error) {
      setIotState("error");
      setIotMessage(error instanceof Error ? error.message : "No se pudo crear el hallazgo.");
    }
  }

  async function applyIoTLegal(device: IoTDeviceItem) {
    setIotState("saving");
    setIotMessage("Aplicando normas registradas...");
    try {
      const text = `${device.known_vulnerabilities} ${device.logs_available} ${device.open_ports} ${device.device_type}`.toLowerCase();
      const result = await apiPost<{ applied: Array<{ norm_reference: string }> }>(`/cybercrime/iot/${device.id}/apply-legal`, {
        analyst_name: analystName || identitySession.user?.name || "Analista local",
        unauthorized_access: text.includes("acceso") || text.includes("credencial") || text.includes("puerto"),
        damage: text.includes("daño") || text.includes("dano") || text.includes("malware") || text.includes("alter"),
        public_systems: text.includes("servicio") || text.includes("infraestructura") || text.includes("publico"),
        communications_interruption: text.includes("interrup") || text.includes("red") || text.includes("comunicacion"),
        personal_data: text.includes("camara") || text.includes("audio") || text.includes("usuario")
      });
      setIotState("saved");
      setIotMessage(`Normas aplicadas: ${result.applied.map((item) => item.norm_reference).join(", ") || "sin nuevas normas"}.`);
      if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
      await refreshCybercrime();
    } catch (error) {
      setIotState("error");
      setIotMessage(error instanceof Error ? error.message : "No se pudieron aplicar las normas.");
    }
  }

  async function searchLegal() {
    const [found, recommended] = await Promise.all([
      apiGet<LegalArticle[]>(`/legal-knowledge/articles?q=${encodeURIComponent(legalQuery)}`),
      apiPost<LegalRecommendationResponse>("/legal-knowledge/articles/recommend", { incident_text: legalQuery })
    ]);
    setArticles(found);
    setLegalRecommendation(recommended);
  }

  async function decideLegalRecommendation(item: LegalRecommendation, decision_status: "aprobado" | "descartado") {
    if (!selectedCaseId) {
      setError("Selecciona un caso antes de aprobar o descartar una norma.");
      setLegalApplyState("error");
      setLegalApplyMessage("Selecciona un caso para aplicar la norma.");
      return;
    }
    localStorage.setItem("operia_analyst_name", analystName);
    setLegalApplyState("applying");
    setLegalApplyMessage(`${decision_status === "aprobado" ? "Aplicando" : "Descartando"} ${item.reference} en el caso...`);
    try {
      await apiPost<LegalMapping>("/legal-knowledge/mappings/decision", {
        case_id: selectedCaseId,
        article_id: item.article_id,
        decision_status,
        analyst_name: analystName,
        analyst_rationale:
          decision_status === "aprobado"
            ? "Norma aceptada por el analista para el encuadre preliminar del caso."
            : "Norma descartada por el analista para este estado de evidencia.",
        legal_role: item.legal_role,
        applicability_to_case: item.applicability_to_case,
        probatory_limits: item.probatory_limits,
        confidence_level: item.confidence
      });
      await refreshCaseCollections(selectedCaseId);
      setLegalApplyState("applied");
      setLegalApplyMessage(`${item.reference} ${decision_status === "aprobado" ? "aplicada" : "descartada"} para el caso seleccionado.`);
    } catch (error) {
      setLegalApplyState("error");
      setLegalApplyMessage(error instanceof Error ? error.message : "No se pudo actualizar el encuadre legal.");
    }
  }

  async function changeLegalMappingDecision(mapping: LegalMapping, decision_status: "aprobado" | "descartado") {
    if (!selectedCaseId || !mapping.article_id) return;
    await apiPost<LegalMapping>("/legal-knowledge/mappings/decision", {
      case_id: selectedCaseId,
      article_id: mapping.article_id,
      decision_status,
      analyst_name: analystName || mapping.analyst_name,
      analyst_rationale:
        decision_status === "aprobado"
          ? "Norma reactivada por el analista luego de revisión."
          : "Norma retirada del encuadre por corrección del analista.",
      legal_role: mapping.legal_role,
      applicability_to_case: mapping.applicability_to_case,
      probatory_limits: mapping.probatory_limits,
      confidence_level: mapping.confidence_level
    });
    await refreshCaseCollections(selectedCaseId);
  }

  function legalElementsForMapping(mappingId: number) {
    const elements = legalProbatoryMatrix?.rows
      .filter((row) => row.mapping_id === mappingId)
      .map((row) => row.legal_element)
      .filter(Boolean) || [];
    return Array.from(new Set(elements));
  }

  async function linkEvidenceToLegalMapping(mapping: LegalMapping) {
    if (!selectedCaseId) return;
    const evidenceId = Number(legalEvidenceSelection[mapping.id] || evidence[0]?.id || 0);
    if (!evidenceId) {
      setError("Carga o selecciona una evidencia antes de vincularla a una norma.");
      return;
    }
    await apiPost<LegalMappingEvidence>("/legal-knowledge/mappings/evidence", {
      case_id: selectedCaseId,
      legal_mapping_id: mapping.id,
      evidence_id: evidenceId,
      linked_by: analystName,
      link_rationale: "La evidencia fue seleccionada por el analista como soporte del encuadre legal.",
      legal_element: legalElementSelection[mapping.id] || mapping.legal_role || "elemento del tipo penal",
      probatory_strength: mapping.confidence_level || "medio",
      element_status: mapping.confidence_level === "alto" ? "probado" : "debil",
      missing_evidence: "",
      contradiction_risk: "bajo",
      recommended_measure: "Corroborar con fuentes externas si se pretende atribucion personal."
    });
    await refreshCaseCollections(selectedCaseId);
  }

  async function saveLegalLink(link: LegalMappingEvidence) {
    if (!selectedCaseId) return;
    const draft = legalLinkDrafts[link.id] || {};
    await apiPut<LegalMappingEvidence>(`/legal-knowledge/mappings/evidence/${link.id}`, {
      ...link,
      ...draft,
      case_id: selectedCaseId
    });
    setLegalLinkDrafts((current) => {
      const next = { ...current };
      delete next[link.id];
      return next;
    });
    await refreshCaseCollections(selectedCaseId);
  }

  async function unlinkLegalEvidence(linkId: number) {
    if (!confirm("Quitar esta evidencia del encuadre legal? La evidencia no se borra; solo se deshace el vinculo juridico.")) return;
    await apiDelete(`/legal-knowledge/mappings/evidence/${linkId}`);
    await refreshCaseCollections(selectedCaseId);
  }

  async function runAiAssist() {
    if (latestReport) {
      const enriched = await apiPost<ReportItem>(`/reports/${latestReport.id}/ai-enrich`, {
        case_id: selectedCaseId || undefined,
        prompt: aiPrompt
      });
      const result = {
        status: enriched.status,
        report_id: enriched.id,
        message: "Informe ampliado con analisis tecnico-juridico. Revisa y vuelve a exportar PDF.",
        observations: enriched.observations
      };
      setAiEnrichmentResult(result);
      setAiResult(result);
      if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
      await loadReportPreview(enriched.id);
      return;
    }
    if (selectedCaseId) {
      const result = await apiPost<CaseAnalysisResult>(`/ai/case/${selectedCaseId}/recommendations`, { focus: aiPrompt });
      setAiEnrichmentResult(null);
      setAiResult(result);
      return;
    }
    const result = await apiPost<CaseAnalysisResult>("/ai/assist", { model_name: "mistral", prompt: aiPrompt });
    setAiEnrichmentResult(null);
    setAiResult(result);
  }

  async function generateReport() {
    if (!selectedCaseId) return;
    localStorage.setItem("operia_analyst_name", analystName);
    const author = encodeURIComponent(analystName.trim());
    const report = await apiPost<ReportItem>(`/reports/case/${selectedCaseId}/generate?author=${author}`);
    await refreshCaseCollections(selectedCaseId);
    setReviewResult({ generated_report_id: report.id, status: "generated" });
  }

  async function generateReportFromCtfDashboard() {
    if (!selectedCaseId) {
      setCtfDashboardState("error");
      setCtfDashboardMessage("Selecciona un caso antes de generar el informe.");
      return;
    }
    setCtfDashboardState("working");
    setCtfDashboardMessage("Generando informe integral para el caso activo...");
    try {
      await generateReport();
      setCtfDashboardState("success");
      setCtfDashboardMessage("Informe generado y asociado al caso activo.");
    } catch (error) {
      setCtfDashboardState("error");
      setCtfDashboardMessage(error instanceof Error ? error.message : "No se pudo generar el informe.");
    }
  }

  async function reviewReport() {
    if (!latestReport) return;
    const result = await apiPost<ReportReviewResult>(`/reports/${latestReport.id}/review`);
    setReviewAudit(result);
    setReviewResult(result);
    if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
    await loadReportPreview(latestReport.id);
  }

  async function loadReportPreview(reportId = latestReport?.id) {
    if (!reportId) return;
    const preview = await apiGet<ReportPreview>(`/reports/${reportId}/preview`);
    setReportPreview(preview);
    setExecutiveSummaryDraft(preview.executive_summary);
  }

  async function updateRubricEvaluation() {
    if (!selectedCaseId) {
      setRubricState("error");
      setRubricMessage("Selecciona un caso para evaluar la rúbrica.");
      return;
    }
    setRubricState("updating");
    setRubricMessage("Actualizando evaluación de rúbrica...");
    try {
      const result = await apiPost<RubricEvaluation>(`/rubrics/case/${selectedCaseId}/evaluate`);
      setRubricEvaluation(result);
      setRubricState("updated");
      setRubricMessage(`Evaluación actualizada: ${result.total_score}/${result.max_score} (${result.percentage}%).`);
      if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
    } catch (error) {
      setRubricState("error");
      setRubricMessage(error instanceof Error ? error.message : "No se pudo actualizar la rúbrica.");
    }
  }

  async function updateRubricFromCtfDashboard() {
    setCtfDashboardState("working");
    setCtfDashboardMessage("Evaluando cumplimiento de rúbrica CTF...");
    try {
      await updateRubricEvaluation();
      setCtfDashboardState("success");
      setCtfDashboardMessage("Rúbrica evaluada. Revisa el semáforo de preparación.");
    } catch (error) {
      setCtfDashboardState("error");
      setCtfDashboardMessage(error instanceof Error ? error.message : "No se pudo evaluar la rúbrica.");
    }
  }

  function exportPdfFromCtfDashboard() {
    if (!latestReport) {
      setCtfDashboardState("error");
      setCtfDashboardMessage("Genera un informe antes de exportar el PDF.");
      return;
    }
    window.open(`${API_BASE}/exports/reports/${latestReport.id}/pdf`, "_blank", "noopener,noreferrer");
    setCtfDashboardState("success");
    setCtfDashboardMessage("Exportación PDF iniciada. El manifiesto queda registrado por el backend.");
  }

  async function saveExecutiveSummary() {
    if (!latestReport || !executiveSummaryDraft.trim()) return;
    const updated = await apiPut<ReportItem>(`/reports/${latestReport.id}/executive-summary`, {
      executive_summary: executiveSummaryDraft,
      author: analystName || latestReport.author
    });
    setReviewResult({ status: "executive_summary_updated", report_id: updated.id });
    if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
    await loadReportPreview(updated.id);
  }

  async function requestFinalExport() {
    if (!latestReport) return;
    const readiness = await apiGet<{ can_export_final: boolean; exportability: { level: string; score: number }; contradictions: { count: number } }>(
      `/reports/${latestReport.id}/exportability`
    );
    setExportFinalResult(readiness);
    if (!readiness.can_export_final) return;
    const response = await fetch(`${API_BASE}/exports/reports/${latestReport.id}/pdf/seal-final`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        analyst_name: analystName || latestReport.author,
        declaration: "Cierre pericial final con checklist verificado, anexos incorporados y exportacion sellada."
      })
    });
    if (!response.ok) {
      const detail = await response.text();
      setExportFinalResult({ status: "blocked", detail });
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    setExportFinalResult({
      status: "sealed",
      seal_id: response.headers.get("x-operia-seal-id"),
      sha256: response.headers.get("x-operia-sha256"),
      manifest_id: response.headers.get("x-operia-export-manifest-id")
    });
    window.open(url, "_blank");
    if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
    await loadReportPreview(latestReport.id);
  }

  async function runCaseRecommendations() {
    if (!selectedCaseId) return;
    setAiResult(await apiPost(`/ai/case/${selectedCaseId}/recommendations`, { focus: aiPrompt }));
  }

  async function runLegalTypification(createSuggestions = false, focusOverride?: string) {
    if (!selectedCaseId) {
      setError("Selecciona un caso antes de tipificar el incidente.");
      return;
    }
    setLegalApplyState(createSuggestions ? "applying" : "idle");
    setLegalApplyMessage(createSuggestions ? "Aplicando tipificacion al caso..." : "");
    try {
      const result = await apiPost<LegalTypificationResult>(`/ai/case/${selectedCaseId}/legal-typification`, {
        focus: focusOverride || aiPrompt,
        create_suggestions: createSuggestions,
        analyst_name: analystName
      });
      setLegalTypification(result);
      if (createSuggestions) {
        await refreshCaseCollections(selectedCaseId);
        setLegalApplyState("applied");
        setLegalApplyMessage(
          result.suggested_mapping_ids.length
            ? `Tipificacion aplicada: ${result.suggested_mapping_ids.length} norma(s) sugerida(s) incorporada(s) al caso.`
            : "La tipificacion ya estaba incorporada al caso; no se duplicaron normas."
        );
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "No se pudo aplicar la tipificacion al caso.";
      setLegalApplyState("error");
      setLegalApplyMessage(message);
    }
  }

  async function searchAndTypifyLegal(createSuggestions = false) {
    await searchLegal();
    if (selectedCaseId) {
      await runLegalTypification(createSuggestions, legalQuery);
    }
  }

  async function verifyEvidenceIntegrity(evidenceId: number) {
    setModulePayload(await apiGet(`/evidence/${evidenceId}/integrity`));
    if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
  }

  async function refreshReportAnnexes() {
    if (!latestReport) return;
    const updated = await apiPost<ReportItem>(`/reports/${latestReport.id}/annexes/refresh`);
    setReviewResult({ status: "annexes_refreshed", report_id: updated.id });
    if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
    await loadReportPreview(updated.id);
  }

  async function transitionReportStatus(status: string) {
    if (!latestReport) return;
    const updated = await apiPost<ReportItem>(`/reports/${latestReport.id}/versions/transition`, {
      status,
      user: analystName || latestReport.author,
      note: `Cambio de version a ${status}`
    });
    setReviewResult({ status: "version_transition", report_id: updated.id, next_status: updated.status, version: updated.version });
    if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
    await loadReportPreview(updated.id);
  }

  async function closeCase() {
    if (!selectedCaseId) return;
    try {
      const result = await apiPost<ClosureStatus>(`/cases/${selectedCaseId}/close`, { closure_note: closureNote });
      setClosureStatus(result);
      setModulePayload({ status: "case_closed", case_id: selectedCaseId, warnings: result.closure_warnings || [] });
      await refreshCore();
      await refreshCaseCollections(selectedCaseId);
    } catch (error) {
      const message = error instanceof Error ? error.message : "No se pudo cerrar el caso.";
      setClosureStatus((current) => current ? { ...current, message } : current);
      setError(message);
    }
  }

  async function runAiSecurity() {
    setAiSecurityResult(
      await apiPost("/ai-security/evaluations", {
        model_name: "mistral",
        run_tests: false,
        overall_score: 72,
        network_blocked: true,
        tools_enabled: false
      })
    );
  }

  function renderIndicatorOutcome() {
    if (!indicatorResult) return <EmptyState text="Ejecuta el analisis para obtener una lectura pericial del indicador." />;
    return (
      <div className="forensic-outcome">
        <div className={`outcome-banner ${indicatorResult.risk_level}`}>
          <div>
            <span>Indicador analizado</span>
            <strong>{indicatorResult.indicator}</strong>
          </div>
          <div>
            <span>Tipo</span>
            <strong>{prettySpanish(indicatorResult.indicator_type)}</strong>
          </div>
          <div>
            <span>Riesgo</span>
            <strong>{prettySpanish(indicatorResult.risk_level)}</strong>
          </div>
          <div>
            <span>Confianza</span>
            <strong>{prettySpanish(indicatorResult.confidence)}</strong>
          </div>
        </div>
        <div className="forensic-columns">
          <div>
            <h4>Hallazgos tecnicos</h4>
            <div className="summary-list">
              {indicatorResult.findings.map((item) => <span key={item}>{prettySpanish(item)}</span>)}
            </div>
          </div>
          <div>
            <h4>Acciones recomendadas</h4>
            <div className="summary-list">
              {indicatorResult.recommended_actions.map((item) => <span key={item}>{prettySpanish(item)}</span>)}
            </div>
          </div>
        </div>
        <div className="notice">
          {prettySpanish(indicatorResult.legal_relevance)} Este resultado orienta la investigacion, pero debe vincularse con evidencia, custodia y fuentes verificables antes de sostener atribucion.
        </div>
        {indicatorFindingMessage && (
          <div className={`action-feedback ${indicatorFindingState}`}>
            {indicatorFindingMessage}
          </div>
        )}
        <div className="button-row">
          <button className="secondary-button" onClick={saveIndicatorAsFinding} disabled={!selectedCaseId || indicatorFindingState === "saving"}>
            <FileCheck2 size={16} /> {indicatorFindingState === "saving" ? "Guardando..." : indicatorFindingState === "saved" ? "Guardar otro hallazgo" : "Guardar como hallazgo"}
          </button>
          <button className="secondary-button" onClick={() => setActive("evidence")} disabled={!selectedCaseId}>
            <Fingerprint size={16} /> Ver evidencia
          </button>
          <button className="secondary-button" onClick={() => setActive("reports")} disabled={!latestReport}>
            <FileText size={16} /> Ver informe
          </button>
        </div>
      </div>
    );
  }

  function renderAiEnrichmentOutcome() {
    if (!aiEnrichmentResult) return <EmptyState text="Ejecuta la ampliacion para ver que se incorporo al informe." />;
    return (
      <div className="forensic-outcome">
        <div className="outcome-banner medium">
          <div>
            <span>Informe</span>
            <strong>#{aiEnrichmentResult.report_id || latestReport?.id || "-"}</strong>
          </div>
          <div>
            <span>Estado</span>
            <strong>{prettySpanish(aiEnrichmentResult.status)}</strong>
          </div>
          <div>
            <span>Accion</span>
            <strong>Ampliacion aplicada</strong>
          </div>
        </div>
        <p>{prettySpanish(aiEnrichmentResult.message)}</p>
        {aiEnrichmentResult.observations && <div className="notice">{prettySpanish(aiEnrichmentResult.observations)}</div>}
        <div className="summary-list">
          <span>Se recalcularon secciones del informe y vista previa.</span>
          <span>Requiere revision humana antes de exportacion final.</span>
          <span>La fundamentacion legal debe permanecer vinculada a biblioteca registrada.</span>
        </div>
        <div className="button-row">
          <button className="secondary-button" onClick={() => loadReportPreview(aiEnrichmentResult.report_id || latestReport?.id)}>
            <FileCheck2 size={16} /> Ver vista previa
          </button>
          <button className="secondary-button" onClick={() => setActive("reports")}>
            <FileText size={16} /> Abrir informes
          </button>
        </div>
      </div>
    );
  }

  function renderCaseAnalysisOutcome() {
    const result = aiResult as CaseAnalysisResult | null;
    if (!result) return <EmptyState text="Ejecuta el analisis para obtener una lectura operativa del caso." />;
    const articles = result.recommended_articles || [];
    const profile = result.legal_profile;
    return (
      <div className="forensic-outcome">
        <div className="outcome-banner medium">
          <div>
            <span>Perfil del incidente</span>
            <strong>{prettySpanish(profile?.label || selectedCase?.incident_type || "Incidente digital")}</strong>
          </div>
          <div>
            <span>Normas sugeridas</span>
            <strong>{articles.length}</strong>
          </div>
          <div>
            <span>Revision</span>
            <strong>{result.human_review_required === false ? "No requerida" : "Humana"}</strong>
          </div>
        </div>
        {profile?.legal_theory && (
          <div className="notice">
            {prettySpanish(profile.legal_theory)}
          </div>
        )}
        <div className="forensic-columns">
          <div>
            <h4>Encuadre sugerido</h4>
            <div className="summary-list">
              {articles.slice(0, 5).map((item) => (
                <span key={`${item.article_id}-${item.reference}`}>
                  {item.reference} - {prettySpanish(item.title)} ({prettySpanish(item.legal_role)})
                </span>
              ))}
              {!articles.length && <span>Sin normas sugeridas para este analisis.</span>}
            </div>
          </div>
          <div>
            <h4>Que hacer ahora</h4>
            <div className="summary-list">
              {(result.operational_next_steps || []).map((item) => <span key={item}>{prettySpanish(item)}</span>)}
              {!result.operational_next_steps?.length && <span>Completar revision humana y matriz legal-probatoria.</span>}
            </div>
          </div>
        </div>
        {profile?.recommended_measures?.length ? (
          <div className="requirements">
            <strong>Medidas recomendadas</strong>
            {profile.recommended_measures.map((item) => <span key={item}>{prettySpanish(item)}</span>)}
          </div>
        ) : null}
        {result.status && !result.response && (
          <div className="notice">
            No se generó texto adicional. Usá la tipificación legal y la matriz probatoria para sostener el informe.
          </div>
        )}
        {legalApplyMessage && (
          <div className={`action-feedback ${legalApplyState}`}>
            {legalApplyMessage}
          </div>
        )}
        <div className="button-row">
          <button className="secondary-button" onClick={() => searchAndTypifyLegal(true)} disabled={!selectedCaseId || legalApplyState === "applying"}>
            <Gavel size={16} /> {legalApplyState === "applying" ? "Aplicando..." : legalApplyState === "applied" ? "Encuadre aplicado" : "Aplicar encuadre al caso"}
          </button>
          <button className="secondary-button" onClick={() => setActive("legalKnowledge")}>
            <BookOpen size={16} /> Ver biblioteca legal
          </button>
        </div>
      </div>
    );
  }

  function renderReviewOutcome() {
    if (!reviewAudit) return <EmptyState text="Ejecuta la revision para obtener auditoria profesional del informe." />;
    const hasCritical = reviewAudit.critical_errors.length > 0;
    const reviewClass = hasCritical ? "high" : reviewAudit.score >= 85 ? "low" : "medium";
    return (
      <div className="forensic-outcome">
        <div className={`outcome-banner ${reviewClass}`}>
          <div>
            <span>Score</span>
            <strong>{reviewAudit.score}/100</strong>
          </div>
          <div>
            <span>Estado</span>
            <strong>{prettySpanish(reviewAudit.status)}</strong>
          </div>
          <div>
            <span>Criticos</span>
            <strong>{reviewAudit.critical_errors.length}</strong>
          </div>
          <div>
            <span>Advertencias</span>
            <strong>{reviewAudit.warnings.length}</strong>
          </div>
        </div>
        <div className="forensic-columns">
          <div>
            <h4>Advertencias</h4>
            <div className="summary-list">
              {reviewAudit.warnings.map((item) => <span key={item}>{prettySpanish(item)}</span>)}
              {!reviewAudit.warnings.length && <span>Sin advertencias relevantes.</span>}
            </div>
          </div>
          <div>
            <h4>Sugerencias</h4>
            <div className="summary-list">
              {reviewAudit.suggestions.map((item) => <span key={item}>{prettySpanish(item)}</span>)}
              {!reviewAudit.suggestions.length && <span>Sin sugerencias pendientes.</span>}
            </div>
          </div>
        </div>
        {!!reviewAudit.critical_errors.length && (
          <div className="requirements danger">
            <strong>Errores criticos</strong>
            {reviewAudit.critical_errors.map((item) => <span key={item}>{prettySpanish(item)}</span>)}
          </div>
        )}
        <div className="button-row">
          <button className="secondary-button" onClick={() => setActive("reports")}><FileText size={16} /> Corregir informe</button>
          <button className="secondary-button" onClick={() => setActive("legalKnowledge")}><Gavel size={16} /> Revisar matriz legal</button>
          <button className="secondary-button" onClick={requestFinalExport} disabled={!latestReport}><Download size={16} /> Evaluar exportacion</button>
        </div>
      </div>
    );
  }

  function renderExportFinalOutcome() {
    if (!exportFinalResult) return null;
    const result = exportFinalResult as {
      status?: string;
      detail?: string;
      seal_id?: string | null;
      sha256?: string | null;
      manifest_id?: string | null;
      can_export_final?: boolean;
      exportability?: { level?: string; score?: number };
      contradictions?: { count?: number };
    };
    const blocked = result.status === "blocked" || result.can_export_final === false;
    return (
      <div className={`export-outcome ${blocked ? "blocked" : "ready"}`}>
        <div>
          <span>{blocked ? "Exportacion final bloqueada" : result.status === "sealed" ? "Exportacion final sellada" : "Evaluacion de exportacion"}</span>
          <strong>
            {result.status === "sealed"
              ? `Sello ${result.seal_id || "generado"}`
              : result.exportability?.level || prettySpanish(result.status || "Resultado disponible")}
          </strong>
          {result.exportability?.score !== undefined && <small>Score de exportabilidad: {result.exportability.score}/100</small>}
          {result.contradictions?.count !== undefined && <small>Contradicciones detectadas: {result.contradictions.count}</small>}
          {result.detail && <small>{prettySpanish(result.detail)}</small>}
        </div>
        {result.sha256 && <code>SHA-256 PDF: {result.sha256}</code>}
        {result.manifest_id && <small>Manifiesto #{result.manifest_id}</small>}
      </div>
    );
  }

  function renderWorkflow() {
    return (
      <div className="workflow">
        <section className="work-surface">
          <div className="section-head">
            <div>
              <h2>Flujo Caso - Evidencia - Informe</h2>
              <p>Camino operativo de punta a punta para resolver un incidente con OPERIA.</p>
            </div>
            <div className="section-actions">
              <button className="new-case-button" onClick={startNewCaseDraft}>
                <Briefcase size={17} /> Nuevo Caso
              </button>
              <button className="icon-button" onClick={refreshCore} title="Actualizar">
                <RefreshCcw size={18} />
              </button>
            </div>
          </div>
          <div className="case-selector">
            <div className="case-summary">
              <strong>{selectedCase?.title || "Nuevo caso operativo"}</strong>
              <span>{selectedCase ? `${selectedCase.case_code} | ${selectedCase.incident_type} | ${selectedCase.status}` : "Crea o selecciona un caso para iniciar."}</span>
            </div>
            <div className="case-selector-actions">
              <button className="secondary-button" onClick={() => setActive("history")}>
                <History size={17} /> Abrir Historial
              </button>
              <small>Los casos abiertos quedan guardados para retomarlos desde Historial.</small>
            </div>
          </div>
        </section>

        <div className="step-grid">
          <StepCard number={1} title="Crear un caso" done={Boolean(selectedCase)}>
            <form className="compact-form" onSubmit={createCase}>
              <input placeholder="Codigo del caso" value={caseForm.case_code} onChange={(e) => setCaseForm({ ...caseForm, case_code: e.target.value })} required />
              <input placeholder="Titulo" value={caseForm.title} onChange={(e) => setCaseForm({ ...caseForm, title: e.target.value })} required />
              <select
                value={caseForm.incident_type}
                onChange={(e) => {
                  const selected = attackTypes.find((item) => item.value === e.target.value);
                  setCaseForm({ ...caseForm, incident_type: e.target.value });
                  if (selected) setLegalQuery(selected.query);
                }}
              >
                {attackTypes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
              <textarea placeholder="Descripcion inicial" value={caseForm.description} onChange={(e) => setCaseForm({ ...caseForm, description: e.target.value })} />
              <button><Briefcase size={17} /> Crear caso</button>
            </form>
          </StepCard>

          <StepCard number={2} title="Registrar personas y entidades" done={participants.length > 0}>
            <form className="compact-form" onSubmit={createParticipant}>
              <div className="inline-grid">
                <select value={participantForm.participant_type} onChange={(e) => setParticipantForm({ ...participantForm, participant_type: e.target.value })}>
                  <option value="damnificado">Damnificado</option>
                  <option value="victima">Victima</option>
                  <option value="testigo">Testigo</option>
                  <option value="denunciante">Denunciante</option>
                  <option value="sospechoso">Sospechoso</option>
                  <option value="imputado">Imputado</option>
                  <option value="representante_legal">Representante legal</option>
                  <option value="entidad_financiera">Entidad financiera</option>
                  <option value="plataforma_digital">Plataforma digital</option>
                  <option value="otro">Otro</option>
                </select>
                <select value={participantForm.person_type} onChange={(e) => setParticipantForm({ ...participantForm, person_type: e.target.value })}>
                  <option value="persona_fisica">Persona fisica</option>
                  <option value="persona_juridica">Persona juridica</option>
                  <option value="organismo">Organismo</option>
                  <option value="cuenta_digital">Cuenta digital</option>
                  <option value="alias_identidad">Alias/identidad digital</option>
                  <option value="desconocido">Desconocido</option>
                </select>
              </div>
              <input placeholder="Nombre, razon social, alias o identificador" value={participantForm.display_name} onChange={(e) => setParticipantForm({ ...participantForm, display_name: e.target.value })} required />
              <div className="inline-grid">
                <input placeholder="Tipo documento" value={participantForm.document_type} onChange={(e) => setParticipantForm({ ...participantForm, document_type: e.target.value })} />
                <input placeholder="Documento / CUIT / ID" value={participantForm.document_number} onChange={(e) => setParticipantForm({ ...participantForm, document_number: e.target.value })} />
              </div>
              <div className="inline-grid">
                <input placeholder="Email" value={participantForm.email} onChange={(e) => setParticipantForm({ ...participantForm, email: e.target.value })} />
                <input placeholder="Telefono" value={participantForm.phone} onChange={(e) => setParticipantForm({ ...participantForm, phone: e.target.value })} />
              </div>
              <textarea placeholder="Relacion con el caso / rol investigativo" value={participantForm.relationship_to_case} onChange={(e) => setParticipantForm({ ...participantForm, relationship_to_case: e.target.value })} />
              <button disabled={!selectedCaseId}><Users size={17} /> Registrar participante</button>
            </form>
            <div className="mini-list">
              {participants.slice(0, 5).map((item) => (
                <span key={item.id}>{item.participant_type}: {item.display_name} ({item.person_type})</span>
              ))}
            </div>
          </StepCard>

          <StepCard number={3} title="Cargar evidencia y calcular hash" done={Boolean(latestEvidence?.sha256_hash)}>
            <form className="compact-form" onSubmit={uploadEvidence}>
              <textarea placeholder="Descripcion de evidencia" value={evidenceForm.description} onChange={(e) => setEvidenceForm({ ...evidenceForm, description: e.target.value })} required />
              <input placeholder="Responsable" value={evidenceForm.responsible} onChange={(e) => setEvidenceForm({ ...evidenceForm, responsible: e.target.value })} />
              <input placeholder="Custodio" value={evidenceForm.custodian} onChange={(e) => setEvidenceForm({ ...evidenceForm, custodian: e.target.value })} />
              <input type="file" onChange={(e) => setEvidenceFile(e.target.files?.[0] ?? null)} />
              <button disabled={!selectedCaseId || !evidenceFile}><Upload size={17} /> Subir y hashear</button>
            </form>
            {latestEvidence && <code>SHA-256: {latestEvidence.sha256_hash}</code>}
          </StepCard>

          <StepCard number={4} title="Registrar cadena de custodia" done={custody.length > 0}>
            <form className="compact-form" onSubmit={createCustodyAction}>
              <input placeholder="Accion" value={custodyForm.action_type} onChange={(e) => setCustodyForm({ ...custodyForm, action_type: e.target.value })} />
              <input placeholder="Responsable" value={custodyForm.user_responsible} onChange={(e) => setCustodyForm({ ...custodyForm, user_responsible: e.target.value })} />
              <textarea placeholder="Detalle de la accion" value={custodyForm.detailed_description} onChange={(e) => setCustodyForm({ ...custodyForm, detailed_description: e.target.value })} required />
              <button disabled={!selectedCaseId}><Fingerprint size={17} /> Registrar custodia</button>
            </form>
          </StepCard>

          <StepCard number={5} title="Analizar IP, URL o dato cybercrime" done={Boolean(indicatorResult)}>
            <div className="compact-form">
              <input value={indicator} onChange={(e) => setIndicator(e.target.value)} placeholder="IP, dominio o URL" />
              <button onClick={analyzeIndicator} disabled={!indicator}><Globe2 size={17} /> Analizar indicador</button>
            </div>
            {renderIndicatorOutcome()}
          </StepCard>

          <StepCard number={6} title="Tipificar incidente con normativa argentina" done={Boolean(legalTypification?.principal_typification || legalMappings.length)}>
            <div className="compact-form">
              <input value={legalQuery} onChange={(e) => setLegalQuery(e.target.value)} />
              <button onClick={() => searchAndTypifyLegal(false)}><Gavel size={17} /> Tipificar y sugerir norma</button>
              <button className="secondary-button" onClick={() => searchAndTypifyLegal(true)} disabled={!selectedCaseId || legalApplyState === "applying"}>
                <CheckCircle2 size={17} /> {legalApplyState === "applying" ? "Aplicando..." : legalApplyState === "applied" ? "Aplicado al caso" : "Aplicar al caso"}
              </button>
            </div>
            {legalApplyMessage && (
              <div className={`action-feedback ${legalApplyState}`}>
                {legalApplyMessage}
              </div>
            )}
            {legalTypification?.principal_typification ? (
              <div className="typification-card compact">
                <span>{legalTypification.profile?.label || "Tipificacion asistida"}</span>
                <h3>{legalTypification.principal_typification.reference} · {prettySpanish(legalTypification.principal_typification.title)}</h3>
                <p>{prettySpanish(legalTypification.principal_typification.applicability_to_case)}</p>
                <small>Elementos: {prettySpanish(legalTypification.principal_typification.why)}</small>
                <small>Limites: {prettySpanish(legalTypification.principal_typification.probatory_limits)}</small>
                <div className="readiness-bar"><div style={{ width: `${legalTypification.readiness_score}%` }} /></div>
                <small>Confianza {prettySpanish(legalTypification.confidence)} · {prettySpanish(legalTypification.decision_level)}</small>
              </div>
            ) : (
              <EmptyState text="Describe el incidente y ejecuta la tipificacion. OPERIA sugerira la norma principal y conexas." />
            )}
            {legalTypification?.connected_typifications?.length ? (
              <div className="mini-list">
                {legalTypification.connected_typifications.slice(0, 4).map((item) => (
                  <span key={`${item.article_id}-${item.reference}`}>{item.reference} · {prettySpanish(item.title)} · {prettySpanish(item.legal_role)}</span>
                ))}
              </div>
            ) : null}
            {legalTypification?.missing_for_stronger_typification?.length ? (
              <ul className="compact-list">
                {legalTypification.missing_for_stronger_typification.map((item) => <li key={item}>{prettySpanish(item)}</li>)}
              </ul>
            ) : null}
          </StepCard>

          <StepCard number={7} title="Ampliar análisis técnico-jurídico" done={Boolean(aiResult)}>
            <div className="compact-form">
              <textarea value={aiPrompt} onChange={(e) => setAiPrompt(e.target.value)} />
              <button onClick={runAiAssist}><Bot size={17} /> {latestReport ? "Ampliar informe" : "Analizar caso"}</button>
            </div>
            {latestReport && <p className="notice">Con informe generado, esta accion agrega hipotesis, conclusiones y fundamentacion legal al reporte.</p>}
            {latestReport ? renderAiEnrichmentOutcome() : renderCaseAnalysisOutcome()}
          </StepCard>

          <StepCard number={8} title="Generar informe" done={reports.length > 0}>
            <div className="compact-form">
              <input placeholder="Analista / operador interviniente" value={analystName} onChange={(e) => setAnalystName(e.target.value)} />
            </div>
            <button onClick={generateReport} disabled={!selectedCaseId}><FileText size={17} /> Generar informe integral</button>
            {latestReport && <p className="notice">Ultimo informe: {latestReport.title}</p>}
            <div className="summary-list">
              <span>Nivel de exportabilidad: {exportabilitySnapshot.level}</span>
              <span>Score de exportabilidad: {exportabilitySnapshot.score}/100</span>
            </div>
          </StepCard>

          <StepCard number={9} title="Revisar informe" done={Boolean(reviewResult) && latestReport?.review_score !== undefined}>
            <button onClick={reviewReport} disabled={!latestReport}><FileCheck2 size={17} /> Revisar informe</button>
            {renderReviewOutcome()}
          </StepCard>

          <StepCard number={10} title="Exportar PDF" done={Boolean(latestReport)}>
            {latestReport ? (
              <a className="download-button" href={`${API_BASE}/exports/reports/${latestReport.id}/pdf`} target="_blank">
                <Download size={17} /> Exportar PDF con manifiesto
              </a>
            ) : (
              <EmptyState text="Genera un informe antes de exportar." />
            )}
          </StepCard>

          <StepCard number={11} title="Resumen operativo" done={Boolean(selectedCase && latestEvidence && latestReport)}>
            <div className="summary-list">
              <span>Casos: {cases.length}</span>
              <span>Participantes del caso: {participants.length}</span>
              <span>Evidencias del caso: {evidence.length}</span>
              <span>Acciones de custodia: {custody.length}</span>
              <span>Informes del caso: {reports.length}</span>
              <span>Estado del caso: {selectedCase?.status || "sin caso"}</span>
              <span>Exportabilidad: {exportabilitySnapshot.level}</span>
            </div>
          </StepCard>

          <StepCard number={12} title="Cerrar caso" done={closureStatus?.already_closed}>
            <div className="compact-form">
              <textarea value={closureNote} onChange={(e) => setClosureNote(e.target.value)} />
              <button onClick={closeCase} disabled={!selectedCaseId || closureStatus?.already_closed}>
                <CheckCircle2 size={17} /> Cerrar caso
              </button>
            </div>
            <div className="button-row">
              <button className="secondary-button" onClick={requestFinalExport} disabled={!latestReport}>
                <Download size={16} /> Exportar final sellado
              </button>
              <button className="secondary-button" onClick={() => setActive("reports")} disabled={!latestReport}>
                <FileText size={16} /> Ver informe
              </button>
            </div>
            {renderExportFinalOutcome()}
            {closureStatus?.message && <p className="notice success">{closureStatus.message}</p>}
            {closureStatus?.already_closed && <p className="notice success">Caso cerrado. Las acciones futuras deben considerarse posteriores al cierre.</p>}
            {closureStatus && !closureStatus.ready_to_close && !closureStatus.already_closed && (
              <div className="requirements">
                <strong>Advertencias antes de cerrar:</strong>
                {closureStatus.missing.map((item) => (
                  <span key={item}>{item}</span>
                ))}
                <em>Estas advertencias no bloquean el cierre operativo; quedan registradas para trazabilidad.</em>
              </div>
            )}
            {!!closureStatus?.closure_warnings?.length && (
              <div className="requirements">
                <strong>El caso se cerro con advertencias registradas:</strong>
                {closureStatus.closure_warnings.map((item) => (
                  <span key={item}>{item}</span>
                ))}
              </div>
            )}
            {closureStatus?.ready_to_close && <p className="notice success">El caso cumple los requisitos minimos de cierre.</p>}
          </StepCard>
        </div>
      </div>
    );
  }

  function renderDashboard() {
    const hashedEvidence = evidence.filter((item) => Boolean(item.sha256_hash)).length;
    const approvedLegalMappings = legalMappings.filter((item) => item.decision_status !== "descartado").length;
    const reportReviewed = Boolean(latestReport && latestReport.review_score >= 80);
    const pdfExports = manifests.filter((item) => item.report_id === latestReport?.id || item.export_type.toLowerCase().includes("pdf"));
    const rubricPercent = rubricEvaluation?.percentage ?? 0;
    const technicalFindingCount = dashboard.metrics?.proof_matrix_rows ?? legalProbatoryMatrix?.rows.length ?? 0;
    const hasTechnicalFindings = technicalFindingCount > 0;
    const ctfStatusClass = (status: string) => status === "crítico" ? "critical" : status === "listo" ? "ready" : status === "parcial" ? "partial" : "incomplete";
    const ctfItems = [
      { key: "case", label: "Caso activo", value: selectedCase ? selectedCase.case_code : "Sin caso seleccionado", status: selectedCase ? "listo" : "crítico", detail: selectedCase ? selectedCase.title : "Selecciona o crea un caso para iniciar el tablero." },
      { key: "evidence", label: "Evidencia cargada", value: `${evidence.length}`, status: evidence.length ? "listo" : "incompleto", detail: evidence.length ? "Hay evidencia asociada al caso." : "Carga evidencia y preserva el archivo o fuente." },
      { key: "hashes", label: "Hashes completos", value: `${hashedEvidence}/${evidence.length || 0}`, status: evidence.length && hashedEvidence === evidence.length ? "listo" : evidence.length ? "parcial" : "incompleto", detail: evidence.length ? "Verifica SHA-256 en cada evidencia." : "Primero carga evidencia." },
      { key: "custody", label: "Cadena de custodia", value: `${custody.length}`, status: custody.length ? "listo" : "incompleto", detail: custody.length ? "Acciones de custodia registradas." : "Registra preservación, responsable y procedimiento." },
      { key: "deepfake", label: "Deepfake / medios", value: `${deepfakeAnalyses.length}`, status: deepfakeAnalyses.length ? "listo" : "parcial", detail: deepfakeAnalyses.length ? "Hay análisis de autenticación de medios." : "Opcional según el caso; úsalo si hay imagen, video o audio." },
      { key: "blockchain", label: "Blockchain", value: `${blockchainTransactions.length}`, status: blockchainTransactions.length ? "listo" : "parcial", detail: blockchainTransactions.length ? "Hay transacciones registradas." : "Opcional según el caso; úsalo si hay wallets, pagos o tx hash." },
      { key: "iot", label: "IoT", value: `${iotDevices.length}`, status: iotDevices.length ? "listo" : "parcial", detail: iotDevices.length ? "Hay dispositivos IoT registrados." : "Opcional según el caso; úsalo si hay cámaras, sensores o dispositivos." },
      { key: "legal", label: "Normas aplicadas", value: `${approvedLegalMappings}`, status: approvedLegalMappings ? "listo" : "incompleto", detail: approvedLegalMappings ? "Existe encuadre legal aprobado o sugerido." : "Tipifica el incidente desde biblioteca legal registrada." },
      { key: "findings", label: "Hallazgos", value: `${technicalFindingCount}`, status: hasTechnicalFindings ? "listo" : "incompleto", detail: hasTechnicalFindings ? "Hay hallazgos o matriz técnica/probatoria." : "Guarda hallazgos desde Cybercrime o laboratorios." },
      { key: "report", label: "Informe generado", value: reports.length ? "Sí" : "No", status: reports.length ? "listo" : "incompleto", detail: reports.length ? latestReport?.title || "Informe disponible." : "Genera el informe integral." },
      { key: "review", label: "Informe revisado", value: latestReport ? `${latestReport.review_score}/100` : "Sin revisión", status: reportReviewed ? "listo" : latestReport ? "parcial" : "incompleto", detail: reportReviewed ? "La revisión supera el umbral operativo." : "Ejecuta revisión y corrige advertencias." },
      { key: "export", label: "PDF exportado", value: `${pdfExports.length}`, status: pdfExports.length ? "listo" : "incompleto", detail: pdfExports.length ? "Hay exportación registrada." : "Exporta PDF con manifiesto antes de entregar." },
      { key: "rubric", label: "Rúbrica completada", value: rubricEvaluation ? `${rubricEvaluation.percentage}%` : "Sin evaluar", status: rubricEvaluation ? (rubricPercent >= 80 ? "listo" : rubricPercent >= 50 ? "parcial" : "crítico") : "incompleto", detail: rubricEvaluation ? rubricEvaluation.summary : "Evalúa la rúbrica del desafío." },
    ];
    const statusWeight: Record<string, number> = { listo: 1, parcial: 0.55, incompleto: 0, crítico: 0 };
    const ctfScore = Math.round((ctfItems.reduce((total, item) => total + statusWeight[item.status], 0) / ctfItems.length) * 100);
    const criticalCount = ctfItems.filter((item) => item.status === "crítico").length;
    const incompleteCount = ctfItems.filter((item) => item.status === "incompleto").length;
    const ctfLevel = criticalCount ? "Crítico" : ctfScore >= 82 ? "Listo" : ctfScore >= 52 ? "Parcial" : "Incompleto";
    const ctfLevelClass = criticalCount ? "critical" : ctfScore >= 82 ? "ready" : ctfScore >= 52 ? "partial" : "incomplete";
    const ctfMissing = ctfItems.filter((item) => item.status === "crítico" || item.status === "incompleto").slice(0, 6);
    const currentCaseReadiness = [
      { label: "Caso seleccionado", ok: Boolean(selectedCase), detail: selectedCase?.case_code || "Sin caso" },
      { label: "Evidencia preservada", ok: evidence.length > 0, detail: `${evidence.length} evidencia(s)` },
      { label: "Custodia", ok: custody.length > 0, detail: `${custody.length} accion(es)` },
      { label: "Tipificacion legal", ok: legalMappings.some((item) => item.decision_status !== "descartado"), detail: `${legalMappings.length} mapeo(s)` },
      { label: "Informe", ok: reports.length > 0, detail: latestReport ? professionalReportStatus(latestReport.status) : "Sin informe" },
      { label: "Revision", ok: Boolean(latestReport && latestReport.review_score >= 80), detail: latestReport ? `Score ${latestReport.review_score}` : "Sin revision" },
    ];
    const nextAction =
      !selectedCase ? "Seleccionar o crear un caso operativo." :
      !evidence.length ? "Cargar evidencia y calcular hash." :
      !custody.length ? "Registrar cadena de custodia." :
      !legalMappings.length ? "Tipificar el incidente y aplicar norma al caso." :
      !latestReport ? "Generar informe integral." :
      latestReport.review_score < 80 ? "Revisar informe y corregir advertencias." :
      "Evaluar exportacion final sellada.";

    return (
      <section className="work-surface">
        <div className="section-head">
          <div>
            <h2>Dashboard Operativo</h2>
            <p>Centro de mando para saber que esta listo, que falta y cual es la proxima accion pericial.</p>
          </div>
          <button className="icon-button" onClick={refreshCore} title="Actualizar"><RefreshCcw size={18} /></button>
        </div>
        <div className="command-panel">
          <div>
            <span className="tool-kicker">Proxima accion recomendada</span>
            <h3>{nextAction}</h3>
            <p>{selectedCase ? `${selectedCase.case_code} - ${selectedCase.title}` : "OPERIA necesita un caso activo para guiar el flujo."}</p>
          </div>
          <div className="button-row">
            <button className="secondary-button" onClick={() => setActive("workflow")}><CheckCircle2 size={16} /> Abrir flujo</button>
            <button className="secondary-button" onClick={() => setActive("caseDetail")} disabled={!selectedCaseId}><FileCheck2 size={16} /> Detalle del caso</button>
          </div>
        </div>
        <div className="readiness-grid">
          {currentCaseReadiness.map((item) => (
            <div className={`readiness-card ${item.ok ? "ok" : "pending"}`} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.ok ? "OK" : "Pendiente"}</strong>
              <small>{item.detail}</small>
            </div>
          ))}
        </div>
        {dashboard.metrics ? <MetricGrid metrics={dashboard.metrics} /> : <EmptyState text="Sin metricas cargadas." />}
        <div className="ctf-panel">
          <div className="ctf-hero">
            <div>
              <span className="tool-kicker">Preparación CTF</span>
              <h3>Estado de entrega del caso</h3>
              <p>
                Semáforo operativo para verificar evidencia, laboratorios, encuadre legal, informe, exportación y rúbrica antes de entregar.
              </p>
            </div>
            <div className={`ctf-score ${ctfLevelClass}`}>
              <span>{ctfLevel}</span>
              <strong>{ctfScore}/100</strong>
              <small>{incompleteCount} pendiente(s)</small>
            </div>
          </div>
          {ctfDashboardMessage && (
            <div className={`action-feedback ${ctfDashboardState === "working" ? "updating" : ctfDashboardState === "success" ? "updated" : ctfDashboardState}`}>
              {ctfDashboardMessage}
            </div>
          )}
          <div className="ctf-action-row">
            <button className="secondary-button" onClick={() => setActive("deepfakeMedia")} disabled={!selectedCaseId}><FileCheck2 size={16} /> Ir a Deepfake Lab</button>
            <button className="secondary-button" onClick={() => setActive("blockchainForensics")} disabled={!selectedCaseId}><Globe2 size={16} /> Ir a Blockchain Lab</button>
            <button className="secondary-button" onClick={() => setActive("iotForensics")} disabled={!selectedCaseId}><Shield size={16} /> Ir a IoT Lab</button>
            <button className="secondary-button" onClick={() => setActive("legalKnowledge")} disabled={!selectedCaseId}><BookOpen size={16} /> Ir a Biblioteca Legal</button>
            <button className="secondary-button" onClick={updateRubricFromCtfDashboard} disabled={!selectedCaseId || ctfDashboardState === "working"}><Gavel size={16} /> Evaluar rúbrica</button>
            <button onClick={generateReportFromCtfDashboard} disabled={!selectedCaseId || ctfDashboardState === "working"}><FileText size={16} /> Generar informe</button>
            <button onClick={exportPdfFromCtfDashboard} disabled={!latestReport}><Download size={16} /> Exportar PDF</button>
          </div>
          <div className="ctf-grid">
            {ctfItems.map((item) => (
              <div className={`ctf-card ${ctfStatusClass(item.status)}`} key={item.key}>
                <div>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </div>
                <em>{prettySpanish(item.status)}</em>
                <p>{item.detail}</p>
              </div>
            ))}
          </div>
          <div className={`ctf-guidance ${ctfLevelClass}`}>
            <strong>{ctfLevel === "Listo" ? "El caso está cerca de una entrega defendible." : "Qué falta para mejorar la entrega"}</strong>
            {ctfMissing.length ? (
              ctfMissing.map((item) => <span key={item.key}>{item.label}: {item.detail}</span>)
            ) : (
              <span>Revisa visualmente el PDF final, valida conclusiones y conserva el manifiesto de exportación.</span>
            )}
          </div>
        </div>
        <div className="preview-grid">
          <div>
            <h4>Casos por estado</h4>
            <div className="summary-list">
              {Object.entries(dashboard.cases_by_status || {}).map(([status, count]) => (
                <span key={status}>{prettySpanish(status)}: {count}</span>
              ))}
              {!dashboard.cases_by_status && <span>Sin estados cargados.</span>}
            </div>
          </div>
          <div>
            <h4>Informes recientes</h4>
            {(dashboard.report_readiness || []).slice(0, 6).map((item) => (
              <div className={`preview-section ${item.ready_for_final ? "" : "warning"}`} key={item.report_id}>
                <strong>{item.title}</strong>
                <span>{professionalReportStatus(item.status)} | Score {item.review_score}</span>
                <small>{item.ready_for_final ? "Listo para cierre sellado" : "Requiere completar checklist"}</small>
              </div>
            ))}
          </div>
        </div>
        {!!dashboard.alerts?.length && (
          <div className="requirements">
            <strong>Alertas operativas</strong>
            {dashboard.alerts.map((item) => <span key={item}>{prettySpanish(item)}</span>)}
          </div>
        )}
      </section>
    );
  }

  function renderCases() {
    return (
      <section className="work-surface">
        <div className="section-head">
          <div>
            <h2>Casos Registrados</h2>
            <p>Sistema compartido de casos preparado para SaaS.</p>
          </div>
        </div>
        <div className="case-list">
          <div className="case-list-header">
            <span>Código</span>
            <span>Expediente</span>
            <span>Tipo</span>
            <span>Estado</span>
            <span>Acción</span>
          </div>
          {cases.map((item) => (
            <button className={`case-row ${selectedCaseId === item.id ? "selected" : ""}`} key={item.id} onClick={() => setSelectedCaseId(item.id)}>
              <code>{item.case_code}</code>
              <strong>{item.title}</strong>
              <span>{prettySpanish(item.incident_type)}</span>
              <em>{prettySpanish(item.status)}</em>
              <small>{selectedCaseId === item.id ? "Seleccionado" : "Abrir"}</small>
            </button>
          ))}
          {!cases.length && <EmptyState text="No hay casos registrados." />}
        </div>
      </section>
    );
  }

  function renderHistory() {
    const isClosedCase = (item: CaseItem) => item.status.toLowerCase() === "cerrado";
    const openItems = chronologicalCases.filter((item) => !isClosedCase(item));
    const closedItems = chronologicalCases.filter((item) => isClosedCase(item));

    return (
      <section className="work-surface history-workspace">
        <div className="section-head">
          <div>
            <h2>Historial</h2>
            <p>Linea cronologica de casos, informes, flujo de trabajo y exportaciones asociadas.</p>
          </div>
          <div className="section-actions">
            <button className="new-case-button" onClick={() => {
              startNewCaseDraft();
              setActive("workflow");
            }}>
              <Briefcase size={17} /> Nuevo Caso
            </button>
            <button className="icon-button" onClick={refreshCore} title="Actualizar historial">
              <RefreshCcw size={18} />
            </button>
          </div>
        </div>

        <div className="history-stats">
          <div>
            <span>Total de casos</span>
            <strong>{chronologicalCases.length}</strong>
          </div>
          <div>
            <span>En curso</span>
            <strong>{openItems.length}</strong>
          </div>
          <div>
            <span>Cerrados</span>
            <strong>{closedItems.length}</strong>
          </div>
        </div>

        <div className="history-list">
          {chronologicalCases.map((item) => {
            const isClosed = isClosedCase(item);
            const isSelected = selectedCaseId === item.id;
            return (
              <article className={`history-item ${isSelected ? "selected" : ""}`} key={item.id}>
                <div className={`history-dot ${isClosed ? "closed" : "open"}`} />
                <div className="history-main">
                  <div className="history-title-row">
                    <div>
                      <code>{item.case_code}</code>
                      <h3>{item.title}</h3>
                    </div>
                    <span className={`badge ${isClosed ? "" : "success"}`}>{prettySpanish(item.status)}</span>
                  </div>
                  <div className="history-meta">
                    <span>{prettySpanish(item.incident_type)}</span>
                    <span>Ultima actividad: {formatHistoryDate(item.updated_at || item.created_at)}</span>
                  </div>
                  <p>{item.description ? prettySpanish(item.description) : "Sin descripcion inicial registrada."}</p>
                  <div className="history-footnote">
                    <span>Flujo de trabajo, informes y exportaciones permanecen asociados a este caso.</span>
                  </div>
                </div>
                <div className="history-actions">
                  {!isClosed && (
                    <button onClick={() => openCaseFromHistory(item.id, "workflow")}>
                      <RefreshCcw size={16} /> Continuar trabajo
                    </button>
                  )}
                  <button className="secondary-button" onClick={() => openCaseFromHistory(item.id, "caseDetail")}>
                    <FileCheck2 size={16} /> Ver detalle
                  </button>
                  {isClosed && <small>Caso cerrado: disponible para consulta y exportacion.</small>}
                </div>
              </article>
            );
          })}
          {!chronologicalCases.length && <EmptyState text="No hay casos registrados en el historial." />}
        </div>
      </section>
    );
  }

  function renderCaseDetail() {
    const locked = selectedCase?.status === "cerrado";
    const legalRows = legalProbatoryMatrix?.rows || [];
    const latestAudit = auditLogs[0];
    const readinessItems = [
      { label: "Narrativa del caso", ok: Boolean(selectedCase?.description), detail: selectedCase?.description ? "Cargada" : "Falta descripción inicial" },
      { label: "Participantes", ok: participants.length > 0, detail: `${participants.length} registro(s)` },
      { label: "Evidencia preservada", ok: evidence.length > 0, detail: `${evidence.length} evidencia(s)` },
      { label: "Hashes", ok: evidence.length > 0 && evidence.every((item) => Boolean(item.sha256_hash)), detail: evidence.length ? "Integridad verificable" : "Sin archivos" },
      { label: "Custodia", ok: custody.length > 0, detail: `${custody.length} acción(es)` },
      { label: "Mapeo legal", ok: legalMappings.some((item) => item.decision_status !== "descartado"), detail: `${legalMappings.length} norma(s)` },
      { label: "Informe", ok: Boolean(latestReport), detail: latestReport ? professionalReportStatus(latestReport.status) : "No generado" },
      { label: "Revisión", ok: Boolean(latestReport && latestReport.review_score >= 80), detail: latestReport ? `Score ${latestReport.review_score}` : "Sin revisión" }
    ];
    const tabs: Array<{ key: CaseDetailTab; label: string; count?: number }> = [
      { key: "summary", label: "Resumen" },
      { key: "participants", label: "Personas", count: participants.length },
      { key: "evidence", label: "Evidencia", count: evidence.length },
      { key: "custody", label: "Custodia", count: custody.length },
      { key: "legal", label: "Legal", count: legalMappings.length },
      { key: "reports", label: "Informes", count: reports.length },
      { key: "audit", label: "Auditoría", count: auditLogs.length }
    ];

    const renderParticipantsPanel = () => (
      <div className="detail-panel">
        <div className="panel-head">
          <h3>Personas y entidades</h3>
        </div>
        {participants.map((item) => (
          <div className="editable-record" key={item.id}>
            <div>
              <strong>{prettySpanish(item.display_name)}</strong>
              <span>{prettySpanish(item.participant_type)} | {prettySpanish(item.person_type)} | {prettySpanish(item.sensitivity_level)}</span>
              <small>{prettySpanish(item.relationship_to_case || item.role_description || "Relación pendiente")}</small>
            </div>
            <div className="record-actions">
              <button className="icon-button" onClick={() => setEditingParticipant(item)} title="Editar"><Save size={15} /></button>
              <button className="icon-button danger" onClick={() => deleteParticipant(item.id)} title="Eliminar"><Trash2 size={15} /></button>
            </div>
          </div>
        ))}
        {!participants.length && <EmptyState text="Sin participantes cargados." />}
      </div>
    );

    const renderEvidencePanel = () => (
      <div className="detail-panel">
        <div className="panel-head">
          <h3>Evidencia</h3>
          <button className="secondary-button" onClick={() => setActive("evidence")}>Abrir evidencia</button>
        </div>
        {evidence.map((item) => (
          <div className="editable-record" key={item.id}>
            <div>
              <strong>{prettySpanish(item.evidence_type)}</strong>
              <span>{prettySpanish(item.description)}</span>
              <code>{item.sha256_hash || "hash pendiente"}</code>
            </div>
            <div className="record-actions">
              <button className="icon-button" onClick={() => setEditingEvidence(item)} title="Editar"><Save size={15} /></button>
              <button className="icon-button danger" onClick={() => deleteEvidence(item.id)} title="Eliminar"><Trash2 size={15} /></button>
            </div>
          </div>
        ))}
        {!evidence.length && <EmptyState text="Sin evidencia cargada." />}
      </div>
    );

    const renderCustodyPanel = () => (
      <div className="detail-panel">
        <div className="panel-head">
          <h3>Cadena de custodia</h3>
        </div>
        {custody.map((item) => (
          <div className="editable-record" key={item.id}>
            <div>
              <strong>{prettySpanish(item.action_type)}</strong>
              <span>{prettySpanish(item.detailed_description)}</span>
              <small>{prettySpanish(item.user_responsible || "Responsable pendiente")} | {prettySpanish(item.status)}</small>
            </div>
            <div className="record-actions">
              <button className="icon-button" onClick={() => setEditingCustody(item)} title="Editar"><Save size={15} /></button>
              <button className="icon-button danger" onClick={() => deleteCustodyAction(item.id)} title="Eliminar"><Trash2 size={15} /></button>
            </div>
          </div>
        ))}
        {!custody.length && <EmptyState text="Sin acciones de custodia." />}
      </div>
    );

    const renderLegalPanel = () => (
      <div className="detail-panel wide">
        <div className="panel-head">
          <h3>Mapeo legal y matriz probatoria</h3>
          <button className="secondary-button" onClick={() => setActive("legalKnowledge")}>Abrir biblioteca</button>
        </div>
        {legalQualityControl && (
          <div className={`quality-strip ${legalQualityControl.risk_level === "bajo" ? "success" : legalQualityControl.risk_level === "alto" ? "danger" : ""}`}>
            <strong>Semáforo legal: {prettySpanish(legalQualityControl.risk_level)}</strong>
            <span>Score {legalQualityControl.score}/100 | {prettySpanish(legalQualityControl.conclusion_impact)}</span>
          </div>
        )}
        {legalRows.slice(0, 8).map((item, index) => (
          <div className="editable-record" key={`${item.mapping_id}-${index}`}>
            <div>
              <strong>{item.norm_reference} · {prettySpanish(item.legal_element)}</strong>
              <span>{prettySpanish(item.element_status)} | fuerza {prettySpanish(item.probatory_strength)} | riesgo {prettySpanish(item.contradiction_risk)}</span>
              <small>{item.evidence_description || item.missing_evidence || "Sin vínculo probatorio registrado."}</small>
            </div>
          </div>
        ))}
        {!legalRows.length && <EmptyState text="Sin matriz legal-probatoria cargada." />}
      </div>
    );

    const renderReportsPanel = () => (
      <div className="detail-panel wide">
        <div className="panel-head">
          <h3>Informes y exportaciones</h3>
          <button className="secondary-button" onClick={() => setActive("reports")}>Abrir informes</button>
        </div>
        {reports.map((item) => (
          <div className="editable-record" key={item.id}>
            <div>
              <strong>{item.title}</strong>
              <span>{professionalReportStatus(item.status)} | Score {item.review_score}</span>
              <small>Exportabilidad estimada: {exportabilitySnapshot.level} ({exportabilitySnapshot.score}/100)</small>
            </div>
            <a className="text-link" href={`${API_BASE}/exports/reports/${item.id}/pdf`} target="_blank">Exportar PDF</a>
          </div>
        ))}
        {!reports.length && <EmptyState text="Sin informes generados." />}
        {!!manifests.length && (
          <div className="mini-list">
            {manifests.slice(0, 6).map((item) => (
              <span key={item.id}>{item.export_type}: {item.filename} | {item.sha256_hash.slice(0, 16)}...</span>
            ))}
          </div>
        )}
      </div>
    );

    const renderAuditPanel = () => (
      <div className="detail-panel wide">
        <div className="panel-head">
          <h3>Auditoría del caso</h3>
        </div>
        <div className="audit-list">
          {auditLogs.slice(0, 20).map((item) => (
            <div key={item.id}>
              <strong>{prettySpanish(item.action)}</strong>
              <span>{item.module} | {item.severity} | {new Date(item.created_at).toLocaleString()}</span>
              <small>{item.details || `${item.entity_type} ${item.entity_id}`}</small>
            </div>
          ))}
          {!auditLogs.length && <EmptyState text="Sin auditoría visible para este caso." />}
        </div>
      </div>
    );

    return (
      <div className="case-detail">
        <section className="work-surface">
          <div className="section-head">
            <div>
              <h2>Expediente Maestro del Caso</h2>
              <p>{selectedCase ? `${selectedCase.case_code} - ${selectedCase.title}` : "Selecciona un caso para ver su expediente completo."}</p>
            </div>
            <select value={selectedCaseId} onChange={(event) => setSelectedCaseId(Number(event.target.value) || "")}>
              <option value="">Seleccionar caso</option>
              {cases.map((item) => <option value={item.id} key={item.id}>{item.case_code}</option>)}
            </select>
          </div>
          {selectedCase ? (
            <div className="case-dossier-hero">
              <div className="dossier-main">
                <span className="eyebrow">{selectedCase.case_code}</span>
                <h3>{selectedCase.title}</h3>
                <p>{prettySpanish(selectedCase.description || "Sin narrativa inicial cargada.")}</p>
                <div className="dossier-badges">
                  <span>{prettySpanish(selectedCase.status)}</span>
                  <span>{prettySpanish(selectedCase.incident_type)}</span>
                  <span>{exportabilitySnapshot.level} · {exportabilitySnapshot.score}/100</span>
                </div>
              </div>
              <div className="dossier-actions">
                <button onClick={() => setActive("workflow")}><CheckCircle2 size={16} /> Flujo</button>
                <button className="secondary-button" onClick={() => setActive("reports")}><FileText size={16} /> Informes</button>
                <button className="secondary-button" onClick={() => setActive("legalKnowledge")}><Gavel size={16} /> Legal</button>
              </div>
            </div>
          ) : <EmptyState text="No hay caso seleccionado." />}
          {locked && <p className="notice success">Caso cerrado: las modificaciones futuras deberian tratarse como reapertura o correccion auditada.</p>}
        </section>

        <section className="work-surface compact-surface">
          <div className="dossier-tabs">
            {tabs.map((tab) => (
              <button key={tab.key} className={caseDetailTab === tab.key ? "active" : ""} onClick={() => setCaseDetailTab(tab.key)}>
                {tab.label}{typeof tab.count === "number" ? ` ${tab.count}` : ""}
              </button>
            ))}
          </div>

          {caseDetailTab === "summary" && (
            <div className="dossier-grid">
              <div className="detail-panel wide">
                <div className="panel-head">
                  <h3>Estado operativo del expediente</h3>
                </div>
                <div className="readiness-list">
                  {readinessItems.map((item) => (
                    <div className={`readiness-item ${item.ok ? "ok" : ""}`} key={item.label}>
                      <CheckCircle2 size={16} />
                      <div>
                        <strong>{item.label}</strong>
                        <span>{item.detail}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="detail-panel">
                <div className="panel-head">
                  <h3>Resumen técnico</h3>
                </div>
                <div className="case-overview">
                  <div><span>Participantes</span><strong>{participants.length}</strong></div>
                  <div><span>Evidencia</span><strong>{evidence.length}</strong></div>
                  <div><span>Custodia</span><strong>{custody.length}</strong></div>
                  <div><span>Informes</span><strong>{reports.length}</strong></div>
                </div>
              </div>
              <div className="detail-panel">
                <div className="panel-head">
                  <h3>Última actividad</h3>
                </div>
                {latestAudit ? (
                  <div className="editable-record single">
                    <div>
                      <strong>{prettySpanish(latestAudit.action)}</strong>
                      <span>{latestAudit.module} | {latestAudit.severity}</span>
                      <small>{new Date(latestAudit.created_at).toLocaleString()}</small>
                    </div>
                  </div>
                ) : <EmptyState text="Sin actividad auditada." />}
              </div>
            </div>
          )}
          {caseDetailTab === "participants" && renderParticipantsPanel()}
          {caseDetailTab === "evidence" && renderEvidencePanel()}
          {caseDetailTab === "custody" && renderCustodyPanel()}
          {caseDetailTab === "legal" && renderLegalPanel()}
          {caseDetailTab === "reports" && renderReportsPanel()}
          {caseDetailTab === "audit" && renderAuditPanel()}
        </section>

        {editingParticipant && (
          <form className="edit-drawer" onSubmit={saveParticipant}>
            <h3>Editar participante</h3>
            <div className="inline-grid">
              <input value={editingParticipant.display_name} onChange={(e) => setEditingParticipant({ ...editingParticipant, display_name: e.target.value })} />
              <input value={editingParticipant.participant_type} onChange={(e) => setEditingParticipant({ ...editingParticipant, participant_type: e.target.value })} />
            </div>
            <div className="inline-grid">
              <input value={editingParticipant.document_type || ""} onChange={(e) => setEditingParticipant({ ...editingParticipant, document_type: e.target.value })} />
              <input value={editingParticipant.document_number || ""} onChange={(e) => setEditingParticipant({ ...editingParticipant, document_number: e.target.value })} />
            </div>
            <textarea value={editingParticipant.relationship_to_case || ""} onChange={(e) => setEditingParticipant({ ...editingParticipant, relationship_to_case: e.target.value })} />
            <div className="actions-line">
              <button><Save size={16} /> Guardar</button>
              <button type="button" className="secondary" onClick={() => setEditingParticipant(null)}>Cancelar</button>
            </div>
          </form>
        )}

        {editingEvidence && (
          <form className="edit-drawer" onSubmit={saveEvidence}>
            <h3>Editar evidencia</h3>
            <div className="inline-grid">
              <input value={editingEvidence.evidence_type} onChange={(e) => setEditingEvidence({ ...editingEvidence, evidence_type: e.target.value })} />
              <input value={editingEvidence.integrity_status} onChange={(e) => setEditingEvidence({ ...editingEvidence, integrity_status: e.target.value })} />
            </div>
            <textarea value={editingEvidence.description} onChange={(e) => setEditingEvidence({ ...editingEvidence, description: e.target.value })} />
            <input value={editingEvidence.sha256_hash || ""} onChange={(e) => setEditingEvidence({ ...editingEvidence, sha256_hash: e.target.value })} />
            <div className="actions-line">
              <button><Save size={16} /> Guardar</button>
              <button type="button" className="secondary" onClick={() => setEditingEvidence(null)}>Cancelar</button>
            </div>
          </form>
        )}

        {editingCustody && (
          <form className="edit-drawer" onSubmit={saveCustodyAction}>
            <h3>Editar custodia</h3>
            <div className="inline-grid">
              <input value={editingCustody.action_type} onChange={(e) => setEditingCustody({ ...editingCustody, action_type: e.target.value })} />
              <input value={editingCustody.user_responsible || ""} onChange={(e) => setEditingCustody({ ...editingCustody, user_responsible: e.target.value })} />
            </div>
            <textarea value={editingCustody.detailed_description} onChange={(e) => setEditingCustody({ ...editingCustody, detailed_description: e.target.value })} />
            <input value={editingCustody.status || ""} onChange={(e) => setEditingCustody({ ...editingCustody, status: e.target.value })} />
            <div className="actions-line">
              <button><Save size={16} /> Guardar</button>
              <button type="button" className="secondary" onClick={() => setEditingCustody(null)}>Cancelar</button>
            </div>
          </form>
        )}
      </div>
    );
  }

  function renderEvidence() {
    return (
      <section className="work-surface">
        <div className="section-head">
          <div>
            <h2>Evidencia del Caso</h2>
            <p>{selectedCase ? `${selectedCase.case_code} - ${selectedCase.title}` : "Selecciona un caso."}</p>
          </div>
        </div>
        <div className="table">
            {evidence.map((item) => (
              <div className="record" key={item.id}>
                <strong>{item.evidence_type}</strong>
                <span>{item.description}</span>
                <code>{item.sha256_hash || "hash pendiente"}</code>
                <div className="button-row">
                  <button className="secondary-button" onClick={() => verifyEvidenceIntegrity(item.id)}>Verificar integridad</button>
                  <a className="download-button secondary" href={`${API_BASE}/evidence/${item.id}/download`} target="_blank">Descargar</a>
                </div>
              </div>
            ))}
          {!evidence.length && <EmptyState text="Sin evidencia para el caso seleccionado." />}
        </div>
      </section>
    );
  }

  function renderReports() {
    return (
      <section className="work-surface">
        <div className="section-head">
          <div>
            <h2>Informes</h2>
            <p>Vista previa profesional, resumen editable, contradicciones y exportabilidad final.</p>
          </div>
          <button onClick={generateReport} disabled={!selectedCaseId}><FileText size={17} /> Generar informe</button>
        </div>
        {latestReport && (
          <div className="report-toolbar">
            <button onClick={() => loadReportPreview()}><FileCheck2 size={16} /> Vista previa profesional</button>
            <button onClick={reviewReport}><CheckCircle2 size={16} /> Revisar</button>
            <button onClick={requestFinalExport} className={reportPreview?.can_export_final ? "" : "secondary"}>
              <Download size={16} /> Sellar y exportar final
            </button>
            <button onClick={refreshReportAnnexes} className="secondary"><FileText size={16} /> Actualizar anexos</button>
            <a className="download-button secondary" href={`${API_BASE}/exports/reports/${latestReport.id}/pdf`} target="_blank">
              <Download size={16} /> Exportar borrador PDF
            </a>
          </div>
        )}
        {reportPreview && (
          <div className="report-preview">
            <div className="preview-cover">
              <div>
                <span className="eyebrow">Vista previa del informe</span>
                <h3>{reportPreview.title}</h3>
                <p>{prettySpanish(reportPreview.exportability.level)} · Score {reportPreview.exportability.score}/100 · RevisiÃ³n {reportPreview.review_score}</p>
              </div>
              <span className={`badge ${reportPreview.can_export_final ? "success" : ""}`}>
                {reportPreview.can_export_final ? "Exportable como final" : "No exportable como final"}
              </span>
            </div>
            {reportPreview.final_seal && (
              <div className="notice success">
                Sello pericial final: {reportPreview.final_seal.seal_id} - Version {reportPreview.final_seal.report_version}
              </div>
            )}
            {!!reportPreview.warnings.length && (
              <div className="requirements">
                <strong>Alertas de vista previa</strong>
                {reportPreview.warnings.map((item) => <span key={item}>{prettySpanish(item)}</span>)}
              </div>
            )}
            <div className="editor-panel">
              <label>Resumen ejecutivo editable</label>
              <textarea value={executiveSummaryDraft} onChange={(event) => setExecutiveSummaryDraft(event.target.value)} />
              <button onClick={saveExecutiveSummary} disabled={!executiveSummaryDraft.trim()}>
                <Save size={16} /> Guardar resumen ejecutivo
              </button>
            </div>
            <div className="preview-grid">
              <div>
                <h4>Checklist pericial final</h4>
                <div className="summary-list">
                  <span>Estado: {reportPreview.final_checklist.ready ? "Completo" : "Incompleto"}</span>
                  <span>Score: {reportPreview.final_checklist.score}/100</span>
                </div>
                {reportPreview.final_checklist.items.map((item) => (
                  <div className={`preview-section ${item.ok ? "" : "warning"}`} key={item.key}>
                    <strong>{item.ok ? "Cumplido" : "Pendiente"} · {prettySpanish(item.label)}</strong>
                    <small>{prettySpanish(item.message)}</small>
                  </div>
                ))}
              </div>
              <div>
                <h4>Versionado del informe</h4>
                <div className="button-row">
                  {["borrador", "preliminar", "revisado", "final", "corregido", "reabierto"].map((status) => (
                    <button key={status} className="secondary" onClick={() => transitionReportStatus(status)}>
                      {prettySpanish(status)}
                    </button>
                  ))}
                </div>
                <p className="notice">La versiÃ³n final solo se permite si el checklist pericial estÃ¡ completo.</p>
              </div>
            </div>
            <div className="preview-grid">
              <div>
                <h4>Secciones renderizables</h4>
                {reportPreview.sections.map((section) => (
                  <div className="preview-section" key={section.title}>
                    <strong>{prettySpanish(section.title)}</strong>
                    <span>{section.word_count} palabras {section.has_tables ? "· contiene tabla" : ""}</span>
                    <small>{prettySpanish(section.excerpt)}</small>
                  </div>
                ))}
              </div>
              <div>
                <h4>Contradicciones legal-probatorias</h4>
                {reportPreview.contradictions.issues.map((issue, index) => (
                  <div className="preview-section warning" key={`${issue.norm_reference}-${index}`}>
                    <strong>{issue.norm_reference} · {prettySpanish(issue.legal_element)}</strong>
                    <span>{prettySpanish(issue.severity)}</span>
                    <small>{prettySpanish(issue.message)} {prettySpanish(issue.recommended_action)}</small>
                  </div>
                ))}
                {!reportPreview.contradictions.issues.length && <EmptyState text="Sin contradicciones bloqueantes detectadas." />}
              </div>
            </div>
            <div>
              <h4>Anexos reales</h4>
              <div className="preview-grid">
                {reportPreview.annexes.items.map((item, index) => (
                  <div className="preview-section" key={`${item.type}-${index}`}>
                    <strong>{prettySpanish(item.title)}</strong>
                    <span>{prettySpanish(item.type)} {item.sha256 ? `· SHA-256 ${item.sha256}` : ""}</span>
                    <small>{prettySpanish(item.detail || item.integrity_status || `Elementos: ${item.rows || 1}`)}</small>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
        <JsonPanel data={exportFinalResult} />
        <div className="table">
          {reports.map((item) => (
            <div className="record record-grid" key={item.id}>
              <strong>{item.title}</strong>
              <span>{professionalReportStatus(item.status)}</span>
              <em>Score {item.review_score}</em>
              <span>{exportabilitySnapshot.level}</span>
              <button className="text-link" onClick={() => loadReportPreview(item.id)}>Preview</button>
              <a href={`${API_BASE}/exports/reports/${item.id}/pdf`} target="_blank">PDF</a>
            </div>
          ))}
          {!reports.length && <EmptyState text="Sin informes para el caso seleccionado." />}
        </div>
      </section>
    );
  }

  function renderRubricCompliance() {
    const statusClass = rubricEvaluation?.status === "completo" ? "ok" : rubricEvaluation?.status === "parcial" ? "pending" : "blocked";
    return (
      <div className="report-card rubric-panel">
        <div className="panel-head">
          <div>
            <h4>Cumplimiento de Rúbrica</h4>
            <p>Written Legal Evidence Report 2026: secciones A-D y resumen investigativo final.</p>
          </div>
          <button onClick={updateRubricEvaluation} disabled={!selectedCaseId || rubricState === "updating"}>
            <RefreshCcw size={16} /> {rubricState === "updating" ? "Actualizando..." : "Actualizar evaluación"}
          </button>
        </div>
        {rubricMessage && <div className={`action-feedback ${rubricState}`}>{prettySpanish(rubricMessage)}</div>}
        {rubricEvaluation ? (
          <>
            <div className="rubric-score-row">
              <div className={statusClass}>
                <span>Score total</span>
                <strong>{rubricEvaluation.total_score}/{rubricEvaluation.max_score}</strong>
                <small>{rubricEvaluation.percentage}% - {prettySpanish(rubricEvaluation.status)}</small>
              </div>
              <p>{prettySpanish(rubricEvaluation.summary)}</p>
            </div>
            <div className="rubric-section-grid">
              {rubricEvaluation.sections.map((section) => (
                <article className={`rubric-section ${section.status}`} key={section.key}>
                  <div>
                    <span>Sección {section.key} - {section.weight}%</span>
                    <h4>{section.label}</h4>
                  </div>
                  <strong>{section.estimated_score}/{section.max_score}</strong>
                  <small>Estado: {prettySpanish(section.status)}</small>
                  {!!section.missing.length && (
                    <div className="summary-list">
                      {section.missing.slice(0, 4).map((item) => <span key={item}>{prettySpanish(item)}</span>)}
                    </div>
                  )}
                  {!section.missing.length && <small>Sin faltantes críticos detectados.</small>}
                  <em>{prettySpanish(section.recommendations[0] || "Mantener consistencia documental.")}</em>
                </article>
              ))}
            </div>
          </>
        ) : (
          <EmptyState text="Todavía no hay evaluación de rúbrica para este caso. Actualiza la evaluación para calcular puntaje y faltantes." />
        )}
      </div>
    );
  }

  function renderReportsProfessional() {
    const includedSections = reportPreview?.sections.filter((section) => section.word_count > 0) || [];
    const emptySections = reportPreview?.sections.filter((section) => section.word_count <= 0) || [];
    const missingChecklist = reportPreview?.final_checklist.items.filter((item) => !item.ok) || [];
    const completedChecklist = reportPreview?.final_checklist.items.filter((item) => item.ok) || [];

    return (
      <section className="work-surface">
        <div className="section-head">
          <div>
            <h2>Informes</h2>
            <p>Control profesional del informe: contenido incluido, faltantes, versionado, anexos y exportacion final.</p>
          </div>
          <button onClick={generateReport} disabled={!selectedCaseId}><FileText size={17} /> Generar informe</button>
        </div>
        {latestReport && (
          <div className="report-toolbar">
            <button onClick={() => loadReportPreview()}><FileCheck2 size={16} /> Vista previa profesional</button>
            <button onClick={reviewReport}><CheckCircle2 size={16} /> Revisar</button>
            <button onClick={requestFinalExport} className={reportPreview?.can_export_final ? "" : "secondary"}>
              <Download size={16} /> Sellar y exportar final
            </button>
            <button onClick={refreshReportAnnexes} className="secondary"><FileText size={16} /> Actualizar anexos</button>
            <a className="download-button secondary" href={`${API_BASE}/exports/reports/${latestReport.id}/pdf`} target="_blank">
              <Download size={16} /> Exportar borrador PDF
            </a>
          </div>
        )}
        {!latestReport && <EmptyState text="Todavia no hay informe para el caso seleccionado. Genera un informe para activar la vista de control final." />}
        {renderRubricCompliance()}
        {reportPreview && (
          <div className="report-preview professional">
            <div className="preview-cover">
              <div>
                <span className="eyebrow">Panel de control del informe</span>
                <h3>{reportPreview.title}</h3>
                <p>{prettySpanish(reportPreview.exportability.level)} - Score {reportPreview.exportability.score}/100 - Revision {reportPreview.review_score}</p>
              </div>
              <span className={`badge ${reportPreview.can_export_final ? "success" : ""}`}>
                {reportPreview.can_export_final ? "Exportable como final" : "No exportable como final"}
              </span>
            </div>
            <div className="report-status-grid">
              <div className={reportPreview.final_checklist.ready ? "ok" : "pending"}>
                <span>Checklist final</span>
                <strong>{reportPreview.final_checklist.ready ? "Completo" : "Incompleto"}</strong>
                <small>{completedChecklist.length}/{reportPreview.final_checklist.items.length} controles cumplidos</small>
              </div>
              <div className={reportPreview.contradictions.blocking ? "blocked" : "ok"}>
                <span>Contradicciones</span>
                <strong>{reportPreview.contradictions.count}</strong>
                <small>{reportPreview.contradictions.blocking ? "Requiere correccion" : "Sin bloqueo detectado"}</small>
              </div>
              <div className={includedSections.length ? "ok" : "pending"}>
                <span>Contenido PDF</span>
                <strong>{includedSections.length}</strong>
                <small>secciones con contenido</small>
              </div>
              <div className={reportPreview.annexes.count ? "ok" : "pending"}>
                <span>Anexos</span>
                <strong>{reportPreview.annexes.count}</strong>
                <small>elementos vinculados</small>
              </div>
            </div>
            {reportPreview.final_seal && (
              <div className="notice success">
                Sello pericial final: {reportPreview.final_seal.seal_id} - Version {reportPreview.final_seal.report_version}
              </div>
            )}
            {!!reportPreview.warnings.length && (
              <div className="requirements">
                <strong>Alertas de vista previa</strong>
                {reportPreview.warnings.map((item) => <span key={item}>{prettySpanish(item)}</span>)}
              </div>
            )}
            <div className="preview-grid">
              <div className="report-card">
                <h4>Que incluira el PDF final</h4>
                <div className="report-inclusion-list">
                  {includedSections.map((section) => (
                    <div key={section.title}>
                      <CheckCircle2 size={16} />
                      <span>
                        <strong>{prettySpanish(section.title)}</strong>
                        <small>{section.word_count} palabras {section.has_tables ? "- incluye tabla" : ""}</small>
                      </span>
                    </div>
                  ))}
                  {!includedSections.length && <EmptyState text="No hay secciones con contenido suficiente para renderizar." />}
                </div>
              </div>
              <div className="report-card">
                <h4>Que falta para cerrarlo</h4>
                <div className="summary-list">
                  {missingChecklist.map((item) => (
                    <span key={item.key}>
                      <strong>{prettySpanish(item.label)}:</strong> {prettySpanish(item.message)}
                    </span>
                  ))}
                  {!missingChecklist.length && <span>Sin faltantes criticos para cierre pericial.</span>}
                </div>
              </div>
            </div>
            <div className="preview-grid">
              <div className="report-card">
                <h4>Resumen ejecutivo editable</h4>
                <textarea className="executive-editor" value={executiveSummaryDraft} onChange={(event) => setExecutiveSummaryDraft(event.target.value)} />
                <button onClick={saveExecutiveSummary} disabled={!executiveSummaryDraft.trim()}>
                  <Save size={16} /> Guardar resumen ejecutivo
                </button>
              </div>
              <div className="report-card">
                <h4>Versionado del informe</h4>
                <p>Usa estos estados para controlar madurez documental. La version final exige checklist completo.</p>
                <div className="version-row">
                  {["borrador", "preliminar", "revisado", "final", "corregido", "reabierto"].map((status) => (
                    <button key={status} className={latestReport?.status === status ? "" : "secondary"} onClick={() => transitionReportStatus(status)}>
                      {prettySpanish(status)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="preview-grid">
              <div className="report-card">
                <h4>Checklist pericial final</h4>
                {reportPreview.final_checklist.items.map((item) => (
                  <div className={`check-row ${item.ok ? "ok" : "pending"}`} key={item.key}>
                    <span>{item.ok ? "Cumplido" : "Pendiente"}</span>
                    <strong>{prettySpanish(item.label)}</strong>
                    <small>{prettySpanish(item.message)}</small>
                  </div>
                ))}
              </div>
              <div className="report-card">
                <h4>Contradicciones legal-probatorias</h4>
                {reportPreview.contradictions.issues.map((issue, index) => (
                  <div className="preview-section warning" key={`${issue.norm_reference}-${index}`}>
                    <strong>{issue.norm_reference} - {prettySpanish(issue.legal_element)}</strong>
                    <span>{prettySpanish(issue.severity)}</span>
                    <small>{prettySpanish(issue.message)} {prettySpanish(issue.recommended_action)}</small>
                  </div>
                ))}
                {!reportPreview.contradictions.issues.length && <EmptyState text="Sin contradicciones bloqueantes detectadas." />}
              </div>
            </div>
            {!!emptySections.length && (
              <div className="requirements">
                <strong>Secciones sin contenido suficiente</strong>
                {emptySections.map((section) => <span key={section.title}>{prettySpanish(section.title)}</span>)}
              </div>
            )}
            <div className="report-card">
              <h4>Anexos reales</h4>
              <div className="preview-grid">
                {reportPreview.annexes.items.map((item, index) => (
                  <div className="preview-section" key={`${item.type}-${index}`}>
                    <strong>{prettySpanish(item.title)}</strong>
                    <span>{prettySpanish(item.type)} {item.sha256 ? `- SHA-256 ${item.sha256}` : ""}</span>
                    <small>{prettySpanish(item.detail || item.integrity_status || `Elementos: ${item.rows || 1}`)}</small>
                  </div>
                ))}
                {!reportPreview.annexes.items.length && <EmptyState text="Sin anexos vinculados todavia." />}
              </div>
            </div>
            {renderExportFinalOutcome()}
          </div>
        )}
        {!reportPreview && renderExportFinalOutcome()}
        <div className="report-list">
          <h4>Informes del caso</h4>
          {reports.map((item) => (
            <div className="record record-grid" key={item.id}>
              <strong>{item.title}</strong>
              <span>{professionalReportStatus(item.status)}</span>
              <em>Score {item.review_score}</em>
              <span>{exportabilitySnapshot.level}</span>
              <button className="text-link" onClick={() => loadReportPreview(item.id)}>Preview</button>
              <a href={`${API_BASE}/exports/reports/${item.id}/pdf`} target="_blank">PDF</a>
            </div>
          ))}
          {!reports.length && <EmptyState text="Sin informes para el caso seleccionado." />}
        </div>
      </section>
    );
  }

  function renderLegalKnowledge() {
    return (
      <section className="work-surface">
        <div className="section-head">
          <div>
            <h2>Biblioteca Legal Argentina</h2>
            <p>Perfiles CTF, normas argentinas registradas y aplicación controlada al caso.</p>
          </div>
          <div className="legal-search-panel">
            <select
              value={attackTypes.find((item) => item.query === legalQuery)?.value || ""}
              onChange={(event) => {
                const selected = attackTypes.find((item) => item.value === event.target.value);
                if (selected) setLegalQuery(selected.query);
              }}
              aria-label="Tipo de incidente"
            >
              <option value="">Buscar por texto libre</option>
              {attackTypes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
            <input value={legalQuery} onChange={(e) => setLegalQuery(e.target.value)} placeholder="Buscar norma o describir incidente" />
            <button className="icon-button" onClick={searchLegal} title="Buscar"><Search size={18} /></button>
          </div>
        </div>
        {legalApplyMessage && (
          <div className={`action-feedback ${legalApplyState}`}>
            {legalApplyMessage}
          </div>
        )}
        <div className="notice">
          La biblioteca solo usa normas y fuentes registradas. No atribuye autoría sin evidencia suficiente ni reemplaza revisión profesional.
        </div>
        {legalRecommendation?.profile && (
          <div className="case-panel">
            <div className="section-head compact-head">
              <div>
                <h3>{prettySpanish(legalRecommendation.profile.label)}</h3>
                <p>{prettySpanish(legalRecommendation.profile.legal_theory)}</p>
              </div>
            </div>
            <div className="split">
              <div>
                <strong>Evidencia requerida</strong>
                <ul className="compact-list">
                  {legalRecommendation.profile.required_evidence.map((item) => <li key={item}>{prettySpanish(item)}</li>)}
                </ul>
              </div>
              <div>
                <strong>Medidas recomendadas</strong>
                <ul className="compact-list">
                  {legalRecommendation.profile.recommended_measures.map((item) => <li key={item}>{prettySpanish(item)}</li>)}
                </ul>
              </div>
            </div>
          </div>
        )}
        {legalRecommendation?.recommendations?.length ? (
          <div className="article-list legal-card-list">
            {legalRecommendation.recommendations.map((item) => (
              <article className={item.sensitive ? "sensitive" : ""} key={`${item.reference}-${item.article_id}`}>
                <div>
                  <span>{item.reference} · {item.legal_role} · confianza {item.confidence}</span>
                  <h3>{prettySpanish(item.title)}</h3>
                </div>
                <p>{prettySpanish(item.text)}</p>
                {item.warning && <div className="notice sensitive-warning">{prettySpanish(item.warning)}</div>}
                <div className="legal-card-grid">
                  <small><strong>Aplicación:</strong> {prettySpanish(item.applicability_to_case)}</small>
                  <small><strong>Límites:</strong> {prettySpanish(item.probatory_limits)}</small>
                  <small><strong>Elementos objetivos:</strong> {prettySpanish(item.why)}</small>
                  <small><strong>Elemento subjetivo:</strong> {prettySpanish(item.subjective_elements)}</small>
                  <small><strong>Evidencia necesaria:</strong> {prettySpanish(item.evidence_needed)}</small>
                  <small><strong>Relación con incidente:</strong> {prettySpanish(item.incident_relations || legalRecommendation.profile?.label || "")}</small>
                  <small><strong>Fuente:</strong> {prettySpanish(item.source_title || "Fuente oficial registrada")} · <a href={item.source_url} target="_blank" rel="noreferrer">ver oficial</a></small>
                </div>
                {item.precedents.length > 0 && <small>Jurisprudencia registrada: {item.precedents.length}</small>}
                {item.doctrine.length > 0 && <small>Doctrina registrada: {item.doctrine.length}</small>}
                <div className="button-row">
                  <button onClick={() => decideLegalRecommendation(item, "aprobado")} disabled={!selectedCaseId}>
                    <CheckCircle2 size={16} /> Aplicar al caso
                  </button>
                  <button className="secondary-button" onClick={() => decideLegalRecommendation(item, "descartado")} disabled={!selectedCaseId}>
                    <Trash2 size={16} /> Descartar
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : null}
        <div className="case-panel">
          <div className="section-head compact-head">
            <div>
              <h3>Mapeo legal aprobado por analista</h3>
              <p>Normas aceptadas o descartadas para el caso seleccionado. Podés corregir artículos y vínculos sin borrar evidencia.</p>
            </div>
            {legalQualityControl && (
              <span className={`badge ${legalQualityControl.risk_level === "bajo" ? "success" : ""}`}>
                Semáforo legal: {prettySpanish(legalQualityControl.risk_level)}
              </span>
            )}
          </div>
          <div className="table">
            {legalMappings.map((item) => {
              const elementOptions = legalElementsForMapping(item.id);
              return (
              <div className="record" key={item.id}>
                <strong>{item.norm_reference} · {item.decision_status}</strong>
                <span>{item.legal_role || item.legal_area} · confianza {item.confidence_level}</span>
                <em>{item.analyst_name || "Analista no informado"}</em>
                <small>{prettySpanish(item.analysis)}</small>
                {item.decision_status === "aprobado" && (
                  <div className="button-row">
                    <select
                      value={legalEvidenceSelection[item.id] || ""}
                      onChange={(e) => setLegalEvidenceSelection({ ...legalEvidenceSelection, [item.id]: e.target.value })}
                    >
                      <option value="">Seleccionar evidencia del caso activo</option>
                      {evidence.map((ev) => (
                        <option key={ev.id} value={ev.id}>#{ev.id} {ev.description}</option>
                      ))}
                    </select>
                    <select
                      value={legalElementSelection[item.id] || ""}
                      onChange={(e) => setLegalElementSelection({ ...legalElementSelection, [item.id]: e.target.value })}
                    >
                      <option value="">Elemento legal a sostener</option>
                      {elementOptions.map((element) => (
                        <option key={element} value={element}>{prettySpanish(element)}</option>
                      ))}
                    </select>
                    <button onClick={() => linkEvidenceToLegalMapping(item)} disabled={!evidence.length}>
                      <FileCheck2 size={16} /> Vincular evidencia
                    </button>
                    <button className="secondary-button" onClick={() => changeLegalMappingDecision(item, "descartado")}>
                      <Trash2 size={16} /> Quitar artículo
                    </button>
                  </div>
                )}
                {item.decision_status === "descartado" && (
                  <div className="button-row">
                    <button onClick={() => changeLegalMappingDecision(item, "aprobado")}>
                      <CheckCircle2 size={16} /> Reactivar artículo
                    </button>
                  </div>
                )}
                {legalMappingEvidence.filter((link) => link.legal_mapping_id === item.id).map((link) => {
                  const ev = evidence.find((e) => e.id === link.evidence_id);
                  const draft = legalLinkDrafts[link.id] || {};
                  const current = { ...link, ...draft };
                  return (
                    <div className="inline-editor" key={link.id}>
                      Evidencia vinculada: #{link.evidence_id} {ev?.description || ""} · {link.legal_element} · fuerza {link.probatory_strength}
                      <input value={current.legal_element || ""} onChange={(event) => setLegalLinkDrafts({ ...legalLinkDrafts, [link.id]: { ...draft, legal_element: event.target.value } })} placeholder="Elemento legal" />
                      <select value={current.element_status || "pendiente"} onChange={(event) => setLegalLinkDrafts({ ...legalLinkDrafts, [link.id]: { ...draft, element_status: event.target.value } })}>
                        <option value="probado">Probado</option>
                        <option value="debil">Débil</option>
                        <option value="faltante">Faltante</option>
                        <option value="controvertido">Controvertido</option>
                        <option value="pendiente">Pendiente</option>
                      </select>
                      <select value={current.probatory_strength || "medio"} onChange={(event) => setLegalLinkDrafts({ ...legalLinkDrafts, [link.id]: { ...draft, probatory_strength: event.target.value } })}>
                        <option value="alto">Fuerza alta</option>
                        <option value="medio">Fuerza media</option>
                        <option value="bajo">Fuerza baja</option>
                      </select>
                      <select value={current.contradiction_risk || "bajo"} onChange={(event) => setLegalLinkDrafts({ ...legalLinkDrafts, [link.id]: { ...draft, contradiction_risk: event.target.value } })}>
                        <option value="bajo">Riesgo bajo</option>
                        <option value="medio">Riesgo medio</option>
                        <option value="alto">Riesgo alto</option>
                        <option value="critico">Riesgo crítico</option>
                      </select>
                      <input value={current.missing_evidence || ""} onChange={(event) => setLegalLinkDrafts({ ...legalLinkDrafts, [link.id]: { ...draft, missing_evidence: event.target.value } })} placeholder="Evidencia faltante" />
                      <input value={current.recommended_measure || ""} onChange={(event) => setLegalLinkDrafts({ ...legalLinkDrafts, [link.id]: { ...draft, recommended_measure: event.target.value } })} placeholder="Medida recomendada" />
                      <div className="button-row">
                        <button onClick={() => saveLegalLink(link)}><Save size={16} /> Guardar vínculo</button>
                        <button className="secondary-button" onClick={() => unlinkLegalEvidence(link.id)}><Trash2 size={16} /> Desvincular</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            );})}
            {!legalMappings.length && <EmptyState text="No hay normas aprobadas o descartadas para este caso." />}
          </div>
          <div className="section-head compact-head">
            <div>
              <h3>Matriz legal-probatoria</h3>
              <p>Controla que cada norma quede sostenida por evidencia concreta.</p>
            </div>
            {legalProbatoryMatrix && <span className="badge">Faltantes: {legalProbatoryMatrix.summary.missing_elements || 0}</span>}
          </div>
          <div className="table">
            {legalProbatoryMatrix?.rows.slice(0, 8).map((row, index) => (
              <div className="record" key={`${row.mapping_id}-${row.legal_element}-${index}`}>
                <strong>{row.norm_reference} · {row.legal_element}</strong>
                <span>{row.element_status} · fuerza {row.probatory_strength} · riesgo {row.contradiction_risk}</span>
                {row.evidence_id && <small>#{row.evidence_id} {row.evidence_description} {row.evidence_hash ? `· SHA-256 ${row.evidence_hash}` : ""}</small>}
                {row.missing_evidence && <small>{prettySpanish(row.missing_evidence)}</small>}
                {row.recommended_measure && <em>{prettySpanish(row.recommended_measure)}</em>}
              </div>
            ))}
            {!legalProbatoryMatrix?.rows.length && <EmptyState text="La matriz aparece cuando vinculas evidencia a normas aprobadas." />}
          </div>
          <div className="section-head compact-head">
            <div>
              <h3>Control de calidad legal</h3>
              <p>Detecta faltantes y contradicciones antes de usar el encuadre en un informe.</p>
            </div>
            {legalQualityControl && <span className="badge">Score {legalQualityControl.score} · riesgo {legalQualityControl.risk_level}</span>}
          </div>
          <div className="table">
            {legalQualityControl?.issues.slice(0, 6).map((issue) => (
              <div className="record" key={`${issue.code}-${issue.message}`}>
                <strong>{issue.severity} · {issue.code}</strong>
                <span>{issue.message}</span>
                <small>{issue.recommended_action}</small>
              </div>
            ))}
            {legalQualityControl && !legalQualityControl.issues.length && <EmptyState text="No hay observaciones críticas en el encuadre legal actual." />}
          </div>
        </div>
        <div className="article-list">
          {articles.map((item) => (
            <article key={item.id}>
              <div>
                <span>{item.code} art. {item.article_number}{item.subsection ? ` inc. ${item.subsection}` : ""}</span>
                <h3>{prettySpanish(item.title)}</h3>
              </div>
              <p>{prettySpanish(item.objective_elements)}</p>
              <small>{prettySpanish(item.evidentiary_requirements)}</small>
            </article>
          ))}
        </div>
      </section>
    );
  }

  function renderCybercrime() {
    return (
      <section className="work-surface cyber-workbench">
        <div className="section-head">
          <div>
            <h2>Cybercrime Workbench</h2>
            <p>Flujo guiado para analizar indicadores, registrar sesiones controladas y guardar conclusiones tecnicas por caso.</p>
          </div>
          <button className="secondary-button" onClick={refreshCybercrime}><RefreshCcw size={16} /> Actualizar</button>
        </div>

        {cyberDashboard && <MetricGrid metrics={cyberDashboard as unknown as Record<string, number>} />}

        <div className="split">
          <div className="form cyber-analysis-panel">
            <h3>Paso 1 - Analizar indicador</h3>
            <p className="muted">Carga una IP, URL, dominio, correo o hash. OPERIA lo clasifica, estima riesgo y sugiere medidas de preservacion.</p>
            <input value={indicator} onChange={(event) => setIndicator(event.target.value)} placeholder="IP, URL, dominio, email o hash" />
            <button onClick={analyzeIndicator} disabled={!indicator.trim()}>
              <Search size={17} /> Analizar indicador
            </button>
            {indicatorResult && (
              <div className={`risk-card ${indicatorResult.risk_level}`}>
                <div>
                  <span>Tipo</span>
                  <strong>{prettySpanish(indicatorResult.indicator_type)}</strong>
                </div>
                <div>
                  <span>Riesgo</span>
                  <strong>{prettySpanish(indicatorResult.risk_level)}</strong>
                </div>
                <div>
                  <span>Confianza</span>
                  <strong>{prettySpanish(indicatorResult.confidence)}</strong>
                </div>
              </div>
            )}
          </div>

          <div className="detail-panel">
            <div className="panel-head">
              <h3>Resultado técnico</h3>
            </div>
            {indicatorResult ? (
              <div className="cyber-result">
                <strong>{indicatorResult.indicator}</strong>
                <div className="summary-list">
                  {indicatorResult.findings.map((item) => <span key={item}>{item}</span>)}
                </div>
                <h4>Acciones recomendadas</h4>
                <div className="mini-list">
                  {indicatorResult.recommended_actions.map((item) => <span key={item}>{item}</span>)}
                </div>
                <p className="notice">{indicatorResult.legal_relevance}</p>
                <p className="muted">Que significa: este resultado orienta la investigacion. No prueba autoria y debe vincularse con evidencia, custodia y fuentes verificables.</p>
              </div>
            ) : <EmptyState text="Sin análisis de indicador todavía." />}
          </div>
        </div>

        <div className="detail-grid">
          <form className="detail-panel" onSubmit={createCyberLabSession}>
            <div className="panel-head">
              <h3>Paso 2 - Crear sesion de laboratorio</h3>
            </div>
            <input placeholder="Título de sesión" value={cyberLabForm.title} onChange={(e) => setCyberLabForm({ ...cyberLabForm, title: e.target.value })} />
            <div className="inline-grid">
              <input placeholder="Propósito" value={cyberLabForm.purpose} onChange={(e) => setCyberLabForm({ ...cyberLabForm, purpose: e.target.value })} />
              <select value={cyberLabForm.risk_level} onChange={(e) => setCyberLabForm({ ...cyberLabForm, risk_level: e.target.value })}>
                <option value="bajo">Riesgo bajo</option>
                <option value="medio">Riesgo medio</option>
                <option value="alto">Riesgo alto</option>
              </select>
            </div>
            <input placeholder="Operador" value={cyberLabForm.operator} onChange={(e) => setCyberLabForm({ ...cyberLabForm, operator: e.target.value })} />
            <button disabled={!selectedCaseId}><BrainCircuit size={17} /> Crear sesión controlada</button>
          </form>

          <form className="detail-panel" onSubmit={createCyberProofRow}>
            <div className="panel-head">
              <h3>Paso 3 - Guardar conclusion defensible</h3>
            </div>
            <textarea placeholder="Conclusión técnica prudente" value={cyberProofForm.defensible_conclusion} onChange={(e) => setCyberProofForm({ ...cyberProofForm, defensible_conclusion: e.target.value })} />
            <textarea placeholder="Encuadre o relación legal preliminar" value={cyberProofForm.legal_framing} onChange={(e) => setCyberProofForm({ ...cyberProofForm, legal_framing: e.target.value })} />
            <div className="inline-grid">
              <select value={cyberProofForm.confidence_level} onChange={(e) => setCyberProofForm({ ...cyberProofForm, confidence_level: e.target.value })}>
                <option value="bajo">Confianza baja</option>
                <option value="medio">Confianza media</option>
                <option value="alto">Confianza alta</option>
              </select>
              <input placeholder="Debilidad o límite probatorio" value={cyberProofForm.weakness} onChange={(e) => setCyberProofForm({ ...cyberProofForm, weakness: e.target.value })} />
            </div>
            <button disabled={!selectedCaseId}><FileCheck2 size={17} /> Guardar en matriz cybercrime</button>
          </form>
        </div>

        <div className="detail-grid">
          <div className="detail-panel">
            <div className="panel-head">
              <h3>Sesiones del caso</h3>
            </div>
            {cyberLabSessions.slice(0, 8).map((item) => (
              <div className="editable-record single" key={item.id}>
                <div>
                  <strong>{item.session_code} · {item.title}</strong>
                  <span>{prettySpanish(item.purpose)} | {prettySpanish(item.risk_level)} | {prettySpanish(item.status)}</span>
                  <small>{item.result_summary || `Operador: ${item.operator}`}</small>
                </div>
              </div>
            ))}
            {!cyberLabSessions.length && <EmptyState text="Sin sesiones cybercrime asociadas." />}
          </div>

          <div className="detail-panel">
            <div className="panel-head">
              <h3>Matriz técnica</h3>
            </div>
            {cyberProofRows.slice(0, 8).map((item) => (
              <div className="editable-record single" key={item.id}>
                <div>
                  <strong>{prettySpanish(item.confidence_level)} · {prettySpanish(item.status)}</strong>
                  <span>{item.defensible_conclusion}</span>
                  <small>{item.risk_flag || item.weakness || item.legal_framing || "Sin observaciones."}</small>
                </div>
              </div>
            ))}
            {!cyberProofRows.length && <EmptyState text="Sin conclusiones técnicas guardadas." />}
          </div>
        </div>
      </section>
    );
  }

  function renderDeepfakeMedia() {
    const checklistDone = deepfakeChecklist.filter((item) => deepfakeChecklistState[item.key]).length;
    return (
      <section className="work-surface cyber-workbench">
        <div className="section-head">
          <div>
            <h2>Deepfake / Medios</h2>
            <p>Laboratorio local para registrar autenticación preliminar de imagen, video, audio, documento o captura sin afirmar conclusiones absolutas.</p>
          </div>
          <button className="secondary-button" onClick={refreshCybercrime}><RefreshCcw size={16} /> Actualizar</button>
        </div>

        {deepfakeMessage && <div className={`action-feedback ${deepfakeState}`}>{deepfakeMessage}</div>}

        <div className="split deepfake-layout">
          <form className="form deepfake-form" onSubmit={saveDeepfakeAnalysis}>
            <h3>Registrar análisis de medio</h3>
            <div className="inline-grid">
              <select value={deepfakeForm.media_type} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, media_type: e.target.value })}>
                <option value="imagen">Imagen</option>
                <option value="video">Video</option>
                <option value="audio">Audio</option>
                <option value="documento">Documento</option>
                <option value="captura">Captura</option>
              </select>
              <select value={deepfakeForm.evidence_id} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, evidence_id: e.target.value })}>
                <option value="">Sin evidencia vinculada</option>
                {evidence.map((item) => (
                  <option key={item.id} value={item.id}>#{item.id} - {item.description.slice(0, 60)}</option>
                ))}
              </select>
            </div>
            <input placeholder="Origen del archivo, URL, publicación o soporte" value={deepfakeForm.source_origin} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, source_origin: e.target.value })} />
            <input placeholder="Herramienta usada" value={deepfakeForm.tool_used} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, tool_used: e.target.value })} />
            <textarea placeholder="Resumen de metadatos EXIF/media" value={deepfakeForm.metadata_summary} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, metadata_summary: e.target.value })} />
            <textarea placeholder="Hallazgos técnicos observados" value={deepfakeForm.findings} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, findings: e.target.value })} />
            <textarea placeholder="Limitaciones del análisis" value={deepfakeForm.limitations} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, limitations: e.target.value })} />
            <select value={deepfakeForm.classification} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, classification: e.target.value })}>
              <option value="auténtico preliminar">Auténtico preliminar</option>
              <option value="manipulado probable">Manipulado probable</option>
              <option value="indicios de edición">Indicios de edición</option>
              <option value="no concluyente">No concluyente</option>
              <option value="requiere pericia especializada">Requiere pericia especializada</option>
            </select>
            <button disabled={!selectedCaseId || deepfakeState === "saving"}><Save size={17} /> Guardar análisis</button>
          </form>

          <div className="detail-panel">
            <div className="panel-head">
              <div>
                <h3>Checklist de autenticidad</h3>
                <p>{checklistDone}/{deepfakeChecklist.length} controles marcados.</p>
              </div>
              <span className="badge">Preliminar</span>
            </div>
            <div className="checklist-grid">
              {deepfakeChecklist.map((item) => (
                <label className={`check-pill ${deepfakeChecklistState[item.key] ? "checked" : ""}`} key={item.key}>
                  <input
                    type="checkbox"
                    checked={Boolean(deepfakeChecklistState[item.key])}
                    onChange={(e) => setDeepfakeChecklistState({ ...deepfakeChecklistState, [item.key]: e.target.checked })}
                  />
                  <span>{item.label}</span>
                </label>
              ))}
            </div>
            <p className="notice">La clasificación es preliminar: no prueba por sí sola autenticidad, falsedad, autoría ni origen del archivo.</p>
          </div>
        </div>

        <div className="article-list deepfake-results">
          {deepfakeAnalyses.map((analysis) => (
            <article key={analysis.id}>
              <div className="panel-head">
                <div>
                  <span>{analysis.media_type} · {analysis.classification}</span>
                  <h3>Análisis #{analysis.id} {analysis.evidence_id ? `· Evidencia #${analysis.evidence_id}` : ""}</h3>
                </div>
                <span className="badge">{analysis.finding_id ? `Hallazgo #${analysis.finding_id}` : "Sin hallazgo"}</span>
              </div>
              <p>{analysis.findings || "Sin hallazgos concluyentes cargados."}</p>
              <div className="legal-card-grid">
                <small>Hash: {analysis.evidence_hash || "pendiente"}</small>
                <small>Origen: {analysis.source_origin || "pendiente"}</small>
                <small>Herramienta: {analysis.tool_used || "pendiente"}</small>
                <small>Limitaciones: {analysis.limitations || "requiere pericia especializada"}</small>
              </div>
              <div className="mini-list">
                {analysis.checklist.filter((item) => item.ok).map((item) => <span key={item.key}>{item.label}</span>)}
                {!analysis.checklist.some((item) => item.ok) && <span>Checklist pendiente.</span>}
              </div>
              <p className="notice">{analysis.warning}</p>
              <div className="actions-line">
                <button className="secondary-button" onClick={() => createDeepfakeFinding(analysis.id)}><FileCheck2 size={16} /> Crear hallazgo</button>
                <button onClick={() => applyDeepfakeLegal(analysis)}><Gavel size={16} /> Aplicar normas sugeridas</button>
              </div>
            </article>
          ))}
          {!deepfakeAnalyses.length && <EmptyState text="Sin análisis de medios registrados para el caso seleccionado." />}
        </div>
      </section>
    );
  }

  function renderBlockchainForensics() {
    const highRisk = blockchainTransactions.filter((item) => ["mixer", "bridge", "contrato inteligente"].includes(item.wallet_classification)).length;
    const linked = blockchainTransactions.filter((item) => item.evidence_id).length;
    return (
      <section className="work-surface cyber-workbench">
        <div className="section-head">
          <div>
            <h2>Blockchain Forensics</h2>
            <p>Registro pericial de wallets, transacciones y ruta probable sin consultar exploradores ni atribuir identidad personal automáticamente.</p>
          </div>
          <button className="secondary-button" onClick={refreshCybercrime}><RefreshCcw size={16} /> Actualizar</button>
        </div>

        {blockchainMessage && <div className={`action-feedback ${blockchainState}`}>{blockchainMessage}</div>}

        <div className="risk-card medium blockchain-risk-row">
          <div><span>Transacciones</span><strong>{blockchainTransactions.length}</strong></div>
          <div><span>Con evidencia</span><strong>{linked}</strong></div>
          <div><span>Riesgo reforzado</span><strong>{highRisk}</strong></div>
        </div>

        <div className="split blockchain-layout">
          <form className="form blockchain-form" onSubmit={saveBlockchainTransaction}>
            <h3>Registrar transacción</h3>
            <div className="inline-grid">
              <input placeholder="Red / blockchain" value={blockchainForm.blockchain} onChange={(e) => setBlockchainForm({ ...blockchainForm, blockchain: e.target.value })} />
              <input placeholder="Token" value={blockchainForm.token} onChange={(e) => setBlockchainForm({ ...blockchainForm, token: e.target.value })} />
            </div>
            <input placeholder="Hash de transacción" value={blockchainForm.tx_hash} onChange={(e) => setBlockchainForm({ ...blockchainForm, tx_hash: e.target.value })} />
            <div className="inline-grid">
              <input placeholder="Wallet origen" value={blockchainForm.source_wallet} onChange={(e) => setBlockchainForm({ ...blockchainForm, source_wallet: e.target.value })} />
              <input placeholder="Wallet destino" value={blockchainForm.destination_wallet} onChange={(e) => setBlockchainForm({ ...blockchainForm, destination_wallet: e.target.value })} />
            </div>
            <div className="inline-grid">
              <input placeholder="Monto" type="number" step="any" value={blockchainForm.amount} onChange={(e) => setBlockchainForm({ ...blockchainForm, amount: e.target.value })} />
              <input placeholder="Valor aproximado" type="number" step="any" value={blockchainForm.approximate_value} onChange={(e) => setBlockchainForm({ ...blockchainForm, approximate_value: e.target.value })} />
            </div>
            <div className="inline-grid">
              <input placeholder="Fecha/hora" value={blockchainForm.tx_datetime} onChange={(e) => setBlockchainForm({ ...blockchainForm, tx_datetime: e.target.value })} />
              <select value={blockchainForm.wallet_classification} onChange={(e) => setBlockchainForm({ ...blockchainForm, wallet_classification: e.target.value })}>
                {walletClassifications.map((item) => <option value={item} key={item}>{prettySpanish(item)}</option>)}
              </select>
            </div>
            <select value={blockchainForm.evidence_id} onChange={(e) => setBlockchainForm({ ...blockchainForm, evidence_id: e.target.value })}>
              <option value="">Sin evidencia vinculada</option>
              {evidence.map((item) => (
                <option key={item.id} value={item.id}>#{item.id} - {item.description.slice(0, 60)}</option>
              ))}
            </select>
            <input placeholder="URL del explorador preservada manualmente" value={blockchainForm.explorer_url} onChange={(e) => setBlockchainForm({ ...blockchainForm, explorer_url: e.target.value })} />
            <input placeholder="Herramienta usada" value={blockchainForm.tool_used} onChange={(e) => setBlockchainForm({ ...blockchainForm, tool_used: e.target.value })} />
            <textarea placeholder="Hipótesis de ruta" value={blockchainForm.route_hypothesis} onChange={(e) => setBlockchainForm({ ...blockchainForm, route_hypothesis: e.target.value })} />
            <textarea placeholder="Limitaciones y evidencia faltante" value={blockchainForm.limitations} onChange={(e) => setBlockchainForm({ ...blockchainForm, limitations: e.target.value })} />
            <button disabled={!selectedCaseId || !blockchainForm.tx_hash.trim() || blockchainState === "saving"}><Save size={17} /> Guardar transacción</button>
          </form>

          <div className="detail-panel">
            <div className="panel-head">
              <div>
                <h3>Medidas recomendadas</h3>
                <p>Checklist operativo para no saltar de wallet a identidad sin soporte.</p>
              </div>
              <span className="badge">No API externa</span>
            </div>
            <ul className="compact-list">
              <li>Preservar captura del explorador y registrar fecha/hora.</li>
              <li>Guardar URL del explorador si fue consultada manualmente.</li>
              <li>Identificar exchange/plataforma si aplica y solicitar datos por vía legal.</li>
              <li>Correlacionar con comunicaciones, pagos, cuentas e IPs.</li>
              <li>Evitar atribución personal solo por wallet.</li>
            </ul>
            <p className="notice">OPERIA no consulta exploradores externos automáticamente. El enlace solo se abre si fue cargado manualmente.</p>
          </div>
        </div>

        <div className="detail-panel">
          <div className="panel-head">
            <h3>Transacciones registradas</h3>
          </div>
          <div className="table blockchain-table">
            {blockchainTransactions.map((item) => (
              <div className="record blockchain-row" key={item.id}>
                <div>
                  <strong>{item.blockchain} · {item.amount} {item.token}</strong>
                  <span>{item.tx_hash}</span>
                  <small>{item.source_wallet || "origen pendiente"} → {item.destination_wallet || "destino pendiente"}</small>
                </div>
                <div>
                  <span className={`badge ${["mixer", "bridge"].includes(item.wallet_classification) ? "blocked" : ""}`}>{prettySpanish(item.wallet_classification)}</span>
                  <small>Valor aprox. {item.approximate_value}</small>
                  <small>{item.evidence_id ? `Evidencia #${item.evidence_id}` : "Sin evidencia vinculada"}</small>
                </div>
                <p>{item.route_hypothesis || "Hipótesis de ruta pendiente."}</p>
                <small>{item.warning}</small>
                <div className="actions-line">
                  <button className="secondary-button" onClick={() => createBlockchainFinding(item.id)}><FileCheck2 size={16} /> Crear hallazgo</button>
                  <button onClick={() => applyBlockchainLegal(item)}><Gavel size={16} /> Aplicar normas</button>
                  {item.explorer_url && (
                    <a className="button-link" href={item.explorer_url} target="_blank" rel="noreferrer"><Globe2 size={16} /> Explorador</a>
                  )}
                </div>
              </div>
            ))}
            {!blockchainTransactions.length && <EmptyState text="Sin transacciones blockchain registradas para el caso seleccionado." />}
          </div>
        </div>
      </section>
    );
  }

  function renderIoTForensics() {
    const checklistDone = iotChecklist.filter((item) => iotChecklistState[item.key]).length;
    const linked = iotDevices.filter((item) => item.evidence_id).length;
    return (
      <section className="work-surface cyber-workbench">
        <div className="section-head">
          <div>
            <h2>IoT Forensics</h2>
            <p>Registro forense de dispositivos conectados, estado observable, evidencia, logs y límites sin ejecutar escaneos reales automáticamente.</p>
          </div>
          <button className="secondary-button" onClick={refreshCybercrime}><RefreshCcw size={16} /> Actualizar</button>
        </div>

        {iotMessage && <div className={`action-feedback ${iotState}`}>{iotMessage}</div>}

        <div className="risk-card medium iot-risk-row">
          <div><span>Dispositivos</span><strong>{iotDevices.length}</strong></div>
          <div><span>Con evidencia</span><strong>{linked}</strong></div>
          <div><span>Checklist actual</span><strong>{checklistDone}/{iotChecklist.length}</strong></div>
        </div>

        <div className="split iot-layout">
          <form className="form iot-form" onSubmit={saveIoTDevice}>
            <h3>Registrar dispositivo</h3>
            <div className="inline-grid">
              <input placeholder="Tipo de dispositivo" value={iotForm.device_type} onChange={(e) => setIotForm({ ...iotForm, device_type: e.target.value })} />
              <input placeholder="Fabricante" value={iotForm.manufacturer} onChange={(e) => setIotForm({ ...iotForm, manufacturer: e.target.value })} />
            </div>
            <div className="inline-grid">
              <input placeholder="Modelo" value={iotForm.model} onChange={(e) => setIotForm({ ...iotForm, model: e.target.value })} />
              <input placeholder="Firmware" value={iotForm.firmware} onChange={(e) => setIotForm({ ...iotForm, firmware: e.target.value })} />
            </div>
            <div className="inline-grid">
              <input placeholder="IP interna" value={iotForm.internal_ip} onChange={(e) => setIotForm({ ...iotForm, internal_ip: e.target.value })} />
              <input placeholder="IP externa" value={iotForm.external_ip} onChange={(e) => setIotForm({ ...iotForm, external_ip: e.target.value })} />
            </div>
            <input placeholder="MAC" value={iotForm.mac} onChange={(e) => setIotForm({ ...iotForm, mac: e.target.value })} />
            <select value={iotForm.evidence_id} onChange={(e) => setIotForm({ ...iotForm, evidence_id: e.target.value })}>
              <option value="">Sin evidencia vinculada</option>
              {evidence.map((item) => (
                <option key={item.id} value={item.id}>#{item.id} - {item.description.slice(0, 60)}</option>
              ))}
            </select>
            <textarea placeholder="Puertos abiertos observados o declarados" value={iotForm.open_ports} onChange={(e) => setIotForm({ ...iotForm, open_ports: e.target.value })} />
            <textarea placeholder="Vulnerabilidades conocidas" value={iotForm.known_vulnerabilities} onChange={(e) => setIotForm({ ...iotForm, known_vulnerabilities: e.target.value })} />
            <textarea placeholder="Logs disponibles" value={iotForm.logs_available} onChange={(e) => setIotForm({ ...iotForm, logs_available: e.target.value })} />
            <input placeholder="Herramienta o metodología usada" value={iotForm.tool_used} onChange={(e) => setIotForm({ ...iotForm, tool_used: e.target.value })} />
            <textarea placeholder="Limitaciones" value={iotForm.limitations} onChange={(e) => setIotForm({ ...iotForm, limitations: e.target.value })} />
            <button disabled={!selectedCaseId || iotState === "saving"}><Save size={17} /> Guardar dispositivo</button>
          </form>

          <div className="detail-panel">
            <div className="panel-head">
              <div>
                <h3>Checklist IoT</h3>
                <p>Preservación y contexto antes de cualquier análisis intrusivo.</p>
              </div>
              <span className="badge">Sin escaneo</span>
            </div>
            <div className="checklist-grid">
              {iotChecklist.map((item) => (
                <label className={`check-pill ${iotChecklistState[item.key] ? "checked" : ""}`} key={item.key}>
                  <input
                    type="checkbox"
                    checked={Boolean(iotChecklistState[item.key])}
                    onChange={(e) => setIotChecklistState({ ...iotChecklistState, [item.key]: e.target.checked })}
                  />
                  <span>{item.label}</span>
                </label>
              ))}
            </div>
            <p className="notice">No se recomiendan comandos peligrosos ni escaneos reales desde esta pantalla. Todo análisis activo requiere autorización y metodología documentada.</p>
          </div>
        </div>

        <div className="detail-panel">
          <div className="panel-head">
            <h3>Dispositivos registrados</h3>
          </div>
          <div className="table iot-table">
            {iotDevices.map((item) => (
              <div className="record iot-row" key={item.id}>
                <div>
                  <strong>{item.device_type} · {item.manufacturer || "fabricante pendiente"} {item.model}</strong>
                  <span>Firmware {item.firmware || "pendiente"} · MAC {item.mac || "pendiente"}</span>
                  <small>IP interna {item.internal_ip || "-"} · IP externa {item.external_ip || "-"}</small>
                </div>
                <div>
                  <span>{item.evidence_id ? `Evidencia #${item.evidence_id}` : "Sin evidencia vinculada"}</span>
                  <small>Hash {item.evidence_hash || "pendiente"}</small>
                  <small>{item.finding_id ? `Hallazgo #${item.finding_id}` : "Sin hallazgo"}</small>
                </div>
                <p>{item.known_vulnerabilities || item.logs_available || "Hallazgos pendientes."}</p>
                <small>{item.warning}</small>
                <div className="actions-line">
                  <button className="secondary-button" onClick={() => createIoTFinding(item.id)}><FileCheck2 size={16} /> Crear hallazgo</button>
                  <button onClick={() => applyIoTLegal(item)}><Gavel size={16} /> Aplicar normas</button>
                </div>
              </div>
            ))}
            {!iotDevices.length && <EmptyState text="Sin dispositivos IoT registrados para el caso seleccionado." />}
          </div>
        </div>
      </section>
    );
  }


  function renderExternalTools() {
    const categories = ["Todas", ...Array.from(new Set(externalToolsCatalog.map((item) => item.category))).sort()];
    const operatingSystems = ["Todos", ...Array.from(new Set(externalToolsCatalog.flatMap((item) => item.operatingSystems))).sort()];
    const specialAreas = ["Todas", "Deepfake / Media", "Blockchain Transactions", "IoT Devices"];
    const normalize = (value: string) => value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    const query = normalize(externalToolQuery.trim());
    const filteredTools = externalToolsCatalog.filter((item) => {
      const haystack = normalize([
        item.name,
        item.category,
        item.description,
        item.forensicUse,
        item.license,
        item.status,
        item.difficulty,
        item.kind.join(" "),
        item.tags.join(" "),
        item.specialArea || ""
      ].join(" "));
      return (
        (!query || haystack.includes(query)) &&
        (externalToolCategory === "Todas" || item.category === externalToolCategory) &&
        (externalToolOs === "Todos" || item.operatingSystems.includes(externalToolOs)) &&
        (externalToolDifficulty === "Todas" || item.difficulty === externalToolDifficulty) &&
        (!externalToolOnlineOnly || Boolean(item.onlineUrl)) &&
        (!externalToolGithubOnly || Boolean(item.githubUrl)) &&
        (externalToolSpecialArea === "Todas" || item.specialArea === externalToolSpecialArea)
      );
    });
    const totalCategories = new Set(externalToolsCatalog.map((item) => item.category)).size;
    const openSourceTotal = externalToolsCatalog.filter((item) => item.kind.includes("Open Source")).length;
    const onlineTotal = externalToolsCatalog.filter((item) => item.onlineUrl).length;
    const specialTotal = externalToolsCatalog.filter((item) => item.specialArea).length;
    const reviewTotal = externalToolsCatalog.filter((item) => item.status === "Legacy" || item.status === "Verificar").length;
    const specialAreaCards = [
      {
        area: "Deepfake / Media",
        title: "Deepfake / Media Forensics",
        text: "Autenticación de imagen, video, audio, metadatos, compresión, frames y origen del contenido.",
        warning: "Usar para verificación, autenticación, investigación legítima y preservación de evidencia. No usar para crear o difundir contenido engañoso."
      },
      {
        area: "Blockchain Transactions",
        title: "Blockchain Transactions",
        text: "Exploradores, wallets, contratos, grafos, trazabilidad de fondos y análisis de smart contracts.",
        warning: "Respetar legislación aplicable, privacidad, reglas probatorias y límites de investigación autorizada."
      },
      {
        area: "IoT Devices",
        title: "IoT Devices Forensics",
        text: "Firmware, dispositivos, tráfico, puertos, servicios, sistemas embebidos y análisis de laboratorio.",
        warning: "Analizar únicamente dispositivos propios, entornos de laboratorio o sistemas con autorización expresa."
      }
    ];
    const openExternalLink = (url: string, item: InventoryCyberTool, action: string) => {
      const notice = item.externalExecutionNotice || "Vas a salir de Operia. El análisis, descarga o consulta se realizará en una plataforma externa. Operia no procesa ni almacena tus datos.";
      const ok = window.confirm(`${notice}\n\nAcción: ${action}\nHerramienta: ${item.name}`);
      if (ok) window.open(url, "_blank", "noopener,noreferrer");
    };
    const toolButton = (item: InventoryCyberTool, url: string | null | undefined, label: string, className: string, action: string, icon: ReactNode) => (
      url ? (
        <button type="button" className={className} onClick={() => openExternalLink(url, item, action)}>
          {icon}
          {label}
        </button>
      ) : (
        <button type="button" className="tool-link disabled" disabled>
          <Globe2 size={15} />
          Sin ejecución online
        </button>
      )
    );
    const renderToolCard = (item: InventoryCyberTool) => (
      <article className={`inventory-card risk-${item.privacyRiskLevel.toLowerCase()}`} key={item.id}>
        <div className="inventory-card-head">
          <div>
            <span className="tool-kicker">{item.category}</span>
            <h4>{item.name}</h4>
          </div>
          <span className={`tool-status ${item.status.toLowerCase().replace(/\s+/g, "-")}`}>{item.status}</span>
        </div>
        <p>{item.description}</p>
        <div className="forensic-use">
          <strong>Uso forense</strong>
          <span>{item.forensicUse}</span>
        </div>
        <div className="tool-badges left">
          <span className="tool-badge local">{item.difficulty}</span>
          <span className="tool-badge">{item.license}</span>
          <span className={`tool-badge privacy-${item.privacyRiskLevel.toLowerCase()}`}>Riesgo {item.privacyRiskLevel}</span>
          {item.specialArea && <span className="tool-badge ai">{item.specialArea}</span>}
        </div>
        <div className="tool-meta">
          <span>Sistemas: {item.operatingSystems.join(", ")}</span>
          <span>Modo: {item.executionMode}</span>
          <span>{item.dataHandling}</span>
        </div>
        <div className="tag-cloud">
          {item.kind.map((kind) => <span key={`${item.id}-${kind}`}>{kind}</span>)}
          {item.tags.slice(0, 5).map((tag) => <span key={`${item.id}-${tag}`}>{tag}</span>)}
        </div>
        {(item.warning || item.externalExecutionNotice) && (
          <small className="tool-safety">{item.warning || item.externalExecutionNotice}</small>
        )}
        <div className="inventory-actions">
          {toolButton(item, item.officialUrl, "Página oficial", "tool-link official", "Página oficial", <Globe2 size={15} />)}
          {toolButton(item, item.downloadUrl || item.githubUrl, item.githubUrl ? "Repositorio" : "Descargar", "tool-link download", "Descarga o repositorio oficial", <Download size={15} />)}
          {toolButton(item, item.onlineUrl, "Usar online externo", "tool-link online", "Uso online externo", <Globe2 size={15} />)}
        </div>
      </article>
    );

    return (
      <section className="work-surface external-inventory-workbench">
        <div className="inventory-hero">
          <div>
            <span className="tool-kicker">Cyber Forensics Open Source Inventory</span>
            <h2>Herramientas Externas</h2>
            <p>Inventario de herramientas para informática forense, seguridad informática, OSINT, DFIR, deepfake/media, blockchain e IoT.</p>
          </div>
          <div className="inventory-hero-badge">
            <strong>{externalToolsCatalog.length}</strong>
            <span>herramientas curadas</span>
          </div>
        </div>

        <div className="tool-dashboard">
          <div className="tool-stat"><span>Total</span><strong>{externalToolsCatalog.length}</strong></div>
          <div className="tool-stat"><span>Categorías</span><strong>{totalCategories}</strong></div>
          <div className="tool-stat"><span>Open source</span><strong>{openSourceTotal}</strong></div>
          <div className="tool-stat"><span>Uso online</span><strong>{onlineTotal}</strong></div>
          <div className="tool-stat"><span>Áreas especiales</span><strong>{specialTotal}</strong></div>
          <div className="tool-stat"><span>Legacy / verificar</span><strong>{reviewTotal}</strong></div>
        </div>

        <div className="inventory-notice">
          OPERIA funciona como inventario y panel de acceso externo. No ejecuta análisis, no almacena evidencia, no recibe archivos, no conserva resultados y no procesa datos del usuario. Toda operación se realiza fuera de OPERIA, en la página oficial, repositorio, descarga local o servicio externo correspondiente.
        </div>

        <div className="inventory-search-panel">
          <div className="search-box">
            <Search size={18} />
            <input
              placeholder="Buscar por herramienta, categoría, descripción, tags o uso forense"
              value={externalToolQuery}
              onChange={(event) => setExternalToolQuery(event.target.value)}
            />
          </div>
          <div className="inventory-filters">
            <select value={externalToolCategory} onChange={(event) => setExternalToolCategory(event.target.value)}>
              {categories.map((category) => <option key={category}>{category}</option>)}
            </select>
            <select value={externalToolOs} onChange={(event) => setExternalToolOs(event.target.value)}>
              {operatingSystems.map((os) => <option key={os}>{os}</option>)}
            </select>
            <select value={externalToolDifficulty} onChange={(event) => setExternalToolDifficulty(event.target.value)}>
              {["Todas", "Básico", "Intermedio", "Avanzado", "Experto"].map((level) => <option key={level}>{level}</option>)}
            </select>
            <select value={externalToolSpecialArea} onChange={(event) => setExternalToolSpecialArea(event.target.value)}>
              {specialAreas.map((area) => <option key={area}>{area}</option>)}
            </select>
            <label><input type="checkbox" checked={externalToolOnlineOnly} onChange={(event) => setExternalToolOnlineOnly(event.target.checked)} /> Con uso online</label>
            <label><input type="checkbox" checked={externalToolGithubOnly} onChange={(event) => setExternalToolGithubOnly(event.target.checked)} /> Con repositorio</label>
          </div>
        </div>

        <div className="special-areas">
          {specialAreaCards.map((area) => {
            const areaCount = externalToolsCatalog.filter((item) => item.specialArea === area.area).length;
            return (
              <button
                className={externalToolSpecialArea === area.area ? "special-area active" : "special-area"}
                type="button"
                key={area.area}
                onClick={() => setExternalToolSpecialArea(area.area)}
              >
                <span>{area.title}</span>
                <strong>{areaCount} herramientas</strong>
                <small>{area.text}</small>
                <em>{area.warning}</em>
              </button>
            );
          })}
        </div>

        <div className="inventory-layout">
          <aside className="inventory-sidebar">
            <h3>Categorías</h3>
            <button className={externalToolCategory === "Todas" ? "active" : ""} onClick={() => setExternalToolCategory("Todas")}>Todas</button>
            {categories.filter((category) => category !== "Todas").map((category) => (
              <button className={externalToolCategory === category ? "active" : ""} key={category} onClick={() => setExternalToolCategory(category)}>
                {category}
              </button>
            ))}
          </aside>

          <div className="inventory-results">
            <div className="panel-head">
              <div>
                <h3>Inventario de herramientas</h3>
                <p>{filteredTools.length} resultado(s). Cada acceso abre una fuente externa y no procesa evidencia dentro de OPERIA.</p>
              </div>
              <button
                className="secondary-button"
                onClick={() => {
                  setExternalToolQuery("");
                  setExternalToolCategory("Todas");
                  setExternalToolOs("Todos");
                  setExternalToolDifficulty("Todas");
                  setExternalToolSpecialArea("Todas");
                  setExternalToolOnlineOnly(false);
                  setExternalToolGithubOnly(false);
                }}
              >
                <RefreshCcw size={15} /> Limpiar filtros
              </button>
            </div>
            <div className="inventory-grid">
              {filteredTools.map(renderToolCard)}
              {!filteredTools.length && <EmptyState text="No hay herramientas para esos filtros. Limpia filtros o busca por otra categoría." />}
            </div>
          </div>
        </div>

        <footer className="inventory-footer">
          Este inventario está destinado a fines de informática forense, investigación defensiva, respuesta a incidentes, auditoría autorizada, preservación de evidencia, docencia y análisis técnico-jurídico. No debe utilizarse para acceder, interferir, explotar o analizar sistemas sin autorización expresa.
        </footer>
      </section>
    );
  }

  function renderAi() {
    return (
      <section className="work-surface ai-legal-workbench">
        <div className="section-head">
          <div>
            <h2>Asistente de Analisis y Tipificacion</h2>
            <p>Asistencia local para vincular incidente, evidencia y biblioteca legal argentina registrada.</p>
          </div>
        </div>

        <div className="ai-hero-panel">
          <div>
            <span className="tool-kicker">Caso seleccionado</span>
            <h3>{selectedCase ? `${selectedCase.case_code} · ${selectedCase.title}` : "Selecciona un caso para iniciar"}</h3>
            <p>{selectedCase ? prettySpanish(selectedCase.incident_type) : "La tipificacion requiere un caso, una narrativa y biblioteca legal registrada."}</p>
          </div>
          <div className="ai-score-card">
            <span>Modo</span>
            <strong>RAG legal local</strong>
            <small>Sin API externa por defecto</small>
          </div>
        </div>

        <div className="ai-action-grid">
          <div className="detail-panel">
            <div className="panel-head">
              <div>
                <h3>1. Contexto para la asistencia</h3>
                <p>Describe el incidente o agrega foco investigativo. La respuesta se limita a fuentes legales registradas.</p>
              </div>
            </div>
            <textarea value={aiPrompt} onChange={(e) => setAiPrompt(e.target.value)} />
            <div className="button-row">
              <button onClick={() => runLegalTypification(false)} disabled={!selectedCaseId}><Gavel size={17} /> Tipificar delito</button>
              <button className="secondary-button" onClick={() => runLegalTypification(true)} disabled={!selectedCaseId || legalApplyState === "applying"}>
                <CheckCircle2 size={17} /> {legalApplyState === "applying" ? "Guardando..." : "Guardar sugerencias"}
              </button>
              <button className="secondary-button" onClick={runAiAssist}><Bot size={17} /> Ampliar analisis</button>
              <button className="secondary-button" onClick={runCaseRecommendations} disabled={!selectedCaseId}>
                <FileCheck2 size={17} /> Proximos pasos
              </button>
            </div>
            {legalApplyMessage && (
              <div className={`action-feedback ${legalApplyState}`}>
                {legalApplyMessage}
              </div>
            )}
          </div>

          <div className="detail-panel">
            <div className="panel-head">
              <div>
                <h3>2. Resultado de tipificacion</h3>
                <p>Delito sugerido, articulos conexos, confianza y evidencia faltante.</p>
              </div>
              {legalTypification && <span className={`badge ${legalTypification.confidence === "alto" ? "success" : ""}`}>Confianza {prettySpanish(legalTypification.confidence)}</span>}
            </div>
            {legalTypification?.principal_typification ? (
              <div className="typification-card">
                <span>{legalTypification.profile?.label || "Incidente digital"}</span>
                <h3>{legalTypification.principal_typification.reference} · {prettySpanish(legalTypification.principal_typification.title)}</h3>
                <p>{prettySpanish(legalTypification.principal_typification.applicability_to_case)}</p>
                <div className="readiness-bar">
                  <div style={{ width: `${legalTypification.readiness_score}%` }} />
                </div>
                <small>{prettySpanish(legalTypification.decision_level)} · Score {legalTypification.readiness_score}/100</small>
              </div>
            ) : (
              <EmptyState text="Ejecuta 'Tipificar delito' para obtener una propuesta jurídica asistida." />
            )}
          </div>
        </div>

        {legalTypification && (
          <div className="ai-result-grid">
            <div className="detail-panel">
              <h3>Elementos y evidencia necesaria</h3>
              <div className="summary-list">
                <span>Elementos objetivos: {prettySpanish(legalTypification.principal_typification?.why || "sin norma principal")}</span>
                <span>Elemento subjetivo: {prettySpanish(legalTypification.principal_typification?.subjective_elements || "requiere revision")}</span>
                <span>Evidencia requerida: {prettySpanish(legalTypification.principal_typification?.evidence_needed || "pendiente")}</span>
                <span>Limites: {prettySpanish(legalTypification.principal_typification?.probatory_limits || "requiere validacion humana")}</span>
              </div>
            </div>
            <div className="detail-panel">
              <h3>Normas conexas</h3>
              <div className="mini-list">
                {legalTypification.connected_typifications.slice(0, 5).map((item) => (
                  <span key={`${item.article_id}-${item.reference}`}>{item.reference} · {prettySpanish(item.title)} · {prettySpanish(item.legal_role)}</span>
                ))}
                {!legalTypification.connected_typifications.length && <span>Sin normas conexas registradas para este perfil.</span>}
              </div>
            </div>
            <div className="detail-panel">
              <h3>Estado probatorio</h3>
              <div className="case-overview">
                <div><span>Evidencias</span><strong>{legalTypification.evidence_snapshot.evidence_count}</strong></div>
                <div><span>Custodia</span><strong>{legalTypification.evidence_snapshot.custody_actions}</strong></div>
                <div><span>Mapeos aprobados</span><strong>{legalTypification.evidence_snapshot.approved_legal_mappings}</strong></div>
              </div>
              <ul className="compact-list">
                {legalTypification.missing_for_stronger_typification.map((item) => <li key={item}>{prettySpanish(item)}</li>)}
                {!legalTypification.missing_for_stronger_typification.length && <li>Base minima completa para revision del analista.</li>}
              </ul>
            </div>
            <div className="detail-panel">
              <h3>Medidas recomendadas</h3>
              <ul className="compact-list">
                {legalTypification.recommended_measures.map((item) => <li key={item}>{prettySpanish(item)}</li>)}
              </ul>
            </div>
          </div>
        )}

        <div className="detail-panel">
          <div className="panel-head">
            <div>
              <h3>3. Analisis operativo del caso</h3>
              <p>Lectura accionable del incidente, sin exponer salida tecnica cruda.</p>
            </div>
          </div>
          {renderCaseAnalysisOutcome()}
        </div>
      </section>
    );
  }

  function renderAiSecurity() {
    return (
      <section className="work-surface">
        <div className="section-head">
          <div>
            <h2>AI Security</h2>
            <p>Evaluacion controlada de modelos. Reporta riesgo observado bajo condiciones concretas.</p>
          </div>
          <button onClick={runAiSecurity}><BrainCircuit size={17} /> Crear evaluacion</button>
        </div>
        <JsonPanel data={aiSecurityResult} />
      </section>
    );
  }

  function renderIdentity() {
    const currentRole = identitySession.user?.role || "";
    const currentPermissions = currentRole ? permissions[currentRole] || [] : [];
    return (
      <section className="work-surface">
        <div className="section-head">
          <div>
            <h2>Identidad y Permisos</h2>
            <p>Login local con token bearer, usuario visible y permisos por rol.</p>
          </div>
          <button className="icon-button" onClick={refreshIdentity} title="Actualizar"><RefreshCcw size={18} /></button>
        </div>

        {identitySession.authenticated && identitySession.user ? (
          <div className="preview-grid">
            <div>
              <h4>Sesion activa</h4>
              <div className="summary-list">
                <span>Usuario: {identitySession.user.name}</span>
                <span>Email: {identitySession.user.email || "sin email"}</span>
                <span>Rol: {identitySession.user.role}</span>
                <span>Organizacion: {identitySession.user.organization_id || "local"}</span>
              </div>
              <button className="secondary" onClick={logout}>Cerrar sesion</button>
            </div>
            <div>
              <h4>Permisos visibles</h4>
              <div className="mini-list">
                {currentPermissions.map((permission) => <span key={permission}>{permission}</span>)}
                {!currentPermissions.length && <span>Sin permisos declarados para el rol.</span>}
              </div>
            </div>
          </div>
        ) : (
          <div className="split">
            <form className="form" onSubmit={login}>
              <h3>Iniciar sesion</h3>
              <input placeholder="Email" value={loginForm.email} onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })} />
              <input placeholder="Password" type="password" value={loginForm.password} onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })} />
              <button><Users size={17} /> Entrar</button>
            </form>
            <form className="form" onSubmit={bootstrapAdmin}>
              <h3>Crear admin inicial</h3>
              <input placeholder="Organizacion" value={bootstrapForm.organization_name} onChange={(e) => setBootstrapForm({ ...bootstrapForm, organization_name: e.target.value })} />
              <input placeholder="Nombre" value={bootstrapForm.name} onChange={(e) => setBootstrapForm({ ...bootstrapForm, name: e.target.value })} />
              <input placeholder="Email" value={bootstrapForm.email} onChange={(e) => setBootstrapForm({ ...bootstrapForm, email: e.target.value })} />
              <input placeholder="Password" type="password" value={bootstrapForm.password} onChange={(e) => setBootstrapForm({ ...bootstrapForm, password: e.target.value })} />
              <button className="secondary"><Shield size={17} /> Bootstrap admin</button>
            </form>
          </div>
        )}

        <JsonPanel data={{ authenticated: identitySession.authenticated, user: identitySession.user, permissions }} />
      </section>
    );
  }

  function renderModuleStatus(title: string) {
    return (
      <section className="work-surface">
        <div className="section-head">
          <div>
            <h2>{title}</h2>
            <p>Modulo conectado a la API canonica.</p>
          </div>
        </div>
        <JsonPanel data={modulePayload} />
      </section>
    );
  }

  function renderActive() {
    if (active === "workflow") return renderWorkflow();
    if (active === "dashboard") return renderDashboard();
    if (active === "caseDetail") return renderCaseDetail();
    if (active === "cases") return renderCases();
    if (active === "evidence") return renderEvidence();
    if (active === "reports") return renderReportsProfessional();
    if (active === "legalKnowledge") return renderLegalKnowledge();
    if (active === "cybercrime") return renderCybercrime();
    if (active === "deepfakeMedia") return renderDeepfakeMedia();
    if (active === "blockchainForensics") return renderBlockchainForensics();
    if (active === "iotForensics") return renderIoTForensics();
    if (active === "externalTools") return renderExternalTools();
    if (active === "ai") return renderAi();
    if (active === "aiSecurity") return renderAiSecurity();
    if (active === "identity") return renderIdentity();
    if (active === "history") return renderHistory();
    return renderModuleStatus(modules.find((item) => item.key === active)?.label ?? "Modulo");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Wrench size={23} />
          <div>
            <strong>OPERIA</strong>
            <span>Forensic Tracing</span>
          </div>
        </div>
        <nav>
          {modules.map((item) => {
            const Icon = item.icon;
            return (
              <button key={item.key} className={active === item.key ? "active" : ""} onClick={() => setActive(item.key)}>
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>

      <main>
        <header>
          <div>
            <p>Plataforma modular forense</p>
            <h1>{modules.find((item) => item.key === active)?.label}</h1>
          </div>
          <span className="status">{loading ? "Cargando" : "Operativo"}</span>
        </header>

        {error && <div className="error">{error}</div>}
        {renderActive()}
      </main>
    </div>
  );
}
