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
import { API_BASE, apiDelete, apiGet, apiPost, apiPostForm, apiPut } from "./api";

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
  | "aiSecurity"
  | "geoTrace"
  | "geoProximity"
  | "identity"
  | "exports"
  | "settings";

type CaseItem = {
  id: number;
  case_code: string;
  title: string;
  description: string;
  incident_type: string;
  status: string;
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
  confidence: string;
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
  { key: "aiSecurity", label: "AI Security", icon: BrainCircuit },
  { key: "geoTrace", label: "Geo Trace", icon: Map },
  { key: "geoProximity", label: "Geo Proximity", icon: Navigation },
  { key: "identity", label: "Usuarios", icon: Users },
  { key: "exports", label: "Exportaciones", icon: Download },
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
  { value: "otro", label: "Otro", query: "incidente informático evidencia digital" }
];

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
  const [indicatorResult, setIndicatorResult] = useState<unknown>(null);
  const [legalQuery, setLegalQuery] = useState("phishing fraude acceso datos");
  const [legalRecommendation, setLegalRecommendation] = useState<LegalRecommendationResponse | null>(null);
  const [aiPrompt, setAiPrompt] = useState("Analiza el caso, evidencia cargada, riesgos y proximos pasos. No inventes normas legales.");
  const [aiResult, setAiResult] = useState<unknown>(null);
  const [analystName, setAnalystName] = useState(localStorage.getItem("operia_analyst_name") || "");
  const [reviewResult, setReviewResult] = useState<unknown>(null);
  const [reportPreview, setReportPreview] = useState<ReportPreview | null>(null);
  const [executiveSummaryDraft, setExecutiveSummaryDraft] = useState("");
  const [exportFinalResult, setExportFinalResult] = useState<unknown>(null);
  const [closureStatus, setClosureStatus] = useState<ClosureStatus | null>(null);
  const [closureNote, setClosureNote] = useState("Cierre operativo con evidencia preservada, informe revisado y PDF exportado.");
  const [aiSecurityResult, setAiSecurityResult] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedCase = useMemo(() => cases.find((item) => item.id === Number(selectedCaseId)), [cases, selectedCaseId]);
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
      setLegalProbatoryMatrix(null);
      setLegalQualityControl(null);
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
      qualityControlData
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
      apiGet<LegalQualityControl>(`/legal-knowledge/case/${caseId}/quality-control`)
    ]);
    setParticipants(participantData);
    setEvidence(evidenceData);
    setReports(reportData);
    setCustody(custodyData);
    setAuditLogs(auditData);
    setManifests(manifestData);
    setLegalMappings(mappingData);
    setLegalMappingEvidence(mappingEvidenceData);
    setLegalProbatoryMatrix(probatoryMatrixData);
    setLegalQualityControl(qualityControlData);
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
      const paths: Partial<Record<ModuleKey, string>> = {
        ai: "/ai/",
        aiSecurity: "/ai-security/",
        cybercrime: "/cybercrime/",
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
    refreshCaseCollections(selectedCaseId).catch((err: Error) => setError(err.message));
  }, [selectedCaseId]);

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
    setIndicatorResult(await apiPost("/cybercrime/analyze-indicator", { case_id: selectedCaseId || undefined, indicator }));
    if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
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
      return;
    }
    localStorage.setItem("operia_analyst_name", analystName);
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
      setAiResult({
        status: enriched.status,
        report_id: enriched.id,
        message: "Informe ampliado con analisis tecnico-juridico. Revisa y vuelve a exportar PDF.",
        observations: enriched.observations
      });
      if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
      return;
    }
    setAiResult(await apiPost("/ai/assist", { case_id: selectedCaseId || undefined, model_name: "mistral", prompt: aiPrompt }));
  }

  async function generateReport() {
    if (!selectedCaseId) return;
    localStorage.setItem("operia_analyst_name", analystName);
    const author = encodeURIComponent(analystName.trim());
    const report = await apiPost<ReportItem>(`/reports/case/${selectedCaseId}/generate?author=${author}`);
    await refreshCaseCollections(selectedCaseId);
    setReviewResult({ generated_report_id: report.id, status: "generated" });
  }

  async function reviewReport() {
    if (!latestReport) return;
    setReviewResult(await apiPost(`/reports/${latestReport.id}/review`));
    if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
  }

  async function loadReportPreview(reportId = latestReport?.id) {
    if (!reportId) return;
    const preview = await apiGet<ReportPreview>(`/reports/${reportId}/preview`);
    setReportPreview(preview);
    setExecutiveSummaryDraft(preview.executive_summary);
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
    const result = await apiPost<ClosureStatus>(`/cases/${selectedCaseId}/close`, { closure_note: closureNote });
    setClosureStatus(result);
    await refreshCore();
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

  function renderWorkflow() {
    return (
      <div className="workflow">
        <section className="work-surface">
          <div className="section-head">
            <div>
              <h2>Flujo Caso - Evidencia - Informe</h2>
              <p>Camino operativo de punta a punta para resolver un incidente con OPERIA.</p>
            </div>
            <button className="icon-button" onClick={refreshCore} title="Actualizar">
              <RefreshCcw size={18} />
            </button>
          </div>
          <div className="case-selector">
            <label>
              Caso activo
              <select value={selectedCaseId} onChange={(event) => setSelectedCaseId(Number(event.target.value) || "")}>
                <option value="">Sin caso seleccionado</option>
                {cases.map((item) => (
                  <option value={item.id} key={item.id}>
                    {item.case_code} - {item.title}
                  </option>
                ))}
              </select>
            </label>
            <div className="case-summary">
              <strong>{selectedCase?.title || "Nuevo caso operativo"}</strong>
              <span>{selectedCase ? `${selectedCase.case_code} | ${selectedCase.incident_type} | ${selectedCase.status}` : "Crea o selecciona un caso para iniciar."}</span>
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
            <JsonPanel data={indicatorResult} />
          </StepCard>

          <StepCard number={6} title="Consultar biblioteca legal argentina" done={articles.length > 0}>
            <div className="compact-form">
              <input value={legalQuery} onChange={(e) => setLegalQuery(e.target.value)} />
              <button onClick={searchLegal}><Search size={17} /> Buscar normas</button>
            </div>
            <div className="mini-list">
              {articles.slice(0, 4).map((item) => (
                <span key={item.id}>{item.code} art. {item.article_number} - {item.title}</span>
              ))}
            </div>
            <JsonPanel data={legalRecommendation} />
          </StepCard>

          <StepCard number={7} title="Ampliar análisis técnico-jurídico" done={Boolean(aiResult)}>
            <div className="compact-form">
              <textarea value={aiPrompt} onChange={(e) => setAiPrompt(e.target.value)} />
              <button onClick={runAiAssist}><Bot size={17} /> {latestReport ? "Ampliar informe" : "Analizar caso"}</button>
            </div>
            {latestReport && <p className="notice">Con informe generado, esta accion agrega hipotesis, conclusiones y fundamentacion legal al reporte.</p>}
            <JsonPanel data={aiResult} />
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
            <JsonPanel data={reviewResult} />
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
              <button onClick={closeCase} disabled={!closureStatus?.ready_to_close}>
                <CheckCircle2 size={17} /> Cerrar caso
              </button>
            </div>
            {closureStatus?.already_closed && <p className="notice success">Caso cerrado. Las acciones futuras deben considerarse posteriores al cierre.</p>}
            {closureStatus && !closureStatus.ready_to_close && !closureStatus.already_closed && (
              <div className="requirements">
                <strong>Falta para cerrar:</strong>
                {closureStatus.missing.map((item) => (
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
    return (
      <section className="work-surface">
        <div className="section-head">
          <div>
            <h2>Dashboard Operativo</h2>
            <p>Resumen de casos, evidencia, reportes y modulos integrados.</p>
          </div>
          <button className="icon-button" onClick={refreshCore} title="Actualizar"><RefreshCcw size={18} /></button>
        </div>
        {dashboard.metrics ? <MetricGrid metrics={dashboard.metrics} /> : <EmptyState text="Sin metricas cargadas." />}
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
                <span>{prettySpanish(item.status)} | Score {item.review_score}</span>
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
        <div className="table">
          {cases.map((item) => (
            <button className={`row-button ${selectedCaseId === item.id ? "selected" : ""}`} key={item.id} onClick={() => setSelectedCaseId(item.id)}>
              <span>{item.case_code}</span>
              <strong>{item.title}</strong>
              <em>{item.incident_type}</em>
            </button>
          ))}
        </div>
      </section>
    );
  }

  function renderCaseDetail() {
    const locked = selectedCase?.status === "cerrado";
    return (
      <div className="case-detail">
        <section className="work-surface">
          <div className="section-head">
            <div>
              <h2>Detalle Profesional del Caso</h2>
              <p>{selectedCase ? `${selectedCase.case_code} - ${selectedCase.title}` : "Selecciona un caso para ver su expediente completo."}</p>
            </div>
            <select value={selectedCaseId} onChange={(event) => setSelectedCaseId(Number(event.target.value) || "")}>
              <option value="">Seleccionar caso</option>
              {cases.map((item) => <option value={item.id} key={item.id}>{item.case_code}</option>)}
            </select>
          </div>
          {selectedCase ? (
            <div className="case-overview">
              <div><span>Estado</span><strong>{selectedCase.status}</strong></div>
              <div><span>Incidente</span><strong>{selectedCase.incident_type}</strong></div>
              <div><span>Participantes</span><strong>{participants.length}</strong></div>
              <div><span>Evidencia</span><strong>{evidence.length}</strong></div>
              <div><span>Custodia</span><strong>{custody.length}</strong></div>
              <div><span>Informes</span><strong>{reports.length}</strong></div>
            </div>
          ) : <EmptyState text="No hay caso seleccionado." />}
          {locked && <p className="notice success">Caso cerrado: las modificaciones futuras deberian tratarse como reapertura o correccion auditada.</p>}
        </section>

        <section className="detail-grid">
          <div className="detail-panel">
            <div className="panel-head">
              <h3>Personas y entidades</h3>
            </div>
            {participants.map((item) => (
              <div className="editable-record" key={item.id}>
                <div>
                  <strong>{item.display_name}</strong>
                  <span>{item.participant_type} | {item.person_type} | {item.sensitivity_level}</span>
                  <small>{item.relationship_to_case || item.role_description || "Relacion pendiente"}</small>
                </div>
                <div className="record-actions">
                  <button className="icon-button" onClick={() => setEditingParticipant(item)} title="Editar"><Save size={15} /></button>
                  <button className="icon-button danger" onClick={() => deleteParticipant(item.id)} title="Eliminar"><Trash2 size={15} /></button>
                </div>
              </div>
            ))}
            {!participants.length && <EmptyState text="Sin participantes cargados." />}
          </div>

          <div className="detail-panel">
            <div className="panel-head">
              <h3>Evidencia</h3>
            </div>
            {evidence.map((item) => (
              <div className="editable-record" key={item.id}>
                <div>
                  <strong>{item.evidence_type}</strong>
                  <span>{item.description}</span>
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

          <div className="detail-panel">
            <div className="panel-head">
              <h3>Cadena de custodia</h3>
            </div>
            {custody.map((item) => (
              <div className="editable-record" key={item.id}>
                <div>
                  <strong>{item.action_type}</strong>
                  <span>{item.detailed_description}</span>
                  <small>{item.user_responsible || "Responsable pendiente"} | {item.status}</small>
                </div>
                <div className="record-actions">
                  <button className="icon-button" onClick={() => setEditingCustody(item)} title="Editar"><Save size={15} /></button>
                  <button className="icon-button danger" onClick={() => deleteCustodyAction(item.id)} title="Eliminar"><Trash2 size={15} /></button>
                </div>
              </div>
            ))}
            {!custody.length && <EmptyState text="Sin acciones de custodia." />}
          </div>

          <div className="detail-panel">
            <div className="panel-head">
              <h3>Informes y exportaciones</h3>
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
            <div className="mini-list">
              {manifests.slice(0, 6).map((item) => (
                <span key={item.id}>{item.export_type}: {item.filename} | {item.sha256_hash.slice(0, 16)}...</span>
              ))}
            </div>
          </div>

          <div className="detail-panel wide">
            <div className="panel-head">
              <h3>Auditoria del caso</h3>
            </div>
            <div className="audit-list">
              {auditLogs.slice(0, 20).map((item) => (
                <div key={item.id}>
                  <strong>{item.action}</strong>
                  <span>{item.module} | {item.severity} | {new Date(item.created_at).toLocaleString()}</span>
                  <small>{item.details || `${item.entity_type} ${item.entity_id}`}</small>
                </div>
              ))}
              {!auditLogs.length && <EmptyState text="Sin auditoria visible para este caso." />}
            </div>
          </div>
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

  function renderLegalKnowledge() {
    return (
      <section className="work-surface">
        <div className="section-head">
          <div>
            <h2>Biblioteca Legal Argentina</h2>
            <p>Búsqueda estructurada sobre fuentes registradas.</p>
          </div>
          <div className="search">
            <input value={legalQuery} onChange={(e) => setLegalQuery(e.target.value)} />
            <button className="icon-button" onClick={searchLegal} title="Buscar"><Search size={18} /></button>
          </div>
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
          <div className="article-list">
            {legalRecommendation.recommendations.map((item) => (
              <article key={`${item.reference}-${item.article_id}`}>
                <div>
                  <span>{item.reference} · {item.legal_role} · confianza {item.confidence}</span>
                  <h3>{prettySpanish(item.title)}</h3>
                </div>
                <p>{prettySpanish(item.text)}</p>
                <small>{prettySpanish(item.applicability_to_case)}</small>
                <small>{prettySpanish(item.probatory_limits)}</small>
                <small>Elementos: {prettySpanish(item.why)}</small>
                <small>Evidencia: {prettySpanish(item.evidence_needed)}</small>
                {item.precedents.length > 0 && <small>Jurisprudencia registrada: {item.precedents.length}</small>}
                {item.doctrine.length > 0 && <small>Doctrina registrada: {item.doctrine.length}</small>}
                <div className="button-row">
                  <button onClick={() => decideLegalRecommendation(item, "aprobado")} disabled={!selectedCaseId}>
                    <CheckCircle2 size={16} /> Aprobar para el caso
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

  function renderAi() {
    return (
      <section className="work-surface">
        <div className="section-head">
          <div>
            <h2>Asistente de Analisis</h2>
            <p>Apoyo tecnico-juridico interno para estructurar hipotesis, evidencia y normativa.</p>
          </div>
        </div>
        <div className="split">
          <div className="form">
            <textarea value={aiPrompt} onChange={(e) => setAiPrompt(e.target.value)} />
            <button onClick={runAiAssist}><Bot size={17} /> Analizar caso</button>
            <button className="secondary" onClick={runCaseRecommendations} disabled={!selectedCaseId}>
              <FileCheck2 size={17} /> Recomendaciones del caso
            </button>
          </div>
          <JsonPanel data={aiResult} />
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
    if (active === "reports") return renderReports();
    if (active === "legalKnowledge") return renderLegalKnowledge();
    if (active === "ai") return renderAi();
    if (active === "aiSecurity") return renderAiSecurity();
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
