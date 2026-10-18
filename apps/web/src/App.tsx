import { guardCaseResult } from "@/lib/case-result";
import { Card } from "@/components/ui/card";
import { ModuleSurface } from "@/components/layout/module-surface";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { EvidenceWorkspace } from "@/components/evidence/evidence-workspace";
import { ReportRegister } from "@/components/reports/report-register";
import { FormField } from "@/components/forms/form-field";
import { Input } from "@/components/ui/input";
import { fetchScopedDownload } from "@/lib/scoped-download";
import LocalAiGateway from "./LocalAiGateway";
import CaseAccessPanel from "./CaseAccessPanel";
import { ApplicationShell } from "@/components/layout/application-shell";
import { CasesWorkspace } from "@/components/cases/cases-workspace";
import { DossierHeader } from "@/components/cases/dossier-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { ReactNode } from "react";
import {
  BarChart3,
  BookOpen,
  Bot,
  BrainCircuit,
  Briefcase,
  Calculator,
  CheckCircle2,
  Download,
  FileCheck2,
  FileText,
  Fingerprint,
  Gavel,
  Globe2,
  History,
  Map,
  MonitorPlay,
  Navigation,
  Network,
  Presentation,
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
import { API_BASE, apiDelete, apiGet, apiPatch, apiPost, apiPostForm, apiPut, authHeaders, getAuthToken, setAuthToken } from "./api";
import { externalToolsCatalog, type InventoryCyberTool } from "./externalToolsCatalog";
import MobileForensics from "./MobileForensics";

type ModuleKey =
  | "workflow"
  | "dashboard"
  | "caseDetail"
  | "cases"
  | "evidence"
  | "reports"
  | "casePresentation"
  | "mind"
  | "legalKnowledge"
  | "ai"
  | "cybercrime"
  | "deepfakeMedia"
  | "blockchainForensics"
  | "iotForensics"
  | "mobileForensics"
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
  ledger_entry?: { version: number; root_action_id: number; previous_action_id: number | null; actor_name: string; recorded_at: string; reason: string } | null;
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

type DamageItem = {
  id: number;
  case_id: number;
  concept: string;
  amount: number;
  currency: string;
  base_date: string;
  value_source: string;
  formula_used: string;
  supporting_evidence: string;
  certainty_level: string;
  observations: string;
  created_at?: string;
  updated_at?: string;
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

type PresentationItem = {
  id: number;
  case_id: number;
  source_report_id: number | null;
  title: string;
  presentation_type: string;
  version: string;
  status: string;
  author: string;
  selected_fragments: string;
  review_score: number;
  exported_file: string;
  created_at?: string;
  updated_at?: string;
};

type PresentationSlide = {
  id: number;
  presentation_id: number;
  slide_number: number;
  title: string;
  content_type: string;
  text: string;
  speaker_notes: string;
  confidentiality_level: string;
};

type PresentationReview = {
  score: number;
  status?: string;
  clarity: number;
  evidentiary_strength: number;
  narrative_coherence: number;
  legal_solidity: number;
  visual_quality: number;
  critical_errors?: string[];
  warnings?: string[];
  oral_exposure_risks: string[];
  recommendations: string[];
  page_recommendations?: string[];
};

type AiSecurityEvaluation = {
  id?: number;
  provider?: string;
  model_name?: string;
  environment?: string;
  network_blocked?: boolean;
  tools_enabled?: boolean;
  overall_score?: number;
  risk_level?: string;
  recommendation?: string;
  conclusion?: string;
  created_at?: string;
};

type IdentitySession = {
  authenticated: boolean;
  user?: IdentityUser | null;
};

type IdentityUser = {
    id: number;
    organization_id?: number;
    name: string;
    email?: string;
    role: string;
    status?: string;
    title?: string;
    agency?: string;
    registration_id?: string;
    phone?: string;
    signature?: string;
    profile_notes?: string;
};

type PermissionPayload = Record<string, string[]>;
type CaseDetailTab = "summary" | "participants" | "evidence" | "custody" | "damage" | "legal" | "reports" | "audit";

type ExportOutcome = {
  status?: string;
  message?: string;
  seal_id?: string | null;
  sha256?: string | null;
  manifest_id?: string | null;
  can_export_final?: boolean;
  exportability?: { level?: string; score?: number };
  contradictions?: { count?: number; blocking?: boolean };
  final_checklist?: { score?: number; ready?: boolean; missing?: string[]; items?: Array<{ key?: string; label?: string; ok?: boolean; message?: string }> };
  missing?: string[];
};

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
  route_order: number;
  include_in_report: boolean;
  preservation_checklist: string;
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

type MindNote = {
  id: number;
  case_id?: number;
  note_type: string;
  title: string;
  vault_path: string;
  tags: string;
  confidence: string;
  review_status: string;
  summary?: string;
  content: string;
  updated_at?: string;
};

type MindPrompt = {
  id: number;
  key: string;
  title: string;
  purpose: string;
  prompt_text: string;
  output_format: string;
};

type MindAgent = {
  id: number;
  key: string;
  name: string;
  role: string;
  scope: string;
  allowed_modules?: string;
  restrictions?: string;
  risk_level?: string;
};

type MindGraphPayload = {
  case_id?: number;
  nodes: Array<{ id: number; node_key: string; node_type: string; label: string; source_module?: string }>;
  edges: Array<{ id: number; source_node_key: string; target_node_key: string; relation_type: string; label?: string; confidence?: string }>;
  node_types?: string[];
  relation_types?: string[];
};

type MindSearchResult = {
  id: number;
  case_id?: number;
  note_type: string;
  title: string;
  summary: string;
  content_excerpt: string;
  vault_path: string;
  confidence: string;
  review_status: string;
  score: number;
  matches: string[];
};

type MindAuditEntry = {
  id: number;
  case_id?: number;
  action: string;
  entity_type: string;
  entity_id: string;
  severity: string;
  details: string;
  created_at?: string;
};

type MindCaseBrief = {
  case_id: number;
  case_code: string;
  title: string;
  readiness: string;
  confidence: string;
  known_facts: string[];
  missing_information: string[];
  risks: string[];
  contradictions: string[];
  recommended_next_steps: string[];
  memory_highlights: string[];
  graph_summary: Record<string, number>;
};

type NavigationSection = "Operación" | "Forense" | "Inteligencia" | "Administración";

const modules: Array<{ key: ModuleKey; label: string; icon: typeof BarChart3; section: NavigationSection }> = [
  { key: "workflow", label: "Flujo Operativo", icon: CheckCircle2, section: "Operación" },
  { key: "dashboard", label: "Dashboard", icon: BarChart3, section: "Operación" },
  { key: "caseDetail", label: "Expediente", icon: FileCheck2, section: "Operación" },
  { key: "cases", label: "Casos", icon: Briefcase, section: "Operación" },
  { key: "evidence", label: "Evidencia", icon: Fingerprint, section: "Operación" },
  { key: "reports", label: "Informes", icon: FileText, section: "Operación" },
  { key: "casePresentation", label: "Exposición del Caso", icon: MonitorPlay, section: "Operación" },
  { key: "mind", label: "Cerebro / Memoria", icon: BrainCircuit, section: "Inteligencia" },
  { key: "legalKnowledge", label: "Biblioteca Legal", icon: BookOpen, section: "Inteligencia" },
  { key: "ai", label: "Asistente IA", icon: Bot, section: "Inteligencia" },
  { key: "cybercrime", label: "Cybercrime", icon: Shield, section: "Forense" },
  { key: "deepfakeMedia", label: "Deepfake / Medios", icon: FileCheck2, section: "Forense" },
  { key: "blockchainForensics", label: "Blockchain Investigation Lab", icon: Globe2, section: "Forense" },
  { key: "iotForensics", label: "IoT Forensics", icon: Shield, section: "Forense" },
  { key: "mobileForensics", label: "Forense móvil", icon: Shield, section: "Forense" },
  { key: "externalTools", label: "Herramientas Externas", icon: Wrench, section: "Forense" },
  { key: "aiSecurity", label: "AI Security", icon: BrainCircuit, section: "Forense" },
  { key: "geoTrace", label: "Geo Trace", icon: Map, section: "Forense" },
  { key: "geoProximity", label: "Geo Proximity", icon: Navigation, section: "Forense" },
  { key: "identity", label: "Usuarios", icon: Users, section: "Administración" },
  { key: "exports", label: "Exportaciones", icon: Download, section: "Administración" },
  { key: "history", label: "Historial", icon: History, section: "Administración" },
  { key: "settings", label: "Configuración", icon: Settings, section: "Administración" }
];

const navigationSections: NavigationSection[] = ["Operación", "Forense", "Inteligencia", "Administración"];

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

const emptyDamageForm = {
  concept: "",
  amount: "",
  currency: "ARS",
  base_date: "",
  value_source: "",
  formula_used: "",
  supporting_evidence: "",
  certainty_level: "medio",
  observations: ""
};

const damagePresets = [
  {
    label: "Pérdida patrimonial directa",
    concept: "Pérdida patrimonial directa",
    formula_used: "Daño patrimonial directo = importe transferido, debitado, apropiado o sustraído acreditado por comprobante.",
    value_source: "Comprobante bancario, transferencia, billetera virtual, extracto, denuncia o constancia documentada."
  },
  {
    label: "Costos de recuperación o pericia",
    concept: "Costos de recuperación o pericia",
    formula_used: "Costos de recuperación = horas técnicas x valor hora documentado + servicios contratados vinculados al incidente.",
    value_source: "Factura, presupuesto, orden de trabajo, registro horario técnico o constancia profesional."
  },
  {
    label: "Indisponibilidad operativa",
    concept: "Indisponibilidad operativa",
    formula_used: "Indisponibilidad = horas de interrupción x costo operativo/hora documentado.",
    value_source: "Registro de caída, ticket, informe de continuidad, métrica de facturación o declaración contable verificable."
  },
  {
    label: "Reposición y mitigación",
    concept: "Reposición y mitigación",
    formula_used: "Reposición/mitigación = costo de restauración, hardening, licencias, reposición o servicios necesarios directamente vinculados.",
    value_source: "Factura, presupuesto, ticket de soporte, orden de compra o constancia de servicio."
  }
];

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

function deepfakeAnalysisReadiness(analysis: DeepfakeAnalysisItem) {
  const checkedControls = analysis.checklist.filter((item) => item.ok).length;
  const checks = [
    { key: "evidence", label: "Evidencia vinculada", ok: Boolean(analysis.evidence_id) },
    { key: "hash", label: "Hash preservado", ok: Boolean(analysis.evidence_hash) },
    { key: "origin", label: "Origen documentado", ok: Boolean(analysis.source_origin) },
    { key: "metadata", label: "Metadatos o EXIF", ok: Boolean(analysis.metadata_summary) },
    { key: "findings", label: "Hallazgos técnicos", ok: Boolean(analysis.findings) },
    { key: "limits", label: "Limitaciones declaradas", ok: Boolean(analysis.limitations) },
    { key: "checklist", label: "Checklist suficiente", ok: checkedControls >= 6 },
    { key: "finding", label: "Hallazgo creado", ok: Boolean(analysis.finding_id) },
    { key: "legal", label: "Normas aplicadas", ok: analysis.legal_mapping_ids.length > 0 }
  ];
  const score = Math.round((checks.filter((item) => item.ok).length / checks.length) * 100);
  const status = score >= 78 ? "listo" : score >= 45 ? "parcial" : "incompleto";
  const missing = checks.filter((item) => !item.ok).map((item) => item.label);
  return { checkedControls, checks, score, status, missing };
}

function iotDeviceReadiness(device: IoTDeviceItem) {
  const checkedControls = device.checklist.filter((item) => item.ok).length;
  const hasNetworkIdentifier = Boolean(device.internal_ip || device.external_ip || device.mac);
  const checks = [
    { key: "identity", label: "Identificación del dispositivo", ok: Boolean(device.device_type && (device.manufacturer || device.model)) },
    { key: "network", label: "Identificador de red", ok: hasNetworkIdentifier },
    { key: "evidence", label: "Evidencia vinculada", ok: Boolean(device.evidence_id) },
    { key: "hash", label: "Hash preservado", ok: Boolean(device.evidence_hash) },
    { key: "logs", label: "Logs o estado documentado", ok: Boolean(device.logs_available || device.open_ports || device.known_vulnerabilities) },
    { key: "tool", label: "Metodología/herramienta", ok: Boolean(device.tool_used) },
    { key: "limits", label: "Limitaciones declaradas", ok: Boolean(device.limitations) },
    { key: "checklist", label: "Checklist suficiente", ok: checkedControls >= 6 },
    { key: "finding", label: "Hallazgo creado", ok: Boolean(device.finding_id) },
    { key: "legal", label: "Normas aplicadas", ok: device.legal_mapping_ids.length > 0 }
  ];
  const score = Math.round((checks.filter((item) => item.ok).length / checks.length) * 100);
  const status = score >= 80 ? "listo" : score >= 50 ? "parcial" : "incompleto";
  const missing = checks.filter((item) => !item.ok).map((item) => item.label);
  return { checkedControls, checks, score, status, missing };
}

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
  "wallet desconocida",
  "wallet receptora",
  "wallet intermediaria",
  "wallet de origen",
  "wallet de destino",
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
  tool_used: "OPERIA Blockchain Investigation Lab",
  route_order: "",
  include_in_report: true,
  preservation_checklist: "",
  limitations: "Una wallet no identifica por sí sola a una persona sin evidencia externa corroborante."
};

const blockchainExplorerCatalog = [
  {
    key: "bitcoin",
    label: "Bitcoin",
    tx: "https://www.blockchain.com/explorer/transactions/btc/",
    address: "https://www.blockchain.com/explorer/addresses/btc/",
    home: "https://www.blockchain.com/explorer/assets/btc"
  },
  {
    key: "ethereum",
    label: "Ethereum",
    tx: "https://etherscan.io/tx/",
    address: "https://etherscan.io/address/",
    home: "https://etherscan.io"
  },
  {
    key: "tron",
    label: "TRON / USDT TRC20",
    tx: "https://tronscan.org/#/transaction/",
    address: "https://tronscan.org/#/address/",
    home: "https://tronscan.org"
  },
  {
    key: "bsc",
    label: "BNB Smart Chain",
    tx: "https://bscscan.com/tx/",
    address: "https://bscscan.com/address/",
    home: "https://bscscan.com"
  },
  {
    key: "polygon",
    label: "Polygon",
    tx: "https://polygonscan.com/tx/",
    address: "https://polygonscan.com/address/",
    home: "https://polygonscan.com"
  },
  {
    key: "solana",
    label: "Solana",
    tx: "https://solscan.io/tx/",
    address: "https://solscan.io/account/",
    home: "https://solscan.io"
  }
];

function getBlockchainExplorer(blockchain: string) {
  const normalized = blockchain.toLowerCase();
  return (
    blockchainExplorerCatalog.find((item) => normalized.includes(item.key)) ||
    blockchainExplorerCatalog.find((item) => normalized.includes("bnb") && item.key === "bsc") ||
    blockchainExplorerCatalog.find((item) => normalized.includes("usdt") && item.key === "tron") ||
    blockchainExplorerCatalog[0]
  );
}

function buildBlockchainUrl(blockchain: string, type: "tx" | "source" | "destination", value: string) {
  const explorer = getBlockchainExplorer(blockchain);
  const cleanValue = value.trim();
  if (!cleanValue) return explorer.home;
  if (type === "tx") return `${explorer.tx}${encodeURIComponent(cleanValue)}`;
  return `${explorer.address}${encodeURIComponent(cleanValue)}`;
}

function formatMoneyARS(value: number) {
  return new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 2 }).format(value || 0);
}

function blockchainTransactionReadiness(item: BlockchainTransactionItem) {
  const checks = [
    { key: "tx_hash", label: "Hash de transacción", ok: Boolean(item.tx_hash?.trim()) },
    { key: "explorer", label: "URL o fuente preservada", ok: Boolean(item.explorer_url?.trim()) },
    { key: "wallets", label: "Wallet origen y destino", ok: Boolean(item.source_wallet?.trim() && item.destination_wallet?.trim()) },
    { key: "amount", label: "Monto y token", ok: Number(item.amount) > 0 && Boolean(item.token?.trim()) },
    { key: "datetime", label: "Fecha/hora observada", ok: Boolean(item.tx_datetime?.trim()) },
    { key: "evidence", label: "Evidencia vinculada", ok: Boolean(item.evidence_id) },
    { key: "route", label: "Hipótesis de ruta", ok: Boolean(item.route_hypothesis?.trim()) },
    { key: "finding", label: "Hallazgo creado", ok: Boolean(item.finding_id) },
    { key: "legal", label: "Normas aplicadas", ok: item.legal_mapping_ids.length > 0 }
  ];
  const okCount = checks.filter((check) => check.ok).length;
  const score = Math.round((okCount / checks.length) * 100);
  const missing = checks.filter((check) => !check.ok).map((check) => check.label);
  const status = score >= 78 ? "listo" : score >= 45 ? "parcial" : "incompleto";
  const label = status === "listo" ? "Listo para informe" : status === "parcial" ? "Requiere refuerzo" : "Insuficiente";
  return { checks, score, missing, status, label };
}

function blockchainDraftReadiness(form: typeof emptyBlockchainForm) {
  const checks = [
    { key: "hash", label: "Hash de transaccion", ok: Boolean(form.tx_hash.trim()), critical: true },
    { key: "network", label: "Red y token definidos", ok: Boolean(form.blockchain.trim() && form.token.trim()), critical: true },
    { key: "wallets", label: "Wallet origen y destino", ok: Boolean(form.source_wallet.trim() && form.destination_wallet.trim()), critical: true },
    { key: "amount", label: "Monto documentado", ok: Number(form.amount || 0) > 0, critical: false },
    { key: "datetime", label: "Fecha/hora observada", ok: Boolean(form.tx_datetime.trim()), critical: true },
    { key: "explorer", label: "URL o fuente preservada", ok: Boolean(form.explorer_url.trim()), critical: true },
    { key: "evidence", label: "Evidencia vinculada", ok: Boolean(form.evidence_id), critical: true },
    { key: "tool", label: "Herramienta o metodo usado", ok: Boolean(form.tool_used.trim()), critical: false },
    { key: "route", label: "Hipotesis de ruta", ok: Boolean(form.route_hypothesis.trim()), critical: false },
    { key: "limits", label: "Limites periciales declarados", ok: Boolean(form.limitations.trim()), critical: false }
  ];
  const okCount = checks.filter((check) => check.ok).length;
  const score = Math.round((okCount / checks.length) * 100);
  const missing = checks.filter((check) => !check.ok).map((check) => check.label);
  const criticalMissing = checks.filter((check) => check.critical && !check.ok).map((check) => check.label);
  const ready = criticalMissing.length === 0 && score >= 70;
  return { checks, score, missing, criticalMissing, ready };
}

function shortBlockchainLabel(value = "") {
  const clean = value.trim();
  if (!clean) return "Pendiente";
  if (clean.length <= 22) return clean;
  return `${clean.slice(0, 10)}...${clean.slice(-8)}`;
}

function buildBlockchainGraph(transactions: BlockchainTransactionItem[]) {
  const nodes = new globalThis.Map<string, { id: string; label: string; total: number; risk: boolean; service: boolean }>();
  const edges = transactions.map((tx) => {
    const source = tx.source_wallet?.trim() || `origen-pendiente-${tx.id}`;
    const target = tx.destination_wallet?.trim() || `destino-pendiente-${tx.id}`;
    const classification = tx.wallet_classification || "desconocido";
    const risk = ["mixer", "bridge", "contrato inteligente"].includes(classification);
    const service = ["exchange", "mixer", "bridge", "contrato inteligente"].includes(classification);

    [source, target].forEach((id) => {
      const previous = nodes.get(id);
      nodes.set(id, {
        id,
        label: shortBlockchainLabel(id),
        total: (previous?.total || 0) + 1,
        risk: Boolean(previous?.risk || risk),
        service: Boolean(previous?.service || service)
      });
    });

    return {
      id: tx.id,
      source,
      target,
      sourceLabel: shortBlockchainLabel(source),
      targetLabel: shortBlockchainLabel(target),
      amountLabel: `${tx.amount || "0"} ${tx.token || ""}`.trim(),
      classification,
      readiness: blockchainTransactionReadiness(tx),
      txHashLabel: shortBlockchainLabel(tx.tx_hash || ""),
      risk
    };
  });

  const repeatedWallets = Array.from(nodes.values()).filter((node) => node.total > 1);
  const serviceNodes = Array.from(nodes.values()).filter((node) => node.service);
  const readyEdges = edges.filter((edge) => edge.readiness.status === "listo").length;
  return { nodes: Array.from(nodes.values()), edges, repeatedWallets, serviceNodes, readyEdges };
}

function blockchainCriticalFlags(item: BlockchainTransactionItem) {
  const flags = [];
  if (!item.evidence_id) flags.push("Falta evidencia preservada vinculada.");
  if (!item.explorer_url) flags.push("Falta URL, captura o fuente de consulta del explorador.");
  if (!item.tx_datetime) flags.push("Falta fecha/hora observada de la transacción.");
  if (!item.route_hypothesis) flags.push("Falta hipótesis de ruta documentada.");
  if (!item.finding_id) flags.push("No fue convertido todavía en hallazgo técnico.");
  if (!item.legal_mapping_ids.length) flags.push("No tiene normas aplicadas al caso.");
  if (["mixer", "bridge", "contrato inteligente"].includes(item.wallet_classification)) {
    flags.push("Punto crítico: requiere cautela reforzada por mixer, bridge o contrato inteligente.");
  }
  if (!item.amount || Number(item.amount) <= 0) flags.push("Falta monto verificable.");
  return flags;
}

function blockchainRouteOverview(transactions: BlockchainTransactionItem[]) {
  const totalARS = transactions.reduce((sum, item) => sum + Number(item.approximate_value || 0), 0);
  const criticalFlags = transactions.flatMap((item) => blockchainCriticalFlags(item));
  const servicePoints = transactions.filter((item) => ["exchange", "mixer", "bridge", "contrato inteligente"].includes(item.wallet_classification));
  const readyCount = transactions.filter((item) => blockchainTransactionReadiness(item).status === "listo").length;
  const recommendedRequests = [
    servicePoints.some((item) => item.wallet_classification === "exchange") && "Oficio a exchange o plataforma para KYC, logs, IPs, fecha/hora, titularidad y movimientos asociados.",
    servicePoints.some((item) => item.wallet_classification === "mixer") && "Documentar límite de trazabilidad por mixer y requerir análisis complementario antes de sostener atribución.",
    servicePoints.some((item) => item.wallet_classification === "bridge") && "Preservar transacciones puente en ambas redes y correlacionar hash, fecha, monto y wallet.",
    transactions.some((item) => !item.evidence_id) && "Vincular cada transacción con captura, comprobante, exportación del explorador o evidencia hashada.",
    transactions.some((item) => !item.finding_id) && "Convertir los movimientos relevantes en hallazgos técnicos para que ingresen al informe final.",
    transactions.some((item) => !item.legal_mapping_ids.length) && "Aplicar normas desde biblioteca legal y vincularlas a evidencia concreta."
  ].filter(Boolean) as string[];
  return { totalARS, criticalFlags, servicePoints, readyCount, recommendedRequests };
}

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
    .replace(/Ã¡/g, "á")
    .replace(/Ã©/g, "é")
    .replace(/Ã­/g, "í")
    .replace(/Ã³/g, "ó")
    .replace(/Ãº/g, "ú")
    .replace(/Ã±/g, "ñ")
    .replace(/Ã/g, "Á")
    .replace(/Ã‰/g, "É")
    .replace(/Ã/g, "Í")
    .replace(/Ã“/g, "Ó")
    .replace(/Ãš/g, "Ú")
    .replace(/Ã‘/g, "Ñ")
    .replace(/Â·/g, "·")
    .replace(/â†’/g, "→")
    .replace(/âœ“/g, "✓")
    .replace(/â€¢/g, "•")
    .replace(/\?ltima/g, "Última")
    .replace(/\?ltimo/g, "Último")
    .replace(/est\?/g, "está")
    .replace(/autor\?a/g, "autoría")
    .replace(/Auditor\?a/g, "Auditoría")
    .replace(/auditor\?a/g, "auditoría")
    .replace(/fundamentaci\?n/g, "fundamentación")
    .replace(/cerro/g, "cerró")
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
    .replace(/\bpreservación\b/g, "preservación")
    .replace(/\bcuantificacion\b/g, "cuantificación")
    .replace(/\bvictima\b/g, "víctima")
    .replace(/\bdisposicion\b/g, "disposición")
    .replace(/\bdefraudacion\b/g, "defraudación")
    .replace(/\beconomica\b/g, "económica")
    .replace(/\btecnica\b/g, "técnica")
    .replace(/\bjuridica\b/g, "jurídica")
    .replace(/\bcriticas\b/g, "críticas");
}

function formatMoney(amount: number, currency = "ARS") {
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: currency || "ARS",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(Number.isFinite(amount) ? amount : 0);
}

function professionalReportStatus(status = "") {
  const normalized = status.toLowerCase();
  if (normalized.includes("cerrado") || normalized.includes("final")) return "Caso Cerrado";
  if (normalized.includes("investigativo") || normalized.includes("enriquecido") || normalized.includes("ia")) return "En Proceso Investigativo";
  if (normalized.includes("análisis") || normalized.includes("análisis")) return "En Proceso de Análisis";
  return "Caso en Proceso de Inicio de Investigación";
}

function isAuthenticationErrorMessage(message = "") {
  const normalized = message.toLowerCase();
  return normalized.includes("autentic") || normalized.includes("sesión requerida") || normalized.includes("sesion requerida") || normalized.includes("credencial");
}

async function readExportOutcome(response: Response): Promise<ExportOutcome> {
  const contentType = response.headers.get("content-type") || "";
  const raw = await response.text();
  const looksLikeJson = contentType.includes("application/json") || raw.trim().startsWith("{") || raw.trim().startsWith("[");
  if (looksLikeJson) {
    try {
      const parsed = JSON.parse(raw);
      const detail = parsed.detail && typeof parsed.detail === "object" ? parsed.detail : parsed;
      return {
        status: "blocked",
        message: extractReadableMessage(detail.message || parsed.message || detail, "La exportación final fue bloqueada por controles periciales."),
        exportability: detail.exportability,
        contradictions: detail.contradictions,
        final_checklist: detail.final_checklist,
        missing: detail.exportability?.checklist?.missing || detail.final_checklist?.missing || parsed.missing || []
      };
    } catch {
      return { status: "blocked", message: "La exportación final fue bloqueada por controles periciales." };
    }
  }
  return { status: "blocked", message: extractReadableMessage(raw, "La exportación final fue bloqueada por controles periciales.") };
}

function extractReadableMessage(value: unknown, fallback = "La acción no pudo completarse."): string {
  if (!value) return fallback;
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return fallback;
    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      try {
        return extractReadableMessage(JSON.parse(trimmed), fallback);
      } catch {
        return prettySpanish(trimmed);
      }
    }
    return prettySpanish(trimmed);
  }
  if (Array.isArray(value)) {
    return value.map((item) => extractReadableMessage(item, "")).filter(Boolean).join("; ") || fallback;
  }
  if (typeof value === "object") {
    const data = value as Record<string, unknown>;
    for (const key of ["message", "detail", "error", "title"]) {
      if (data[key]) return extractReadableMessage(data[key], fallback);
    }
    if (data.exportability || data.final_checklist || data.contradictions) {
      return "La exportación final requiere completar controles periciales antes de sellarse.";
    }
  }
  return fallback;
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

function formatPayloadValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Sin dato";
  if (typeof value === "boolean") return value ? "Sí" : "No";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return prettySpanish(value.replace(/_/g, " "));
  if (Array.isArray(value)) return value.length ? value.map(formatPayloadValue).join(", ") : "Sin registros";
  if (typeof value === "object") return "Información disponible";
  return String(value);
}

function DataPanel({ data, empty = "Sin resultados todavía." }: { data: unknown; empty?: string }) {
  if (!data) return <EmptyState text={empty} />;
  if (typeof data !== "object") return <div className="readable-panel">{formatPayloadValue(data)}</div>;
  const entries = Object.entries(data as Record<string, unknown>).filter(([, value]) => value !== undefined && value !== null);
  if (!entries.length) return <EmptyState text={empty} />;
  return (
    <div className="readable-panel">
      {entries.slice(0, 12).map(([key, value]) => (
        <div className="readable-row" key={key}>
          <span>{prettySpanish(key.replace(/_/g, " "))}</span>
          <strong>{formatPayloadValue(value)}</strong>
        </div>
      ))}
    </div>
  );
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

export function App({ initialModule = "cases" }: { initialModule?: ModuleKey } = {}) {
  const [active, setActive] = useState<ModuleKey>(initialModule);
  const [caseDetailTab, setCaseDetailTab] = useState<CaseDetailTab>("summary");
  const [dashboard, setDashboard] = useState<DashboardPayload>({});
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<number | "">("");
  const [caseAccess, setCaseAccess] = useState<{ caseId: number; token: string; capabilities: string[] } | null>(null);
  const [caseCollectionsLoading, setCaseCollectionsLoading] = useState(false);
  const [caseCollectionsError, setCaseCollectionsError] = useState("");
  const editorReturnFocus = useRef<HTMLElement | null>(null);
  const [caseTask, setCaseTask] = useState("");
  const caseTaskLock = useRef(false);
  const [caseFeedback, setCaseFeedback] = useState("");
  const [pendingNavigation, setPendingNavigation] = useState<(() => void) | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [participants, setParticipants] = useState<CaseParticipant[]>([]);
  const [custody, setCustody] = useState<CustodyAction[]>([]);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [presentations, setPresentations] = useState<PresentationItem[]>([]);
  const [presentationSlides, setPresentationSlides] = useState<PresentationSlide[]>([]);
  const [selectedPresentationId, setSelectedPresentationId] = useState<number | "">("");
  const [presentationReview, setPresentationReview] = useState<PresentationReview | null>(null);
  const [presentationState, setPresentationState] = useState<"idle" | "working" | "success" | "error">("idle");
  const [presentationMessage, setPresentationMessage] = useState("");
  const [historyReportsByCase, setHistoryReportsByCase] = useState<Record<number, ReportItem[]>>({});
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [manifests, setManifests] = useState<ExportManifest[]>([]);
  const [legalMappings, setLegalMappings] = useState<LegalMapping[]>([]);
  const [legalMappingEvidence, setLegalMappingEvidence] = useState<LegalMappingEvidence[]>([]);
  const [legalProbatoryMatrix, setLegalProbatoryMatrix] = useState<LegalProbatoryMatrix | null>(null);
  const [legalQualityControl, setLegalQualityControl] = useState<LegalQualityControl | null>(null);
  const [legalEvidenceSelection, setLegalEvidenceSelection] = useState<Record<number, string>>({});
  const [legalElementSelection, setLegalElementSelection] = useState<Record<number, string>>({});
  const [legalLinkDrafts, setLegalLinkDrafts] = useState<Record<number, Partial<LegalMappingEvidence>>>({});
  const [mindNotes, setMindNotes] = useState<MindNote[]>([]);
  const [mindPrompts, setMindPrompts] = useState<MindPrompt[]>([]);
  const [mindAgents, setMindAgents] = useState<MindAgent[]>([]);
  const [mindGraph, setMindGraph] = useState<MindGraphPayload | null>(null);
  const [mindAudit, setMindAudit] = useState<MindAuditEntry[]>([]);
  const [mindBrief, setMindBrief] = useState<MindCaseBrief | null>(null);
  const [mindSearchQuery, setMindSearchQuery] = useState("");
  const [mindSearchResults, setMindSearchResults] = useState<MindSearchResult[]>([]);
  const [mindMessage, setMindMessage] = useState("");
  const [mindState, setMindState] = useState<"idle" | "working" | "success" | "error">("idle");
  const [mindNoteForm, setMindNoteForm] = useState({
    note_type: "nota",
    title: "",
    content: "",
    tags: "operia, memoria"
  });
  const [mindRelationForm, setMindRelationForm] = useState({
    source_node_key: "",
    target_node_key: "",
    relation_type: "vinculado_con",
    label: "",
    confidence: "medio"
  });
  const [articles, setArticles] = useState<LegalArticle[]>([]);
  const [modulePayload, setModulePayload] = useState<unknown>(null);
  const [authToken, setAuthTokenState] = useState(getAuthToken());
  useEffect(() => {
    const syncSession = () => setAuthTokenState(getAuthToken());
    window.addEventListener("operia:auth-changed", syncSession);
    window.addEventListener("storage", syncSession);
    return () => {
      window.removeEventListener("operia:auth-changed", syncSession);
      window.removeEventListener("storage", syncSession);
    };
  }, []);
  const [identitySession, setIdentitySession] = useState<IdentitySession>({ authenticated: false });
  const [permissions, setPermissions] = useState<PermissionPayload>({});
  const [loginForm, setLoginForm] = useState({ email: "", password: "" });
  const [identityUsers, setIdentityUsers] = useState<IdentityUser[]>([]);
  const [identityMessage, setIdentityMessage] = useState("");
  const [identityState, setIdentityState] = useState<"idle" | "working" | "success" | "error">("idle");
  const [profileForm, setProfileForm] = useState({
    name: "",
    title: "",
    agency: "",
    registration_id: "",
    phone: "",
    signature: "",
    profile_notes: ""
  });
  const [newUserForm, setNewUserForm] = useState({
    name: "",
    email: "",
    role: "analista",
    status: "active",
    title: "",
    agency: "",
    password: "OperiaUser2026!"
  });
  const [passwordDrafts, setPasswordDrafts] = useState<Record<number, string>>({});
  const [bootstrapForm, setBootstrapForm] = useState({
    organization_name: "OPERIA Local",
    organization_slug: "operia-local",
    name: "OPERIA Admin",
    email: "admin@operia.local",
    password: "OperiaAdmin2026!"
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
  const [evidenceUploadVersion, setEvidenceUploadVersion] = useState(0);
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [custodyForm, setCustodyForm] = useState({ action_type: "revisión", detailed_description: "", user_responsible: "" });
  const [editingCustody, setEditingCustody] = useState<CustodyAction | null>(null);
  const [custodyReason, setCustodyReason] = useState("");
  const caseCollectionsRequest = useRef(0);
  const custodyScope = useRef({ caseId: selectedCaseId, token: authToken, generation: 0 });
  if (custodyScope.current.caseId !== selectedCaseId || custodyScope.current.token !== authToken) {
    custodyScope.current = { caseId: selectedCaseId, token: authToken, generation: custodyScope.current.generation + 1 };
  }
  useEffect(() => { setEditingCustody(null); setCustodyReason(""); setEditingParticipant(null); setEditingEvidence(null); setPendingNavigation(null); setCaseDetailTab("summary"); setEvidenceForm({ description: "", responsible: "", custodian: "" }); setEvidenceFile(null); setCustodyForm({ action_type: "revisión", detailed_description: "", user_responsible: "" }); setCaseFeedback(""); setCaseTask(""); caseTaskLock.current = false; }, [selectedCaseId, authToken]);
  const [damageItems, setDamageItems] = useState<DamageItem[]>([]);
  const [damageForm, setDamageForm] = useState(emptyDamageForm);
  const [damageState, setDamageState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [damageMessage, setDamageMessage] = useState("");
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
  const [editingBlockchainId, setEditingBlockchainId] = useState<number | null>(null);
  const [blockchainState, setBlockchainState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [blockchainMessage, setBlockchainMessage] = useState("");
  const [iotDevices, setIotDevices] = useState<IoTDeviceItem[]>([]);
  const [iotForm, setIotForm] = useState(emptyIoTForm);
  const [editingIotId, setEditingIotId] = useState<number | null>(null);
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
  const [cyberLabForm, setCyberLabForm] = useState({ title: "", purpose: "análisis de indicador", risk_level: "medio", operator: "" });
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
  const damageTotal = useMemo(() => damageItems.reduce((total, item) => total + Number(item.amount || 0), 0), [damageItems]);
  const damageSupportedTotal = useMemo(
    () => damageItems.filter((item) => item.value_source || item.supporting_evidence).reduce((total, item) => total + Number(item.amount || 0), 0),
    [damageItems]
  );
  const exportabilitySnapshot = useMemo(
    () => reportExportabilitySnapshot(selectedCase, evidence, custody, legalMappings, legalProbatoryMatrix, legalQualityControl, latestReport),
    [selectedCase, evidence, custody, legalMappings, legalProbatoryMatrix, legalQualityControl, latestReport]
  );

  function clearCaseCollections() {
    setCaseAccess(null);
    setCaseCollectionsError("");
    setEvidence([]);
    setParticipants([]);
    setReports([]);
    setPresentations([]);
    setPresentationSlides([]);
    setSelectedPresentationId("");
    setPresentationReview(null);
    setPresentationState("idle");
    setPresentationMessage("");
    setCustody([]);
    setDamageItems([]);
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
    setDamageState("idle");
    setDamageMessage("");
  }

  async function refreshCaseCollections(caseId: number | "") {
    if (caseId && caseId !== custodyScope.current.caseId) return;
    const requestId = ++caseCollectionsRequest.current;
    const generation = custodyScope.current.generation;
    const token = getAuthToken();
    const current = () => requestId === caseCollectionsRequest.current && caseId === custodyScope.current.caseId && generation === custodyScope.current.generation && token === getAuthToken();
    clearCaseCollections();
    if (!caseId || !token) { setCaseCollectionsLoading(false); return; }
    setCaseCollectionsLoading(true);
    try {
    const accessData = await apiGet<{ capabilities: string[] }>(`/cases/${caseId}/access/me`);
    const [
      participantData,
      evidenceData,
      reportData,
      custodyData,
      damageData,
      auditData,
      manifestData,
      mappingData,
      mappingEvidenceData,
      probatoryMatrixData,
      qualityControlData,
      deepfakeData,
      blockchainData,
      iotData,
      rubricData,
      presentationData
    ] = await Promise.all([
      apiGet<CaseParticipant[]>(`/cases/${caseId}/participants`),
      apiGet<EvidenceItem[]>(`/evidence/case/${caseId}`),
      apiGet<ReportItem[]>(`/reports/case/${caseId}`),
      apiGet<CustodyAction[]>(`/evidence/case/${caseId}/custody-actions`),
      apiGet<DamageItem[]>(`/cases/${caseId}/damage-items`),
      apiGet<AuditLog[]>(`/audit/logs?case_id=${caseId}`).catch(() => []),
      apiGet<ExportManifest[]>(`/exports/manifests?case_id=${caseId}`),
      apiGet<LegalMapping[]>(`/legal-knowledge/case/${caseId}/mappings`),
      apiGet<LegalMappingEvidence[]>(`/legal-knowledge/case/${caseId}/mapping-evidence`),
      apiGet<LegalProbatoryMatrix>(`/legal-knowledge/case/${caseId}/probatory-matrix`),
      apiGet<LegalQualityControl>(`/legal-knowledge/case/${caseId}/quality-control`),
      apiGet<DeepfakeAnalysisItem[]>(`/cybercrime/deepfake/case/${caseId}`).catch(() => []),
      apiGet<BlockchainTransactionItem[]>(`/cybercrime/blockchain/case/${caseId}`).catch(() => []),
      apiGet<IoTDeviceItem[]>(`/cybercrime/iot/case/${caseId}`).catch(() => []),
      apiGet<RubricEvaluation>(`/rubrics/case/${caseId}/score`).catch(() => null),
      apiGet<PresentationItem[]>(`/reports/presentations/case/${caseId}`).catch(() => [])
    ]);
    const slidesData = presentationData[0]?.id
      ? await apiGet<PresentationSlide[]>(`/reports/presentations/${presentationData[0].id}/slides`).catch(() => []) : [];
    const closureData = await apiGet<ClosureStatus>(`/cases/${caseId}/closure-status`);
    if (!current()) return;
    setCaseAccess({ caseId: Number(caseId), token, capabilities: accessData.capabilities });
    setParticipants(participantData);
    setEvidence(evidenceData);
    setReports(reportData);
    setPresentations(presentationData);
    const nextPresentationId = presentationData[0]?.id || "";
    setSelectedPresentationId(nextPresentationId);
    setPresentationSlides(slidesData);
    setPresentationReview(null);
    setCustody(custodyData);
    setDamageItems(damageData);
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
    setClosureStatus(closureData);
    } catch (err) {
      if (current()) setCaseCollectionsError(err instanceof Error ? err.message : "No se pudo consultar el expediente.");
      throw err;
    } finally {
      if (current()) setCaseCollectionsLoading(false);
    }
  }

  async function refreshCore() {
    const token = getAuthToken();
    const generation = custodyScope.current.generation;
    setError("");
    const [dashboardData, casesData] = await Promise.all([
      apiGet<DashboardPayload>("/dashboard/"),
      apiGet<CaseItem[]>("/cases")
    ]);
    const reportPairs = await Promise.all(
      casesData.map(async (item) => {
        const caseReports = await apiGet<ReportItem[]>(`/reports/case/${item.id}`).catch(() => []);
        return [item.id, caseReports] as const;
      })
    );
    if (token !== getAuthToken() || generation !== custodyScope.current.generation) return;
    setDashboard(dashboardData);
    setCases(casesData);
    setHistoryReportsByCase(Object.fromEntries(reportPairs));
    const currentStillExists = selectedCaseId && casesData.some((item) => item.id === selectedCaseId);
    const nextCaseId = currentStillExists ? selectedCaseId : casesData[0]?.id || "";
    setSelectedCaseId(nextCaseId);
    await refreshCaseCollections(nextCaseId);
  }

  async function refreshMind() {
    const token = getAuthToken();
    const generation = custodyScope.current.generation;
    const caseQuery = selectedCaseId ? `?case_id=${selectedCaseId}` : "";
    const [notesData, promptsData, agentsData, graphData, auditData, briefData] = await Promise.all([
      apiGet<MindNote[]>(`/mind/notes${caseQuery}`).catch(() => []),
      apiGet<MindPrompt[]>("/mind/prompts").catch(() => []),
      apiGet<MindAgent[]>("/mind/agents").catch(() => []),
      selectedCaseId ? apiGet<MindGraphPayload>(`/mind/cases/${selectedCaseId}/graph`).catch(() => null) : Promise.resolve(null),
      apiGet<MindAuditEntry[]>(`/mind/audit${caseQuery}`).catch(() => []),
      selectedCaseId ? apiGet<MindCaseBrief>(`/mind/cases/${selectedCaseId}/brief`).catch(() => null) : Promise.resolve(null)
    ]);
    if (token !== getAuthToken() || generation !== custodyScope.current.generation || selectedCaseId !== custodyScope.current.caseId) return;
    setMindNotes(notesData);
    setMindPrompts(promptsData);
    setMindAgents(agentsData);
    setMindGraph(graphData);
    setMindAudit(auditData);
    setMindBrief(briefData);
  }

  async function loadModule(key: ModuleKey) {
    setLoading(true);
    setError("");
    try {
      if (["workflow", "dashboard", "cases", "evidence", "reports", "casePresentation"].includes(key)) {
        if (!getAuthToken()) return;
        if (["workflow", "evidence", "reports", "casePresentation"].includes(key) && cases.length) return;
        await refreshCore();
        return;
      }
      if (key === "legalKnowledge") {
        setArticles(await apiGet<LegalArticle[]>(`/legal-knowledge/articles?q=${encodeURIComponent(legalQuery)}`));
        return;
      }
      if (key === "mind") {
        await refreshMind();
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
      handleUiError(err, "No se pudo conectar con la API.", { focusIdentity: false });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadModule(active);
  }, [active]);

  useEffect(() => {
    clearCaseCollections();
    setCases([]);
    setSelectedCaseId("");
    setHistoryReportsByCase({});
    setDashboard({});
    setModulePayload(null);
    setMindNotes([]);
    setMindGraph(null);
    setMindBrief(null);
    setMindAudit([]);
    setMindSearchResults([]);
    refreshIdentity().then(() => {
      if (authToken && authToken === getAuthToken()) return refreshCore();
    }).catch(() => undefined);
  }, [authToken]);

  useEffect(() => {
    const user = identitySession.user;
    if (!user) return;
    setProfileForm({
      name: user.name || "",
      title: user.title || "",
      agency: user.agency || "",
      registration_id: user.registration_id || "",
      phone: user.phone || "",
      signature: user.signature || "",
      profile_notes: user.profile_notes || ""
    });
  }, [identitySession.user?.id]);

  useEffect(() => {
    setIndicatorResult(null); setAiResult(null); setAiEnrichmentResult(null); setLegalTypification(null); setLegalRecommendation(null);
    setReviewResult(null); setReviewAudit(null); setExportFinalResult(null); setModulePayload(null);
    setCyberLabSessions([]); setCyberProofRows([]); setMindSearchResults([]); setMindNotes([]); setMindGraph(null); setMindBrief(null);
    setEditingBlockchainId(null); setBlockchainForm(emptyBlockchainForm); setEditingIotId(null); setIotForm(emptyIoTForm);
    const current = captureCaseContext();
    refreshCaseCollections(selectedCaseId).catch((err: Error) => { if (current()) setError(err.message); });
  }, [selectedCaseId, authToken]);

  async function refreshIdentity() {
    const token = getAuthToken();
    const [session, permissionData] = await Promise.all([
      apiGet<IdentitySession>("/identity/me"),
      apiGet<PermissionPayload>("/identity/permissions")
    ]);
    if (token !== getAuthToken()) return;
    setIdentitySession(session);
    setPermissions(permissionData);
    if (session.authenticated) {
      try {
        setIdentityUsers(await apiGet<IdentityUser[]>("/identity/users"));
      } catch {
        setIdentityUsers([]);
      }
    } else {
      setIdentityUsers([]);
    }
    setModulePayload({ status: session.authenticated ? "sesion_activa" : "sin_sesion" });
  }

  function handleUiError(err: unknown, fallback: string, options: { focusIdentity?: boolean } = {}) {
    const raw = err instanceof Error ? err.message : fallback;
    if (isAuthenticationErrorMessage(raw)) {
      setError("Acción protegida. Inicia sesión como administrador o usa Recuperar acceso local desde Usuarios.");
      setAuthToken("");
      setAuthTokenState("");
      setIdentitySession({ authenticated: false });
      if (options.focusIdentity) setActive("identity");
      return;
    }
    setError(extractReadableMessage(raw || fallback, fallback));
  }

  function activePermissions() {
    const role = identitySession.user?.role || "";
    return role ? permissions[role] || [] : [];
  }

  function canUse(permission: string) {
    const granted = activePermissions();
    return granted.includes("*") || granted.includes(permission);
  }

  function canCase(capability: string, permission: string) {
    return canUse(permission) && caseAccess?.caseId === selectedCaseId && caseAccess.token === getAuthToken() && caseAccess.capabilities.includes(capability);
  }

  function canModifySelectedCase() {
    return canCase("write", "cases:write") || canCase("participants", "cases:write") ||
      canCase("evidence", "evidence:write") || canCase("analysis", "evidence:write") || canCase("analysis", "ai:use") ||
      ["reports", "review", "approve"].some(capability => canCase(capability, "reports:write"));
  }

  function requestNavigation(action: () => void) {
    if (editingParticipant || editingEvidence || editingCustody || evidenceFile || evidenceForm.description.trim() || (reportPreview && executiveSummaryDraft !== reportPreview.executive_summary)) setPendingNavigation(() => action);
    else action();
  }

  function navigateTo(module: ModuleKey) {
    if (module !== active) requestNavigation(() => { setEditingParticipant(null); setEditingEvidence(null); setEditingCustody(null); setCustodyReason(""); setActive(module); });
  }

  function selectCase(caseId: number | "") {
    if (caseId !== selectedCaseId) requestNavigation(() => setSelectedCaseId(caseId));
  }

  function captureCaseContext() {
    const generation = custodyScope.current.generation;
    const token = getAuthToken();
    return () => generation === custodyScope.current.generation && token === getAuthToken();
  }

  async function runCaseTask(label: string, action: () => Promise<unknown>) {
    if (caseTaskLock.current) return;
    const current = captureCaseContext();
    caseTaskLock.current = true;
    setCaseTask(label); setCaseFeedback(""); setError("");
    try {
      await action();
      if (current()) setCaseFeedback(previous => previous || `${label}: operación terminada. Revisá el resultado registrado.`);
    } catch (err) {
      if (current()) setError(err instanceof Error ? err.message : "No se pudo completar la operación.");
    } finally {
      if (current()) { setCaseTask(""); caseTaskLock.current = false; }
    }
  }

  async function downloadArtifact(path: string, filename: string) {
    const current = captureCaseContext();
    const blob = await fetchScopedDownload(`${API_BASE}${path}`, getAuthToken(), current);
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url; link.download = filename; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function downloadReport(reportId: number) {
    if (!canCase("export", "reports:read") || !reports.some(item => item.id === reportId && item.case_id === selectedCaseId)) throw new Error("No tenés permiso de exportación para este informe.");
    await downloadArtifact(`/exports/reports/${reportId}/pdf`, `operia-informe-${reportId}.pdf`);
  }

  function renderEvidenceUpload() {
    return <form className="premium-form" onSubmit={event => { event.preventDefault(); void runCaseTask("Incorporar evidencia", () => uploadEvidence(event)); }} aria-label="Incorporar evidencia al expediente" aria-busy={Boolean(caseTask)}>
      <p className="premium-form-help">Los campos con * son obligatorios. Solo se registra el archivo al confirmar la carga.</p>
      <fieldset disabled={!canCase("evidence", "evidence:write") || Boolean(caseTask)}><legend className="sr-only">Datos y archivo de evidencia</legend>
        <FormField label="Descripción de evidencia"><textarea required maxLength={10000} value={evidenceForm.description} onChange={e => setEvidenceForm({ ...evidenceForm, description: e.target.value })} /></FormField>
        <FormField label="Responsable"><Input value={evidenceForm.responsible} onChange={e => setEvidenceForm({ ...evidenceForm, responsible: e.target.value })} /></FormField>
        <FormField label="Custodio"><Input value={evidenceForm.custodian} onChange={e => setEvidenceForm({ ...evidenceForm, custodian: e.target.value })} /></FormField>
        <FormField label="Archivo original" hint="La API calcula el hash y registra la custodia. El archivo no se envía a conectores externos."><Input key={`${authToken}:${selectedCaseId}:${evidenceUploadVersion}`} type="file" required onChange={e => setEvidenceFile(e.target.files?.[0] || null)} /></FormField>
        <Button type="submit" disabled={!evidenceFile || !evidenceForm.description.trim()} className="h-auto min-h-10 whitespace-normal"><Upload size={16} />{caseTask || "Subir y calcular hash"}</Button>
      </fieldset>
      {!canCase("evidence", "evidence:write") && <p className="premium-permissions-note">Requiere un expediente activo y permiso para incorporar evidencia.</p>}
    </form>;
  }

  function guardPermission(permission: string, actionLabel: string) {
    if (!identitySession.authenticated) {
      setError(`Para ${actionLabel} tenés que iniciar sesión con un usuario autorizado.`);
      setActive("identity");
      return false;
    }
    if (!canUse(permission)) {
      setError(`Tu rol actual no tiene permiso para ${actionLabel}. Requiere: ${permission}.`);
      return false;
    }
    return true;
  }

  function handleMindError(err: unknown, fallback: string) {
    const raw = err instanceof Error ? err.message : "";
    if (isAuthenticationErrorMessage(raw)) {
      setMindMessage("Acción protegida. Inicia sesión en Usuarios para guardar memoria, snapshots o auditoría.");
      return;
    }
    setMindMessage(extractReadableMessage(raw || fallback, fallback));
  }

  async function createMindNote(event: FormEvent) {
    const requestCurrent = captureCaseContext();
    event.preventDefault();
    if (!mindNoteForm.title.trim() || !mindNoteForm.content.trim()) {
      setMindState("error");
      setMindMessage("Completa título y contenido para guardar la nota en memoria.");
      return;
    }
    setMindState("working");
    setMindMessage("");
    try {
      await guardCaseResult(apiPost<MindNote>("/mind/notes", {
        case_id: selectedCaseId || undefined,
        note_type: mindNoteForm.note_type,
        title: mindNoteForm.title.trim(),
        content: mindNoteForm.content.trim(),
        tags: mindNoteForm.tags.split(",").map((item) => item.trim()).filter(Boolean),
        source_module: "frontend",
        confidence: "medio",
        review_status: "borrador"
      }), requestCurrent);
      setMindNoteForm({ note_type: "nota", title: "", content: "", tags: "operia, memoria" });
      setMindState("success");
      setMindMessage("Nota guardada en la memoria forense y en el vault Markdown.");
      await guardCaseResult(refreshMind(), requestCurrent);
    } catch (err) {
      if (!requestCurrent()) return;
      setMindState("error");
      handleMindError(err, "No se pudo guardar la nota. Verifica el caso activo y vuelve a intentar.");
    }
  }

  async function createMindSnapshot() {
    const requestCurrent = captureCaseContext();
    if (!selectedCaseId) {
      setMindState("error");
      setMindMessage("Selecciona un caso para crear un snapshot de memoria.");
      return;
    }
    setMindState("working");
    setMindMessage("");
    try {
      const result = await guardCaseResult(apiPost<{ message: string; graph_nodes: number; graph_edges: number }>(`/mind/cases/${selectedCaseId}/snapshot`), requestCurrent);
      setMindState("success");
      setMindMessage(`${result.message} Grafo actualizado: ${result.graph_nodes} nodos y ${result.graph_edges} relaciones.`);
      await guardCaseResult(refreshMind(), requestCurrent);
    } catch (err) {
      if (!requestCurrent()) return;
      setMindState("error");
      handleMindError(err, "No se pudo crear el snapshot del caso. Verifica permisos y caso activo.");
    }
  }

  async function createReportMindSnapshot() {
    const requestCurrent = captureCaseContext();
    if (!latestReport) {
      setMindState("error");
      setMindMessage("Genera primero un informe para guardarlo en memoria.");
      return;
    }
    setMindState("working");
    setMindMessage("");
    try {
      const result = await guardCaseResult(apiPost<{ message: string; graph_nodes: number; graph_edges: number }>(`/mind/reports/${latestReport.id}/snapshot`), requestCurrent);
      setMindState("success");
      setMindMessage(`${result.message} Grafo actualizado: ${result.graph_nodes} nodos y ${result.graph_edges} relaciones.`);
      await guardCaseResult(refreshMind(), requestCurrent);
    } catch (err) {
      if (!requestCurrent()) return;
      setMindState("error");
      handleMindError(err, "No se pudo guardar el informe en memoria. Genera o selecciona un informe válido.");
    }
  }

  async function createPresentationMindSnapshot() {
    const requestCurrent = captureCaseContext();
    const selectedPresentation = presentations.find((item) => item.id === Number(selectedPresentationId)) || presentations[0];
    if (!selectedPresentation) {
      setMindState("error");
      setMindMessage("Genera primero una exposicion del caso para guardarla en memoria.");
      return;
    }
    setMindState("working");
    setMindMessage("");
    try {
      const result = await guardCaseResult(apiPost<{ message: string; graph_nodes: number; graph_edges: number }>(
        `/mind/presentations/${selectedPresentation.id}/snapshot`
      ), requestCurrent);
      setMindState("success");
      setMindMessage(`${result.message} Grafo actualizado: ${result.graph_nodes} nodos y ${result.graph_edges} relaciones.`);
      await guardCaseResult(refreshMind(), requestCurrent);
    } catch (err) {
      if (!requestCurrent()) return;
      setMindState("error");
      handleMindError(err, "No se pudo guardar la exposición en memoria. Genera primero una exposición válida.");
    }
  }

  async function createMindRelation(event: FormEvent) {
    const requestCurrent = captureCaseContext();
    event.preventDefault();
    if (!selectedCaseId) {
      setMindState("error");
      setMindMessage("Selecciona un caso antes de crear relaciones de grafo.");
      return;
    }
    if (!mindRelationForm.source_node_key || !mindRelationForm.target_node_key) {
      setMindState("error");
      setMindMessage("Selecciona nodo origen y nodo destino para crear la relación.");
      return;
    }
    if (mindRelationForm.source_node_key === mindRelationForm.target_node_key) {
      setMindState("error");
      setMindMessage("La relación necesita dos nodos distintos.");
      return;
    }
    setMindState("working");
    setMindMessage("");
    try {
      await guardCaseResult(apiPost("/mind/graph/edges", {
        case_id: Number(selectedCaseId),
        source_node_key: mindRelationForm.source_node_key,
        target_node_key: mindRelationForm.target_node_key,
        relation_type: mindRelationForm.relation_type,
        label: mindRelationForm.label,
        confidence: mindRelationForm.confidence,
        metadata: { source: "frontend_mind" }
      }), requestCurrent);
      setMindState("success");
      setMindMessage("Relación guardada en el grafo de memoria forense.");
      setMindRelationForm({ source_node_key: "", target_node_key: "", relation_type: "vinculado_con", label: "", confidence: "medio" });
      await guardCaseResult(refreshMind(), requestCurrent);
    } catch (err) {
      if (!requestCurrent()) return;
      setMindState("error");
      handleMindError(err, "No se pudo crear la relación. Verifica permisos y nodos seleccionados.");
    }
  }

  async function searchMind(event?: FormEvent) {
    const requestCurrent = captureCaseContext();
    event?.preventDefault();
    const query = mindSearchQuery.trim();
    if (query.length < 2) {
      setMindSearchResults([]);
      setMindState("error");
      setMindMessage("Escribí al menos dos caracteres para consultar la memoria.");
      return;
    }
    setMindState("working");
    setMindMessage("");
    try {
      const caseParam = selectedCaseId ? `&case_id=${selectedCaseId}` : "";
      const results = await guardCaseResult(apiGet<MindSearchResult[]>(`/mind/search?q=${encodeURIComponent(query)}${caseParam}`), requestCurrent);
      setMindSearchResults(results);
      setMindState("success");
      setMindMessage(results.length ? `Memoria consultada: ${results.length} coincidencia(s) relevantes.` : "No se encontraron coincidencias en la memoria seleccionada.");
    } catch (err) {
      if (!requestCurrent()) return;
      setMindState("error");
      handleMindError(err, "No se pudo consultar la memoria en este momento.");
    }
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

  async function deleteCaseFromHistory(caseId: number, title: string) {
    if (!guardPermission("cases:write", "eliminar casos del historial")) return;
    const confirmed = window.confirm(`¿Eliminar definitivamente el caso "${title}" y sus informes asociados? Esta acción no se puede deshacer.`);
    if (!confirmed) return;
    setLoading(true);
    setError("");
    try {
      await apiDelete(`/cases/${caseId}`);
      if (selectedCaseId === caseId) {
        setSelectedCaseId("");
        await refreshCaseCollections("");
      }
      await refreshCore();
      setModulePayload({ status: "caso_eliminado", case_id: caseId, message: "Caso eliminado del historial." });
    } catch (err) {
      handleUiError(err, "No se pudo eliminar el caso.", { focusIdentity: true });
    } finally {
      setLoading(false);
    }
  }

  async function refreshCybercrime() {
    const requestCurrent = captureCaseContext();
    const caseParam = selectedCaseId ? `?case_id=${selectedCaseId}` : "";
    const [dashboardData, toolsData, labData, proofRowsData, deepfakeData, blockchainData, iotData] = await guardCaseResult(Promise.all([
      apiGet<CybercrimeDashboard>("/cybercrime/dashboard"),
      apiGet<CyberTool[]>("/cybercrime/tools"),
      apiGet<CyberLabSession[]>(`/cybercrime/lab/sessions${caseParam}`),
      selectedCaseId ? apiGet<CyberProofRow[]>(`/cybercrime/proof-matrix${caseParam}`) : Promise.resolve([]),
      selectedCaseId ? apiGet<DeepfakeAnalysisItem[]>(`/cybercrime/deepfake/case/${selectedCaseId}`) : Promise.resolve([]),
      selectedCaseId ? apiGet<BlockchainTransactionItem[]>(`/cybercrime/blockchain/case/${selectedCaseId}`) : Promise.resolve([]),
      selectedCaseId ? apiGet<IoTDeviceItem[]>(`/cybercrime/iot/case/${selectedCaseId}`) : Promise.resolve([])
    ]), requestCurrent);
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
    setLoading(true);
    setError("");
    try {
      const result = await apiPost<{ access_token: string; user: IdentitySession["user"] }>("/identity/login", loginForm);
      setAuthToken(result.access_token);
      setAuthTokenState(result.access_token);
      setIdentitySession({ authenticated: true, user: result.user });
      setLoginForm({ email: "", password: "" });
      setModulePayload({ status: "sesion_iniciada", message: "Sesión iniciada correctamente." });
      setIdentityState("success");
      setIdentityMessage(`Sesión iniciada como ${result.user?.name || result.user?.email || "usuario autorizado"}.`);
      await refreshIdentity();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo iniciar sesión.";
      setIdentityState("error");
      setIdentityMessage(
        message.toLowerCase().includes("credencial")
          ? "Credenciales inválidas. Si no recordás la clave local, usá Recuperar acceso local."
          : extractReadableMessage(message, "No se pudo iniciar sesión.")
      );
      setError(
        message.toLowerCase().includes("credencial")
          ? "Credenciales inválidas. Si no recordás la clave local, usá Recuperar acceso local."
          : extractReadableMessage(message, "No se pudo iniciar sesión.")
      );
    } finally {
      setLoading(false);
    }
  }

  async function bootstrapAdmin(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await apiPost<{ access_token: string; user: IdentitySession["user"] }>("/identity/bootstrap-admin", bootstrapForm);
      setAuthToken(result.access_token);
      setAuthTokenState(result.access_token);
      setIdentitySession({ authenticated: true, user: result.user });
      setModulePayload({ status: "admin_creado", message: "Administrador inicial creado y autenticado." });
      setIdentityState("success");
      setIdentityMessage("Administrador inicial creado. La sesión quedó activa para operar la plataforma.");
      await refreshIdentity();
    } catch (err) {
      const message = extractReadableMessage(err instanceof Error ? err.message : err, "No se pudo crear el administrador inicial.");
      setIdentityState("error");
      setIdentityMessage(message);
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  async function recoverLocalAdmin() {
    setLoading(true);
    setError("");
    try {
      const result = await apiPost<{ access_token: string; user: IdentitySession["user"] }>("/identity/local-admin-recovery", bootstrapForm);
      setAuthToken(result.access_token);
      setAuthTokenState(result.access_token);
      setIdentitySession({ authenticated: true, user: result.user });
      setLoginForm({ email: result.user?.email || "", password: "" });
      setModulePayload({ status: "acceso_local_recuperado", message: "Acceso local recuperado. Sesión iniciada correctamente." });
      setIdentityState("success");
      setIdentityMessage("Acceso local recuperado. Ya podés ejecutar acciones protegidas.");
      await refreshIdentity();
    } catch (err) {
      setIdentityState("error");
      setIdentityMessage(extractReadableMessage(err instanceof Error ? err.message : err, "No se pudo recuperar el acceso local."));
      handleUiError(err, "No se pudo recuperar el acceso local.");
    } finally {
      setLoading(false);
    }
  }

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    setIdentityState("working");
    setIdentityMessage("Guardando perfil del analista...");
    try {
      const updated = await apiPut<IdentityUser>("/identity/me/profile", profileForm);
      setIdentitySession((current) => ({ ...current, authenticated: true, user: updated }));
      setIdentityState("success");
      setIdentityMessage("Perfil del analista actualizado. Estos datos se usarán para firmar acciones e informes.");
      await refreshIdentity();
    } catch (err) {
      setIdentityState("error");
      setIdentityMessage(err instanceof Error ? err.message : "No se pudo guardar el perfil.");
    }
  }

  async function createIdentityUser(event: FormEvent) {
    event.preventDefault();
    setIdentityState("working");
    setIdentityMessage("Creando usuario...");
    try {
      await apiPost<IdentityUser>("/identity/users", newUserForm);
      setNewUserForm({ name: "", email: "", role: "analista", status: "active", title: "", agency: "", password: "OperiaUser2026!" });
      setIdentityState("success");
      setIdentityMessage("Usuario creado correctamente.");
      await refreshIdentity();
    } catch (err) {
      setIdentityState("error");
      setIdentityMessage(err instanceof Error ? err.message : "No se pudo crear el usuario.");
    }
  }

  async function updateIdentityUser(userId: number, changes: Partial<IdentityUser>) {
    setIdentityState("working");
    setIdentityMessage("Actualizando usuario...");
    try {
      await apiPut<IdentityUser>(`/identity/users/${userId}`, changes);
      setIdentityState("success");
      setIdentityMessage("Usuario actualizado correctamente.");
      await refreshIdentity();
    } catch (err) {
      setIdentityState("error");
      setIdentityMessage(err instanceof Error ? err.message : "No se pudo actualizar el usuario.");
    }
  }

  async function resetIdentityPassword(userId: number) {
    const password = passwordDrafts[userId] || "";
    if (password.length < 10) {
      setIdentityState("error");
      setIdentityMessage("La nueva clave debe tener al menos 10 caracteres.");
      return;
    }
    setIdentityState("working");
    setIdentityMessage("Actualizando clave y revocando sesiones anteriores...");
    try {
      await apiPost(`/identity/users/${userId}/reset-password`, { password });
      setPasswordDrafts((current) => ({ ...current, [userId]: "" }));
      setIdentityState("success");
      setIdentityMessage("Clave actualizada. Las sesiones anteriores del usuario fueron revocadas.");
    } catch (err) {
      setIdentityState("error");
      setIdentityMessage(err instanceof Error ? err.message : "No se pudo actualizar la clave.");
    }
  }

  async function logout() {
    await apiPost("/identity/logout", { token: authToken }).catch(() => undefined);
    setAuthToken("");
    setAuthTokenState("");
    setIdentitySession({ authenticated: false });
    setIdentityState("success");
    setIdentityMessage("Sesión cerrada correctamente.");
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
    setCustodyForm({ action_type: "revisión", detailed_description: "", user_responsible: "" });
    setEditingCustody(null);
    setDamageForm(emptyDamageForm);
    setDamageItems([]);
    setDamageState("idle");
    setDamageMessage("");
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
    if (!selectedCaseId || !evidenceFile || !canCase("evidence", "evidence:write")) throw new Error("No tenés permiso para incorporar evidencia.");
    const current = captureCaseContext();
    const params = new URLSearchParams({
      description: evidenceForm.description,
      responsible: evidenceForm.responsible,
      custodian: evidenceForm.custodian
    });
    const form = new FormData();
    form.append("file", evidenceFile);
    await apiPostForm<EvidenceItem>(`/evidence/case/${selectedCaseId}/upload?${params.toString()}`, form);
    if (!current()) return;
    setEvidenceForm({ description: "", responsible: "", custodian: "" });
    setEvidenceFile(null);
    setEvidenceUploadVersion(version => version + 1);
    await refreshCaseCollections(selectedCaseId);
  }

  async function createParticipant(event: FormEvent) {
    event.preventDefault();
    if (!selectedCaseId || !canCase("participants", "cases:write")) throw new Error("No tenés permiso para registrar datos en este expediente.");
    const current = captureCaseContext();
    await apiPost<CaseParticipant>(`/cases/${selectedCaseId}/participants`, participantForm);
    if (!current()) return;
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
    if (!editingParticipant || editingParticipant.case_id !== selectedCaseId || !canCase("participants", "cases:write")) throw new Error("No tenés permiso para guardar este registro.");
    const current = captureCaseContext();
    await apiPut<CaseParticipant>(`/cases/participants/${editingParticipant.id}`, editingParticipant);
    if (!current()) return;
    setEditingParticipant(null);
    await refreshCaseCollections(selectedCaseId);
  }

  async function deleteParticipant(id: number) {
    if (!confirm("?¿¿Eliminar participante del caso?")) return;
    await apiDelete(`/cases/participants/${id}`);
    await refreshCaseCollections(selectedCaseId);
  }

  async function saveEvidence(event: FormEvent) {
    event.preventDefault();
    if (!editingEvidence || editingEvidence.case_id !== selectedCaseId || !canCase("evidence", "evidence:write")) throw new Error("No tenés permiso para guardar este registro.");
    const current = captureCaseContext();
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
    if (!current()) return;
    setEditingEvidence(null);
    await refreshCaseCollections(selectedCaseId);
  }

  async function deleteEvidence(id: number) {
    if (!confirm("¿Eliminar evidencia? Esta acción debe quedar reservada a correcciones controladas.")) return;
    await apiDelete(`/evidence/${id}`);
    await refreshCaseCollections(selectedCaseId);
  }

  async function createCustodyAction(event: FormEvent) {
    event.preventDefault();
    if (!selectedCaseId || !canCase("evidence", "evidence:write")) throw new Error("No tenés permiso para registrar datos en este expediente.");
    const current = captureCaseContext();
    await apiPost("/evidence/custody-actions", {
      ...custodyForm,
      case_id: Number(selectedCaseId),
      evidence_id: latestEvidence?.id,
      hash_after: latestEvidence?.sha256_hash || ""
    });
    if (!current()) return;
    setCustodyForm({ action_type: "revisión", detailed_description: "", user_responsible: "" });
    await refreshCaseCollections(selectedCaseId);
  }

  async function saveCustodyAction(event: FormEvent) {
    event.preventDefault();
    if (!editingCustody || !canCase("evidence", "evidence:write")) throw new Error("No tenés permiso para rectificar custodia.");
    if (!custodyReason.trim() || editingCustody.case_id !== Number(selectedCaseId)) return;
    const caseId = editingCustody.case_id;
    const generation = custodyScope.current.generation;
    const token = getAuthToken();
    try {
      await apiPost<CustodyAction>(`/evidence/custody-actions/${editingCustody.id}/rectifications`, {
        reason: custodyReason,
        changes: { detailed_description: editingCustody.detailed_description, status: editingCustody.status || "registrada" }
      });
      const events = await apiGet<CustodyAction[]>(`/evidence/case/${caseId}/custody-actions`);
      if (custodyScope.current.generation !== generation || getAuthToken() !== token) return;
      setCustody(events);
    } catch (err) {
      if (custodyScope.current.generation !== generation || getAuthToken() !== token) return;
      handleUiError(err, "No se pudo registrar la rectificación. Recargá la cadena si otra revisión fue incorporada.");
      throw err;
    }
    setEditingCustody(null);
    setCustodyReason("");
  }

  async function createDamageItem(event?: FormEvent) {
    event?.preventDefault();
    if (!selectedCaseId) {
      setDamageState("error");
      setDamageMessage("Selecciona o crea un caso antes de cuantificar daño.");
      return;
    }
    const amount = Number(String(damageForm.amount).replace(",", "."));
    if (!damageForm.concept.trim() || !Number.isFinite(amount) || amount <= 0) {
      setDamageState("error");
      setDamageMessage("Completa un concepto y un monto mayor a cero.");
      return;
    }
    setDamageState("saving");
    setDamageMessage("Registrando concepto económico...");
    try {
      await apiPost<DamageItem>(`/cases/${selectedCaseId}/damage-items`, {
        case_id: Number(selectedCaseId),
        concept: damageForm.concept.trim(),
        amount,
        currency: damageForm.currency || "ARS",
        base_date: damageForm.base_date,
        value_source: damageForm.value_source,
        formula_used: damageForm.formula_used,
        supporting_evidence: damageForm.supporting_evidence,
        certainty_level: damageForm.certainty_level,
        observations: damageForm.observations
      });
      setDamageForm(emptyDamageForm);
      setDamageState("saved");
      setDamageMessage("Daño económico incorporado al caso. Regenera el informe para reflejar el nuevo total.");
      await refreshCaseCollections(selectedCaseId);
    } catch (err) {
      setDamageState("error");
      setDamageMessage(err instanceof Error ? err.message : "No se pudo registrar el daño económico.");
    }
  }

  function applyDamagePreset(preset: (typeof damagePresets)[number]) {
    setDamageForm((current) => ({
      ...current,
      concept: preset.concept,
      formula_used: preset.formula_used,
      value_source: current.value_source || preset.value_source
    }));
    setDamageState("idle");
    setDamageMessage("");
  }

  async function analyzeIndicator() {
    const requestCurrent = captureCaseContext();
    setIndicatorFindingState("idle");
    setIndicatorFindingMessage("");
    setIndicatorResult(await guardCaseResult(apiPost("/cybercrime/analyze-indicator", { case_id: selectedCaseId || undefined, indicator }), requestCurrent));
    if (selectedCaseId) await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
    await guardCaseResult(refreshCybercrime(), requestCurrent);
  }

  async function saveIndicatorAsFinding() {
    const requestCurrent = captureCaseContext();
    if (!selectedCaseId || !indicatorResult) return;
    setIndicatorFindingState("saving");
    setIndicatorFindingMessage("Guardando hallazgo tecnico en el caso...");
    try {
      const saved = await guardCaseResult(apiPost<{ id: number }>(`/cases/${selectedCaseId}/findings`, {
        case_id: selectedCaseId,
        evidence_id: latestEvidence?.id,
        title: `Indicador ${prettySpanish(indicatorResult.indicator_type)} analizado`,
        technical_finding: indicatorResult.findings.join("\n"),
        explanation: `El indicador ${indicatorResult.indicator} fue clasificado con riesgo ${prettySpanish(indicatorResult.risk_level)} y confianza ${prettySpanish(indicatorResult.confidence)}.`,
        confidence_level: indicatorResult.confidence,
        weaknesses_or_limitations: "El análisis de indicador no prueba autoría por sí solo; requiere correlación con evidencia preservada, fuentes externas verificables y revisión humana.",
        tools_used: "OPERIA Cybercrime Indicator Analyzer",
        supporting_evidence: latestEvidence ? `Evidencia #${latestEvidence.id}: ${latestEvidence.description}` : "Pendiente de vincular con evidencia preservada.",
        preliminary_legal_relevance: indicatorResult.legal_relevance,
        status: "validado"
      }), requestCurrent);
      await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
      setIndicatorFindingState("saved");
      setIndicatorFindingMessage(`Hallazgo #${saved.id} incorporado al caso y disponible para informe.`);
      setModulePayload({ status: "hallazgo_guardado", finding_id: saved.id, indicator: indicatorResult.indicator, case_id: selectedCaseId });
    } catch (error) {
      if (!requestCurrent()) return;
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
    const requestCurrent = captureCaseContext();
    event.preventDefault();
    if (!selectedCaseId) {
      setError("Selecciona un caso antes de crear una sesión cybercrime.");
      return;
    }
    await guardCaseResult(apiPost<CyberLabSession>("/cybercrime/lab/sessions", {
      ...cyberLabForm,
      case_id: Number(selectedCaseId),
      operator: cyberLabForm.operator || analystName || identitySession.user?.name || "Analista local",
      title: cyberLabForm.title || `Análisis cybercrime - ${indicator}`
    }), requestCurrent);
    setCyberLabForm({ title: "", purpose: "análisis de indicador", risk_level: "medio", operator: "" });
    await guardCaseResult(refreshCybercrime(), requestCurrent);
  }

  async function createCyberProofRow(event: FormEvent) {
    const requestCurrent = captureCaseContext();
    event.preventDefault();
    if (!selectedCaseId) {
      setError("Selecciona un caso antes de guardar una conclusión cybercrime.");
      return;
    }
    await guardCaseResult(apiPost<CyberProofRow>("/cybercrime/proof-matrix", {
      ...cyberProofForm,
      case_id: Number(selectedCaseId),
      defensible_conclusion:
        cyberProofForm.defensible_conclusion ||
        `El indicador ${indicator} fue clasificado como ${indicatorResult?.indicator_type || "dato técnico"} con riesgo ${indicatorResult?.risk_level || "medio"}.`,
      legal_framing: cyberProofForm.legal_framing || "Requiere vinculación con evidencia preservada y encuadre legal aprobado por analista."
    }), requestCurrent);
    setCyberProofForm({ defensible_conclusion: "", legal_framing: "", confidence_level: "medio", weakness: "" });
    await guardCaseResult(refreshCybercrime(), requestCurrent);
  }

  async function saveDeepfakeAnalysis(event: FormEvent) {
    const requestCurrent = captureCaseContext();
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
      await guardCaseResult(apiPost<DeepfakeAnalysisItem>("/cybercrime/deepfake", {
        ...deepfakeForm,
        case_id: Number(selectedCaseId),
        evidence_id: deepfakeForm.evidence_id ? Number(deepfakeForm.evidence_id) : undefined,
        evidence_hash: selectedEvidence?.sha256_hash || "",
        source_origin: deepfakeForm.source_origin || selectedEvidence?.source || selectedEvidence?.file_location || "",
        checklist: deepfakeChecklistState,
        analyst_name: analystName || identitySession.user?.name || "Analista local"
      }), requestCurrent);
      setDeepfakeForm(emptyDeepfakeForm);
      setDeepfakeChecklistState(emptyDeepfakeChecklist);
      setDeepfakeState("saved");
      setDeepfakeMessage("Análisis guardado y vinculado al caso.");
      await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
      await guardCaseResult(refreshCybercrime(), requestCurrent);
    } catch (error) {
      if (!requestCurrent()) return;
      setDeepfakeState("error");
      setDeepfakeMessage(error instanceof Error ? error.message : "No se pudo guardar el análisis.");
    }
  }

  async function createDeepfakeFinding(analysisId: number) {
    const requestCurrent = captureCaseContext();
    setDeepfakeState("saving");
    setDeepfakeMessage("Creando hallazgo técnico...");
    try {
      const result = await guardCaseResult(apiPost<{ id: number; message: string }>(`/cybercrime/deepfake/${analysisId}/finding`), requestCurrent);
      setDeepfakeState("saved");
      setDeepfakeMessage(result.message || `Hallazgo #${result.id} creado.`);
      if (selectedCaseId) await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
      await guardCaseResult(refreshCybercrime(), requestCurrent);
    } catch (error) {
      if (!requestCurrent()) return;
      setDeepfakeState("error");
      setDeepfakeMessage(error instanceof Error ? error.message : "No se pudo crear el hallazgo.");
    }
  }

  async function applyDeepfakeLegal(analysis: DeepfakeAnalysisItem) {
    const requestCurrent = captureCaseContext();
    setDeepfakeState("saving");
    setDeepfakeMessage("Aplicando normas sugeridas...");
    try {
      const text = `${analysis.media_type} ${analysis.findings} ${analysis.legal_relevance}`.toLowerCase();
      const result = await guardCaseResult(apiPost<{ applied: Array<{ norm_reference: string }> }>(`/cybercrime/deepfake/${analysis.id}/apply-legal`, {
        analyst_name: analystName || identitySession.user?.name || "Analista local",
        fraud: text.includes("fraude") || text.includes("estafa") || text.includes("transferencia"),
        document_falsity: analysis.media_type === "documento" || text.includes("documento") || text.includes("certificado"),
        honor_affectation: text.includes("honor") || text.includes("reputación") || text.includes("reputacion"),
        personal_data: true,
        intellectual_property: true
      }), requestCurrent);
      setDeepfakeState("saved");
      setDeepfakeMessage(`Normas aplicadas: ${result.applied.map((item) => item.norm_reference).join(", ") || "sin nuevas normas"}.`);
      if (selectedCaseId) await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
      await guardCaseResult(refreshCybercrime(), requestCurrent);
    } catch (error) {
      if (!requestCurrent()) return;
      setDeepfakeState("error");
      setDeepfakeMessage(error instanceof Error ? error.message : "No se pudieron aplicar las normas.");
    }
  }

  async function saveBlockchainTransaction(event: FormEvent) {
    const requestCurrent = captureCaseContext();
    event.preventDefault();
    if (!selectedCaseId) {
      setBlockchainState("error");
      setBlockchainMessage("Selecciona un caso antes de registrar la transacción.");
      return;
    }
    setBlockchainState("saving");
    setBlockchainMessage(editingBlockchainId ? "Actualizando salto blockchain..." : "Registrando transacción blockchain...");
    try {
      const selectedEvidence = evidence.find((item) => item.id === Number(blockchainForm.evidence_id));
      const payload = {
        ...blockchainForm,
        case_id: Number(selectedCaseId),
        evidence_id: blockchainForm.evidence_id ? Number(blockchainForm.evidence_id) : undefined,
        amount: Number(blockchainForm.amount || 0),
        approximate_value: Number(blockchainForm.approximate_value || 0),
        route_order: Number(blockchainForm.route_order || blockchainTransactions.length + 1),
        include_in_report: Boolean(blockchainForm.include_in_report),
        preservation_checklist: blockchainDraftReadiness(blockchainForm).checks
          .map((check) => `${check.ok ? "OK" : "PENDIENTE"}: ${check.label}`)
          .join("\n"),
        evidence_hash: selectedEvidence?.sha256_hash || "",
        analyst_name: analystName || identitySession.user?.name || "Analista local"
      };
      if (editingBlockchainId) {
        await guardCaseResult(apiPatch<BlockchainTransactionItem>(`/cybercrime/blockchain/${editingBlockchainId}`, payload), requestCurrent);
      } else {
        await guardCaseResult(apiPost<BlockchainTransactionItem>("/cybercrime/blockchain", payload), requestCurrent);
      }
      setBlockchainForm(emptyBlockchainForm);
      setEditingBlockchainId(null);
      setBlockchainState("saved");
      setBlockchainMessage(editingBlockchainId ? "Salto blockchain actualizado y asentado en custodia." : "Transacción registrada con límites de atribución.");
      await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
      await guardCaseResult(refreshCybercrime(), requestCurrent);
    } catch (error) {
      if (!requestCurrent()) return;
      setBlockchainState("error");
      setBlockchainMessage(error instanceof Error ? error.message : "No se pudo registrar la transacción.");
    }
  }

  function editBlockchainTransaction(transaction: BlockchainTransactionItem) {
    setEditingBlockchainId(transaction.id);
    setBlockchainForm({
      evidence_id: transaction.evidence_id ? String(transaction.evidence_id) : "",
      source_wallet: transaction.source_wallet || "",
      destination_wallet: transaction.destination_wallet || "",
      tx_hash: transaction.tx_hash || "",
      blockchain: transaction.blockchain || "Bitcoin",
      token: transaction.token || "BTC",
      amount: String(transaction.amount || ""),
      approximate_value: String(transaction.approximate_value || ""),
      tx_datetime: transaction.tx_datetime || "",
      explorer_url: transaction.explorer_url || "",
      route_hypothesis: transaction.route_hypothesis || "",
      wallet_classification: transaction.wallet_classification || "desconocido",
      tool_used: transaction.tool_used || "OPERIA Blockchain Investigation Lab",
      route_order: String(transaction.route_order || ""),
      include_in_report: transaction.include_in_report !== false,
      preservation_checklist: transaction.preservation_checklist || "",
      limitations: transaction.limitations || "Una wallet no identifica por sí sola a una persona sin evidencia externa corroborante."
    });
    setBlockchainState("idle");
    setBlockchainMessage(`Editando salto blockchain #${transaction.id}. Al guardar, se actualizará el registro y se asentará custodia.`);
  }

  function cancelBlockchainEdit() {
    setEditingBlockchainId(null);
    setBlockchainForm(emptyBlockchainForm);
    setBlockchainState("idle");
    setBlockchainMessage("");
  }

  async function toggleBlockchainReportInclusion(transaction: BlockchainTransactionItem) {
    const requestCurrent = captureCaseContext();
    if (!selectedCaseId) return;
    setBlockchainState("saving");
    setBlockchainMessage(transaction.include_in_report ? "Excluyendo salto del informe..." : "Incorporando salto al informe...");
    try {
      await guardCaseResult(apiPatch<BlockchainTransactionItem>(`/cybercrime/blockchain/${transaction.id}`, {
        ...transaction,
        include_in_report: !transaction.include_in_report,
        evidence_id: transaction.evidence_id || undefined
      }), requestCurrent);
      setBlockchainState("saved");
      setBlockchainMessage(!transaction.include_in_report ? "Salto incorporado al informe final." : "Salto excluido del informe final. Permanece en el laboratorio.");
      await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
      await guardCaseResult(refreshCybercrime(), requestCurrent);
    } catch (error) {
      if (!requestCurrent()) return;
      setBlockchainState("error");
      setBlockchainMessage(error instanceof Error ? error.message : "No se pudo actualizar la inclusión en informe.");
    }
  }

  async function createBlockchainFinding(transactionId: number) {
    const requestCurrent = captureCaseContext();
    setBlockchainState("saving");
    setBlockchainMessage("Creando hallazgo blockchain...");
    try {
      const result = await guardCaseResult(apiPost<{ id: number; message: string }>(`/cybercrime/blockchain/${transactionId}/finding`), requestCurrent);
      setBlockchainState("saved");
      setBlockchainMessage(result.message || `Hallazgo #${result.id} creado.`);
      if (selectedCaseId) await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
      await guardCaseResult(refreshCybercrime(), requestCurrent);
    } catch (error) {
      if (!requestCurrent()) return;
      setBlockchainState("error");
      setBlockchainMessage(error instanceof Error ? error.message : "No se pudo crear el hallazgo.");
    }
  }

  async function applyBlockchainLegal(transaction: BlockchainTransactionItem) {
    const requestCurrent = captureCaseContext();
    setBlockchainState("saving");
    setBlockchainMessage("Aplicando normas registradas...");
    try {
      const text = `${transaction.route_hypothesis} ${transaction.wallet_classification} ${transaction.blockchain}`.toLowerCase();
      const result = await guardCaseResult(apiPost<{ applied: Array<{ norm_reference: string }> }>(`/cybercrime/blockchain/${transaction.id}/apply-legal`, {
        analyst_name: analystName || identitySession.user?.name || "Analista local",
        fraud: text.includes("estafa") || text.includes("fraude") || text.includes("phishing"),
        computer_manipulation: text.includes("manipulación") || text.includes("manipulacion") || text.includes("contrato inteligente"),
        extortion: text.includes("extorsión") || text.includes("extorsion") || text.includes("ransomware"),
        blackmail: text.includes("chantaje"),
        personal_data: text.includes("exchange") || text.includes("cuenta") || text.includes("kyc")
      }), requestCurrent);
      setBlockchainState("saved");
      setBlockchainMessage(`Normas aplicadas: ${result.applied.map((item) => item.norm_reference).join(", ") || "sin nuevas normas"}.`);
      if (selectedCaseId) await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
      await guardCaseResult(refreshCybercrime(), requestCurrent);
    } catch (error) {
      if (!requestCurrent()) return;
      setBlockchainState("error");
      setBlockchainMessage(error instanceof Error ? error.message : "No se pudieron aplicar las normas.");
    }
  }

  async function saveIoTDevice(event: FormEvent) {
    const requestCurrent = captureCaseContext();
    event.preventDefault();
    if (!selectedCaseId) {
      setIotState("error");
      setIotMessage("Selecciona un caso antes de registrar el dispositivo.");
      return;
    }
    setIotState("saving");
    setIotMessage(editingIotId ? "Actualizando ficha IoT..." : "Registrando dispositivo IoT...");
    try {
      const selectedEvidence = evidence.find((item) => item.id === Number(iotForm.evidence_id));
      const payload = {
        ...iotForm,
        case_id: Number(selectedCaseId),
        evidence_id: iotForm.evidence_id ? Number(iotForm.evidence_id) : undefined,
        evidence_hash: selectedEvidence?.sha256_hash || "",
        checklist: iotChecklistState,
        analyst_name: analystName || identitySession.user?.name || "Analista local"
      };
      if (editingIotId) {
        await guardCaseResult(apiPatch<IoTDeviceItem>(`/cybercrime/iot/${editingIotId}`, payload), requestCurrent);
      } else {
        await guardCaseResult(apiPost<IoTDeviceItem>("/cybercrime/iot", payload), requestCurrent);
      }
      setIotForm(emptyIoTForm);
      setEditingIotId(null);
      setIotChecklistState(emptyIoTChecklist);
      setIotState("saved");
      setIotMessage(editingIotId ? "Ficha IoT actualizada y asentada en custodia." : "Dispositivo IoT registrado con metodología y límites.");
      await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
      await guardCaseResult(refreshCybercrime(), requestCurrent);
    } catch (error) {
      if (!requestCurrent()) return;
      setIotState("error");
      setIotMessage(error instanceof Error ? error.message : "No se pudo registrar el dispositivo.");
    }
  }

  function editIoTDevice(device: IoTDeviceItem) {
    setEditingIotId(device.id);
    setIotForm({
      evidence_id: device.evidence_id ? String(device.evidence_id) : "",
      device_type: device.device_type || "cámara IP",
      manufacturer: device.manufacturer || "",
      model: device.model || "",
      firmware: device.firmware || "",
      internal_ip: device.internal_ip || "",
      external_ip: device.external_ip || "",
      mac: device.mac || "",
      open_ports: device.open_ports || "",
      known_vulnerabilities: device.known_vulnerabilities || "",
      logs_available: device.logs_available || "",
      tool_used: device.tool_used || "OPERIA IoT Forensics",
      limitations: device.limitations || "No se ejecutaron escaneos reales. Requiere autorización, preservación de estado y correlación externa."
    });
    setIotChecklistState(Object.fromEntries(device.checklist.map((item) => [item.key, Boolean(item.ok)])) as Record<string, boolean>);
    setIotState("idle");
    setIotMessage(`Editando ficha IoT #${device.id}. Guardar asentará la actualización en custodia.`);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function createIoTFinding(deviceId: number) {
    const requestCurrent = captureCaseContext();
    setIotState("saving");
    setIotMessage("Creando hallazgo IoT...");
    try {
      const result = await guardCaseResult(apiPost<{ id: number; message: string }>(`/cybercrime/iot/${deviceId}/finding`), requestCurrent);
      setIotState("saved");
      setIotMessage(result.message || `Hallazgo #${result.id} creado.`);
      if (selectedCaseId) await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
      await guardCaseResult(refreshCybercrime(), requestCurrent);
    } catch (error) {
      if (!requestCurrent()) return;
      setIotState("error");
      setIotMessage(error instanceof Error ? error.message : "No se pudo crear el hallazgo.");
    }
  }

  async function applyIoTLegal(device: IoTDeviceItem) {
    const requestCurrent = captureCaseContext();
    setIotState("saving");
    setIotMessage("Aplicando normas registradas...");
    try {
      const text = `${device.known_vulnerabilities} ${device.logs_available} ${device.open_ports} ${device.device_type}`.toLowerCase();
      const result = await guardCaseResult(apiPost<{ applied: Array<{ norm_reference: string }> }>(`/cybercrime/iot/${device.id}/apply-legal`, {
        analyst_name: analystName || identitySession.user?.name || "Analista local",
        unauthorized_access: text.includes("acceso") || text.includes("credencial") || text.includes("puerto"),
        damage: text.includes("daño") || text.includes("dano") || text.includes("malware") || text.includes("alter"),
        public_systems: text.includes("servicio") || text.includes("infraestructura") || text.includes("publico"),
        communications_interruption: text.includes("interrup") || text.includes("red") || text.includes("comunicacion"),
        personal_data: text.includes("camara") || text.includes("audio") || text.includes("usuario")
      }), requestCurrent);
      setIotState("saved");
      setIotMessage(`Normas aplicadas: ${result.applied.map((item) => item.norm_reference).join(", ") || "sin nuevas normas"}.`);
      if (selectedCaseId) await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
      await guardCaseResult(refreshCybercrime(), requestCurrent);
    } catch (error) {
      if (!requestCurrent()) return;
      setIotState("error");
      setIotMessage(error instanceof Error ? error.message : "No se pudieron aplicar las normas.");
    }
  }

  async function searchLegal() {
    const requestCurrent = captureCaseContext();
    const [found, recommended] = await guardCaseResult(Promise.all([
      apiGet<LegalArticle[]>(`/legal-knowledge/articles?q=${encodeURIComponent(legalQuery)}`),
      apiPost<LegalRecommendationResponse>("/legal-knowledge/articles/recommend", { incident_text: legalQuery })
    ]), requestCurrent);
    setArticles(found);
    setLegalRecommendation(recommended);
  }

  async function decideLegalRecommendation(item: LegalRecommendation, decision_status: "aprobado" | "descartado") {
    const requestCurrent = captureCaseContext();
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
      await guardCaseResult(apiPost<LegalMapping>("/legal-knowledge/mappings/decision", {
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
      }), requestCurrent);
      await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
      setLegalApplyState("applied");
      setLegalApplyMessage(`${item.reference} ${decision_status === "aprobado" ? "aplicada" : "descartada"} para el caso seleccionado.`);
    } catch (error) {
      if (!requestCurrent()) return;
      setLegalApplyState("error");
      setLegalApplyMessage(error instanceof Error ? error.message : "No se pudo actualizar el encuadre legal.");
    }
  }

  async function changeLegalMappingDecision(mapping: LegalMapping, decision_status: "aprobado" | "descartado") {
    const requestCurrent = captureCaseContext();
    if (!selectedCaseId || !mapping.article_id) return;
    await guardCaseResult(apiPost<LegalMapping>("/legal-knowledge/mappings/decision", {
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
    }), requestCurrent);
    await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
  }

  function legalElementsForMapping(mappingId: number) {
    const elements = legalProbatoryMatrix?.rows
      .filter((row) => row.mapping_id === mappingId)
      .map((row) => row.legal_element)
      .filter(Boolean) || [];
    return Array.from(new Set(elements));
  }

  async function linkEvidenceToLegalMapping(mapping: LegalMapping) {
    const requestCurrent = captureCaseContext();
    if (!selectedCaseId) return;
    const evidenceId = Number(legalEvidenceSelection[mapping.id] || evidence[0]?.id || 0);
    if (!evidenceId) {
      setError("Carga o selecciona una evidencia antes de vincularla a una norma.");
      return;
    }
    await guardCaseResult(apiPost<LegalMappingEvidence>("/legal-knowledge/mappings/evidence", {
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
      recommended_measure: "Corroborar con fuentes externas si se pretende atribución personal."
    }), requestCurrent);
    await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
  }

  async function saveLegalLink(link: LegalMappingEvidence) {
    const requestCurrent = captureCaseContext();
    if (!selectedCaseId) return;
    const draft = legalLinkDrafts[link.id] || {};
    await guardCaseResult(apiPut<LegalMappingEvidence>(`/legal-knowledge/mappings/evidence/${link.id}`, {
      ...link,
      ...draft,
      case_id: selectedCaseId
    }), requestCurrent);
    setLegalLinkDrafts((current) => {
      const next = { ...current };
      delete next[link.id];
      return next;
    });
    await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
  }

  async function unlinkLegalEvidence(linkId: number) {
    const requestCurrent = captureCaseContext();
    if (!confirm("Quitar esta evidencia del encuadre legal? La evidencia no se borra; solo se deshace el vinculo juridico.")) return;
    await guardCaseResult(apiDelete(`/legal-knowledge/mappings/evidence/${linkId}`), requestCurrent);
    await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
  }

  async function runAiAssist() {
    const requestCurrent = captureCaseContext();
    if (latestReport) {
      const enriched = await guardCaseResult(apiPost<ReportItem>(`/reports/${latestReport.id}/ai-enrich`, {
        case_id: selectedCaseId || undefined,
        prompt: aiPrompt
      }), requestCurrent);
      const result = {
        status: enriched.status,
        report_id: enriched.id,
        message: "Informe ampliado con análisis tecnico-juridico. Revisa y vuelve a exportar PDF.",
        observations: enriched.observations
      };
      setAiEnrichmentResult(result);
      setAiResult(result);
      if (selectedCaseId) await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
      await guardCaseResult(loadReportPreview(enriched.id), requestCurrent);
      return;
    }
    if (selectedCaseId) {
      const result = await guardCaseResult(apiPost<CaseAnalysisResult>(`/ai/case/${selectedCaseId}/recommendations`, { focus: aiPrompt }), requestCurrent);
      setAiEnrichmentResult(null);
      setAiResult(result);
      return;
    }
    const result = await guardCaseResult(apiPost<CaseAnalysisResult>("/ai/assist", { model_name: "mistral", prompt: aiPrompt }), requestCurrent);
    setAiEnrichmentResult(null);
    setAiResult(result);
  }

  async function generateReport() {
    if (!canCase("reports", "reports:write")) throw new Error("No tenés permiso para esta operación de informes.");
    const current = captureCaseContext();
    if (!selectedCaseId) return;
    if (!guardPermission("reports:write", "generar informes")) return;
    localStorage.setItem("operia_analyst_name", analystName);
    const author = encodeURIComponent(analystName.trim());
    const report = await apiPost<ReportItem>(`/reports/case/${selectedCaseId}/generate?author=${author}`);
    if (!current()) return;
    await refreshCaseCollections(selectedCaseId);
    if (!current()) return;
    setReviewResult({ generated_report_id: report.id, status: "generated" });
  }

  async function generateReportFromCtfDashboard() {
    if (!guardPermission("reports:write", "generar informes desde el dashboard CTF")) return;
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
    const targetReport = reports.find(item => item.id === (reportPreview?.report_id ?? latestReport?.id) && item.case_id === selectedCaseId);
    if (!canCase("review", "reports:write")) throw new Error("No tenés permiso para esta operación de informes.");
    const current = captureCaseContext();
    if (!targetReport) return;
    if (!guardPermission("reports:write", "revisar informes")) return;
    const result = await apiPost<ReportReviewResult>(`/reports/${targetReport.id}/review`);
    if (!current()) return;
    setReviewAudit(result);
    if (!current()) return;
    setReviewResult(result);
    if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
    if (!current()) return;
    await loadReportPreview(targetReport.id);
  }

  async function loadReportPreview(reportId = latestReport?.id) {
    if (!reportId || !canCase("read", "reports:read") || !reports.some(item => item.id === reportId && item.case_id === selectedCaseId)) return;
    const current = captureCaseContext();
    const preview = await apiGet<ReportPreview>(`/reports/${reportId}/preview`);
    if (!current()) return;
    setReportPreview(preview); setExecutiveSummaryDraft(preview.executive_summary);
  }

  async function promoteBlockchainTransaction(transaction: BlockchainTransactionItem) {
    const requestCurrent = captureCaseContext();
    setBlockchainState("saving");
    setBlockchainMessage("Convirtiendo la transacción en hallazgo y aplicando normas...");
    try {
      await guardCaseResult(apiPost<{ id: number; message: string }>(`/cybercrime/blockchain/${transaction.id}/finding`), requestCurrent);
      const text = `${transaction.route_hypothesis} ${transaction.wallet_classification} ${transaction.blockchain}`.toLowerCase();
      const result = await guardCaseResult(apiPost<{ applied: Array<{ norm_reference: string }> }>(`/cybercrime/blockchain/${transaction.id}/apply-legal`, {
        fraud: ["fraude", "estafa", "phishing"].some((term) => text.includes(term)),
        computer_manipulation: ["contrato inteligente", "smart contract", "sistema", "manipulacion"].some((term) => text.includes(term)),
        extortion: ["extorsion", "ransomware", "rescate"].some((term) => text.includes(term)),
        personal_data: ["exchange", "kyc", "cuenta", "datos"].some((term) => text.includes(term)),
        analyst_name: analystName || identitySession.user?.name || "Analista Local"
      }), requestCurrent);
      setBlockchainState("saved");
      setBlockchainMessage(`Listo: hallazgo creado y normas aplicadas (${result.applied.map((item) => item.norm_reference).join(", ") || "sin nuevas normas"}). Ya puede aparecer en el informe del caso.`);
      if (selectedCaseId) await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
    } catch (error) {
      if (!requestCurrent()) return;
      setBlockchainState("error");
      setBlockchainMessage(error instanceof Error ? error.message : "No se pudo completar la promoción a hallazgo.");
    }
  }

  async function loadPresentationSlides(presentationId: number | "") {
    const requestCurrent = captureCaseContext();
    setSelectedPresentationId(presentationId);
    setPresentationReview(null);
    if (!presentationId) {
      setPresentationSlides([]);
      return;
    }
    const slides = await guardCaseResult(apiGet<PresentationSlide[]>(`/reports/presentations/${presentationId}/slides`), requestCurrent);
    setPresentationSlides(slides);
  }

  async function generateCasePresentation() {
    const requestCurrent = captureCaseContext();
    if (!latestReport || !selectedCaseId) {
      setPresentationState("error");
      setPresentationMessage("Genera primero un informe del caso para construir la exposición.");
      return;
    }
    setPresentationState("working");
    setPresentationMessage("Preparando guion, diapositivas y notas de exposición...");
    try {
      const presentation = await guardCaseResult(apiPost<PresentationItem>(
        `/reports/${latestReport.id}/presentations/generate?presentation_type=${encodeURIComponent("Exposición ejecutiva del caso")}`
      ), requestCurrent);
      const updated = await guardCaseResult(apiGet<PresentationItem[]>(`/reports/presentations/case/${selectedCaseId}`), requestCurrent);
      setPresentations(updated);
      await guardCaseResult(loadPresentationSlides(presentation.id), requestCurrent);
      setPresentationState("success");
      setPresentationMessage("Exposición generada. Revisa las diapositivas y las notas antes de presentarla.");
    } catch (err) {
      if (!requestCurrent()) return;
      setPresentationState("error");
      setPresentationMessage(err instanceof Error ? err.message : "No se pudo generar la exposición.");
    }
  }

  async function reviewCasePresentation() {
    const requestCurrent = captureCaseContext();
    if (!selectedPresentationId) return;
    setPresentationState("working");
    setPresentationMessage("Revisando claridad, fuerza probatoria, narrativa y solidez legal...");
    try {
      const review = await guardCaseResult(apiPost<PresentationReview>(`/reports/presentations/${selectedPresentationId}/review`), requestCurrent);
      setPresentationReview(review);
      setPresentationState("success");
      setPresentationMessage("Revisión de exposición completada.");
      if (selectedCaseId) await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
    } catch (err) {
      if (!requestCurrent()) return;
      setPresentationState("error");
      setPresentationMessage(err instanceof Error ? err.message : "No se pudo revisar la exposición.");
    }
  }

  async function updatePresentationSlide(slide: PresentationSlide, changes: Partial<PresentationSlide>) {
    const requestCurrent = captureCaseContext();
    const updated = await guardCaseResult(apiPut<PresentationSlide>(`/reports/presentation-slides/${slide.id}`, {
      slide_number: slide.slide_number,
      title: slide.title,
      text: slide.text,
      speaker_notes: slide.speaker_notes,
      confidentiality_level: slide.confidentiality_level,
      content_type: slide.content_type,
      ...changes
    }), requestCurrent);
    setPresentationSlides((current) => current.map((item) => (item.id === updated.id ? updated : item)));
  }

  async function updateRubricEvaluation() {
    if (!guardPermission("reports:write", "evaluar la rúbrica del caso")) return;
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
    if (!guardPermission("reports:write", "evaluar la rúbrica CTF")) return;
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
    void runCaseTask("Descargar informe", () => downloadReport(latestReport.id));
    setCtfDashboardState("success");
    setCtfDashboardMessage("Exportación PDF iniciada. El manifiesto queda registrado por el backend.");
  }

  async function saveExecutiveSummary() {
    const targetReport = reports.find(item => item.id === (reportPreview?.report_id ?? latestReport?.id) && item.case_id === selectedCaseId);
    if (!canCase("reports", "reports:write")) throw new Error("No tenés permiso para esta operación de informes.");
    const current = captureCaseContext();
    if (!targetReport || !executiveSummaryDraft.trim()) return;
    const updated = await apiPut<ReportItem>(`/reports/${targetReport.id}/executive-summary`, {
      executive_summary: executiveSummaryDraft,
      author: analystName || targetReport.author
    });
    if (!current()) return;
    setReviewResult({ status: "executive_summary_updated", report_id: updated.id });
    if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
    if (!current()) return;
    await loadReportPreview(updated.id);
  }

  async function requestFinalExport() {
    const targetReport = reports.find(item => item.id === (reportPreview?.report_id ?? latestReport?.id) && item.case_id === selectedCaseId);
    if (!targetReport || !canCase("export", "reports:read") || !canCase("approve", "reports:write")) throw new Error("Se requieren permisos de aprobación y exportación.");
    const current = captureCaseContext();
    if (!guardPermission("reports:write", "sellar y exportar el informe final")) return;
    setError("");
    try {
      const readiness = await apiGet<ExportOutcome>(
        `/reports/${targetReport.id}/exportability`
      );
      if (!current()) return;
      setExportFinalResult(readiness);
      if (!readiness.can_export_final) return;
      const response = await fetch(`${API_BASE}/exports/reports/${targetReport.id}/pdf/seal-final`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          analyst_name: analystName || targetReport.author,
          declaration: "Cierre pericial final con checklist verificado, anexos incorporados y exportación sellada."
        })
      });
      if (!current()) return;
      if (!response.ok) {
        const outcome = await readExportOutcome(response);
        if (current()) setExportFinalResult(outcome);
        return;
      }
      const blob = await response.blob();
      if (!current()) return;
      const url = URL.createObjectURL(blob);
      setExportFinalResult({
        status: "sealed",
        seal_id: response.headers.get("x-operia-seal-id"),
        sha256: response.headers.get("x-operia-sha256"),
        manifest_id: response.headers.get("x-operia-export-manifest-id")
      });
      const link = document.createElement("a"); link.href = url; link.download = `operia-final-${targetReport.id}.pdf`; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
      if (current()) await loadReportPreview(targetReport.id);
    } catch (error) {
      if (!current()) return;
      const message = error instanceof Error ? error.message : "No se pudo evaluar la exportación final.";
      setExportFinalResult({ status: "blocked", message: extractReadableMessage(message, "No se pudo evaluar la exportación final.") });
      handleUiError(error, message, { focusIdentity: true });
    }
  }

  async function runCaseRecommendations() {
    const requestCurrent = captureCaseContext();
    if (!selectedCaseId) return;
    setAiResult(await guardCaseResult(apiPost(`/ai/case/${selectedCaseId}/recommendations`, { focus: aiPrompt }), requestCurrent));
  }

  async function runLegalTypification(createSuggestions = false, focusOverride?: string) {
    const requestCurrent = captureCaseContext();
    if (!selectedCaseId) {
      setError("Selecciona un caso antes de tipificar el incidente.");
      return;
    }
    setLegalApplyState(createSuggestions ? "applying" : "idle");
    setLegalApplyMessage(createSuggestions ? "Aplicando tipificación al caso..." : "");
    try {
      const result = await guardCaseResult(apiPost<LegalTypificationResult>(`/ai/case/${selectedCaseId}/legal-typification`, {
        focus: focusOverride || aiPrompt,
        create_suggestions: createSuggestions,
        analyst_name: analystName
      }), requestCurrent);
      setLegalTypification(result);
      if (createSuggestions) {
        await guardCaseResult(refreshCaseCollections(selectedCaseId), requestCurrent);
        setLegalApplyState("applied");
        setLegalApplyMessage(
          result.suggested_mapping_ids.length
            ? `Tipificación aplicada: ${result.suggested_mapping_ids.length} norma(s) sugerida(s) incorporada(s) al caso.`
            : "La tipificación ya estaba incorporada al caso; no se duplicaron normas."
        );
      }
    } catch (error) {
      if (!requestCurrent()) return;
      const message = error instanceof Error ? error.message : "No se pudo aplicar la tipificación al caso.";
      setLegalApplyState("error");
      setLegalApplyMessage(message);
    }
  }

  async function searchAndTypifyLegal(createSuggestions = false) {
    const requestCurrent = captureCaseContext();
    await guardCaseResult(searchLegal(), requestCurrent);
    if (selectedCaseId) {
      await guardCaseResult(runLegalTypification(createSuggestions, legalQuery), requestCurrent);
    }
  }

  async function verifyEvidenceIntegrity(evidenceId: number) {
    if (!canCase("evidence", "evidence:write") || !evidence.some(item => item.id === evidenceId && item.case_id === selectedCaseId)) throw new Error("No tenés permiso para verificar esta evidencia.");
    const current = captureCaseContext();
    const result = await apiGet<{ ok: boolean; message?: string; integrity_status?: string }>(`/evidence/${evidenceId}/integrity`);
    if (!current()) return;
    await refreshCaseCollections(selectedCaseId);
    if (!current()) return;
    if (!result.ok) throw new Error(result.message || "La verificación detectó una diferencia de integridad.");
    setCaseFeedback(`Evidencia ${evidenceId}: integridad verificada por la API.`);
  }

  async function refreshReportAnnexes() {
    const targetReport = reports.find(item => item.id === (reportPreview?.report_id ?? latestReport?.id) && item.case_id === selectedCaseId);
    if (!canCase("reports", "reports:write")) throw new Error("No tenés permiso para esta operación de informes.");
    const current = captureCaseContext();
    if (!targetReport) return;
    const updated = await apiPost<ReportItem>(`/reports/${targetReport.id}/annexes/refresh`);
    if (!current()) return;
    setReviewResult({ status: "annexes_refreshed", report_id: updated.id });
    if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
    if (!current()) return;
    await loadReportPreview(updated.id);
  }

  async function transitionReportStatus(status: string) {
    const targetReport = reports.find(item => item.id === (reportPreview?.report_id ?? latestReport?.id) && item.case_id === selectedCaseId);
    if (!canCase("reports", "reports:write")) throw new Error("No tenés permiso para esta operación de informes.");
    const current = captureCaseContext();
    if (!targetReport) return;
    const updated = await apiPost<ReportItem>(`/reports/${targetReport.id}/versions/transition`, {
      status,
      user: analystName || targetReport.author,
      note: `Cambio de version a ${status}`
    });
    if (!current()) return;
    setReviewResult({ status: "version_transition", report_id: updated.id, next_status: updated.status, version: updated.version });
    if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
    if (!current()) return;
    await loadReportPreview(updated.id);
  }

  async function closeCase() {
    if (!selectedCaseId) return;
    if (!guardPermission("cases:write", "cerrar el caso")) return;
    try {
      const result = await apiPost<ClosureStatus>(`/cases/${selectedCaseId}/close`, { closure_note: closureNote });
      setClosureStatus(result);
      setModulePayload({ status: "case_closed", case_id: selectedCaseId, warnings: result.closure_warnings || [] });
      await refreshCore();
      await refreshCaseCollections(selectedCaseId);
    } catch (error) {
      const message = error instanceof Error ? error.message : "No se pudo cerrar el caso.";
      setClosureStatus((current) => current ? { ...current, message } : current);
      handleUiError(error, message, { focusIdentity: true });
    }
  }

  async function runAiSecurity() {
    const requestCurrent = captureCaseContext();
    setAiSecurityResult(
      await guardCaseResult(apiPost<AiSecurityEvaluation>("/ai-security/evaluations", {
        model_name: "mistral",
        run_tests: false,
        overall_score: 72,
        network_blocked: true,
        tools_enabled: false
      }), requestCurrent)
    );
  }

  function renderIndicatorOutcome() {
    if (!indicatorResult) return <EmptyState text="Ejecuta el análisis para obtener una lectura pericial del indicador." />;
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
          {prettySpanish(indicatorResult.legal_relevance)} Este resultado orienta la investigacion, pero debe vincularse con evidencia, custodia y fuentes verificables antes de sostener atribución.
        </div>
        {indicatorFindingMessage && (
          <div className={`action-feedback ${indicatorFindingState}`} role="status" aria-live="polite" aria-atomic="true">
            {indicatorFindingMessage}
          </div>
        )}
        <div className="button-row">
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Operación del módulo", () => (saveIndicatorAsFinding)())} disabled={(!selectedCaseId || indicatorFindingState === "saving") || !(canCase("analysis", "evidence:write")) || Boolean(caseTask)} variant="outline" type="button">
            <FileCheck2 size={16} /> {indicatorFindingState === "saving" ? "Guardando..." : indicatorFindingState === "saved" ? "Guardar otro hallazgo" : "Guardar como hallazgo"}
          </Button>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("evidence")} disabled={!selectedCaseId} variant="outline" type="button">
            <Fingerprint size={16} /> Ver evidencia
          </Button>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("reports")} disabled={!latestReport} variant="outline" type="button">
            <FileText size={16} /> Ver informe
          </Button>
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
          <span>Requiere revisión humana antes de exportacion final.</span>
          <span>La fundamentacion legal debe permanecer vinculada a biblioteca registrada.</span>
        </div>
        <div className="button-row">
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => loadReportPreview(aiEnrichmentResult.report_id || latestReport?.id)} variant="outline" type="button">
            <FileCheck2 size={16} /> Ver vista previa
          </Button>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("reports")} variant="outline" type="button">
            <FileText size={16} /> Abrir informes
          </Button>
        </div>
      </div>
    );
  }

  function renderCaseAnalysisOutcome() {
    const result = aiResult as CaseAnalysisResult | null;
    if (!result) return <EmptyState text="Ejecuta el análisis para obtener una lectura operativa del caso." />;
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
              {!articles.length && <span>Sin normas sugeridas para este análisis.</span>}
            </div>
          </div>
          <div>
            <h4>Que hacer ahora</h4>
            <div className="summary-list">
              {(result.operational_next_steps || []).map((item) => <span key={item}>{prettySpanish(item)}</span>)}
              {!result.operational_next_steps?.length && <span>Completar revisión humana y matriz legal-probatoria.</span>}
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
          <div className={`action-feedback ${legalApplyState}`} role="status" aria-live="polite" aria-atomic="true">
            {legalApplyMessage}
          </div>
        )}
        <div className="button-row">
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Operación del módulo", () => (() => searchAndTypifyLegal(true))())} disabled={!selectedCaseId || legalApplyState === "applying"} variant="outline" type="button">
            <Gavel size={16} /> {legalApplyState === "applying" ? "Aplicando..." : legalApplyState === "applied" ? "Encuadre aplicado" : "Aplicar encuadre al caso"}
          </Button>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("legalKnowledge")} variant="outline" type="button">
            <BookOpen size={16} /> Ver biblioteca legal
          </Button>
        </div>
      </div>
    );
  }

  function renderReviewOutcome() {
    if (!reviewAudit) return <EmptyState text="Ejecuta la revisión para obtener auditoria profesional del informe." />;
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
            <strong>Errores críticos</strong>
            {reviewAudit.critical_errors.map((item) => <span key={item}>{prettySpanish(item)}</span>)}
          </div>
        )}
        <div className="button-row">
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("reports")} variant="outline" type="button"><FileText size={16} /> Corregir informe</Button>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("legalKnowledge")} variant="outline" type="button"><Gavel size={16} /> Revisar matriz legal</Button>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Evaluar exportación", requestFinalExport)} disabled={!latestReport || !canCase("approve", "reports:write") || !canCase("export", "reports:read") || Boolean(caseTask)} variant="outline" type="button"><Download size={16} /> Evaluar exportación</Button>
        </div>
      </div>
    );
  }

  function renderExportFinalOutcome() {
    if (!exportFinalResult) return null;
    const result = exportFinalResult as ExportOutcome;
    const blocked = result.status === "blocked" || result.can_export_final === false;
    const missing = Array.from(new Set(result.missing || result.final_checklist?.missing || []));
    const pendingChecklist = (result.final_checklist?.items || []).filter((item) => !item.ok);
    const readableMessage = extractReadableMessage(
      result.message,
      blocked
        ? "La exportación final requiere completar controles periciales antes de sellarse."
        : "Operación de exportación final completada."
    );
    return (
      <div className={`export-outcome ${blocked ? "blocked" : "ready"}`}>
        <div>
          <span>{blocked ? "Exportación final bloqueada" : result.status === "sealed" ? "Exportación final sellada" : "Evaluación de exportación"}</span>
          <strong>
            {result.status === "sealed"
              ? `Sello ${result.seal_id || "generado"}`
              : result.exportability?.level || prettySpanish(result.status || "Resultado disponible")}
          </strong>
          {result.exportability?.score !== undefined && <small>Score de exportabilidad: {result.exportability.score}/100</small>}
          {result.contradictions?.count !== undefined && <small>Contradicciones detectadas: {result.contradictions.count}</small>}
          {result.final_checklist?.score !== undefined && <small>Checklist pericial: {result.final_checklist.score}/100</small>}
          <p>{readableMessage}</p>
          {blocked && Boolean(missing.length || pendingChecklist.length) && (
            <div className="requirements compact">
              <strong>Falta para exportar final sellado:</strong>
              {missing.map((item) => <span key={item}>{prettySpanish(item)}</span>)}
              {pendingChecklist.map((item) => (
                <span key={item.key || item.label}>{prettySpanish(item.label || "Control pendiente")}: {prettySpanish(item.message || "Pendiente")}</span>
              ))}
            </div>
          )}
        </div>
        {result.sha256 && <code>SHA-256 PDF: {result.sha256}</code>}
        {result.manifest_id && <small>Manifiesto #{result.manifest_id}</small>}
      </div>
    );
  }

  function renderDamagePanel() {
    const unsupportedTotal = Math.max(0, damageTotal - damageSupportedTotal);
    return (
      <div className="damage-panel">
        <div className="damage-metrics">
          <div>
            <span>Daño total estimado</span>
            <strong>{formatMoney(damageTotal, damageItems[0]?.currency || damageForm.currency || "ARS")}</strong>
            <small>Solo suma conceptos cargados en este caso.</small>
          </div>
          <div>
            <span>Conceptos cargados</span>
            <strong>{damageItems.length}</strong>
            <small>Pérdida, recuperación, indisponibilidad u otros rubros.</small>
          </div>
          <div>
            <span>Con soporte documental</span>
            <strong>{formatMoney(damageSupportedTotal, damageItems[0]?.currency || "ARS")}</strong>
            <small>{unsupportedTotal > 0 ? `${formatMoney(unsupportedTotal, damageItems[0]?.currency || "ARS")} requieren soporte.` : "Sin rubros pendientes de soporte."}</small>
          </div>
        </div>

        <div className="damage-presets">
          {damagePresets.map((preset) => (
            <Button type="button" className="h-auto min-h-10 whitespace-normal secondary-button" key={preset.label} onClick={() => applyDamagePreset(preset)} variant="outline">
              <Calculator size={15} /> {preset.label}
            </Button>
          ))}
        </div>

        <form className="compact-form damage-form premium-form" onSubmit={createDamageItem}><fieldset disabled={!canCase("write", "cases:write") || damageState === "saving"}><legend className="sr-only">Cuantificación del daño</legend>
          <div className="inline-grid">
            <FormField label="Concepto del daño"><Input placeholder="Concepto del daño" value={damageForm.concept} onChange={(e) => setDamageForm({ ...damageForm, concept: e.target.value })} /></FormField>
            <div className="inline-grid tight">
              <FormField label="Monto"><Input type="number" min="0" step="0.01" placeholder="Monto" value={damageForm.amount} onChange={(e) => setDamageForm({ ...damageForm, amount: e.target.value })} /></FormField>
              <FormField label="Moneda"><select value={damageForm.currency} onChange={(e) => setDamageForm({ ...damageForm, currency: e.target.value })}>
                <option value="ARS">ARS</option>
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
              </select></FormField>
            </div>
          </div>
          <div className="inline-grid">
            <FormField label="Fecha base o período"><Input placeholder="Fecha base o período" value={damageForm.base_date} onChange={(e) => setDamageForm({ ...damageForm, base_date: e.target.value })} /></FormField>
            <FormField label="Nivel de certeza"><select value={damageForm.certainty_level} onChange={(e) => setDamageForm({ ...damageForm, certainty_level: e.target.value })}>
              <option value="alto">Certeza alta</option>
              <option value="medio">Certeza media</option>
              <option value="bajo">Certeza baja</option>
            </select></FormField>
          </div>
          <FormField label="Fuente del valor: comprobante, factura, extracto, presupuesto, ticket o declaración documentada"><textarea placeholder="Fuente del valor: comprobante, factura, extracto, presupuesto, ticket o declaración documentada" value={damageForm.value_source} onChange={(e) => setDamageForm({ ...damageForm, value_source: e.target.value })} /></FormField>
          <FormField label="Fórmula o criterio de cálculo utilizado"><textarea placeholder="Fórmula o criterio de cálculo utilizado" value={damageForm.formula_used} onChange={(e) => setDamageForm({ ...damageForm, formula_used: e.target.value })} /></FormField>
          <FormField label="Evidencia que sostiene el rubro: hash, archivo, captura, transacción, factura o constancia"><textarea placeholder="Evidencia que sostiene el rubro: hash, archivo, captura, transacción, factura o constancia" value={damageForm.supporting_evidence} onChange={(e) => setDamageForm({ ...damageForm, supporting_evidence: e.target.value })} /></FormField>
          <FormField label="Observaciones, límites o datos faltantes"><textarea placeholder="Observaciones, límites o datos faltantes" value={damageForm.observations} onChange={(e) => setDamageForm({ ...damageForm, observations: e.target.value })} /></FormField>
          <Button disabled={!selectedCaseId || damageState === "saving"} variant="default" type="submit" className="h-auto min-h-10 whitespace-normal"><Calculator size={17} /> Registrar daño económico</Button>
        </fieldset></form>

        {damageMessage && <div className={`action-feedback ${damageState}`} role="status" aria-live="polite" aria-atomic="true">{damageMessage}</div>}

        <div className="damage-list">
          {damageItems.map((item) => (
            <article key={item.id}>
              <div>
                <strong>{prettySpanish(item.concept)}</strong>
                <span>{formatMoney(Number(item.amount || 0), item.currency)} ? Certeza {prettySpanish(item.certainty_level)}</span>
                {item.formula_used && <small>Fórmula: {prettySpanish(item.formula_used)}</small>}
                {item.value_source && <small>Fuente: {prettySpanish(item.value_source)}</small>}
                {item.supporting_evidence && <small>Soporte: {prettySpanish(item.supporting_evidence)}</small>}
              </div>
            </article>
          ))}
          {!damageItems.length && <EmptyState text="Todavía no hay rubros económicos cargados. El informe mostrará 0.00 ARS hasta que registres al menos un concepto." />}
        </div>
      </div>
    );
  }

  function renderWorkflow() {
    return (
      <div className="workflow premium-operating-forms">
        <section className="work-surface">
          <div className="section-head">
            <div>
              <h2>Flujo Caso - Evidencia - Informe</h2>
              <p>Camino operativo de punta a punta para resolver un incidente con OPERIA.</p>
            </div>
            <div className="section-actions">
              <Button className="h-auto min-h-10 whitespace-normal new-case-button" onClick={startNewCaseDraft} variant="default" type="button">
                <Briefcase size={17} /> Nuevo Caso
              </Button>
              <Button className="h-auto min-h-10 whitespace-normal icon-button" onClick={refreshCore} title="Actualizar" variant="outline" type="button" aria-label="Actualizar">
                <RefreshCcw size={18} />
              </Button>
            </div>
          </div>
          <div className="case-selector">
            <div className="case-summary">
              <strong>{selectedCase?.title || "Nuevo caso operativo"}</strong>
              <span>{selectedCase ? `${selectedCase.case_code} | ${selectedCase.incident_type} | ${selectedCase.status}` : "Crea o selecciona un caso para iniciar."}</span>
            </div>
            <div className="case-selector-actions">
              <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("history")} variant="outline" type="button">
                <History size={17} /> Abrir Historial
              </Button>
              <small>Los casos abiertos quedan guardados para retomarlos desde Historial.</small>
            </div>
          </div>
        </section>

        <div className="step-grid">
          <StepCard number={1} title="Crear un caso" done={Boolean(selectedCase)}>
            <form className="compact-form premium-form" onSubmit={event => { event.preventDefault(); void runCaseTask("Crear caso", () => createCase(event)); }}><fieldset disabled={!(identitySession.authenticated && canUse("cases:write")) || Boolean(caseTask)}><legend className="sr-only">Crear caso</legend>
              <FormField label="Código del caso"><Input placeholder="Código del caso" value={caseForm.case_code} onChange={(e) => setCaseForm({ ...caseForm, case_code: e.target.value })} required /></FormField>
              <FormField label="Título"><Input placeholder="Título" value={caseForm.title} onChange={(e) => setCaseForm({ ...caseForm, title: e.target.value })} required /></FormField>
              <FormField label="Tipo de incidente"><select
                value={caseForm.incident_type}
                onChange={(e) => {
                  const selected = attackTypes.find((item) => item.value === e.target.value);
                  setCaseForm({ ...caseForm, incident_type: e.target.value });
                  if (selected) setLegalQuery(selected.query);
                }}
              >
                {attackTypes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select></FormField>
              <FormField label="Descripción"><textarea placeholder="Descripción inicial" value={caseForm.description} onChange={(e) => setCaseForm({ ...caseForm, description: e.target.value })} /></FormField>
              <Button variant="default" type="submit" className="h-auto min-h-10 whitespace-normal"><Briefcase size={17} /> Crear caso</Button>
            </fieldset></form>
          </StepCard>

          <StepCard number={2} title="Registrar personas y entidades" done={participants.length > 0}>
            <form className="compact-form premium-form" onSubmit={event => { event.preventDefault(); void runCaseTask("Registrar participante", () => createParticipant(event)); }}><fieldset disabled={!(canCase("participants", "cases:write")) || Boolean(caseTask)}><legend className="sr-only">Registrar participante</legend>
              <div className="inline-grid">
                <FormField label="Relación con el expediente"><select value={participantForm.participant_type} onChange={(e) => setParticipantForm({ ...participantForm, participant_type: e.target.value })}>
                  <option value="damnificado">Damnificado</option>
                  <option value="victima">Víctima</option>
                  <option value="testigo">Testigo</option>
                  <option value="denunciante">Denunciante</option>
                  <option value="sospechoso">Sospechoso</option>
                  <option value="imputado">Imputado</option>
                  <option value="representante_legal">Representante legal</option>
                  <option value="entidad_financiera">Entidad financiera</option>
                  <option value="plataforma_digital">Plataforma digital</option>
                  <option value="otro">Otro</option>
                </select></FormField>
                <FormField label="Tipo de persona o entidad"><select value={participantForm.person_type} onChange={(e) => setParticipantForm({ ...participantForm, person_type: e.target.value })}>
                  <option value="persona_fisica">Persona física</option>
                  <option value="persona_juridica">Persona jurídica</option>
                  <option value="organismo">Organismo</option>
                  <option value="cuenta_digital">Cuenta digital</option>
                  <option value="alias_identidad">Alias/identidad digital</option>
                  <option value="desconocido">Desconocido</option>
                </select></FormField>
              </div>
              <FormField label="Nombre o identificador"><Input placeholder="Nombre, razon social, alias o identificador" value={participantForm.display_name} onChange={(e) => setParticipantForm({ ...participantForm, display_name: e.target.value })} required /></FormField>
              <div className="inline-grid">
                <FormField label="Tipo de documento"><Input placeholder="Tipo documento" value={participantForm.document_type} onChange={(e) => setParticipantForm({ ...participantForm, document_type: e.target.value })} /></FormField>
                <FormField label="Documento o identificador"><Input placeholder="Documento / CUIT / ID" value={participantForm.document_number} onChange={(e) => setParticipantForm({ ...participantForm, document_number: e.target.value })} /></FormField>
              </div>
              <div className="inline-grid">
                <FormField label="Correo electrónico"><Input placeholder="Email" value={participantForm.email} onChange={(e) => setParticipantForm({ ...participantForm, email: e.target.value })} /></FormField>
                <FormField label="Teléfono"><Input placeholder="Telefono" value={participantForm.phone} onChange={(e) => setParticipantForm({ ...participantForm, phone: e.target.value })} /></FormField>
              </div>
              <FormField label="Relación con el caso"><textarea placeholder="Relacion con el caso / rol investigativo" value={participantForm.relationship_to_case} onChange={(e) => setParticipantForm({ ...participantForm, relationship_to_case: e.target.value })} /></FormField>
              <Button disabled={!selectedCaseId} variant="default" type="submit" className="h-auto min-h-10 whitespace-normal"><Users size={17} /> Registrar participante</Button>
            </fieldset></form>
            <div className="mini-list">
              {participants.slice(0, 5).map((item) => (
                <span key={item.id}>{item.participant_type}: {item.display_name} ({item.person_type})</span>
              ))}
            </div>
          </StepCard>

          <StepCard number={3} title="Cargar evidencia y calcular hash" done={Boolean(latestEvidence?.sha256_hash)}>
            {renderEvidenceUpload()}
            {latestEvidence && <code>SHA-256: {latestEvidence.sha256_hash}</code>}
          </StepCard>

          <StepCard number={4} title="Registrar cadena de custodia" done={custody.length > 0}>
            <form className="compact-form premium-form" onSubmit={event => { event.preventDefault(); void runCaseTask("Registrar custodia", () => createCustodyAction(event)); }}><fieldset disabled={!(canCase("evidence", "evidence:write")) || Boolean(caseTask)}><legend className="sr-only">Registrar custodia</legend>
              <FormField label="Acción de custodia"><Input placeholder="Accion" value={custodyForm.action_type} onChange={(e) => setCustodyForm({ ...custodyForm, action_type: e.target.value })} /></FormField>
              <FormField label="Responsable de la acción"><Input placeholder="Responsable" value={custodyForm.user_responsible} onChange={(e) => setCustodyForm({ ...custodyForm, user_responsible: e.target.value })} /></FormField>
              <FormField label="Descripción del evento"><textarea placeholder="Detalle de la acción" value={custodyForm.detailed_description} onChange={(e) => setCustodyForm({ ...custodyForm, detailed_description: e.target.value })} required /></FormField>
              <Button disabled={!selectedCaseId} variant="default" type="submit" className="h-auto min-h-10 whitespace-normal"><Fingerprint size={17} /> Registrar custodia</Button>
            </fieldset></form>
          </StepCard>

          <StepCard number={5} title="Analizar IP, URL o dato cybercrime" done={Boolean(indicatorResult)}>
            <div className="compact-form">
              <FormField label="IP, dominio o URL"><Input value={indicator} onChange={(e) => setIndicator(e.target.value)} placeholder="IP, dominio o URL" /></FormField>
              <Button onClick={() => void runCaseTask("Operación del módulo", () => (analyzeIndicator)())} disabled={(!indicator) || !(canCase("analysis", "evidence:write")) || Boolean(caseTask)} variant="default" type="button" className="h-auto min-h-10 whitespace-normal"><Globe2 size={17} /> Analizar indicador</Button>
            </div>
            {renderIndicatorOutcome()}
          </StepCard>

          <StepCard number={6} title="Tipificar incidente con normativa argentina" done={Boolean(legalTypification?.principal_typification || legalMappings.length)}>
            <div className="compact-form">
              <FormField label="Consulta legal"><Input value={legalQuery} onChange={(e) => setLegalQuery(e.target.value)} /></FormField>
              <Button onClick={() => void runCaseTask("Operación del módulo", () => (() => searchAndTypifyLegal(false))())} variant="default" type="button" className="h-auto min-h-10 whitespace-normal"><Gavel size={17} /> Tipificar y sugerir norma</Button>
              <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Operación del módulo", () => (() => searchAndTypifyLegal(true))())} disabled={!selectedCaseId || legalApplyState === "applying"} variant="outline" type="button">
                <CheckCircle2 size={17} /> {legalApplyState === "applying" ? "Aplicando..." : legalApplyState === "applied" ? "Aplicado al caso" : "Aplicar al caso"}
              </Button>
            </div>
            {legalApplyMessage && (
              <div className={`action-feedback ${legalApplyState}`} role="status" aria-live="polite" aria-atomic="true">
                {legalApplyMessage}
              </div>
            )}
            {legalTypification?.principal_typification ? (
              <div className="typification-card compact">
                <span>{legalTypification.profile?.label || "Tipificación asistida"}</span>
                <h3>{legalTypification.principal_typification.reference} · {prettySpanish(legalTypification.principal_typification.title)}</h3>
                <p>{prettySpanish(legalTypification.principal_typification.applicability_to_case)}</p>
                <small>Elementos: {prettySpanish(legalTypification.principal_typification.why)}</small>
                <small>Límites: {prettySpanish(legalTypification.principal_typification.probatory_limits)}</small>
                <div className="readiness-bar"><div style={{ width: `${legalTypification.readiness_score}%` }} /></div>
                <small>Confianza {prettySpanish(legalTypification.confidence)} · {prettySpanish(legalTypification.decision_level)}</small>
              </div>
            ) : (
              <EmptyState text="Describe el incidente y ejecuta la tipificación. OPERIA sugerirá la norma principal y conexas." />
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

          <StepCard number={7} title="Cuantificar daño económico" done={damageItems.length > 0}>
            <p className="muted">Carga rubros, fuentes y fórmulas. El informe final usa únicamente conceptos asociados a este caso.</p>
            {renderDamagePanel()}
          </StepCard>

          <StepCard number={8} title="Ampliar análisis técnico-jurídico" done={Boolean(aiResult)}>
            <div className="compact-form">
              <FormField label="Consigna de análisis"><textarea value={aiPrompt} onChange={(e) => setAiPrompt(e.target.value)} /></FormField>
              <Button onClick={() => void runCaseTask("Operación del módulo", () => (runAiAssist)())} variant="default" type="button" disabled={!(canCase("analysis", "ai:use")) || Boolean(caseTask)} className="h-auto min-h-10 whitespace-normal"><Bot size={17} /> {latestReport ? "Ampliar informe" : "Analizar caso"}</Button>
            </div>
            {latestReport && <p className="notice">Con informe generado, esta acción agrega hipótesis, conclusiones y fundamentación legal al reporte.</p>}
            {latestReport ? renderAiEnrichmentOutcome() : renderCaseAnalysisOutcome()}
          </StepCard>

          <StepCard number={9} title="Generar informe" done={reports.length > 0}>
            <div className="compact-form">
              <FormField label="Analista / operador interviniente"><Input placeholder="Analista / operador interviniente" value={analystName} onChange={(e) => setAnalystName(e.target.value)} /></FormField>
            </div>
            <Button onClick={() => void runCaseTask("Generar informe", generateReport)} disabled={!canCase("reports", "reports:write") || Boolean(caseTask)} variant="default" type="button" className="h-auto min-h-10 whitespace-normal"><FileText size={17} /> Generar informe integral</Button>
            {latestReport && <p className="notice">Último informe: {latestReport.title}</p>}
            <div className="summary-list">
              <span>Nivel de exportabilidad: {exportabilitySnapshot.level}</span>
              <span>Score de exportabilidad: {exportabilitySnapshot.score}/100</span>
            </div>
          </StepCard>

          <StepCard number={10} title="Revisar informe" done={Boolean(reviewResult) && latestReport?.review_score !== undefined}>
            <Button onClick={() => void runCaseTask("Revisar informe", reviewReport)} disabled={!latestReport || !canCase("review", "reports:write") || Boolean(caseTask)} variant="default" type="button" className="h-auto min-h-10 whitespace-normal"><FileCheck2 size={17} /> Revisar informe</Button>
            {renderReviewOutcome()}
          </StepCard>

          <StepCard number={11} title="Exportar PDF" done={Boolean(latestReport)}>
            {latestReport ? (
              <Button disabled={!canCase("export", "reports:read") || Boolean(caseTask)} onClick={() => void runCaseTask("Descargar informe", () => downloadReport(latestReport.id))} className="h-auto min-h-10 whitespace-normal">
                <Download size={17} /> Exportar PDF con manifiesto
              </Button>
            ) : (
              <EmptyState text="Genera un informe antes de exportar." />
            )}
          </StepCard>

          <StepCard number={12} title="Resumen operativo" done={Boolean(selectedCase && latestEvidence && latestReport)}>
            <div className="summary-list">
              <span>Casos: {cases.length}</span>
              <span>Participantes del caso: {participants.length}</span>
              <span>Evidencias del caso: {evidence.length}</span>
              <span>Acciones de custodia: {custody.length}</span>
              <span>Informes del caso: {reports.length}</span>
              <span>Daño estimado: {formatMoney(damageTotal, damageItems[0]?.currency || "ARS")}</span>
              <span>Estado del caso: {selectedCase?.status || "sin caso"}</span>
              <span>Exportabilidad: {exportabilitySnapshot.level}</span>
            </div>
          </StepCard>

          <StepCard number={13} title="Cerrar caso" done={closureStatus?.already_closed}>
            <div className="compact-form">
              <FormField label="Nota de cierre del expediente"><textarea value={closureNote} onChange={(e) => setClosureNote(e.target.value)} /></FormField>
              <Button onClick={closeCase} disabled={!selectedCaseId || closureStatus?.already_closed} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">
                <CheckCircle2 size={17} /> Cerrar caso
              </Button>
            </div>
            <div className="button-row">
              <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Evaluar exportación", requestFinalExport)} disabled={!latestReport || !canCase("approve", "reports:write") || !canCase("export", "reports:read") || Boolean(caseTask)} variant="outline" type="button">
                <Download size={16} /> Exportar final sellado
              </Button>
              <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("reports")} disabled={!latestReport} variant="outline" type="button">
                <FileText size={16} /> Ver informe
              </Button>
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
    const rubricPercent = rubricEvaluation?.percentage || 0;
    const technicalFindingCount = dashboard.metrics?.proof_matrix_rows || legalProbatoryMatrix?.rows.length || 0;
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
      { key: "rubric", label: "Rúbrica completada", value: rubricEvaluation ? `${rubricEvaluation.percentage}%` : "Sin evaluar", status: rubricEvaluation ? (rubricPercent >= 80 ? "listo" : rubricPercent >= 50 ? "parcial" : "crítico") : "incompleto", detail: rubricEvaluation ? rubricEvaluation.summary : "Evaluá la rúbrica del desafío." },
    ];
    const statusWeight: Record<string, number> = { listo: 1, parcial: 0.55, incompleto: 0, ["crítico"]: 0 };
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
      { label: "Tipificación legal", ok: legalMappings.some((item) => item.decision_status !== "descartado"), detail: `${legalMappings.length} mapeo(s)` },
      { label: "Informe", ok: reports.length > 0, detail: latestReport ? professionalReportStatus(latestReport.status) : "Sin informe" },
      { label: "Revision", ok: Boolean(latestReport && latestReport.review_score >= 80), detail: latestReport ? `Score ${latestReport.review_score}` : "Sin revisión" },
    ];
    const nextAction =
      !selectedCase ? "Seleccionar o crear un caso operativo." :
      !evidence.length ? "Cargar evidencia y calcular hash." :
      !custody.length ? "Registrar cadena de custodia." :
      !legalMappings.length ? "Tipificar el incidente y aplicar norma al caso." :
      !latestReport ? "Generar informe integral." :
      latestReport.review_score < 80 ? "Revisar informe y corregir advertencias." :
      "Evaluar exportación final sellada.";

    return (
      <ModuleSurface className="" moduleId="dashboard">
        <div className="section-head">
          <div>
            <h2>Dashboard Operativo</h2>
            <p>Centro de mando para saber que esta listo, que falta y cual es la proxima accion pericial.</p>
          </div>
          <Button className="h-auto min-h-10 whitespace-normal icon-button" onClick={refreshCore} title="Actualizar" variant="outline" type="button" aria-label="Actualizar"><RefreshCcw size={18} /></Button>
        </div>
        <div className="command-panel">
          <div>
            <span className="tool-kicker">Proxima accion recomendada</span>
            <h3>{nextAction}</h3>
            <p>{selectedCase ? `${selectedCase.case_code} - ${selectedCase.title}` : "OPERIA necesita un caso activo para guiar el flujo."}</p>
          </div>
          <div className="button-row">
            <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("workflow")} variant="outline" type="button"><CheckCircle2 size={16} /> Abrir flujo</Button>
            <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("caseDetail")} disabled={!selectedCaseId} variant="outline" type="button"><FileCheck2 size={16} /> Detalle del caso</Button>
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
            <div className={`action-feedback ${ctfDashboardState === "working" ? "updating" : ctfDashboardState === "success" ? "updated" : ctfDashboardState}`} role="status" aria-live="polite" aria-atomic="true">
              {ctfDashboardMessage}
            </div>
          )}
          <div className="ctf-action-row">
            <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("deepfakeMedia")} disabled={!selectedCaseId} variant="outline" type="button"><FileCheck2 size={16} /> Ir a Deepfake Lab</Button>
            <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("blockchainForensics")} disabled={!selectedCaseId} variant="outline" type="button"><Globe2 size={16} /> Ir a Blockchain Lab</Button>
            <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("iotForensics")} disabled={!selectedCaseId} variant="outline" type="button"><Shield size={16} /> Ir a IoT Lab</Button>
            <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("legalKnowledge")} disabled={!selectedCaseId} variant="outline" type="button"><BookOpen size={16} /> Ir a Biblioteca Legal</Button>
            <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={updateRubricFromCtfDashboard} disabled={!selectedCaseId || ctfDashboardState === "working"} variant="outline" type="button"><Gavel size={16} /> Evaluar rúbrica</Button>
            <Button onClick={generateReportFromCtfDashboard} disabled={!selectedCaseId || ctfDashboardState === "working"} variant="default" type="button" className="h-auto min-h-10 whitespace-normal"><FileText size={16} /> Generar informe</Button>
            <Button onClick={exportPdfFromCtfDashboard} disabled={!latestReport} variant="default" type="button" className="h-auto min-h-10 whitespace-normal"><Download size={16} /> Exportar PDF</Button>
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
      </ModuleSurface>
    );
  }

  function renderCases() {
    return <CasesWorkspace key={authToken} cases={cases} selectedId={selectedCaseId} loading={loading}
      authenticated={identitySession.authenticated} canCreate={canUse("cases:write")} error={error}
      onOpen={id => requestNavigation(() => { setSelectedCaseId(id); setCaseDetailTab("summary"); setActive("caseDetail"); })}
      onCreate={() => { startNewCaseDraft(); setActive("workflow"); }}
      onRefresh={() => { setLoading(true); refreshCore().catch(err => setError(err.message)).finally(() => setLoading(false)); }}
      onSignIn={() => setActive("identity")} />;
  }

  function renderHistory() {
    const isClosedCase = (item: CaseItem) => item.status.toLowerCase() === "cerrado";
    const openItems = chronologicalCases.filter((item) => !isClosedCase(item));
    const closedItems = chronologicalCases.filter((item) => isClosedCase(item));

    return (
      <ModuleSurface className="history-workspace" moduleId="history">
        <div className="section-head">
          <div>
            <h2>Historial</h2>
            <p>Linea cronologica de casos, informes, flujo de trabajo y exportaciones asociadas.</p>
          </div>
          <div className="section-actions">
            <Button className="h-auto min-h-10 whitespace-normal new-case-button" onClick={() => {
              startNewCaseDraft();
              setActive("workflow");
            }} variant="default" type="button">
              <Briefcase size={17} /> Nuevo Caso
            </Button>
            <Button className="h-auto min-h-10 whitespace-normal icon-button" onClick={refreshCore} title="Actualizar historial" variant="outline" type="button" aria-label="Actualizar historial">
              <RefreshCcw size={18} />
            </Button>
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
            const caseReports = historyReportsByCase[item.id] || [];
            const latestCaseReport = caseReports[0];
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
                    <span>Última actividad: {formatHistoryDate(item.updated_at || item.created_at)}</span>
                  </div>
                  <p>{item.description ? prettySpanish(item.description) : "Sin descripción inicial registrada."}</p>
                  <div className="history-footnote">
                    <span>Flujo de trabajo, informes y exportaciones permanecen asociados a este caso.</span>
                  </div>
                  {latestCaseReport && (
                    <div className="history-report-strip">
                      <FileText size={15} />
                      <span>Último informe: {latestCaseReport.title} · v{latestCaseReport.version} · {professionalReportStatus(latestCaseReport.status)}</span>
                    </div>
                  )}
                </div>
                <div className="history-actions">
                  {!isClosed && (
                    <Button onClick={() => openCaseFromHistory(item.id, "workflow")} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">
                      <RefreshCcw size={16} /> Continuar trabajo
                    </Button>
                  )}
                  <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => openCaseFromHistory(item.id, "caseDetail")} variant="outline" type="button">
                    <FileCheck2 size={16} /> Ver detalle
                  </Button>
                  {latestCaseReport && (
                    <Button variant="outline" onClick={() => requestNavigation(() => { setSelectedCaseId(item.id); setActive("reports"); })} className="h-auto min-h-10 whitespace-normal"><FileText size={16} />Abrir informes</Button>
                  )}
                  <Button className="h-auto min-h-10 whitespace-normal danger" onClick={() => deleteCaseFromHistory(item.id, item.title)} variant="destructive" type="button">
                    <Trash2 size={16} /> Eliminar
                  </Button>
                  {isClosed && <small>Caso cerrado: disponible para consulta y exportación.</small>}
                </div>
              </article>
            );
          })}
          {!chronologicalCases.length && <EmptyState text="No hay casos registrados en el historial." />}
        </div>
      </ModuleSurface>
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
      { label: "Hashes", ok: evidence.length > 0 && evidence.every((item) => Boolean(item.sha256_hash)), detail: evidence.length ? evidence.every(item => Boolean(item.sha256_hash)) ? "Hashes registrados" : "Hay evidencias sin hash" : "Sin evidencia registrada" },
      { label: "Custodia", ok: custody.length > 0, detail: `${custody.length} acción(es)` },
      { label: "Daño económico", ok: damageItems.length > 0, detail: damageItems.length ? formatMoney(damageTotal, damageItems[0]?.currency || "ARS") : "Sin cuantificar" },
      { label: "Mapeo legal", ok: legalMappings.some((item) => item.decision_status !== "descartado"), detail: `${legalMappings.length} norma(s)` },
      { label: "Informe", ok: Boolean(latestReport), detail: latestReport ? professionalReportStatus(latestReport.status) : "No generado" },
      { label: "Revisión", ok: Boolean(latestReport && latestReport.review_score >= 80), detail: latestReport ? `Score ${latestReport.review_score}` : "Sin revisión" }
    ];
    const tabs: Array<{ key: CaseDetailTab; label: string; count?: number }> = [
      { key: "summary", label: "Resumen" },
      { key: "participants", label: "Personas", count: participants.length },
      { key: "evidence", label: "Evidencia", count: evidence.length },
      { key: "custody", label: "Custodia", count: custody.length },
      { key: "damage", label: "Daño", count: damageItems.length },
      { key: "legal", label: "Legal", count: legalMappings.length },
      { key: "reports", label: "Informes", count: reports.length },
      { key: "audit", label: "Auditoría", count: canUse("audit:read") ? auditLogs.length : undefined }
    ];

    const renderParticipantsPanel = () => (
      <Card className="detail-panel">
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
              <Button className="h-auto min-h-10 whitespace-normal icon-button" disabled={!canCase("participants", "cases:write")} onClick={() => { editorReturnFocus.current = document.activeElement as HTMLElement; setEditingParticipant(item); }} title="Editar participante" variant="outline" type="button" aria-label="Editar participante"><Save size={15} /></Button>
              <Button className="h-auto min-h-10 whitespace-normal icon-button danger" disabled={!canCase("participants", "cases:write")} onClick={() => deleteParticipant(item.id)} title="Eliminar participante" variant="destructive" type="button" aria-label="Eliminar participante"><Trash2 size={15} /></Button>
            </div>
          </div>
        ))}
        {!participants.length && <EmptyState text="Sin participantes cargados." />}
      </Card>
    );

    const renderEvidencePanel = () => (
      <Card className="detail-panel">
        <div className="panel-head">
          <h3>Evidencia</h3>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("evidence")} variant="outline" type="button">Abrir evidencia</Button>
        </div>
        {evidence.map((item) => (
          <div className="editable-record" key={item.id}>
            <div>
              <strong>{prettySpanish(item.evidence_type)}</strong>
              <span>{prettySpanish(item.description)}</span>
              <code>{item.sha256_hash || "hash pendiente"}</code>
            </div>
            <div className="record-actions">
              <Button className="h-auto min-h-10 whitespace-normal icon-button" disabled={!canCase("evidence", "evidence:write")} onClick={() => { editorReturnFocus.current = document.activeElement as HTMLElement; setEditingEvidence(item); }} title="Editar evidencia" variant="outline" type="button" aria-label="Editar evidencia"><Save size={15} /></Button>
              <Button className="h-auto min-h-10 whitespace-normal icon-button danger" disabled={!canCase("evidence", "evidence:write")} onClick={() => deleteEvidence(item.id)} title="Eliminar evidencia" variant="destructive" type="button" aria-label="Eliminar evidencia"><Trash2 size={15} /></Button>
            </div>
          </div>
        ))}
        {!evidence.length && <EmptyState text="Sin evidencia cargada." />}
      </Card>
    );

    const renderCustodyPanel = () => (
      <Card className="detail-panel">
        <div className="panel-head">
          <h3>Cadena de custodia</h3>
          <p>Registro histórico: las correcciones agregan una nueva actuación y conservan las anteriores.</p>
        </div>
        {custody.map((item) => (
          <div className="editable-record" key={item.id}>
            <div>
              <strong>{prettySpanish(item.action_type)}</strong>
              <span>{prettySpanish(item.detailed_description)}</span>
              <small>{prettySpanish(item.user_responsible || "Responsable pendiente")} | {prettySpanish(item.status)}</small>
              <small>{item.ledger_entry ? `Evento #${item.id} · versión ${item.ledger_entry.version} · raíz #${item.ledger_entry.root_action_id} · ${item.ledger_entry.actor_name}` : `Evento histórico #${item.id} · sin atribución retrospectiva`}</small>
              {item.ledger_entry?.previous_action_id && <small>Rectifica #{item.ledger_entry.previous_action_id}: {item.ledger_entry.reason}</small>}
            </div>
            <div className="record-actions">
              {custody.some((event) => event.ledger_entry?.previous_action_id === item.id)
                ? <small>Con rectificación posterior registrada</small>
                : <Button className="h-auto min-h-10 whitespace-normal secondary" disabled={!canCase("evidence", "evidence:write")} onClick={() => { editorReturnFocus.current = document.activeElement as HTMLElement; setCustodyReason(""); setEditingCustody(item); }} title="Agregar rectificación" variant="outline" type="button"><Save size={15} /> Rectificar</Button>}
            </div>
          </div>
        ))}
        {!custody.length && <EmptyState text="Sin acciones de custodia." />}
      </Card>
    );

    const renderLegalPanel = () => (
      <Card className="detail-panel wide">
        <div className="panel-head">
          <h3>Mapeo legal y matriz probatoria</h3>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("legalKnowledge")} variant="outline" type="button">Abrir biblioteca</Button>
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
      </Card>
    );

    const renderDamageDetailPanel = () => (
      <Card className="detail-panel wide">
        <div className="panel-head">
          <div>
            <h3>Cuantificación económica del daño</h3>
            <p className="muted">Rubros económicos asociados exclusivamente al caso seleccionado.</p>
          </div>
        </div>
        {renderDamagePanel()}
      </Card>
    );

    const renderReportsPanel = () => (
      <Card className="detail-panel wide">
        <div className="panel-head">
          <h3>Informes y exportaciones</h3>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("reports")} variant="outline" type="button">Abrir informes</Button>
        </div>
        {reports.map((item) => (
          <div className="editable-record" key={item.id}>
            <div>
              <strong>{item.title}</strong>
              <span>{professionalReportStatus(item.status)} | Score {item.review_score}</span>
              <small>Exportabilidad estimada: {exportabilitySnapshot.level} ({exportabilitySnapshot.score}/100)</small>
            </div>
            <Button variant="outline" size="sm" disabled={!canCase("export", "reports:read")} onClick={() => void runCaseTask("Descargar informe", () => downloadReport(item.id))} className="h-auto min-h-10 whitespace-normal">Exportar PDF</Button>
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
      </Card>
    );

    const renderAuditPanel = () => (
      <Card className="detail-panel wide">
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
      </Card>
    );

    return (
      <div className="case-detail premium-dossier">
        <DossierHeader item={selectedCase} cases={cases} selectedId={selectedCaseId} onSelect={selectCase}
          onBack={() => navigateTo("cases")} onWorkflow={() => navigateTo("workflow")}
          onReports={() => navigateTo("reports")} onLegal={() => navigateTo("legalKnowledge")}
          counts={{ evidence: evidence.length, custody: custody.length, reports: reports.length, participants: participants.length }}
          loading={caseCollectionsLoading} readOnly={!caseCollectionsLoading && Boolean(caseAccess) && !canModifySelectedCase()} />
        {locked && <p className="premium-permissions-note">Expediente cerrado. Las rectificaciones conservan los eventos originales.</p>}
        {caseCollectionsError && <div role="alert" className="premium-permissions-note">{caseCollectionsError}</div>}
        {selectedCase && !caseCollectionsLoading && Boolean(caseAccess) && !canModifySelectedCase() && <p className="premium-permissions-note">Acceso de consulta. Las acciones habilitadas dependen de tu rol y de las concesiones de este expediente.</p>}
        <Tabs value={caseDetailTab} onValueChange={value => setCaseDetailTab(value as CaseDetailTab)} className="work-surface compact-surface gap-0">
          <div className="premium-dossier-tabs"><TabsList variant="line" aria-label="Secciones del expediente" className="h-10 gap-2">
            {tabs.map(tab => <TabsTrigger key={tab.key} value={tab.key} disabled={tab.key === "audit" && !canUse("audit:read")} title={tab.key === "audit" && !canUse("audit:read") ? "Tu rol no tiene permiso para consultar auditoría" : undefined} className="px-3 text-xs">{tab.label}{typeof tab.count === "number" && <span className="ml-1 text-[10px] text-muted-foreground">{caseCollectionsLoading ? "—" : tab.count}</span>}</TabsTrigger>)}
          </TabsList></div>
          <TabsContent value={caseDetailTab} className="outline-none">
          {caseCollectionsLoading ? <div role="status" aria-label="Cargando expediente" className="space-y-4 p-4"><Skeleton className="h-10 w-1/2" /><Skeleton className="h-36 w-full" /><Skeleton className="h-20 w-full" /></div>
          : caseCollectionsError || !selectedCase ? <p className="premium-permissions-note">No hay datos del expediente disponibles para mostrar.</p> : <>
          {caseDetailTab === "summary" && (
            <div className="dossier-grid">
              <Card className="detail-panel wide">
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
              </Card>
              <Card className="detail-panel">
                <div className="panel-head">
                  <h3>Resumen técnico</h3>
                </div>
                <div className="case-overview">
                  <div><span>Participantes</span><strong>{participants.length}</strong></div>
                  <div><span>Evidencia</span><strong>{evidence.length}</strong></div>
                  <div><span>Custodia</span><strong>{custody.length}</strong></div>
                  <div><span>Informes</span><strong>{reports.length}</strong></div>
                  <div><span>Daño estimado</span><strong>{damageItems.length ? formatMoney(damageTotal, damageItems[0]?.currency || "ARS") : "Sin cuantificar"}</strong></div>
                </div>
              </Card>
              <Card className="detail-panel">
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
                ) : <EmptyState text={canUse("audit:read") ? "Sin actividad auditada." : "La auditoría requiere un permiso adicional de tu rol."} />}
              </Card>
            </div>
          )}
          {caseDetailTab === "participants" && renderParticipantsPanel()}
          {caseDetailTab === "evidence" && renderEvidencePanel()}
          {caseDetailTab === "custody" && renderCustodyPanel()}
          {caseDetailTab === "damage" && renderDamageDetailPanel()}
          {caseDetailTab === "legal" && renderLegalPanel()}
          {caseDetailTab === "reports" && renderReportsPanel()}
          {caseDetailTab === "audit" && renderAuditPanel()}
          </>}
          </TabsContent>
        </Tabs>
        {selectedCaseId && identitySession.user?.role === "admin" && <CaseAccessPanel key={`${identitySession.user.id}:${selectedCaseId}`} caseId={Number(selectedCaseId)} users={identityUsers} />}

        {editingParticipant && (
          <Dialog open onOpenChange={open => { if (!open && !caseTask) setEditingParticipant(null); }}><DialogContent className="premium-editor-dialog" onCloseAutoFocus={event => { event.preventDefault(); const target = editorReturnFocus.current; if (target?.isConnected) target.focus(); else document.getElementById("main-content")?.focus(); }}><form className="premium-form" onSubmit={event => { event.preventDefault(); void runCaseTask("Editar participante", () => saveParticipant(event)); }}>
            <DialogHeader><DialogTitle>Editar participante</DialogTitle><DialogDescription>Solo se aplican cambios al confirmar. Los eventos originales de custodia se conservan.</DialogDescription></DialogHeader>{error && <p role="alert" className="premium-form-error">{error}</p>}<fieldset disabled={!canCase("participants", "cases:write") || Boolean(caseTask)}><legend className="sr-only">Editar participante</legend>
            <div className="inline-grid">
              <FormField label="Nombre o identificador"><Input value={editingParticipant.display_name} onChange={(e) => setEditingParticipant({ ...editingParticipant, display_name: e.target.value })} /></FormField>
              <FormField label="Relación con el expediente"><Input value={editingParticipant.participant_type} onChange={(e) => setEditingParticipant({ ...editingParticipant, participant_type: e.target.value })} /></FormField>
            </div>
            <div className="inline-grid">
              <FormField label="Tipo de documento"><Input value={editingParticipant.document_type || ""} onChange={(e) => setEditingParticipant({ ...editingParticipant, document_type: e.target.value })} /></FormField>
              <FormField label="Documento o identificador"><Input value={editingParticipant.document_number || ""} onChange={(e) => setEditingParticipant({ ...editingParticipant, document_number: e.target.value })} /></FormField>
            </div>
            <FormField label="Relación con el caso"><textarea value={editingParticipant.relationship_to_case || ""} onChange={(e) => setEditingParticipant({ ...editingParticipant, relationship_to_case: e.target.value })} /></FormField>
            <div className="actions-line">
              <Button className="h-auto min-h-10 whitespace-normal"><Save size={16} /> Guardar</Button>
              <Button type="button" className="h-auto min-h-10 whitespace-normal secondary" onClick={() => setEditingParticipant(null)}>Cancelar</Button>
            </div>
          </fieldset></form></DialogContent></Dialog>
        )}

        {editingEvidence && (
          <Dialog open onOpenChange={open => { if (!open && !caseTask) setEditingEvidence(null); }}><DialogContent className="premium-editor-dialog" onCloseAutoFocus={event => { event.preventDefault(); const target = editorReturnFocus.current; if (target?.isConnected) target.focus(); else document.getElementById("main-content")?.focus(); }}><form className="premium-form" onSubmit={event => { event.preventDefault(); void runCaseTask("Editar evidencia", () => saveEvidence(event)); }}>
            <DialogHeader><DialogTitle>Editar evidencia</DialogTitle><DialogDescription>Solo se aplican cambios al confirmar. Los eventos originales de custodia se conservan.</DialogDescription></DialogHeader>{error && <p role="alert" className="premium-form-error">{error}</p>}<fieldset disabled={!canCase("evidence", "evidence:write") || Boolean(caseTask)}><legend className="sr-only">Editar evidencia</legend>
            <div className="inline-grid">
              <FormField label="Tipo de evidencia"><Input value={editingEvidence.evidence_type} onChange={(e) => setEditingEvidence({ ...editingEvidence, evidence_type: e.target.value })} /></FormField>
              <FormField label="Estado de integridad" hint="Se actualiza mediante la verificación del archivo."><Input readOnly value={editingEvidence.integrity_status} /></FormField>
            </div>
            <FormField label="Descripción"><textarea value={editingEvidence.description} onChange={(e) => setEditingEvidence({ ...editingEvidence, description: e.target.value })} /></FormField>
            <FormField label="SHA-256 registrado" hint="Referencia de integridad; no se modifica desde este editor."><Input readOnly value={editingEvidence.sha256_hash || ""} /></FormField>
            <div className="actions-line">
              <Button className="h-auto min-h-10 whitespace-normal"><Save size={16} /> Guardar</Button>
              <Button type="button" className="h-auto min-h-10 whitespace-normal secondary" onClick={() => setEditingEvidence(null)}>Cancelar</Button>
            </div>
          </fieldset></form></DialogContent></Dialog>
        )}

        {editingCustody && (
          <Dialog open onOpenChange={open => { if (!open && !caseTask) setEditingCustody(null); }}><DialogContent className="premium-editor-dialog" onCloseAutoFocus={event => { event.preventDefault(); const target = editorReturnFocus.current; if (target?.isConnected) target.focus(); else document.getElementById("main-content")?.focus(); }}><form className="premium-form" onSubmit={event => { event.preventDefault(); void runCaseTask("Rectificar evento de custodia", () => saveCustodyAction(event)); }}>
            <DialogHeader><DialogTitle>Rectificar evento de custodia</DialogTitle><DialogDescription>Solo se aplican cambios al confirmar. Los eventos originales de custodia se conservan.</DialogDescription></DialogHeader>{error && <p role="alert" className="premium-form-error">{error}</p>}<fieldset disabled={!canCase("evidence", "evidence:write") || Boolean(caseTask)}><legend className="sr-only">Rectificar evento de custodia</legend>
            <p>El original se conserva. El autor se registra desde tu sesión autenticada.</p>
            <FormField label="Motivo de la rectificación" hint="El evento original permanece inmutable."><textarea required maxLength={2000} value={custodyReason} onChange={(e) => setCustodyReason(e.target.value)} /></FormField>
            <FormField label="Descripción del evento"><textarea value={editingCustody.detailed_description} onChange={(e) => setEditingCustody({ ...editingCustody, detailed_description: e.target.value })} /></FormField>
            <FormField label="Estado del evento"><Input value={editingCustody.status || ""} onChange={(e) => setEditingCustody({ ...editingCustody, status: e.target.value })} /></FormField>
            <div className="actions-line">
              <Button disabled={!custodyReason.trim()} className="h-auto min-h-10 whitespace-normal"><Save size={16} /> Registrar rectificación</Button>
              <Button type="button" className="h-auto min-h-10 whitespace-normal secondary" onClick={() => setEditingCustody(null)}>Cancelar</Button>
            </div>
          </fieldset></form></DialogContent></Dialog>
        )}
      </div>
    );
  }

  function renderEvidence() {
    return <EvidenceWorkspace key={`${authToken}:${selectedCaseId}`} items={evidence} caseId={selectedCaseId} caseCode={selectedCase?.case_code}
      loading={caseCollectionsLoading} error={caseCollectionsError} canVerify={canCase("evidence", "evidence:write")} canDownload={canCase("export", "evidence:read")} busy={Boolean(caseTask)}
      upload={renderEvidenceUpload()} onVerify={id => void runCaseTask("Verificar integridad", () => verifyEvidenceIntegrity(id))}
      onDownload={id => void runCaseTask("Descargar evidencia", async () => {
        if (!canCase("export", "evidence:read") || !evidence.some(item => item.id === id && item.case_id === selectedCaseId)) throw new Error("No tenés permiso para descargar esta evidencia.");
        await downloadArtifact(`/evidence/${id}/download`, `operia-evidencia-${id}.bin`);
      })} />;
  }

  function renderRubricCompliance() {
    const statusClass = rubricEvaluation?.status === "completo" ? "ok" : rubricEvaluation?.status === "parcial" ? "pending" : "blocked";
    return (
      <Card className="report-card rubric-panel">
        <div className="panel-head">
          <div>
            <h3>Cumplimiento de Rúbrica</h3>
            <p>Written Legal Evidence Report 2026: secciones A-D y resumen investigativo final.</p>
          </div>
          <Button onClick={() => void runCaseTask("Evaluar rúbrica", updateRubricEvaluation)} disabled={!canCase("review", "reports:write") || Boolean(caseTask) || rubricState === "updating"} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">
            <RefreshCcw size={16} /> {rubricState === "updating" ? "Actualizando..." : "Actualizar evaluación"}
          </Button>
        </div>
        {rubricMessage && <div className={`action-feedback ${rubricState}`} role="status" aria-live="polite" aria-atomic="true">{prettySpanish(rubricMessage)}</div>}
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
      </Card>
    );
  }

  function renderReportsProfessional() {
    const includedSections = reportPreview?.sections.filter((section) => section.word_count > 0) || [];
    const emptySections = reportPreview?.sections.filter((section) => section.word_count <= 0) || [];
    const missingChecklist = reportPreview?.final_checklist.items.filter((item) => !item.ok) || [];
    const completedChecklist = reportPreview?.final_checklist.items.filter((item) => item.ok) || [];
    const reportNextStep = !selectedCaseId
      ? "Seleccioná o creá un caso antes de trabajar informes."
      : !latestReport
        ? "Generá el informe integral para activar revisión, vista previa y exportación."
        : !reportPreview
          ? "Abrí la vista previa profesional para ver qué incluye el PDF y qué falta."
          : reportPreview.can_export_final
            ? "El informe está listo para sellado final. Exportá solo cuando el analista lo haya validado."
            : "Completá los controles pendientes antes de intentar el sellado final.";

    if (caseCollectionsLoading) return <div role="status" aria-label="Cargando informes"><Skeleton className="h-48 w-full" /></div>;
    if (!selectedCaseId || caseCollectionsError) return <section className="premium-panel"><h2>Informes del expediente</h2><p>{caseCollectionsError || "Seleccioná un expediente desde Casos para consultar sus informes."}</p></section>;
    return (
      <section className="premium-report-workspace" aria-label="Control de informes">
        <div className="premium-section-intro">
          <div>
            <h2>Informes</h2>
            <p>Control profesional del informe: contenido incluido, faltantes, versionado, anexos y exportación final.</p>
          </div>
          <Button onClick={() => void runCaseTask("Generar informe", generateReport)} disabled={!canCase("reports", "reports:write") || Boolean(caseTask)} className="h-auto min-h-10 whitespace-normal"><FileText size={17} /> Generar informe</Button>
        </div>
        <div className="module-guidance">
          <div>
            <span>Próximo paso recomendado</span>
            <strong>{reportNextStep}</strong>
          </div>
          <div>
            <span>Caso activo</span>
            <strong>{selectedCase ? selectedCase.case_code : "Sin caso seleccionado"}</strong>
          </div>
          <div>
            <span>Estado documental</span>
            <strong>{latestReport ? professionalReportStatus(latestReport.status) : "Sin informe"}</strong>
          </div>
        </div>
        {latestReport && (
          <div className="report-toolbar">
            <Button variant="outline" disabled={!canCase("read", "reports:read") || Boolean(caseTask)} onClick={() => requestNavigation(() => void runCaseTask("Abrir vista previa", () => loadReportPreview()))} className="h-auto min-h-10 whitespace-normal"><FileCheck2 size={16} /> Vista previa profesional</Button>
            <Button variant="outline" disabled={!canCase("review", "reports:write") || Boolean(caseTask)} onClick={() => void runCaseTask("Revisar informe", reviewReport)} className="h-auto min-h-10 whitespace-normal"><CheckCircle2 size={16} /> Revisar</Button>
            <Button
              disabled={!canCase("approve", "reports:write") || !canCase("export", "reports:read") || !reportPreview?.can_export_final || Boolean(caseTask)}
              onClick={() => void runCaseTask("Sellar y exportar", requestFinalExport)}
              className={"h-auto min-h-10 whitespace-normal " + (reportPreview?.can_export_final ? "" : "secondary")}
              title={reportPreview?.can_export_final ? "Exportar informe final sellado" : "Primero completá los controles pendientes"}
            >
              <Download size={16} /> Sellar y exportar final
            </Button>
            <Button variant="outline" disabled={!canCase("reports", "reports:write") || Boolean(caseTask)} onClick={() => void runCaseTask("Actualizar anexos", refreshReportAnnexes)} className="h-auto min-h-10 whitespace-normal"><FileText size={16} /> Actualizar anexos</Button>
            <Button variant="outline" disabled={!canCase("export", "reports:read") || Boolean(caseTask)} onClick={() => void runCaseTask("Descargar informe", () => downloadReport(reportPreview?.report_id ?? latestReport.id))} className="h-auto min-h-10 whitespace-normal">
              <Download size={16} /> Exportar borrador PDF
            </Button>
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
              <Card className="report-card">
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
              </Card>
              <Card className="report-card">
                <h4>Que falta para cerrarlo</h4>
                <div className="summary-list">
                  {missingChecklist.map((item) => (
                    <span key={item.key}>
                      <strong>{prettySpanish(item.label)}:</strong> {prettySpanish(item.message)}
                    </span>
                  ))}
                  {!missingChecklist.length && <span>Sin faltantes críticos para cierre pericial.</span>}
                </div>
              </Card>
            </div>
            <div className="preview-grid">
              <Card className="report-card">
                <h4>Resumen ejecutivo editable</h4>
                <FormField label="Resumen ejecutivo" hint="Guardar genera el registro de versión correspondiente; el historial se conserva."><textarea className="executive-editor" disabled={!canCase("reports", "reports:write") || Boolean(caseTask)} value={executiveSummaryDraft} onChange={(event) => setExecutiveSummaryDraft(event.target.value)} /></FormField>
                <Button disabled={!canCase("reports", "reports:write") || Boolean(caseTask) || !executiveSummaryDraft.trim()} onClick={() => void runCaseTask("Guardar resumen", saveExecutiveSummary)} className="h-auto min-h-10 whitespace-normal">
                  <Save size={16} /> Guardar resumen ejecutivo
                </Button>
              </Card>
              <Card className="report-card">
                <h4>Versionado del informe</h4>
                <p>Usa estos estados para controlar madurez documental. La version final exige checklist completo.</p>
                <div className="version-row">
                  {["borrador", "preliminar", "revisado", "final", "corregido", "reabierto"].map((status) => (
                    <Button key={status} variant={(reportPreview?.status || latestReport?.status) === status ? "default" : "outline"} disabled={!canCase("reports", "reports:write") || Boolean(caseTask) || (status === "final" && (!canCase("approve", "reports:write") || !reportPreview?.can_export_final))} onClick={() => void runCaseTask("Cambiar versión", () => transitionReportStatus(status))} className="h-auto min-h-10 whitespace-normal">
                      {prettySpanish(status)}
                    </Button>
                  ))}
                </div>
              </Card>
            </div>
            <div className="preview-grid">
              <Card className="report-card">
                <h4>Checklist pericial final</h4>
                {reportPreview.final_checklist.items.map((item) => (
                  <div className={`check-row ${item.ok ? "ok" : "pending"}`} key={item.key}>
                    <span>{item.ok ? "Cumplido" : "Pendiente"}</span>
                    <strong>{prettySpanish(item.label)}</strong>
                    <small>{prettySpanish(item.message)}</small>
                  </div>
                ))}
              </Card>
              <Card className="report-card">
                <h4>Contradicciones legal-probatorias</h4>
                {reportPreview.contradictions.issues.map((issue, index) => (
                  <div className="preview-section warning" key={`${issue.norm_reference}-${index}`}>
                    <strong>{issue.norm_reference} - {prettySpanish(issue.legal_element)}</strong>
                    <span>{prettySpanish(issue.severity)}</span>
                    <small>{prettySpanish(issue.message)} {prettySpanish(issue.recommended_action)}</small>
                  </div>
                ))}
                {!reportPreview.contradictions.issues.length && <EmptyState text="Sin contradicciones bloqueantes detectadas." />}
              </Card>
            </div>
            {!!emptySections.length && (
              <div className="requirements">
                <strong>Secciones sin contenido suficiente</strong>
                {emptySections.map((section) => <span key={section.title}>{prettySpanish(section.title)}</span>)}
              </div>
            )}
            <Card className="report-card">
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
            </Card>
            {renderExportFinalOutcome()}
          </div>
        )}
        {!reportPreview && renderExportFinalOutcome()}
        <ReportRegister reports={reports} caseId={selectedCaseId} canRead={canCase("read", "reports:read")} canExport={canCase("export", "reports:read")} busy={Boolean(caseTask)}
          onPreview={id => requestNavigation(() => void runCaseTask("Abrir vista previa", () => loadReportPreview(id)))}
          onDownload={id => void runCaseTask("Descargar informe", () => downloadReport(id))} />
      </section>
    );
  }

  function renderLegalKnowledge() {
    return (
      <ModuleSurface className="" moduleId="legalKnowledge">
        <div className="section-head">
          <div>
            <h2>Biblioteca Legal Argentina</h2>
            <p>Perfiles CTF, normas argentinas registradas y aplicaci?n controlada al caso.</p>
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
            <FormField label="Buscar norma o describir incidente"><Input value={legalQuery} onChange={(e) => setLegalQuery(e.target.value)} placeholder="Buscar norma o describir incidente" /></FormField>
            <Button className="h-auto min-h-10 whitespace-normal icon-button" onClick={() => void runCaseTask("Operación del módulo", () => (searchLegal)())} title="Buscar" variant="outline" type="button" aria-label="Buscar"><Search size={18} /></Button>
          </div>
        </div>
        {legalApplyMessage && (
          <div className={`action-feedback ${legalApplyState}`} role="status" aria-live="polite" aria-atomic="true">
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
                  <small><strong>Fuente:</strong> {prettySpanish(item.source_title || "Fuente oficial registrada")} ? <a href={item.source_url} target="_blank" rel="noreferrer">ver oficial</a></small>
                </div>
                {item.precedents.length > 0 && <small>Jurisprudencia registrada: {item.precedents.length}</small>}
                {item.doctrine.length > 0 && <small>Doctrina registrada: {item.doctrine.length}</small>}
                <div className="button-row">
                  <Button onClick={() => void runCaseTask("Operación del módulo", () => (() => decideLegalRecommendation(item, "aprobado"))())} disabled={(!selectedCaseId) || !(canCase("write", "legal:write")) || Boolean(caseTask)} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">
                    <CheckCircle2 size={16} /> Aplicar al caso
                  </Button>
                  <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Operación del módulo", () => (() => decideLegalRecommendation(item, "descartado"))())} disabled={(!selectedCaseId) || !(canCase("write", "legal:write")) || Boolean(caseTask)} variant="outline" type="button">
                    <Trash2 size={16} /> Descartar
                  </Button>
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
                <span>{item.legal_role || item.legal_area} ? confianza {item.confidence_level}</span>
                <em>{item.analyst_name || "Analista no informado"}</em>
                <small>{prettySpanish(item.analysis)}</small>
                {item.decision_status === "aprobado" && (
                  <div className="button-row">
                    <FormField label="Evidencia para vincular"><select
                      value={legalEvidenceSelection[item.id] || ""}
                      onChange={(e) => setLegalEvidenceSelection({ ...legalEvidenceSelection, [item.id]: e.target.value })}
                    >
                      <option value="">Seleccionar evidencia del caso activo</option>
                      {evidence.map((ev) => (
                        <option key={ev.id} value={ev.id}>#{ev.id} {ev.description}</option>
                      ))}
                    </select></FormField>
                    <FormField label="Elemento legal para vincular"><select
                      value={legalElementSelection[item.id] || ""}
                      onChange={(e) => setLegalElementSelection({ ...legalElementSelection, [item.id]: e.target.value })}
                    >
                      <option value="">Elemento legal a sostener</option>
                      {elementOptions.map((element) => (
                        <option key={element} value={element}>{prettySpanish(element)}</option>
                      ))}
                    </select></FormField>
                    <Button onClick={() => void runCaseTask("Operación del módulo", () => (() => linkEvidenceToLegalMapping(item))())} disabled={(!evidence.length) || !(canCase("write", "legal:write")) || Boolean(caseTask)} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">
                      <FileCheck2 size={16} /> Vincular evidencia
                    </Button>
                    <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Operación del módulo", () => (() => changeLegalMappingDecision(item, "descartado"))())} variant="outline" type="button" disabled={!(canCase("write", "legal:write")) || Boolean(caseTask)}>
                      <Trash2 size={16} /> Quitar artículo
                    </Button>
                  </div>
                )}
                {item.decision_status === "descartado" && (
                  <div className="button-row">
                    <Button onClick={() => void runCaseTask("Operación del módulo", () => (() => changeLegalMappingDecision(item, "aprobado"))())} variant="default" type="button" disabled={!(canCase("write", "legal:write")) || Boolean(caseTask)} className="h-auto min-h-10 whitespace-normal">
                      <CheckCircle2 size={16} /> Reactivar artículo
                    </Button>
                  </div>
                )}
                {legalMappingEvidence.filter((link) => link.legal_mapping_id === item.id).map((link) => {
                  const ev = evidence.find((e) => e.id === link.evidence_id);
                  const draft = legalLinkDrafts[link.id] || {};
                  const current = { ...link, ...draft };
                  return (
                    <div className="inline-editor" key={link.id}>
                      Evidencia vinculada: #{link.evidence_id} {ev?.description || ""} · {link.legal_element} · fuerza {link.probatory_strength}
                      <FormField label="Elemento legal"><Input value={current.legal_element || ""} onChange={(event) => setLegalLinkDrafts({ ...legalLinkDrafts, [link.id]: { ...draft, legal_element: event.target.value } })} placeholder="Elemento legal" /></FormField>
                      <FormField label="Estado del elemento legal"><select value={current.element_status || "pendiente"} onChange={(event) => setLegalLinkDrafts({ ...legalLinkDrafts, [link.id]: { ...draft, element_status: event.target.value } })}>
                        <option value="probado">Probado</option>
                        <option value="debil">Débil</option>
                        <option value="faltante">Faltante</option>
                        <option value="controvertido">Controvertido</option>
                        <option value="pendiente">Pendiente</option>
                      </select></FormField>
                      <FormField label="Fuerza probatoria"><select value={current.probatory_strength || "medio"} onChange={(event) => setLegalLinkDrafts({ ...legalLinkDrafts, [link.id]: { ...draft, probatory_strength: event.target.value } })}>
                        <option value="alto">Fuerza alta</option>
                        <option value="medio">Fuerza media</option>
                        <option value="bajo">Fuerza baja</option>
                      </select></FormField>
                      <FormField label="Riesgo de contradicción"><select value={current.contradiction_risk || "bajo"} onChange={(event) => setLegalLinkDrafts({ ...legalLinkDrafts, [link.id]: { ...draft, contradiction_risk: event.target.value } })}>
                        <option value="bajo">Riesgo bajo</option>
                        <option value="medio">Riesgo medio</option>
                        <option value="alto">Riesgo alto</option>
                        <option value="crítico">Riesgo crítico</option>
                      </select></FormField>
                      <FormField label="Evidencia faltante"><Input value={current.missing_evidence || ""} onChange={(event) => setLegalLinkDrafts({ ...legalLinkDrafts, [link.id]: { ...draft, missing_evidence: event.target.value } })} placeholder="Evidencia faltante" /></FormField>
                      <FormField label="Medida recomendada"><Input value={current.recommended_measure || ""} onChange={(event) => setLegalLinkDrafts({ ...legalLinkDrafts, [link.id]: { ...draft, recommended_measure: event.target.value } })} placeholder="Medida recomendada" /></FormField>
                      <div className="button-row">
                        <Button onClick={() => void runCaseTask("Operación del módulo", () => (() => saveLegalLink(link))())} variant="default" type="button" disabled={!(canCase("write", "legal:write")) || Boolean(caseTask)} className="h-auto min-h-10 whitespace-normal"><Save size={16} /> Guardar vínculo</Button>
                        <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Operación del módulo", () => (() => unlinkLegalEvidence(link.id))())} variant="outline" type="button" disabled={!(canCase("write", "legal:write")) || Boolean(caseTask)}><Trash2 size={16} /> Desvincular</Button>
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
                <span>{row.element_status} ? fuerza {row.probatory_strength} ? riesgo {row.contradiction_risk}</span>
                {row.evidence_id && <small>#{row.evidence_id} {row.evidence_description} {row.evidence_hash ? ` · SHA-256 ${row.evidence_hash}` : ""}</small>}
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
            {legalQualityControl && <span className="badge">Score {legalQualityControl.score} ? riesgo {legalQualityControl.risk_level}</span>}
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
      </ModuleSurface>
    );
  }

  function renderCybercrime() {
    return (
      <ModuleSurface className="cyber-workbench" moduleId="cybercrime">
        <div className="section-head">
          <div>
            <h2>Cybercrime Workbench</h2>
            <p>Flujo guiado para analizar indicadores, registrar sesiones controladas y guardar conclusiones tecnicas por caso.</p>
          </div>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={refreshCybercrime} variant="outline" type="button"><RefreshCcw size={16} /> Actualizar</Button>
        </div>

        {cyberDashboard && <MetricGrid metrics={cyberDashboard as unknown as Record<string, number>} />}

        <div className="split">
          <div className="form cyber-analysis-panel">
            <h3>Paso 1 - Analizar indicador</h3>
            <p className="muted">Carga una IP, URL, dominio, correo o hash. OPERIA lo clasifica, estima riesgo y sugiere medidas de preservación.</p>
            <FormField label="IP, URL, dominio, email o hash"><Input value={indicator} onChange={(event) => setIndicator(event.target.value)} placeholder="IP, URL, dominio, email o hash" /></FormField>
            <Button onClick={() => void runCaseTask("Operación del módulo", () => (analyzeIndicator)())} disabled={(!indicator.trim()) || !(canCase("analysis", "evidence:write")) || Boolean(caseTask)} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">
              <Search size={17} /> Analizar indicador
            </Button>
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

          <Card className="detail-panel">
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
                <p className="muted">Que significa: este resultado orienta la investigacion. No prueba autoría y debe vincularse con evidencia, custodia y fuentes verificables.</p>
              </div>
            ) : <EmptyState text="Sin análisis de indicador todavía." />}
          </Card>
        </div>

        <div className="detail-grid">
          <form className="detail-panel" onSubmit={event => { event.preventDefault(); void runCaseTask("Guardar datos del módulo", () => createCyberLabSession(event)); }}><fieldset disabled={!(canCase("analysis", "evidence:write")) || Boolean(caseTask)}><legend className="sr-only">Datos de la operación</legend>
            <div className="panel-head">
              <h3>Paso 2 - Crear sesion de laboratorio</h3>
            </div>
            <FormField label="Título de sesión"><Input placeholder="Título de sesión" value={cyberLabForm.title} onChange={(e) => setCyberLabForm({ ...cyberLabForm, title: e.target.value })} /></FormField>
            <div className="inline-grid">
              <FormField label="Propósito"><Input placeholder="Propósito" value={cyberLabForm.purpose} onChange={(e) => setCyberLabForm({ ...cyberLabForm, purpose: e.target.value })} /></FormField>
              <FormField label="Nivel de riesgo"><select value={cyberLabForm.risk_level} onChange={(e) => setCyberLabForm({ ...cyberLabForm, risk_level: e.target.value })}>
                <option value="bajo">Riesgo bajo</option>
                <option value="medio">Riesgo medio</option>
                <option value="alto">Riesgo alto</option>
              </select></FormField>
            </div>
            <FormField label="Operador"><Input placeholder="Operador" value={cyberLabForm.operator} onChange={(e) => setCyberLabForm({ ...cyberLabForm, operator: e.target.value })} /></FormField>
            <Button disabled={!selectedCaseId} variant="default" type="submit" className="h-auto min-h-10 whitespace-normal"><BrainCircuit size={17} /> Crear sesión controlada</Button>
          </fieldset></form>

          <form className="detail-panel" onSubmit={event => { event.preventDefault(); void runCaseTask("Guardar datos del módulo", () => createCyberProofRow(event)); }}><fieldset disabled={!(canCase("analysis", "evidence:write")) || Boolean(caseTask)}><legend className="sr-only">Datos de la operación</legend>
            <div className="panel-head">
              <h3>Paso 3 - Guardar conclusion defensible</h3>
            </div>
            <FormField label="Conclusión técnica prudente"><textarea placeholder="Conclusión técnica prudente" value={cyberProofForm.defensible_conclusion} onChange={(e) => setCyberProofForm({ ...cyberProofForm, defensible_conclusion: e.target.value })} /></FormField>
            <FormField label="Encuadre o relación legal preliminar"><textarea placeholder="Encuadre o relación legal preliminar" value={cyberProofForm.legal_framing} onChange={(e) => setCyberProofForm({ ...cyberProofForm, legal_framing: e.target.value })} /></FormField>
            <div className="inline-grid">
              <FormField label="Nivel de confianza"><select value={cyberProofForm.confidence_level} onChange={(e) => setCyberProofForm({ ...cyberProofForm, confidence_level: e.target.value })}>
                <option value="bajo">Confianza baja</option>
                <option value="medio">Confianza media</option>
                <option value="alto">Confianza alta</option>
              </select></FormField>
              <FormField label="Debilidad o límite probatorio"><Input placeholder="Debilidad o límite probatorio" value={cyberProofForm.weakness} onChange={(e) => setCyberProofForm({ ...cyberProofForm, weakness: e.target.value })} /></FormField>
            </div>
            <Button disabled={!selectedCaseId} variant="default" type="submit" className="h-auto min-h-10 whitespace-normal"><FileCheck2 size={17} /> Guardar en matriz cybercrime</Button>
          </fieldset></form>
        </div>

        <div className="detail-grid">
          <Card className="detail-panel">
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
          </Card>

          <Card className="detail-panel">
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
          </Card>
        </div>
      </ModuleSurface>
    );
  }

  function renderDeepfakeMedia() {
    const checklistDone = deepfakeChecklist.filter((item) => deepfakeChecklistState[item.key]).length;
    const deepfakeReadiness = deepfakeAnalyses.map((analysis) => deepfakeAnalysisReadiness(analysis));
    const readyDeepfake = deepfakeReadiness.filter((item) => item.status === "listo").length;
    const linkedDeepfake = deepfakeAnalyses.filter((item) => item.evidence_id).length;
    const withFindings = deepfakeAnalyses.filter((item) => item.finding_id).length;
    return (
      <ModuleSurface className="cyber-workbench" moduleId="deepfakeMedia">
        <div className="section-head">
          <div>
            <h2>Deepfake / Medios</h2>
            <p>Laboratorio local para registrar autenticación preliminar de imagen, video, audio, documento o captura sin afirmar conclusiones absolutas.</p>
          </div>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={refreshCybercrime} variant="outline" type="button"><RefreshCcw size={16} /> Actualizar</Button>
        </div>

        {deepfakeMessage && <div className={`action-feedback ${deepfakeState}`} role="status" aria-live="polite" aria-atomic="true">{deepfakeMessage}</div>}

        <div className="module-guidance">
          <div>
            <span>Uso pericial</span>
            <strong>Autenticar y documentar medios antes de afirmar manipulación o autoría.</strong>
          </div>
          <div>
            <span>Próximo paso</span>
            <strong>{deepfakeAnalyses.length ? "Crear hallazgo y aplicar normas si corresponde." : "Vincular evidencia y registrar origen, metadatos y límites."}</strong>
          </div>
          <div>
            <span>Salida al informe</span>
            <strong>{readyDeepfake ? `${readyDeepfake} análisis listo(s)` : "Pendiente de sustento"}</strong>
          </div>
        </div>

        <div className="risk-card medium blockchain-risk-row">
          <div><span>Análisis</span><strong>{deepfakeAnalyses.length}</strong></div>
          <div><span>Con evidencia</span><strong>{linkedDeepfake}</strong></div>
          <div><span>Hallazgos</span><strong>{withFindings}</strong></div>
          <div><span>Listos para informe</span><strong>{readyDeepfake}</strong></div>
        </div>

        <div className="split deepfake-layout">
          <form className="form deepfake-form" onSubmit={event => { event.preventDefault(); void runCaseTask("Guardar datos del módulo", () => saveDeepfakeAnalysis(event)); }}><fieldset disabled={!(canCase("analysis", "evidence:write") && canCase("evidence", "evidence:write")) || Boolean(caseTask)}><legend className="sr-only">Datos de la operación</legend>
            <h3>Registrar análisis de medio</h3>
            <div className="inline-grid">
              <FormField label="Tipo de medio"><select value={deepfakeForm.media_type} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, media_type: e.target.value })}>
                <option value="imagen">Imagen</option>
                <option value="video">Video</option>
                <option value="audio">Audio</option>
                <option value="documento">Documento</option>
                <option value="captura">Captura</option>
              </select></FormField>
              <FormField label="Evidencia asociada"><select value={deepfakeForm.evidence_id} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, evidence_id: e.target.value })}>
                <option value="">Sin evidencia vinculada</option>
                {evidence.map((item) => (
                  <option key={item.id} value={item.id}>#{item.id} - {item.description.slice(0, 60)}</option>
                ))}
              </select></FormField>
            </div>
            <FormField label="Origen del archivo, URL, publicación o soporte"><Input placeholder="Origen del archivo, URL, publicación o soporte" value={deepfakeForm.source_origin} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, source_origin: e.target.value })} /></FormField>
            <FormField label="Herramienta usada"><Input placeholder="Herramienta usada" value={deepfakeForm.tool_used} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, tool_used: e.target.value })} /></FormField>
            <FormField label="Resumen de metadatos EXIF/media"><textarea placeholder="Resumen de metadatos EXIF/media" value={deepfakeForm.metadata_summary} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, metadata_summary: e.target.value })} /></FormField>
            <FormField label="Hallazgos técnicos observados"><textarea placeholder="Hallazgos técnicos observados" value={deepfakeForm.findings} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, findings: e.target.value })} /></FormField>
            <FormField label="Limitaciones del análisis"><textarea placeholder="Limitaciones del análisis" value={deepfakeForm.limitations} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, limitations: e.target.value })} /></FormField>
            <FormField label="Clasificación del análisis"><select value={deepfakeForm.classification} onChange={(e) => setDeepfakeForm({ ...deepfakeForm, classification: e.target.value })}>
              <option value="auténtico preliminar">Auténtico preliminar</option>
              <option value="manipulado probable">Manipulado probable</option>
              <option value="indicios de edición">Indicios de edición</option>
              <option value="no concluyente">No concluyente</option>
              <option value="requiere pericia especializada">Requiere pericia especializada</option>
            </select></FormField>
            <Button disabled={!selectedCaseId || deepfakeState === "saving"} variant="default" type="submit" className="h-auto min-h-10 whitespace-normal"><Save size={17} /> Guardar análisis</Button>
          </fieldset></form>

          <Card className="detail-panel">
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
          </Card>
        </div>

        <div className="article-list deepfake-results">
          {deepfakeAnalyses.map((analysis) => {
            const quality = deepfakeAnalysisReadiness(analysis);
            return (
              <article key={analysis.id}>
                <div className="panel-head">
                  <div>
                    <span>{analysis.media_type} · {analysis.classification}</span>
                    <h3>Análisis #{analysis.id} {analysis.evidence_id ? ` ? Evidencia #${analysis.evidence_id}` : ""}</h3>
                  </div>
                  <div className="route-status-stack">
                    <span className={`readiness-badge ${quality.status}`}>{quality.score}/100 · {quality.status}</span>
                    <span className="badge">{analysis.finding_id ? `Hallazgo #${analysis.finding_id}` : "Sin hallazgo"}</span>
                  </div>
                </div>
                <p>{analysis.findings || "Sin hallazgos concluyentes cargados."}</p>
                <div className="pericial-reading-grid">
                  <div>
                    <strong>Qué acredita</strong>
                    <span>Preserva una observación técnica sobre imagen, video, audio, documento o captura vinculada al caso.</span>
                  </div>
                  <div>
                    <strong>Qué no acredita por sí solo</strong>
                    <span>Autoría, autenticidad definitiva, falsedad penal o identidad del generador sin pericia y corroboración externa.</span>
                  </div>
                  <div>
                    <strong>Qué hacer ahora</strong>
                    <span>{quality.status === "listo" ? "Puede pasar al informe con límites periciales." : `Completar: ${quality.missing.slice(0, 3).join(", ") || "validación"}.`}</span>
                  </div>
                </div>
                <div className="legal-card-grid">
                  <small>Hash: {analysis.evidence_hash || "pendiente"}</small>
                  <small>Origen: {analysis.source_origin || "pendiente"}</small>
                  <small>Herramienta: {analysis.tool_used || "pendiente"}</small>
                  <small>Limitaciones: {analysis.limitations || "requiere pericia especializada"}</small>
                </div>
                <div className="mini-readiness">
                  {quality.checks.map((check) => (
                    <span className={check.ok ? "ok" : "missing"} key={check.key}>{check.ok ? "✓" : "•"} {check.label}</span>
                  ))}
                </div>
                <div className="mini-list">
                  {analysis.checklist.filter((item) => item.ok).map((item) => <span key={item.key}>{item.label}</span>)}
                  {!analysis.checklist.some((item) => item.ok) && <span>Checklist pendiente.</span>}
                </div>
                <p className="notice">{analysis.warning}</p>
                <div className="actions-line">
                  <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Operación del módulo", () => (() => createDeepfakeFinding(analysis.id))())} variant="outline" type="button" disabled={!(canCase("analysis", "evidence:write")) || Boolean(caseTask)}><FileCheck2 size={16} /> Crear hallazgo</Button>
                  <Button onClick={() => void runCaseTask("Operación del módulo", () => (() => applyDeepfakeLegal(analysis))())} variant="default" type="button" disabled={!(canCase("analysis", "evidence:write") && canUse("legal:write")) || Boolean(caseTask)} className="h-auto min-h-10 whitespace-normal"><Gavel size={16} /> Aplicar normas sugeridas</Button>
                </div>
              </article>
            );
          })}
          {!deepfakeAnalyses.length && <EmptyState text="Sin análisis de medios registrados para el caso seleccionado." />}
        </div>
      </ModuleSurface>
    );
  }

  function renderBlockchainForensics() {
    const highRisk = blockchainTransactions.filter((item) => ["mixer", "bridge", "contrato inteligente"].includes(item.wallet_classification)).length;
    const linked = blockchainTransactions.filter((item) => item.evidence_id).length;
    const withExplorer = blockchainTransactions.filter((item) => item.explorer_url).length;
    const includedInReport = blockchainTransactions.filter((item) => item.include_in_report).length;
    const readiness = blockchainTransactions.map((item) => ({ item, quality: blockchainTransactionReadiness(item) }));
    const readyTransactions = readiness.filter((entry) => entry.quality.status === "listo").length;
    const draftChecklist = blockchainDraftReadiness(blockchainForm);
    const explorer = getBlockchainExplorer(blockchainForm.blockchain);
    const draftTxUrl = buildBlockchainUrl(blockchainForm.blockchain, "tx", blockchainForm.tx_hash);
    const draftSourceUrl = buildBlockchainUrl(blockchainForm.blockchain, "source", blockchainForm.source_wallet);
    const draftDestinationUrl = buildBlockchainUrl(blockchainForm.blockchain, "destination", blockchainForm.destination_wallet);
    const blockchainGraph = buildBlockchainGraph(blockchainTransactions);
    const routeOverview = blockchainRouteOverview(blockchainTransactions);
    const moduleReadinessItems = [
      { label: "Transacción o wallet registrada", ok: blockchainTransactions.length > 0 },
      { label: "Evidencia preservada vinculada", ok: linked > 0 },
      { label: "Explorador o fuente documentada", ok: withExplorer > 0 },
      { label: "Hallazgo técnico creado", ok: blockchainTransactions.some((item) => item.finding_id) },
      { label: "Normas aplicadas desde biblioteca", ok: blockchainTransactions.some((item) => item.legal_mapping_ids.length > 0) },
      { label: "Saltos seleccionados para informe", ok: includedInReport > 0 },
      { label: "Ruta lista para informe", ok: readyTransactions > 0 }
    ];
    const moduleScore = Math.round((moduleReadinessItems.filter((item) => item.ok).length / moduleReadinessItems.length) * 100);
    const moduleStatus = moduleScore >= 80 ? "listo" : moduleScore >= 50 ? "parcial" : "incompleto";

    return (
      <ModuleSurface className="cyber-workbench blockchain-lab" moduleId="blockchainForensics">
        <div className="section-head">
          <div>
            <h2>Blockchain Investigation Lab</h2>
            <p>Laboratorio guiado para documentar transacciones, wallets, exploradores consultados, ruta probable, evidencia y límites de atribución.</p>
          </div>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={refreshCybercrime} variant="outline" type="button"><RefreshCcw size={16} /> Actualizar</Button>
        </div>

        {blockchainMessage && <div className={`action-feedback ${blockchainState}`} role="status" aria-live="polite" aria-atomic="true">{blockchainMessage}</div>}

        <div className="module-guidance">
          <div>
            <span>Objetivo del laboratorio</span>
            <strong>Reconstruir movimientos, wallets, saltos y fuentes preservadas.</strong>
          </div>
          <div>
            <span>Próximo paso</span>
            <strong>{blockchainTransactions.length ? "Ordenar saltos, crear hallazgos y vincular evidencia." : "Registrar hash, wallet, explorador, monto y captura preservada."}</strong>
          </div>
          <div>
            <span>Límite pericial</span>
            <strong>Una wallet no identifica por sí sola a una persona.</strong>
          </div>
        </div>

        <div className="risk-card medium blockchain-risk-row">
          <div><span>Transacciones</span><strong>{blockchainTransactions.length}</strong></div>
          <div><span>Con evidencia</span><strong>{linked}</strong></div>
          <div><span>Con explorador</span><strong>{withExplorer}</strong></div>
          <div><span>En informe</span><strong>{includedInReport}</strong></div>
          <div><span>Listas</span><strong>{readyTransactions}</strong></div>
          <div><span>Riesgo reforzado</span><strong>{highRisk}</strong></div>
          <div><span>Valor documentado</span><strong>{formatMoneyARS(routeOverview.totalARS)}</strong></div>
        </div>

        <div className="blockchain-steps">
          <article>
            <span>Paso 1</span>
            <strong>Identificar dato blockchain</strong>
            <p>Hash, wallet, red, token, monto y fecha. Preserva captura, URL y hora de consulta.</p>
          </article>
          <article>
            <span>Paso 2</span>
            <strong>Documentar trazabilidad</strong>
            <p>Origen, destino, servicio observado, hipótesis de ruta y punto donde se debilita la trazabilidad.</p>
          </article>
          <article>
            <span>Paso 3</span>
            <strong>Enviar al informe</strong>
            <p>Crea hallazgo, aplica normas y vincula evidencia para que el informe lo use con sustento.</p>
          </article>
        </div>

        <div className="split blockchain-layout">
          <form className="form blockchain-form" onSubmit={event => { event.preventDefault(); void runCaseTask("Guardar datos del módulo", () => saveBlockchainTransaction(event)); }}><fieldset disabled={!(canCase("analysis", "evidence:write") && canCase("evidence", "evidence:write")) || Boolean(caseTask)}><legend className="sr-only">Datos de la operación</legend>
            <div className="panel-head">
              <div>
                <h3>{editingBlockchainId ? `Editar salto #${editingBlockchainId}` : "Registrar transacción blockchain"}</h3>
                <p>Carga solo datos observados o preservados. La atribución personal exige evidencia externa.</p>
              </div>
              <span className="badge">{explorer.label}</span>
            </div>
            {editingBlockchainId && (
              <div className="notice">
                Estás editando una transacción existente. Al guardar, OPERIA registrará la actualización en custodia.
              </div>
            )}
            <div className="inline-grid">
              <FormField label="Red blockchain"><select value={blockchainForm.blockchain} onChange={(e) => setBlockchainForm({ ...blockchainForm, blockchain: e.target.value })}>
                {blockchainExplorerCatalog.map((item) => <option value={item.label} key={item.key}>{item.label}</option>)}
                <option value="Otra red">Otra red</option>
              </select></FormField>
              <FormField label="Token o activo"><Input placeholder="Token o activo" value={blockchainForm.token} onChange={(e) => setBlockchainForm({ ...blockchainForm, token: e.target.value })} /></FormField>
            </div>
            <FormField label="Hash de transacción"><Input placeholder="Hash de transacción" value={blockchainForm.tx_hash} onChange={(e) => setBlockchainForm({ ...blockchainForm, tx_hash: e.target.value })} /></FormField>
            <div className="inline-grid">
              <FormField label="Wallet origen"><Input placeholder="Wallet origen" value={blockchainForm.source_wallet} onChange={(e) => setBlockchainForm({ ...blockchainForm, source_wallet: e.target.value })} /></FormField>
              <FormField label="Wallet destino"><Input placeholder="Wallet destino" value={blockchainForm.destination_wallet} onChange={(e) => setBlockchainForm({ ...blockchainForm, destination_wallet: e.target.value })} /></FormField>
            </div>
            <div className="inline-grid">
              <FormField label="Monto"><Input placeholder="Monto" type="number" step="any" value={blockchainForm.amount} onChange={(e) => setBlockchainForm({ ...blockchainForm, amount: e.target.value })} /></FormField>
              <FormField label="Valor aproximado en ARS"><Input placeholder="Valor aproximado en ARS" type="number" step="any" value={blockchainForm.approximate_value} onChange={(e) => setBlockchainForm({ ...blockchainForm, approximate_value: e.target.value })} /></FormField>
            </div>
            <div className="inline-grid">
              <FormField label="Fecha/hora observada"><Input placeholder="Fecha/hora observada" value={blockchainForm.tx_datetime} onChange={(e) => setBlockchainForm({ ...blockchainForm, tx_datetime: e.target.value })} /></FormField>
              <FormField label="Clasificación de la billetera"><select value={blockchainForm.wallet_classification} onChange={(e) => setBlockchainForm({ ...blockchainForm, wallet_classification: e.target.value })}>
                {walletClassifications.map((item) => <option value={item} key={item}>{prettySpanish(item)}</option>)}
              </select></FormField>
            </div>
            <div className="inline-grid">
              <FormField label="Orden en la ruta. Ej: 1, 2, 3"><Input
                placeholder="Orden en la ruta. Ej: 1, 2, 3"
                type="number"
                min="0"
                value={blockchainForm.route_order}
                onChange={(e) => setBlockchainForm({ ...blockchainForm, route_order: e.target.value })}
              /></FormField>
              <label className={`toggle-row ${blockchainForm.include_in_report ? "checked" : ""}`}>
                <input
                  type="checkbox"
                  checked={Boolean(blockchainForm.include_in_report)}
                  onChange={(e) => setBlockchainForm({ ...blockchainForm, include_in_report: e.target.checked })}
                />
                <span>Incorporar este salto al informe final</span>
              </label>
            </div>
            <FormField label="Evidencia asociada"><select value={blockchainForm.evidence_id} onChange={(e) => setBlockchainForm({ ...blockchainForm, evidence_id: e.target.value })}>
              <option value="">Sin evidencia vinculada</option>
              {evidence.map((item) => (
                <option key={item.id} value={item.id}>#{item.id} - {item.description.slice(0, 60)}</option>
              ))}
            </select></FormField>
            <div className="inline-grid">
              <FormField label="URL del explorador preservada"><Input placeholder="URL del explorador preservada" value={blockchainForm.explorer_url} onChange={(e) => setBlockchainForm({ ...blockchainForm, explorer_url: e.target.value })} /></FormField>
              <Button
                className="h-auto min-h-10 whitespace-normal secondary-button"
                type="button"
                onClick={() => setBlockchainForm({ ...blockchainForm, explorer_url: draftTxUrl })}
                disabled={!blockchainForm.tx_hash.trim()} variant="outline"
              >
                <Globe2 size={16} /> Usar URL sugerida
              </Button>
            </div>
            <FormField label="Herramienta usada / explorador / método"><Input placeholder="Herramienta usada / explorador / método" value={blockchainForm.tool_used} onChange={(e) => setBlockchainForm({ ...blockchainForm, tool_used: e.target.value })} /></FormField>
            <div className="preservation-card">
              <strong>Acta mínima de consulta</strong>
              <span>Fuente: {blockchainForm.explorer_url || "URL del explorador pendiente"}</span>
              <span>Fecha/hora: {blockchainForm.tx_datetime || "pendiente"}</span>
              <span>Evidencia vinculada: {blockchainForm.evidence_id ? `#${blockchainForm.evidence_id}` : "pendiente"}</span>
              <span>Analista: {analystName || identitySession.user?.name || "Analista local"}</span>
            </div>
            <FormField label="Hipótesis de ruta: origen, destino, intermediarios, exchange, mixer o punto de pérdida de trazabilidad"><textarea placeholder="Hipótesis de ruta: origen, destino, intermediarios, exchange, mixer o punto de pérdida de trazabilidad" value={blockchainForm.route_hypothesis} onChange={(e) => setBlockchainForm({ ...blockchainForm, route_hypothesis: e.target.value })} /></FormField>
            <FormField label="Limitaciones y evidencia faltante: KYC, IPs, comunicaciones, registros de plataforma, capturas o pericia complementaria"><textarea placeholder="Limitaciones y evidencia faltante: KYC, IPs, comunicaciones, registros de plataforma, capturas o pericia complementaria" value={blockchainForm.limitations} onChange={(e) => setBlockchainForm({ ...blockchainForm, limitations: e.target.value })} /></FormField>
            <div className="button-row">
              <Button disabled={!selectedCaseId || !blockchainForm.tx_hash.trim() || blockchainState === "saving"} variant="default" type="submit" className="h-auto min-h-10 whitespace-normal">
                <Save size={17} /> {editingBlockchainId ? "Actualizar salto documentado" : "Guardar transacción documentada"}
              </Button>
              {editingBlockchainId && (
                <Button className="h-auto min-h-10 whitespace-normal secondary-button" type="button" onClick={cancelBlockchainEdit} variant="outline">
                  Cancelar edición
                </Button>
              )}
            </div>
          </fieldset></form>

          <Card className="detail-panel blockchain-guide">
            <div className="panel-head">
              <div>
                <h3>Exploradores y preservación</h3>
                <p>Los botones abren sitios externos en forma manual. No subas evidencia sensible sin autorización.</p>
              </div>
              <span className="badge">Salida controlada</span>
            </div>
            <div className="actions-line explorer-actions">
              <a className="button-link" href={draftTxUrl} target="_blank" rel="noreferrer"><Globe2 size={16} /> Ver transacción</a>
              <a className="button-link secondary-link" href={draftSourceUrl} target="_blank" rel="noreferrer"><Globe2 size={16} /> Wallet origen</a>
              <a className="button-link secondary-link" href={draftDestinationUrl} target="_blank" rel="noreferrer"><Globe2 size={16} /> Wallet destino</a>
            </div>
            <div className="trace-preview">
              <div>
                <span>Origen</span>
                <strong>{blockchainForm.source_wallet || "Wallet origen pendiente"}</strong>
              </div>
              <div className="trace-arrow">→</div>
              <div>
                <span>Destino</span>
                <strong>{blockchainForm.destination_wallet || "Wallet destino pendiente"}</strong>
              </div>
            </div>
            <div className={`preservation-checklist ${draftChecklist.ready ? "ready" : "pending"}`}>
              <div>
                <strong>Checklist de preservación previo al registro</strong>
                <span>{draftChecklist.score}/100 · {draftChecklist.ready ? "Registro suficientemente documentado" : "Completar antes de usar en informe final"}</span>
              </div>
              <div className="forensic-check-grid">
                {draftChecklist.checks.map((check) => (
                  <span className={check.ok ? "ok" : check.critical ? "missing critical" : "missing"} key={check.key}>
                    {check.ok ? "✓" : "•"} {check.label}
                  </span>
                ))}
              </div>
              {draftChecklist.criticalMissing.length > 0 && (
                <div className="missing-strip">
                  <strong>Faltantes críticos:</strong>
                  <span>{draftChecklist.criticalMissing.join(" ? ")}</span>
                </div>
              )}
            </div>
            <div className="mini-readiness">
              {draftChecklist.checks.slice(0, 6).map((check) => (
                <span className={check.ok ? "ok" : "missing"} key={check.label}>
                  {check.ok ? "✓" : "•"} {check.label}
                </span>
              ))}
            </div>
            <ul className="compact-list">
              <li>Preservar captura del explorador, URL, fecha, hora y analista.</li>
              <li>Vincular la captura o comprobante como evidencia del caso.</li>
              <li>Identificar exchange, bridge, mixer o contrato inteligente si aparece.</li>
              <li>Solicitar datos de plataforma por vía legal si hay punto KYC.</li>
              <li>Evitar atribución personal solo por wallet, alias o hash.</li>
            </ul>
          </Card>
        </div>

        <div className={`detail-panel blockchain-readiness-panel ${moduleStatus}`}>
          <div className="panel-head">
            <div>
              <h3>Preparación pericial blockchain</h3>
              <p>Control rápido para saber si la sección blockchain puede pasar al informe con suficiente orden técnico.</p>
            </div>
            <span className={`readiness-badge ${moduleStatus}`}>
              {moduleScore}/100 · {moduleStatus === "listo" ? "Listo" : moduleStatus === "parcial" ? "Parcial" : "Incompleto"}
            </span>
          </div>
          <div className="forensic-check-grid">
            {moduleReadinessItems.map((item) => (
              <span className={item.ok ? "ok" : "missing"} key={item.label}>
                {item.ok ? "✓" : "•"} {item.label}
              </span>
            ))}
          </div>
        </div>

        <Card className="detail-panel blockchain-annex-preview">
          <div className="panel-head">
            <div>
              <h3>Anexo blockchain para informe</h3>
              <p>Resumen de los elementos que OPERIA incorporará al informe final si están vinculados al caso activo.</p>
            </div>
            <span className={`readiness-badge ${moduleStatus}`}>{moduleScore}/100</span>
          </div>
          <div className="annex-preview-grid">
            <div>
              <strong>Acta de consulta</strong>
              <span>{blockchainTransactions.filter((item) => item.explorer_url && item.tx_datetime).length}/{blockchainTransactions.length || 0} con URL y fecha/hora.</span>
            </div>
            <div>
              <strong>Soporte probatorio</strong>
              <span>{linked}/{blockchainTransactions.length || 0} transacciones con evidencia vinculada.</span>
            </div>
            <div>
              <strong>Ruta y grafo</strong>
              <span>{blockchainGraph.edges.length} salto(s), {blockchainGraph.repeatedWallets.length} wallet(s) de enlace.</span>
            </div>
            <div>
              <strong>Valor documentado</strong>
              <span>{formatMoneyARS(routeOverview.totalARS)}</span>
            </div>
          </div>
          <p className="notice">El anexo no atribuye identidad personal por sí solo: documenta trazabilidad económica, fuente consultada, límites y medidas pendientes.</p>
        </Card>

        <Card className="detail-panel blockchain-intel-panel">
          <div className="panel-head">
            <div>
              <h3>Suficiencia, puntos críticos y requerimientos</h3>
              <p>Lectura operativa de la ruta para saber qué falta antes de sostener trazabilidad, daño o atribución.</p>
            </div>
            <span className="badge">{routeOverview.readyCount}/{blockchainTransactions.length || 0} listo(s)</span>
          </div>
          <div className="blockchain-intel-grid">
            <div>
              <h4>Puntos críticos</h4>
              <div className="summary-list">
                {routeOverview.criticalFlags.slice(0, 8).map((flag, index) => <span key={`${flag}-${index}`}>{flag}</span>)}
                {!routeOverview.criticalFlags.length && <span>Sin puntos críticos pendientes en los registros cargados.</span>}
              </div>
            </div>
            <div>
              <h4>Requerimientos sugeridos</h4>
              <div className="summary-list">
                {routeOverview.recommendedRequests.map((item) => <span key={item}>{item}</span>)}
                {!routeOverview.recommendedRequests.length && <span>La ruta registrada no exige requerimientos adicionales automáticos.</span>}
              </div>
            </div>
            <div>
              <h4>Puntos de servicio</h4>
              <div className="summary-list">
                {routeOverview.servicePoints.map((item) => (
                  <span key={item.id}>#{item.id} {prettySpanish(item.wallet_classification)} · {shortBlockchainLabel(item.destination_wallet || item.source_wallet)}</span>
                ))}
                {!routeOverview.servicePoints.length && <span>No se registraron exchanges, mixers, bridges ni contratos inteligentes.</span>}
              </div>
            </div>
          </div>
        </Card>

        <Card className="detail-panel blockchain-graph-panel">
          <div className="panel-head">
            <div>
              <h3>Grafo multi-salto del caso</h3>
              <p>Visualiza conexiones entre wallets cargadas. Si un destino coincide con otro origen, OPERIA lo marca como punto de enlace investigativo.</p>
            </div>
            <span className="badge">{blockchainGraph.repeatedWallets.length ? `${blockchainGraph.repeatedWallets.length} wallet(s) de enlace` : "Sin enlaces repetidos"}</span>
          </div>
          {blockchainGraph.edges.length ? (
            <>
              <div className="graph-summary">
                <span><strong>{blockchainGraph.nodes.length}</strong> nodos</span>
                <span><strong>{blockchainGraph.edges.length}</strong> saltos</span>
                <span><strong>{blockchainGraph.repeatedWallets.length}</strong> enlaces</span>
                <span><strong>{blockchainGraph.serviceNodes.length}</strong> servicios o puntos críticos</span>
                <span><strong>{blockchainGraph.readyEdges}</strong> listos para informe</span>
              </div>
              <div className="blockchain-graph">
                {blockchainGraph.edges.map((edge, index) => (
                  <article className={`graph-hop ${edge.risk ? "risk" : ""} ${edge.readiness.status}`} key={edge.id}>
                    <div className={`graph-node ${blockchainGraph.repeatedWallets.some((node) => node.id === edge.source) ? "linked" : ""}`}>
                      <span>Origen</span>
                      <strong title={edge.source}>{edge.sourceLabel}</strong>
                    </div>
                    <div className="graph-edge">
                      <span>Salto {index + 1}</span>
                      <strong>{edge.amountLabel}</strong>
                      <small>{prettySpanish(edge.classification)} · {edge.readiness.score}/100 · {edge.txHashLabel}</small>
                    </div>
                    <div className={`graph-node ${edge.risk ? "service" : ""} ${blockchainGraph.repeatedWallets.some((node) => node.id === edge.target) ? "linked" : ""}`}>
                      <span>Destino</span>
                      <strong title={edge.target}>{edge.targetLabel}</strong>
                    </div>
                  </article>
                ))}
              </div>
              <div className="graph-legend">
                <span><i className="legend-dot ready" /> Listo</span>
                <span><i className="legend-dot partial" /> Requiere refuerzo</span>
                <span><i className="legend-dot risk" /> Mixer, bridge o contrato</span>
                <span><i className="legend-dot linked" /> Wallet enlaza saltos</span>
              </div>
              {blockchainGraph.repeatedWallets.length > 0 && (
                <div className="missing-strip">
                  <strong>Wallets que conectan saltos:</strong>
                  <span>{blockchainGraph.repeatedWallets.map((node) => node.label).join(" ? ")}</span>
                </div>
              )}
            </>
          ) : (
            <EmptyState text="Registra dos o más transacciones para visualizar una ruta multi-salto." />
          )}
        </Card>

        <Card className="detail-panel">
          <div className="panel-head">
            <div>
              <h3>Ruta de fondos documentada</h3>
              <p>Movimientos registrados para el caso activo y disponibles para informe si se convierten en hallazgo.</p>
            </div>
            <span className="badge">{blockchainTransactions.length ? `${blockchainTransactions.length} registro(s)` : "Sin registros"}</span>
          </div>
          <div className="blockchain-route-list">
            {readiness.map(({ item, quality }) => (
              <article className={`blockchain-route-card ${quality.status}`} key={item.id}>
                <div className="route-card-head">
                  <div>
                    <span>{item.blockchain} · {item.token}</span>
                    <h3>{item.amount} {item.token} · {formatMoneyARS(item.approximate_value)}</h3>
                    <small>{item.tx_datetime || "Fecha/hora pendiente"} · {item.tool_used || "Herramienta pendiente"}</small>
                  </div>
                  <div className="route-status-stack">
                    <span className={`badge ${["mixer", "bridge"].includes(item.wallet_classification) ? "blocked" : ""}`}>{prettySpanish(item.wallet_classification)}</span>
                    <span className={`readiness-badge ${quality.status}`}>{quality.label} · {quality.score}/100</span>
                  </div>
                </div>
                <div className="route-graph">
                  <div><span>Origen</span><strong>{item.source_wallet || "Pendiente"}</strong></div>
                  <div className="trace-arrow">→</div>
                  <div><span>Destino</span><strong>{item.destination_wallet || "Pendiente"}</strong></div>
                </div>
                <div className="route-meta">
                  <span>Hash: {item.tx_hash}</span>
                  <span>Orden de ruta: {item.route_order || "sin ordenar"}</span>
                  <span>{item.include_in_report ? "Incluida en informe" : "Excluida del informe"}</span>
                  <span>{item.evidence_id ? `Evidencia #${item.evidence_id}` : "Sin evidencia vinculada"}</span>
                  <span>{item.finding_id ? `Hallazgo #${item.finding_id}` : "Sin hallazgo"}</span>
                  <span>{item.legal_mapping_ids.length ? `${item.legal_mapping_ids.length} norma(s) aplicada(s)` : "Sin normas aplicadas"}</span>
                </div>
                <div className="pericial-reading-grid">
                  <div>
                    <strong>Qué acredita</strong>
                    <span>Movimiento o indicador económico observado en una red blockchain, condicionado por la fuente preservada.</span>
                  </div>
                  <div>
                    <strong>Qué no acredita por sí solo</strong>
                    <span>Identidad civil, autoría penal, dolo o control humano efectivo de la wallet.</span>
                  </div>
                  <div>
                    <strong>Qué hacer ahora</strong>
                    <span>{quality.status === "listo" ? "Puede integrarse al informe con sus límites." : `Completar: ${quality.missing.slice(0, 3).join(", ") || "validación pericial"}.`}</span>
                  </div>
                </div>
                <p>{item.route_hypothesis || "Hipótesis de ruta pendiente."}</p>
                <p className="notice">{item.limitations || item.warning}</p>
                {quality.missing.length > 0 && (
                  <div className="missing-strip">
                    <strong>Falta para sostener mejor:</strong>
                    <span>{quality.missing.slice(0, 5).join(" ? ")}</span>
                  </div>
                )}
                <div className="actions-line">
                  <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => editBlockchainTransaction(item)} variant="outline" type="button"><Save size={16} /> Editar salto</Button>
                  <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Operación del módulo", () => (() => toggleBlockchainReportInclusion(item))())} variant="outline" type="button" disabled={!(canCase("analysis", "evidence:write")) || Boolean(caseTask)}>
                    <FileText size={16} /> {item.include_in_report ? "Excluir del informe" : "Incorporar al informe"}
                  </Button>
                  <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Operación del módulo", () => (() => createBlockchainFinding(item.id))())} variant="outline" type="button" disabled={!(canCase("analysis", "evidence:write")) || Boolean(caseTask)}><FileCheck2 size={16} /> Crear hallazgo</Button>
                  <Button onClick={() => void runCaseTask("Operación del módulo", () => (() => applyBlockchainLegal(item))())} variant="default" type="button" disabled={!(canCase("analysis", "evidence:write") && canUse("legal:write")) || Boolean(caseTask)} className="h-auto min-h-10 whitespace-normal"><Gavel size={16} /> Aplicar normas</Button>
                  <Button onClick={() => void runCaseTask("Operación del módulo", () => (() => promoteBlockchainTransaction(item))())} variant="default" type="button" className="h-auto min-h-10 whitespace-normal"><FileCheck2 size={16} /> Hallazgo + normas</Button>
                  <a className="button-link secondary-link" href={buildBlockchainUrl(item.blockchain, "tx", item.tx_hash)} target="_blank" rel="noreferrer"><Globe2 size={16} /> Buscar hash</a>
                  <a className="button-link secondary-link" href={buildBlockchainUrl(item.blockchain, "source", item.source_wallet)} target="_blank" rel="noreferrer"><Globe2 size={16} /> Origen</a>
                  <a className="button-link secondary-link" href={buildBlockchainUrl(item.blockchain, "destination", item.destination_wallet)} target="_blank" rel="noreferrer"><Globe2 size={16} /> Destino</a>
                  {item.explorer_url && (
                    <a className="button-link" href={item.explorer_url} target="_blank" rel="noreferrer"><Globe2 size={16} /> Abrir explorador</a>
                  )}
                </div>
              </article>
            ))}
            {!blockchainTransactions.length && <EmptyState text="Sin transacciones blockchain registradas para el caso seleccionado." />}
          </div>
        </Card>
      </ModuleSurface>
    );
  }
  function renderIoTForensics() {
    const checklistDone = iotChecklist.filter((item) => iotChecklistState[item.key]).length;
    const linked = iotDevices.filter((item) => item.evidence_id).length;
    const readiness = iotDevices.map((item) => iotDeviceReadiness(item));
    const readyDevices = readiness.filter((item) => item.status === "listo").length;
    const withFindings = iotDevices.filter((item) => item.finding_id).length;
    return (
      <ModuleSurface className="cyber-workbench" moduleId="iotForensics">
        <div className="section-head">
          <div>
            <h2>IoT Forensics</h2>
            <p>Registro forense de dispositivos conectados, estado observable, evidencia, logs y límites sin ejecutar escaneos reales automáticamente.</p>
          </div>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={refreshCybercrime} variant="outline" type="button"><RefreshCcw size={16} /> Actualizar</Button>
        </div>

        {iotMessage && <div className={`action-feedback ${iotState}`} role="status" aria-live="polite" aria-atomic="true">{iotMessage}</div>}
        {!selectedCaseId && (
          <div className="action-feedback error" role="status" aria-live="polite" aria-atomic="true">
            Selecciona o crea un caso activo antes de registrar dispositivos IoT. Esta pantalla guarda el registro dentro del caso seleccionado.
          </div>
        )}

        <div className="module-guidance">
          <div>
            <span>Objetivo pericial</span>
            <strong>Preservar estado observable, identificadores, configuración, logs y límites.</strong>
          </div>
          <div>
            <span>Próximo paso</span>
            <strong>{iotDevices.length ? "Completar checklist, crear hallazgo y aplicar normas si corresponde." : "Registrar dispositivo y vincular evidencia preservada."}</strong>
          </div>
          <div>
            <span>Control de seguridad</span>
            <strong>No ejecutar escaneos reales sin autorización documentada.</strong>
          </div>
        </div>

        <div className="risk-card medium iot-risk-row">
          <div><span>Dispositivos</span><strong>{iotDevices.length}</strong></div>
          <div><span>Con evidencia</span><strong>{linked}</strong></div>
          <div><span>Hallazgos</span><strong>{withFindings}</strong></div>
          <div><span>Listos para informe</span><strong>{readyDevices}</strong></div>
          <div><span>Checklist actual</span><strong>{checklistDone}/{iotChecklist.length}</strong></div>
        </div>

        <div className="split iot-layout">
          <form className="form iot-form" onSubmit={event => { event.preventDefault(); void runCaseTask("Guardar datos del módulo", () => saveIoTDevice(event)); }}><fieldset disabled={!(canCase("analysis", "evidence:write") && canCase("evidence", "evidence:write")) || Boolean(caseTask)}><legend className="sr-only">Datos de la operación</legend>
            <div className="panel-head compact">
              <div>
                <h3>{editingIotId ? `Editar dispositivo #${editingIotId}` : "Registrar dispositivo"}</h3>
                <p>{editingIotId ? "Actualiza la ficha sin perder trazabilidad del caso." : "Carga datos observados, evidencia y límites del análisis."}</p>
              </div>
            </div>
            <div className="inline-grid">
              <FormField label="Tipo de dispositivo"><Input placeholder="Tipo de dispositivo" value={iotForm.device_type} onChange={(e) => setIotForm({ ...iotForm, device_type: e.target.value })} /></FormField>
              <FormField label="Fabricante"><Input placeholder="Fabricante" value={iotForm.manufacturer} onChange={(e) => setIotForm({ ...iotForm, manufacturer: e.target.value })} /></FormField>
            </div>
            <div className="inline-grid">
              <FormField label="Modelo"><Input placeholder="Modelo" value={iotForm.model} onChange={(e) => setIotForm({ ...iotForm, model: e.target.value })} /></FormField>
              <FormField label="Firmware"><Input placeholder="Firmware" value={iotForm.firmware} onChange={(e) => setIotForm({ ...iotForm, firmware: e.target.value })} /></FormField>
            </div>
            <div className="inline-grid">
              <FormField label="IP interna"><Input placeholder="IP interna" value={iotForm.internal_ip} onChange={(e) => setIotForm({ ...iotForm, internal_ip: e.target.value })} /></FormField>
              <FormField label="IP externa"><Input placeholder="IP externa" value={iotForm.external_ip} onChange={(e) => setIotForm({ ...iotForm, external_ip: e.target.value })} /></FormField>
            </div>
            <FormField label="MAC"><Input placeholder="MAC" value={iotForm.mac} onChange={(e) => setIotForm({ ...iotForm, mac: e.target.value })} /></FormField>
            <FormField label="Evidencia asociada"><select value={iotForm.evidence_id} onChange={(e) => setIotForm({ ...iotForm, evidence_id: e.target.value })}>
              <option value="">Sin evidencia vinculada</option>
              {evidence.map((item) => (
                <option key={item.id} value={item.id}>#{item.id} - {item.description.slice(0, 60)}</option>
              ))}
            </select></FormField>
            <FormField label="Puertos abiertos observados o declarados"><textarea placeholder="Puertos abiertos observados o declarados" value={iotForm.open_ports} onChange={(e) => setIotForm({ ...iotForm, open_ports: e.target.value })} /></FormField>
            <FormField label="Vulnerabilidades conocidas"><textarea placeholder="Vulnerabilidades conocidas" value={iotForm.known_vulnerabilities} onChange={(e) => setIotForm({ ...iotForm, known_vulnerabilities: e.target.value })} /></FormField>
            <FormField label="Logs disponibles"><textarea placeholder="Logs disponibles" value={iotForm.logs_available} onChange={(e) => setIotForm({ ...iotForm, logs_available: e.target.value })} /></FormField>
            <FormField label="Herramienta o metodología usada"><Input placeholder="Herramienta o metodología usada" value={iotForm.tool_used} onChange={(e) => setIotForm({ ...iotForm, tool_used: e.target.value })} /></FormField>
            <FormField label="Limitaciones"><textarea placeholder="Limitaciones" value={iotForm.limitations} onChange={(e) => setIotForm({ ...iotForm, limitations: e.target.value })} /></FormField>
            <Button disabled={!selectedCaseId || iotState === "saving"} variant="default" type="submit" className="h-auto min-h-10 whitespace-normal"><Save size={17} /> {editingIotId ? "Actualizar ficha IoT" : selectedCaseId ? "Guardar dispositivo" : "Selecciona un caso para guardar"}</Button>
            {editingIotId && (
              <Button
                type="button"
                className="h-auto min-h-10 whitespace-normal secondary-button"
                onClick={() => {
                  setEditingIotId(null);
                  setIotForm(emptyIoTForm);
                  setIotChecklistState(emptyIoTChecklist);
                  setIotMessage("Edición cancelada.");
                }} variant="outline"
              >
                Cancelar edición
              </Button>
            )}
          </fieldset></form>

          <Card className="detail-panel">
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
          </Card>
        </div>

        <Card className="detail-panel iot-readiness-panel">
          <div className="panel-head">
            <div>
              <h3>Dispositivos registrados</h3>
              <p>Ficha pericial por dispositivo, con límites, soporte probatorio y preparación para informe.</p>
            </div>
            <span className="badge">{readyDevices}/{iotDevices.length || 0} listos</span>
          </div>
          <div className="article-list iot-table">
            {iotDevices.map((item) => {
              const quality = iotDeviceReadiness(item);
              const identifiers = [
                item.internal_ip ? `IP interna ${item.internal_ip}` : "",
                item.external_ip ? `IP externa ${item.external_ip}` : "",
                item.mac ? `MAC ${item.mac}` : ""
              ].filter(Boolean).join(" · ") || "Identificadores de red pendientes";
              return (
                <article className="iot-row" key={item.id}>
                  <div className="panel-head">
                    <div>
                      <span>{prettySpanish(item.device_type || "Dispositivo IoT")}</span>
                      <h3>{item.manufacturer || "Fabricante pendiente"} {item.model || ""}</h3>
                    </div>
                    <div className="route-status-stack">
                      <span className={`readiness-badge ${quality.status}`}>{quality.score}/100 · {quality.status}</span>
                      <span className="badge">{item.finding_id ? `Hallazgo #${item.finding_id}` : "Sin hallazgo"}</span>
                    </div>
                  </div>
                  <div className="legal-card-grid">
                    <small>Firmware: {item.firmware || "pendiente"}</small>
                    <small>{identifiers}</small>
                    <small>{item.evidence_id ? `Evidencia #${item.evidence_id}` : "Sin evidencia vinculada"}</small>
                    <small>Hash: {item.evidence_hash || "pendiente"}</small>
                  </div>
                  <div className="pericial-reading-grid">
                    <div>
                      <strong>Qué acredita</strong>
                      <span>Estado observable del dispositivo, identificadores técnicos, configuración declarada, logs disponibles y relación con evidencia preservada.</span>
                    </div>
                    <div>
                      <strong>Qué no acredita por sí solo</strong>
                      <span>Autoría, acceso ilegítimo, explotación efectiva o identidad del operador sin timeline, logs, autorización, pericia y corroboración externa.</span>
                    </div>
                    <div>
                      <strong>Qué hacer ahora</strong>
                      <span>{quality.status === "listo" ? "Puede pasar al informe con limitaciones periciales explícitas." : `Completar: ${quality.missing.slice(0, 3).join(", ") || "validación"}.`}</span>
                    </div>
                  </div>
                  <div className="mini-list">
                    {item.open_ports && <span>Puertos: {item.open_ports}</span>}
                    {item.known_vulnerabilities && <span>Vulnerabilidades: {item.known_vulnerabilities}</span>}
                    {item.logs_available && <span>Logs: {item.logs_available}</span>}
                    {!item.open_ports && !item.known_vulnerabilities && !item.logs_available && <span>Sin observaciones técnicas cargadas.</span>}
                  </div>
                  <div className="mini-readiness">
                    {quality.checks.map((check) => (
                      <span className={check.ok ? "ok" : "missing"} key={check.key}>{check.ok ? "✓" : "•"} {check.label}</span>
                    ))}
                  </div>
                  <p className="notice">{item.warning || "Todo análisis activo debe documentar autorización, método y límites."}</p>
                  <div className="timeline-strip">
                    <span>1. Identificación</span>
                    <span>2. Preservación</span>
                    <span>3. Observación técnica</span>
                    <span>4. Hallazgo</span>
                    <span>5. Norma aplicable</span>
                    <span>6. Informe</span>
                  </div>
                  <div className="actions-line">
                    <Button className="h-auto min-h-10 whitespace-normal secondary-button" type="button" onClick={() => editIoTDevice(item)} variant="outline"><FileCheck2 size={16} /> Editar ficha</Button>
                    <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Operación del módulo", () => (() => createIoTFinding(item.id))())} variant="outline" type="button" disabled={!(canCase("analysis", "evidence:write")) || Boolean(caseTask)}><FileCheck2 size={16} /> Crear hallazgo</Button>
                    <Button onClick={() => void runCaseTask("Operación del módulo", () => (() => applyIoTLegal(item))())} variant="default" type="button" disabled={!(canCase("analysis", "evidence:write") && canUse("legal:write")) || Boolean(caseTask)} className="h-auto min-h-10 whitespace-normal"><Gavel size={16} /> Aplicar normas</Button>
                  </div>
                </article>
              );
            })}
            {!iotDevices.length && <EmptyState text="Sin dispositivos IoT registrados para el caso seleccionado." />}
          </div>
        </Card>
      </ModuleSurface>
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
        <Button type="button" className={"h-auto min-h-10 whitespace-normal " + (className)} onClick={() => openExternalLink(url, item, action)} variant="default">
          {icon}
          {label}
        </Button>
      ) : (
        <Button type="button" className="h-auto min-h-10 whitespace-normal tool-link disabled" disabled variant="default">
          <Globe2 size={15} />
          Sin ejecución online
        </Button>
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
      <ModuleSurface className="external-inventory-workbench" moduleId="externalTools">
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
            <FormField label="Buscar por herramienta, categoría, descripción, tags o uso forense"><Input
              placeholder="Buscar por herramienta, categoría, descripción, tags o uso forense"
              value={externalToolQuery}
              onChange={(event) => setExternalToolQuery(event.target.value)}
            /></FormField>
          </div>
          <div className="inventory-filters">
            <FormField label="Categoría de herramienta"><select value={externalToolCategory} onChange={(event) => setExternalToolCategory(event.target.value)}>
              {categories.map((category) => <option key={category}>{category}</option>)}
            </select></FormField>
            <FormField label="Sistema operativo"><select value={externalToolOs} onChange={(event) => setExternalToolOs(event.target.value)}>
              {operatingSystems.map((os) => <option key={os}>{os}</option>)}
            </select></FormField>
            <FormField label="Dificultad"><select value={externalToolDifficulty} onChange={(event) => setExternalToolDifficulty(event.target.value)}>
              {["Todas", "Básico", "Intermedio", "Avanzado", "Experto"].map((level) => <option key={level}>{level}</option>)}
            </select></FormField>
            <FormField label="Área forense"><select value={externalToolSpecialArea} onChange={(event) => setExternalToolSpecialArea(event.target.value)}>
              {specialAreas.map((area) => <option key={area}>{area}</option>)}
            </select></FormField>
            <label><input type="checkbox" checked={externalToolOnlineOnly} onChange={(event) => setExternalToolOnlineOnly(event.target.checked)} /> Con uso online</label>
            <label><input type="checkbox" checked={externalToolGithubOnly} onChange={(event) => setExternalToolGithubOnly(event.target.checked)} /> Con repositorio</label>
          </div>
        </div>

        <div className="special-areas">
          {specialAreaCards.map((area) => {
            const areaCount = externalToolsCatalog.filter((item) => item.specialArea === area.area).length;
            return (
              <Button
                className={"h-auto min-h-10 whitespace-normal " + (externalToolSpecialArea === area.area ? "special-area active grid" : "special-area grid")}
                type="button"
                key={area.area}
                onClick={() => setExternalToolSpecialArea(area.area)} variant="outline" aria-pressed={externalToolSpecialArea === area.area}
              >
                <span>{area.title}</span>
                <strong>{areaCount} herramientas</strong>
                <small>{area.text}</small>
                <em>{area.warning}</em>
              </Button>
            );
          })}
        </div>

        <div className="inventory-layout">
          <aside className="inventory-sidebar">
            <h3>Categorías</h3>
            <Button className={"h-auto min-h-10 whitespace-normal " + (externalToolCategory === "Todas" ? "active" : "")} onClick={() => setExternalToolCategory("Todas")} variant="default" type="button" aria-pressed={externalToolCategory === "Todas"}>Todas</Button>
            {categories.filter((category) => category !== "Todas").map((category) => (
              <Button className={"h-auto min-h-10 whitespace-normal " + (externalToolCategory === category ? "active" : "")} key={category} onClick={() => setExternalToolCategory(category)} variant="default" type="button" aria-pressed={externalToolCategory === category}>
                {category}
              </Button>
            ))}
          </aside>

          <div className="inventory-results">
            <div className="panel-head">
              <div>
                <h3>Inventario de herramientas</h3>
                <p>{filteredTools.length} resultado(s). Cada acceso abre una fuente externa y no procesa evidencia dentro de OPERIA.</p>
              </div>
              <Button
                className="h-auto min-h-10 whitespace-normal secondary-button"
                onClick={() => {
                  setExternalToolQuery("");
                  setExternalToolCategory("Todas");
                  setExternalToolOs("Todos");
                  setExternalToolDifficulty("Todas");
                  setExternalToolSpecialArea("Todas");
                  setExternalToolOnlineOnly(false);
                  setExternalToolGithubOnly(false);
                }} variant="outline" type="button"
              >
                <RefreshCcw size={15} /> Limpiar filtros
              </Button>
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
      </ModuleSurface>
    );
  }

  function renderAi() {
    return (
      <ModuleSurface className="ai-legal-workbench" moduleId="ai">
        <div className="section-head">
          <div>
            <h2>Asistente de Análisis y Tipificación</h2>
            <p>Asistencia local para vincular incidente, evidencia y biblioteca legal argentina registrada.</p>
          </div>
        </div>

        <div className="ai-hero-panel">
          <div>
            <span className="tool-kicker">Caso seleccionado</span>
            <h3>{selectedCase ? `${selectedCase.case_code} ? ${selectedCase.title}` : "Selecciona un caso para iniciar"}</h3>
            <p>{selectedCase ? prettySpanish(selectedCase.incident_type) : "La tipificación requiere un caso, una narrativa y biblioteca legal registrada."}</p>
          </div>
          <div className="ai-score-card">
            <span>Modo</span>
            <strong>RAG legal local</strong>
            <small>Sin API externa por defecto</small>
          </div>
        </div>

        <LocalAiGateway key={`${identitySession.user?.id || "anonymous"}:${selectedCaseId}`} caseId={selectedCaseId} allowed={canCase("analysis", "ai:use")} sessionKey={authToken} />
        <div className="ai-action-grid">
          <Card className="detail-panel">
            <div className="panel-head">
              <div>
                <h3>1. Contexto para la asistencia</h3>
                <p>Describe el incidente o agrega foco investigativo. La respuesta se limita a fuentes legales registradas.</p>
              </div>
            </div>
            <FormField label="Consigna para el análisis"><textarea value={aiPrompt} onChange={(e) => setAiPrompt(e.target.value)} /></FormField>
            <div className="button-row">
              <Button onClick={() => void runCaseTask("Operación del módulo", () => (() => runLegalTypification(false))())} disabled={(!selectedCaseId) || !(canCase("analysis", "ai:use")) || Boolean(caseTask)} variant="default" type="button" className="h-auto min-h-10 whitespace-normal"><Gavel size={17} /> Tipificar delito</Button>
              <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Operación del módulo", () => (() => runLegalTypification(true))())} disabled={(!selectedCaseId || legalApplyState === "applying") || !(canCase("analysis", "ai:use")) || Boolean(caseTask)} variant="outline" type="button">
                <CheckCircle2 size={17} /> {legalApplyState === "applying" ? "Guardando..." : "Guardar sugerencias"}
              </Button>
              <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Operación del módulo", () => (runAiAssist)())} variant="outline" type="button" disabled={!(canCase("analysis", "ai:use")) || Boolean(caseTask)}><Bot size={17} /> Ampliar análisis</Button>
              <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Operación del módulo", () => (runCaseRecommendations)())} disabled={(!selectedCaseId) || !(canCase("analysis", "ai:use")) || Boolean(caseTask)} variant="outline" type="button">
                <FileCheck2 size={17} /> Proximos pasos
              </Button>
            </div>
            {legalApplyMessage && (
              <div className={`action-feedback ${legalApplyState}`} role="status" aria-live="polite" aria-atomic="true">
                {legalApplyMessage}
              </div>
            )}
          </Card>

          <Card className="detail-panel">
            <div className="panel-head">
              <div>
                <h3>2. Resultado de tipificación</h3>
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
          </Card>
        </div>

        {legalTypification && (
          <div className="ai-result-grid">
            <Card className="detail-panel">
              <h3>Elementos y evidencia necesaria</h3>
              <div className="summary-list">
                <span>Elementos objetivos: {prettySpanish(legalTypification.principal_typification?.why || "sin norma principal")}</span>
                <span>Elemento subjetivo: {prettySpanish(legalTypification.principal_typification?.subjective_elements || "requiere revisión")}</span>
                <span>Evidencia requerida: {prettySpanish(legalTypification.principal_typification?.evidence_needed || "pendiente")}</span>
                <span>Límites: {prettySpanish(legalTypification.principal_typification?.probatory_limits || "requiere validación humana")}</span>
              </div>
            </Card>
            <Card className="detail-panel">
              <h3>Normas conexas</h3>
              <div className="mini-list">
                {legalTypification.connected_typifications.slice(0, 5).map((item) => (
                  <span key={`${item.article_id}-${item.reference}`}>{item.reference} · {prettySpanish(item.title)} · {prettySpanish(item.legal_role)}</span>
                ))}
                {!legalTypification.connected_typifications.length && <span>Sin normas conexas registradas para este perfil.</span>}
              </div>
            </Card>
            <Card className="detail-panel">
              <h3>Estado probatorio</h3>
              <div className="case-overview">
                <div><span>Evidencias</span><strong>{legalTypification.evidence_snapshot.evidence_count}</strong></div>
                <div><span>Custodia</span><strong>{legalTypification.evidence_snapshot.custody_actions}</strong></div>
                <div><span>Mapeos aprobados</span><strong>{legalTypification.evidence_snapshot.approved_legal_mappings}</strong></div>
              </div>
              <ul className="compact-list">
                {legalTypification.missing_for_stronger_typification.map((item) => <li key={item}>{prettySpanish(item)}</li>)}
                {!legalTypification.missing_for_stronger_typification.length && <li>Base minima completa para revisión del analista.</li>}
              </ul>
            </Card>
            <Card className="detail-panel">
              <h3>Medidas recomendadas</h3>
              <ul className="compact-list">
                {legalTypification.recommended_measures.map((item) => <li key={item}>{prettySpanish(item)}</li>)}
              </ul>
            </Card>
          </div>
        )}

        <Card className="detail-panel">
          <div className="panel-head">
            <div>
              <h3>3. Análisis operativo del caso</h3>
              <p>Lectura accionable del incidente, sin exponer salida técnica cruda.</p>
            </div>
          </div>
          {renderCaseAnalysisOutcome()}
        </Card>
      </ModuleSurface>
    );
  }

  function renderAiSecurity() {
    const evaluation = aiSecurityResult as AiSecurityEvaluation | null;
    return (
      <ModuleSurface className="" moduleId="aiSecurity">
        <div className="section-head">
          <div>
            <h2>AI Security</h2>
            <p>Auditoría controlada de modelos IA locales antes de usarlos en casos reales.</p>
          </div>
          <Button onClick={() => void runCaseTask("Operación del módulo", () => (runAiSecurity)())} variant="default" type="button" disabled={!(canUse("ai:use") && (!selectedCaseId || canCase("analysis", "ai:use"))) || Boolean(caseTask)} className="h-auto min-h-10 whitespace-normal"><BrainCircuit size={17} /> Crear evaluacion</Button>
        </div>
        <div className="ai-security-grid">
          <div className="ai-security-card primary">
            <h3>Función del módulo</h3>
            <p>
              AI Security no investiga personas ni resuelve casos. Su función es auditar el modelo IA que OPERIA usa como asistente:
              privacidad, fuga de datos, alucinación jurídica, obediencia ante instrucciones maliciosas y uso seguro en entorno forense.
            </p>
          </div>
          <div className="ai-security-card">
            <h3>Resultado esperado</h3>
            <p>
              La conclusión correcta no es "modelo seguro al 100%", sino: bajo condiciones locales, aisladas y auditadas,
              el riesgo observado es bajo, medio, alto o crítico.
            </p>
          </div>
          <div className="ai-security-card">
            <h3>Qué evalúa</h3>
            <ul>
              <li>Privacidad y posible fuga de información.</li>
              <li>Prompt injection, jailbreak y obediencia maliciosa.</li>
              <li>Alucinación legal y citas normativas falsas.</li>
              <li>Uso sin herramientas, sin red y con revisión humana.</li>
            </ul>
          </div>
          <div className="ai-security-card">
            <h3>Cómo mejorarlo</h3>
            <ul>
              <li>Agregar ejecución real de batería de pruebas controladas.</li>
              <li>Mostrar matriz de riesgo por test y reporte descargable.</li>
              <li>Comparar modelos locales: Mistral, DeepSeek u otros.</li>
              <li>Guardar evidencia de auditoría sin exponer datos sensibles.</li>
            </ul>
          </div>
        </div>
        {evaluation ? (
          <div className="ai-security-result">
            <div>
              <span>Modelo evaluado</span>
              <strong>{evaluation.model_name || "Mistral"}</strong>
            </div>
            <div>
              <span>Proveedor</span>
              <strong>{evaluation.provider || "Local"}</strong>
            </div>
            <div>
              <span>Riesgo observado</span>
              <strong>{prettySpanish(evaluation.risk_level || "pendiente")}</strong>
            </div>
            <div>
              <span>Score</span>
              <strong>{evaluation.overall_score ?? "-"} / 100</strong>
            </div>
            <p>{evaluation.conclusion || "Evaluación registrada."}</p>
            {evaluation.recommendation && <p>{evaluation.recommendation}</p>}
          </div>
        ) : (
          <EmptyState text="Todavía no hay evaluación registrada. Ejecuta una evaluación para obtener riesgo observado, recomendación y conclusión auditable." />
        )}
      </ModuleSurface>
    );
  }

  function renderIdentity() {
    const currentRole = identitySession.user?.role || "";
    const currentPermissions = currentRole ? permissions[currentRole] || [] : [];
    const canManageIdentity = currentPermissions.includes("*") || currentPermissions.includes("identity:write");
    const canReadIdentity = canManageIdentity || currentPermissions.includes("identity:read");
    const roleLabels: Record<string, string> = {
      admin: "Administrador",
      coordinador: "Coordinador",
      coordinator: "Coordinador",
      analista: "Analista",
      analyst: "Analista",
      legal: "Legal",
      lector: "Lector"
    };
    const statusLabels: Record<string, string> = { active: "Activo", inactive: "Inactivo", suspended: "Suspendido" };
    return (
      <ModuleSurface className="" moduleId="identity">
        <div className="section-head">
          <div>
            <h2>Identidad y Permisos</h2>
            <p>Acceso local, usuario interviniente y permisos visibles por rol.</p>
          </div>
          <Button className="h-auto min-h-10 whitespace-normal icon-button" onClick={refreshIdentity} title="Actualizar" variant="outline" type="button" aria-label="Actualizar"><RefreshCcw size={18} /></Button>
        </div>

        {identitySession.authenticated && identitySession.user ? (
          <div className="identity-panel">
            <div className="identity-profile">
              <span className="status">Sesión activa</span>
              <h3>{identitySession.user.name}</h3>
              <p>{identitySession.user.email || "Sin email registrado"}</p>
              <div className="summary-list">
                <span>Rol: {roleLabels[identitySession.user.role] || prettySpanish(identitySession.user.role)}</span>
                <span>Organización: {identitySession.user.organization_id || "local"}</span>
                <span>Permisos activos: {currentPermissions.length}</span>
              </div>
              <Button className="h-auto min-h-10 whitespace-normal secondary" onClick={logout} variant="outline" type="button">Cerrar sesión</Button>
            </div>
            <div className="identity-permissions">
              <h3>Permisos del usuario</h3>
              <p>Estas capacidades determinan qué acciones puede ejecutar el operador dentro de OPERIA.</p>
              <div className="permission-chip-grid">
                {currentPermissions.map((permission) => <span key={permission}>{prettySpanish(permission.replace(":", ": "))}</span>)}
                {!currentPermissions.length && <span>Sin permisos declarados para el rol.</span>}
              </div>
            </div>
          </div>
        ) : (
          <div className="identity-login-grid">
            <form className="form" onSubmit={login}>
              <h3>Iniciar sesión</h3>
              <p>Usa el usuario administrador o analista creado para firmar acciones sensibles.</p>
              <FormField label="Email"><Input placeholder="Email" value={loginForm.email} onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })} /></FormField>
              <FormField label="Contraseña"><Input placeholder="Password" type="password" value={loginForm.password} onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })} autoComplete="current-password" /></FormField>
              <Button variant="default" type="submit" className="h-auto min-h-10 whitespace-normal"><Users size={17} /> Entrar</Button>
              <Button type="button" className="h-auto min-h-10 whitespace-normal secondary-button" onClick={recoverLocalAdmin} disabled={loading} variant="outline">
                <Shield size={17} /> Recuperar acceso local
              </Button>
              <p className="hint">Si olvidaste la clave local, esta acción restablece el administrador en esta PC y abre sesión automáticamente.</p>
            </form>
            <form className="form" onSubmit={bootstrapAdmin}>
              <h3>Crear admin inicial</h3>
              <p>Solo se usa la primera vez. Si ya existen usuarios, inicia sesión o recupera el acceso local.</p>
              <FormField label="Organización"><Input placeholder="Organización" value={bootstrapForm.organization_name} onChange={(e) => setBootstrapForm({ ...bootstrapForm, organization_name: e.target.value })} /></FormField>
              <FormField label="Nombre"><Input placeholder="Nombre" value={bootstrapForm.name} onChange={(e) => setBootstrapForm({ ...bootstrapForm, name: e.target.value })} /></FormField>
              <FormField label="Email"><Input placeholder="Email" value={bootstrapForm.email} onChange={(e) => setBootstrapForm({ ...bootstrapForm, email: e.target.value })} /></FormField>
              <FormField label="Contraseña"><Input placeholder="Password" type="password" value={bootstrapForm.password} onChange={(e) => setBootstrapForm({ ...bootstrapForm, password: e.target.value })} autoComplete="new-password" /></FormField>
              <Button className="h-auto min-h-10 whitespace-normal secondary" variant="outline" type="submit"><Shield size={17} /> Bootstrap admin</Button>
              <p className="hint">Disponible solo cuando todavía no existe ningún usuario. No se usa para recuperar contraseñas.</p>
            </form>
          </div>
        )}

        {identityMessage && (
          <div className={identityState === "error" ? "notice error" : "notice success"}>
            {identityMessage}
          </div>
        )}

        {identitySession.authenticated && identitySession.user && (
          <>
            <form className="identity-profile-editor" onSubmit={saveProfile}>
              <div className="section-head compact">
                <div>
                  <h3>Perfil profesional del analista</h3>
                  <p>Datos de autoría, auditoría, cierre de caso e informes finales.</p>
                </div>
                <Button disabled={identityState === "working"} variant="default" type="submit" className="h-auto min-h-10 whitespace-normal"><Save size={17} /> Guardar perfil</Button>
              </div>
              <div className="form-grid two">
                <FormField label="Nombre completo"><Input placeholder="Nombre completo" value={profileForm.name} onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })} /></FormField>
                <FormField label="Cargo o función"><Input placeholder="Cargo o función" value={profileForm.title} onChange={(e) => setProfileForm({ ...profileForm, title: e.target.value })} /></FormField>
                <FormField label="Organismo, equipo o estudio"><Input placeholder="Organismo, equipo o estudio" value={profileForm.agency} onChange={(e) => setProfileForm({ ...profileForm, agency: e.target.value })} /></FormField>
                <FormField label="Matrícula, legajo o identificador profesional"><Input placeholder="Matrícula, legajo o identificador profesional" value={profileForm.registration_id} onChange={(e) => setProfileForm({ ...profileForm, registration_id: e.target.value })} /></FormField>
                <FormField label="Teléfono de contacto"><Input placeholder="Teléfono de contacto" value={profileForm.phone} onChange={(e) => setProfileForm({ ...profileForm, phone: e.target.value })} /></FormField>
                <FormField label="Notas internas del perfil"><Input placeholder="Notas internas del perfil" value={profileForm.profile_notes} onChange={(e) => setProfileForm({ ...profileForm, profile_notes: e.target.value })} /></FormField>
              </div>
              <FormField label="Firma profesional o leyenda de intervención"><textarea placeholder="Firma profesional o leyenda de intervención" value={profileForm.signature} onChange={(e) => setProfileForm({ ...profileForm, signature: e.target.value })} /></FormField>
            </form>

            {canReadIdentity && (
              <div className="identity-admin-grid">
                <div className="identity-admin-panel">
                  <h3>Usuarios del equipo</h3>
                  <p>Roles, estados y claves se administran con auditoría. Las claves nunca se muestran.</p>
                  <div className="user-list">
                    {identityUsers.map((user) => (
                      <div className="user-card" key={user.id}>
                        <div>
                          <strong>{user.name || "Usuario sin nombre"}</strong>
                          <span>{user.email || "Sin email"} · {roleLabels[user.role] || prettySpanish(user.role)} · {statusLabels[user.status || "active"] || user.status}</span>
                          <small>{[user.title, user.agency, user.registration_id].filter(Boolean).join(" · ") || "Perfil profesional incompleto"}</small>
                        </div>
                        {canManageIdentity && (
                          <div className="user-actions">
                            <FormField label="Rol del usuario"><select value={user.role} onChange={(e) => updateIdentityUser(user.id, { role: e.target.value })}>
                              {Object.keys(roleLabels).filter((role) => permissions[role]).map((role) => <option key={role} value={role}>{roleLabels[role]}</option>)}
                            </select></FormField>
                            <FormField label="Estado del usuario"><select value={user.status || "active"} onChange={(e) => updateIdentityUser(user.id, { status: e.target.value })}>
                              <option value="active">Activo</option>
                              <option value="inactive">Inactivo</option>
                              <option value="suspended">Suspendido</option>
                            </select></FormField>
                            <FormField label="Nueva clave"><Input
                              type="password"
                              placeholder="Nueva clave"
                              value={passwordDrafts[user.id] || ""}
                              onChange={(e) => setPasswordDrafts({ ...passwordDrafts, [user.id]: e.target.value })} autoComplete="new-password"
                            /></FormField>
                            <Button type="button" className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => resetIdentityPassword(user.id)} variant="outline">Resetear clave</Button>
                          </div>
                        )}
                      </div>
                    ))}
                    {!identityUsers.length && <div className="empty-state">No hay usuarios visibles para tu rol.</div>}
                  </div>
                </div>

                {canManageIdentity && (
                  <form className="identity-admin-panel" onSubmit={createIdentityUser}>
                    <h3>Crear usuario</h3>
                    <p>Alta controlada para administradores, analistas, legales, coordinadores o lectores.</p>
                    <FormField label="Nombre completo"><Input placeholder="Nombre completo" value={newUserForm.name} onChange={(e) => setNewUserForm({ ...newUserForm, name: e.target.value })} /></FormField>
                    <FormField label="Email"><Input placeholder="Email" value={newUserForm.email} onChange={(e) => setNewUserForm({ ...newUserForm, email: e.target.value })} /></FormField>
                    <div className="form-grid two">
                      <FormField label="Rol del usuario"><select value={newUserForm.role} onChange={(e) => setNewUserForm({ ...newUserForm, role: e.target.value })}>
                        <option value="analista">Analista</option>
                        <option value="legal">Legal</option>
                        <option value="coordinador">Coordinador</option>
                        <option value="lector">Lector</option>
                        <option value="admin">Administrador</option>
                      </select></FormField>
                      <FormField label="Estado del usuario"><select value={newUserForm.status} onChange={(e) => setNewUserForm({ ...newUserForm, status: e.target.value })}>
                        <option value="active">Activo</option>
                        <option value="inactive">Inactivo</option>
                      </select></FormField>
                    </div>
                    <FormField label="Cargo o función"><Input placeholder="Cargo o función" value={newUserForm.title} onChange={(e) => setNewUserForm({ ...newUserForm, title: e.target.value })} /></FormField>
                    <FormField label="Organismo o equipo"><Input placeholder="Organismo o equipo" value={newUserForm.agency} onChange={(e) => setNewUserForm({ ...newUserForm, agency: e.target.value })} /></FormField>
                    <FormField label="Clave inicial"><Input type="password" placeholder="Clave inicial" value={newUserForm.password} onChange={(e) => setNewUserForm({ ...newUserForm, password: e.target.value })} autoComplete="new-password" /></FormField>
                    <Button disabled={identityState === "working"} variant="default" type="submit" className="h-auto min-h-10 whitespace-normal"><Users size={17} /> Crear usuario</Button>
                  </form>
                )}
              </div>
            )}
          </>
        )}

        <div className="role-grid">
          {Object.entries(permissions).map(([role, items]) => (
            <div className="role-card" key={role}>
              <strong>{roleLabels[role] || prettySpanish(role)}</strong>
              <span>{items.length} permisos</span>
              <p>{items.slice(0, 5).map((item) => prettySpanish(item.replace(":", ": "))).join(" · ")}</p>
            </div>
          ))}
        </div>
      </ModuleSurface>
    );
  }

  function renderSettings() {
    const readiness = (modulePayload || {}) as {
      database?: { dialect?: string; schema_version?: string; alembic_heads?: string[]; postgres_ready?: boolean };
      storage?: Record<string, string>;
      saas_readiness?: Record<string, boolean>;
      recommendations?: string[];
    };
    const saasEntries = Object.entries(readiness.saas_readiness || {});
    const storageEntries = Object.entries(readiness.storage || {});
    return (
      <ModuleSurface className="" moduleId="settings">
        <div className="section-head">
          <div>
            <h2>Configuración</h2>
            <p>Estado técnico de la plataforma, base de datos, almacenamiento y preparación SaaS.</p>
          </div>
          <Button className="h-auto min-h-10 whitespace-normal icon-button" onClick={() => loadModule("settings")} title="Actualizar" variant="outline" type="button" aria-label="Actualizar"><RefreshCcw size={18} /></Button>
        </div>

        <div className="settings-hero">
          <div>
            <span>Base de datos</span>
            <strong>{prettySpanish(readiness.database?.dialect || "Sin datos")}</strong>
            <p>Versión de esquema: {readiness.database?.schema_version || "No informada"}</p>
          </div>
          <div>
            <span>Preparación SaaS</span>
            <strong>{saasEntries.filter(([, ok]) => ok).length}/{saasEntries.length || 0}</strong>
            <p>Controles activos para operación profesional y multi-organización.</p>
          </div>
          <div>
            <span>PostgreSQL</span>
            <strong>{readiness.database?.postgres_ready ? "Preparado" : "Pendiente"}</strong>
            <p>{readiness.database?.postgres_ready ? "Listo para despliegue avanzado." : "Operando en modo local SQLite."}</p>
          </div>
        </div>

        <div className="settings-grid">
          <div className="settings-card">
            <h3>Almacenamiento</h3>
            <div className="summary-list">
              {storageEntries.map(([key, value]) => (
                <span key={key}>{prettySpanish(key)}: {value}</span>
              ))}
              {!storageEntries.length && <span>Sin rutas registradas.</span>}
            </div>
          </div>
          <div className="settings-card">
            <h3>Controles SaaS</h3>
            <div className="readiness-list">
              {saasEntries.map(([key, ok]) => (
                <div className={`readiness-item ${ok ? "ok" : ""}`} key={key}>
                  <strong>{prettySpanish(key.replace(/_/g, " "))}</strong>
                  <span>{ok ? "Activo" : "Pendiente"}</span>
                </div>
              ))}
              {!saasEntries.length && <EmptyState text="Sin controles reportados." />}
            </div>
          </div>
        </div>

        <div className="settings-card">
          <h3>Recomendaciones operativas</h3>
          <ul className="clean-list">
            {(readiness.recommendations || []).map((item) => <li key={item}>{prettySpanish(item)}</li>)}
            {!(readiness.recommendations || []).length && <li>No hay recomendaciones pendientes reportadas.</li>}
          </ul>
        </div>
      </ModuleSurface>
    );
  }

  function renderCasePresentation() {
    const selectedPresentation = presentations.find((item) => item.id === Number(selectedPresentationId)) || presentations[0];
    const reviewMetrics = presentationReview
      ? [
          ["Claridad", presentationReview.clarity],
          ["Fuerza probatoria", presentationReview.evidentiary_strength],
          ["Coherencia narrativa", presentationReview.narrative_coherence],
          ["Solidez legal", presentationReview.legal_solidity],
          ["Calidad visual", presentationReview.visual_quality]
        ]
      : [];
    return (
      <ModuleSurface className="presentation-workbench" moduleId="casePresentation">
        <div className="section-head">
          <div>
            <h2>Exposición del Caso</h2>
            <p>Guion profesional para presentar el caso con diapositivas, notas orales, riesgos y exportación PDF.</p>
          </div>
          <div className="actions-row">
            <Button onClick={() => void runCaseTask("Operación del módulo", () => (generateCasePresentation)())} disabled={(!latestReport || presentationState === "working") || !(canCase("reports", "reports:write")) || Boolean(caseTask)} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">
              <MonitorPlay size={16} /> Generar exposición
            </Button>
            <Button className="h-auto min-h-10 whitespace-normal secondary" onClick={() => void runCaseTask("Operación del módulo", () => (reviewCasePresentation)())} disabled={(!selectedPresentationId || presentationState === "working") || !(canCase("review", "reports:write")) || Boolean(caseTask)} variant="outline" type="button">
              <CheckCircle2 size={16} /> Revisar exposición
            </Button>
            {selectedPresentation && (
              <Button variant="outline" disabled={!canCase("export", "reports:read") || Boolean(caseTask)} onClick={() => void runCaseTask("Exportar exposición", async () => {
                if (!canCase("export", "reports:read")) throw new Error("No tenés permiso de exportación.");
                await downloadArtifact(`/reports/presentations/${selectedPresentation.id}/export/pdf`, `operia-exposicion-${selectedPresentation.id}.pdf`);
              })} className="h-auto min-h-10 whitespace-normal"><Download size={16} /> Exportar PDF</Button>
            )}
          </div>
        </div>

        {presentationMessage && (
          <div className={`inline-alert ${presentationState === "error" ? "danger" : presentationState === "success" ? "success" : ""}`}>
            {presentationMessage}
          </div>
        )}

        <div className="presentation-dashboard">
          {[
            ["Caso activo", selectedCase?.case_code || "Sin caso"],
            ["Informe fuente", latestReport ? `#${latestReport.id}` : "Pendiente"],
            ["Exposiciones", presentations.length],
            ["Diapositivas", presentationSlides.length],
            ["Score oral", presentationReview?.score || selectedPresentation?.review_score || 0]
          ].map(([label, value]) => (
            <div className="metric" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>

        {!latestReport && <EmptyState text="Genera primero un informe del caso. La exposición se construye desde el informe, la evidencia, la custodia, el daño y el encuadre legal." />}

        {!!presentations.length && (
          <div className="presentation-selector">
            <label>
              Exposición activa
              <select value={selectedPresentation?.id || ""} onChange={(event) => loadPresentationSlides(Number(event.target.value) || "")}>
                {presentations.map((item) => (
                  <option key={item.id} value={item.id}>{item.title} · v{item.version} · {prettySpanish(item.status)}</option>
                ))}
              </select>
            </label>
            <div className="presentation-brief">
              <strong>{selectedPresentation?.title}</strong>
              <span>{selectedPresentation?.selected_fragments}</span>
            </div>
          </div>
        )}

        {presentationReview && (
          <div className="presentation-review">
            <div>
              <h3>Revisión de exposición</h3>
              <p>Score general: <strong>{presentationReview.score}/100</strong></p>
              <div className="score-grid">
                {reviewMetrics.map(([label, value]) => (
                  <span key={label as string}>{label}: <strong>{value}/100</strong></span>
                ))}
              </div>
            </div>
            <div>
              <h4>Riesgos orales</h4>
              <ul className="clean-list">{presentationReview.oral_exposure_risks.map((item) => <li key={item}>{item}</li>)}</ul>
              <h4>Recomendaciones</h4>
              <ul className="clean-list">{presentationReview.recommendations.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          </div>
        )}

        <div className="slide-grid">
          {presentationSlides.map((slide) => (
            <article className="slide-card" key={slide.id}>
              <div className="slide-number">Slide {slide.slide_number}</div>
              <FormField label="Título de la diapositiva"><Input value={slide.title} onChange={(event) => updatePresentationSlide(slide, { title: event.target.value })} /></FormField>
              <FormField label="Contenido de la diapositiva"><textarea value={slide.text} onChange={(event) => updatePresentationSlide(slide, { text: event.target.value })} /></FormField>
              <label>
                Notas para exposición oral
                <textarea value={slide.speaker_notes} onChange={(event) => updatePresentationSlide(slide, { speaker_notes: event.target.value })} />
              </label>
              <div className="slide-footer">
                <span>{prettySpanish(slide.confidentiality_level)}</span>
                <span>{prettySpanish(slide.content_type)}</span>
              </div>
            </article>
          ))}
          {!presentationSlides.length && latestReport && (
            <EmptyState text="Todavía no hay diapositivas. Usa “Generar exposición” para crear el guion del caso." />
          )}
        </div>
      </ModuleSurface>
    );
  }

  function renderMind() {
    const graphNodeCount = mindGraph?.nodes.length || 0;
    const graphEdgeCount = mindGraph?.edges.length || 0;
    const selectedPresentation = presentations.find((item) => item.id === Number(selectedPresentationId)) || presentations[0];
    const caseScopedNotes = mindNotes.filter((note) => !selectedCaseId || note.case_id === Number(selectedCaseId));
    const recentAudit = mindAudit.slice(0, 6);
    const isWorking = mindState === "working";
    return (
      <ModuleSurface className="mind-workbench" moduleId="mind">
        <div className="section-head">
          <div>
            <h2>Cerebro / Memoria Forense</h2>
            <p>Memoria persistente del caso, notas Markdown, búsqueda local, snapshots, auditoría y grafo de relaciones.</p>
          </div>
          <div className="button-row">
            <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={refreshMind} disabled={isWorking} variant="outline" type="button"><RefreshCcw size={16} /> Actualizar memoria</Button>
            <Button onClick={() => void runCaseTask("Operación del módulo", () => (createMindSnapshot)())} disabled={(!selectedCaseId || isWorking) || !(canCase("analysis", "cases:write")) || Boolean(caseTask)} variant="default" type="button" className="h-auto min-h-10 whitespace-normal"><BrainCircuit size={16} /> Snapshot del caso</Button>
          </div>
        </div>

        {mindMessage && (
          <div className={`inline-status ${mindState === "error" ? "danger" : mindState === "success" ? "success" : ""}`} role="status" aria-live="polite" aria-atomic="true">
            {mindMessage}
          </div>
        )}

        <div className="mind-hero">
          <div>
            <span className="eyebrow">Caso activo</span>
            <h3>{selectedCase ? `${selectedCase.case_code} - ${selectedCase.title}` : "Memoria general"}</h3>
            <p>{selectedCase ? selectedCase.description || "Caso sin narrativa inicial cargada." : "Selecciona un caso para generar memoria contextual, notas y grafo operativo."}</p>
            {selectedCase && (
              <div className="mind-case-tags">
                <span>{prettySpanish(selectedCase.incident_type)}</span>
                <span>{prettySpanish(selectedCase.status)}</span>
              </div>
            )}
          </div>
          <div className="mind-metrics">
            <div><span>Notas del caso</span><strong>{caseScopedNotes.length}</strong></div>
            <div><span>Nodos</span><strong>{graphNodeCount}</strong></div>
            <div><span>Relaciones</span><strong>{graphEdgeCount}</strong></div>
            <div><span>Auditoría</span><strong>{mindAudit.length}</strong></div>
          </div>
        </div>

        <div className="mind-action-strip">
          <Button onClick={() => void runCaseTask("Operación del módulo", () => (createMindSnapshot)())} disabled={(!selectedCaseId || isWorking) || !(canCase("analysis", "cases:write")) || Boolean(caseTask)} variant="default" type="button" className="h-auto min-h-10 whitespace-normal"><BrainCircuit size={16} /> Guardar snapshot del caso</Button>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Operación del módulo", () => (createReportMindSnapshot)())} disabled={(!latestReport || isWorking) || !(canCase("analysis", "reports:write")) || Boolean(caseTask)} variant="outline" type="button"><FileText size={16} /> Guardar último informe</Button>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => void runCaseTask("Operación del módulo", () => (createPresentationMindSnapshot)())} disabled={(!selectedPresentation || isWorking) || !(canCase("analysis", "reports:write")) || Boolean(caseTask)} variant="outline" type="button"><Presentation size={16} /> Guardar exposición</Button>
          <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setMindNoteForm({ ...mindNoteForm, note_type: "hallazgo", title: selectedCase ? `Hallazgo - ${selectedCase.case_code}` : "Hallazgo", content: "" })} variant="outline" type="button"><Save size={16} /> Preparar hallazgo</Button>
        </div>

        {mindBrief && (
          <Card className="panel-card mind-brief-panel">
            <div className="mind-brief-head">
              <div>
                <span className="eyebrow">Lectura ejecutiva local</span>
                <h3>Estado cognitivo del caso</h3>
                <p>Resumen operativo construido desde evidencia, notas, grafo, informes y módulos del caso. No reemplaza revisión humana.</p>
              </div>
              <div className="mind-brief-badges">
                <span className="pill">Preparación: {prettySpanish(mindBrief.readiness)}</span>
                <span className="pill">Confianza: {prettySpanish(mindBrief.confidence)}</span>
              </div>
            </div>
            <div className="mind-brief-grid">
              <article>
                <h4>Qué sabemos</h4>
                <ul>{mindBrief.known_facts.slice(0, 7).map((item) => <li key={item}>{item}</li>)}</ul>
              </article>
              <article>
                <h4>Qué falta</h4>
                <ul>{(mindBrief.missing_information.length ? mindBrief.missing_information : ["Sin brechas críticas detectadas por la lectura local."]).slice(0, 7).map((item) => <li key={item}>{item}</li>)}</ul>
              </article>
              <article>
                <h4>Riesgos y contradicciones</h4>
                <ul>
                  {[...mindBrief.risks, ...mindBrief.contradictions].length
                    ? [...mindBrief.risks, ...mindBrief.contradictions].slice(0, 7).map((item) => <li key={item}>{item}</li>)
                    : <li>No se detectaron contradicciones operativas relevantes.</li>}
                </ul>
              </article>
              <article>
                <h4>Próximos pasos</h4>
                <ul>{mindBrief.recommended_next_steps.slice(0, 7).map((item) => <li key={item}>{item}</li>)}</ul>
              </article>
            </div>
            <div className="mind-brief-footer">
              <div>
                <strong>Memoria destacada</strong>
                <span>{mindBrief.memory_highlights.slice(0, 4).join(" | ")}</span>
              </div>
              <div>
                <strong>Grafo</strong>
                <span>{mindBrief.graph_summary.nodes || 0} nodos, {mindBrief.graph_summary.edges || 0} relaciones, {mindBrief.graph_summary.notes || 0} notas.</span>
              </div>
            </div>
          </Card>
        )}

        <form className="panel-card mind-search-panel" onSubmit={event => { event.preventDefault(); void runCaseTask("Guardar datos del módulo", () => searchMind(event)); }}>
          <div>
            <h3>Consultar memoria</h3>
            <p>Busca en notas, snapshots, hallazgos, hipótesis, tags y resúmenes guardados. La búsqueda es local y no envía evidencia a servicios externos.</p>
          </div>
          <div className="search-row">
            <FormField label="Buscar concepto, evidencia, hipótesis, norma o decisión..."><Input value={mindSearchQuery} onChange={(event) => setMindSearchQuery(event.target.value)} placeholder="Buscar concepto, evidencia, hipótesis, norma o decisión..." /></FormField>
            <Button disabled={isWorking} variant="default" type="submit" className="h-auto min-h-10 whitespace-normal"><Search size={16} /> Consultar</Button>
          </div>
          <div className="mind-search-results">
            {mindSearchResults.map((result) => (
              <article key={result.id} className="mind-result-card">
                <div>
                  <span className="eyebrow">{prettySpanish(result.note_type)} · relevancia {result.score}</span>
                  <h4>{result.title}</h4>
                  <p>{result.content_excerpt || result.summary || "Resultado sin extracto visible."}</p>
                  <small>{result.vault_path}</small>
                </div>
                <span className="pill">{result.matches.map(prettySpanish).join(", ")}</span>
              </article>
            ))}
            {!mindSearchResults.length && <EmptyState text="Consultá la memoria para recuperar notas, hallazgos y contexto del caso." />}
          </div>
        </form>

        <div className="mind-grid">
          <form className="panel-card mind-note-form" onSubmit={event => { event.preventDefault(); void runCaseTask("Guardar datos del módulo", () => createMindNote(event)); }}><fieldset disabled={!(canCase("analysis", "cases:write")) || Boolean(caseTask)}><legend className="sr-only">Datos de la operación</legend>
            <h3>Crear nota rápida</h3>
            <p>Guarda una observación, hipótesis, hallazgo o contexto como archivo Markdown auditable.</p>
            <div className="form-grid two">
              <FormField label="Tipo de nota"><select value={mindNoteForm.note_type} onChange={(event) => setMindNoteForm({ ...mindNoteForm, note_type: event.target.value })}>
                <option value="nota">Nota</option>
                <option value="analisis">Análisis</option>
                <option value="hallazgo">Hallazgo</option>
                <option value="hipotesis">Hipótesis</option>
                <option value="matriz">Matriz</option>
                <option value="documento">Documento</option>
                <option value="auditoria">Auditoría</option>
              </select></FormField>
              <FormField label="Tags separados por coma"><Input value={mindNoteForm.tags} onChange={(event) => setMindNoteForm({ ...mindNoteForm, tags: event.target.value })} placeholder="Tags separados por coma" /></FormField>
            </div>
            <FormField label="Título de la nota"><Input value={mindNoteForm.title} onChange={(event) => setMindNoteForm({ ...mindNoteForm, title: event.target.value })} placeholder="Título de la nota" /></FormField>
            <FormField label="Contenido, contexto, fuente, límite probatorio o decisión del analista"><textarea value={mindNoteForm.content} onChange={(event) => setMindNoteForm({ ...mindNoteForm, content: event.target.value })} placeholder="Contenido, contexto, fuente, límite probatorio o decisión del analista" /></FormField>
            <Button disabled={isWorking} variant="default" type="submit" className="h-auto min-h-10 whitespace-normal"><Save size={16} /> Guardar nota</Button>
          </fieldset></form>

          <Card className="panel-card">
            <h3>Prompts y agentes</h3>
            <p>Accesos disponibles para próximas fases de memoria asistida y redacción controlada.</p>
            <div className="mind-mini-columns">
              <div>
                <strong>Prompts</strong>
                <span>{mindPrompts.length} cargado(s)</span>
              </div>
              <div>
                <strong>Agentes</strong>
                <span>{mindAgents.length} configurado(s)</span>
              </div>
            </div>
            <div className="compact-list">
              {mindAgents.slice(0, 4).map((agent) => (
                <article key={agent.id}>
                  <strong>{agent.name}</strong>
                  <span>{agent.role}</span>
                  <small>{agent.scope}</small>
                </article>
              ))}
              {!mindAgents.length && <EmptyState text="Sin agentes cargados. Actualiza la memoria o verifica la sesión." />}
            </div>
          </Card>
        </div>

        <div className="mind-grid">
          <Card className="panel-card">
            <h3>Notas del caso</h3>
            <p>Memoria persistente del caso y notas generales del vault.</p>
            <div className="mind-note-list">
              {caseScopedNotes.map((note) => (
                <article className="mind-note-card" key={note.id}>
                  <div>
                    <span className="eyebrow">{prettySpanish(note.note_type)} · {prettySpanish(note.review_status)}</span>
                    <h4>{note.title}</h4>
                    <p>{note.summary || note.content || "Sin resumen cargado."}</p>
                    <small>{note.vault_path}</small>
                  </div>
                  <span className="pill">{prettySpanish(note.confidence)}</span>
                </article>
              ))}
              {!caseScopedNotes.length && <EmptyState text="Todavía no hay notas en memoria para este caso." />}
            </div>
          </Card>

          <Card className="panel-card">
            <h3>Grafo de relaciones</h3>
            <p>Relaciones entre caso, evidencia, hallazgos, fuentes legales, informes y notas.</p>
            <form className="mind-relation-form" onSubmit={event => { event.preventDefault(); void runCaseTask("Guardar datos del módulo", () => createMindRelation(event)); }}><fieldset disabled={!(canCase("analysis", "cases:write")) || Boolean(caseTask)}><legend className="sr-only">Datos de la operación</legend>
              <FormField label="Nodo de origen"><select
                value={mindRelationForm.source_node_key}
                onChange={(event) => setMindRelationForm({ ...mindRelationForm, source_node_key: event.target.value })}
              >
                <option value="">Nodo origen</option>
                {(mindGraph?.nodes || []).map((node) => (
                  <option key={node.node_key} value={node.node_key}>
                    {prettySpanish(node.node_type)}: {node.label}
                  </option>
                ))}
              </select></FormField>
              <FormField label="Tipo de relación"><select
                value={mindRelationForm.relation_type}
                onChange={(event) => setMindRelationForm({ ...mindRelationForm, relation_type: event.target.value })}
              >
                {(mindGraph?.relation_types || [
                  "pertenece_a",
                  "vinculado_con",
                  "sostiene",
                  "limita",
                  "contradice",
                  "deriva_de",
                  "analizado_por",
                  "citado_en",
                  "exportado_en",
                  "requiere_revision",
                  "tiene_fuente_legal",
                  "tiene_hash"
                ]).map((relation) => (
                  <option key={relation} value={relation}>{prettySpanish(relation)}</option>
                ))}
              </select></FormField>
              <FormField label="Nodo de destino"><select
                value={mindRelationForm.target_node_key}
                onChange={(event) => setMindRelationForm({ ...mindRelationForm, target_node_key: event.target.value })}
              >
                <option value="">Nodo destino</option>
                {(mindGraph?.nodes || []).map((node) => (
                  <option key={node.node_key} value={node.node_key}>
                    {prettySpanish(node.node_type)}: {node.label}
                  </option>
                ))}
              </select></FormField>
              <FormField label="Nota breve de la relación"><Input
                value={mindRelationForm.label}
                onChange={(event) => setMindRelationForm({ ...mindRelationForm, label: event.target.value })}
                placeholder="Nota breve de la relación"
              /></FormField>
              <FormField label="Confianza de la relación"><select
                value={mindRelationForm.confidence}
                onChange={(event) => setMindRelationForm({ ...mindRelationForm, confidence: event.target.value })}
              >
                <option value="bajo">Confianza baja</option>
                <option value="medio">Confianza media</option>
                <option value="alto">Confianza alta</option>
              </select></FormField>
              <Button disabled={isWorking || !mindGraph?.nodes.length} variant="default" type="submit" className="h-auto min-h-10 whitespace-normal"><Network size={16} /> Crear relación</Button>
            </fieldset></form>
            <div className="graph-summary">
              {(mindGraph?.nodes || []).slice(0, 12).map((node) => (
                <span key={node.node_key}>{prettySpanish(node.node_type)}: {node.label}</span>
              ))}
            </div>
            <div className="compact-list relation-list">
              {(mindGraph?.edges || []).slice(0, 12).map((edge) => (
                <article key={edge.id}>
                  <strong>{prettySpanish(edge.relation_type)}</strong>
                  <span>{edge.source_node_key} → {edge.target_node_key}</span>
                </article>
              ))}
              {!mindGraph?.edges.length && <EmptyState text="Crea un snapshot para construir relaciones del caso." />}
            </div>
          </Card>
        </div>

        <Card className="panel-card">
          <h3>Prompts base</h3>
          <p>Prompts internos para resumir, extraer conceptos, crear notas, vincular memoria, auditar conclusiones y generar informe.</p>
          <div className="prompt-grid">
            {mindPrompts.slice(0, 8).map((prompt) => (
              <article key={prompt.id}>
                <strong>{prompt.title}</strong>
                <span>{prompt.purpose}</span>
                <small>Salida: {prompt.output_format}</small>
              </article>
            ))}
            {!mindPrompts.length && <EmptyState text="Sin prompts cargados." />}
          </div>
        </Card>

        <Card className="panel-card">
          <h3>Auditoría reciente</h3>
          <p>Trazabilidad de creación de notas, snapshots y relaciones de grafo vinculadas al caso o a la organización.</p>
          <div className="compact-list audit-list">
            {recentAudit.map((entry) => (
              <article key={entry.id}>
                <strong>{prettySpanish(entry.action)}</strong>
                <span>{entry.details || `${entry.entity_type} ${entry.entity_id}`}</span>
                <small>{entry.severity} · {entry.created_at ? formatHistoryDate(entry.created_at) : ""}</small>
              </article>
            ))}
            {!recentAudit.length && <EmptyState text="Sin eventos de auditoría de memoria para mostrar." />}
          </div>
        </Card>
      </ModuleSurface>
    );
  }

  function renderModuleStatus(title: string) {
    return (
      <ModuleSurface className="" moduleId="status">
        <div className="section-head">
          <div>
            <h2>{title}</h2>
            <p>Módulo conectado a la API canónica. Esta vista resume el estado disponible sin exponer datos técnicos internos.</p>
          </div>
        </div>
        <DataPanel data={modulePayload} empty="Todavía no hay actividad registrada para este módulo." />
      </ModuleSurface>
    );
  }

  function renderActive() {
    if (active === "workflow") return renderWorkflow();
    if (active === "dashboard") return renderDashboard();
    if (active === "caseDetail") return renderCaseDetail();
    if (active === "cases") return renderCases();
    if (active === "evidence") return renderEvidence();
    if (active === "reports") return renderReportsProfessional();
    if (active === "casePresentation") return renderCasePresentation();
    if (active === "mind") return renderMind();
    if (active === "legalKnowledge") return renderLegalKnowledge();
    if (active === "cybercrime") return renderCybercrime();
    if (active === "deepfakeMedia") return renderDeepfakeMedia();
    if (active === "blockchainForensics") return renderBlockchainForensics();
    if (active === "iotForensics") return renderIoTForensics();
    if (active === "mobileForensics") return selectedCaseId && authToken
      ? <ModuleSurface moduleId="mobileForensics"><MobileForensics key={`${selectedCaseId}:${authToken}`} caseId={Number(selectedCaseId)} caseCapabilities={caseAccess?.caseId === selectedCaseId && caseAccess.token === authToken ? caseAccess.capabilities : []} /></ModuleSurface>
      : <ModuleSurface moduleId="mobileForensics"><h2>Forense móvil</h2><p>Iniciá sesión y seleccioná un caso para registrar dispositivos y exámenes.</p></ModuleSurface>;
    if (active === "externalTools") return renderExternalTools();
    if (active === "ai") return renderAi();
    if (active === "aiSecurity") return renderAiSecurity();
    if (active === "identity") return renderIdentity();
    if (active === "history") return renderHistory();
    if (active === "settings") return renderSettings();
    return renderModuleStatus(modules.find((item) => item.key === active)?.label || "Módulo");
  }

  return (
    <ApplicationShell active={active} items={modules.filter(item => item.key !== "settings" || canUse("settings:read"))}
      sections={navigationSections} onNavigate={navigateTo} user={identitySession.user}
      caseCode={selectedCase?.case_code} loading={loading || caseCollectionsLoading} onIdentity={() => navigateTo("identity")}>
        {error && (
          <div role="alert" className={`error ${isAuthenticationErrorMessage(error) ? "auth-error" : ""}`}>
            <span>{error}</span>
            {isAuthenticationErrorMessage(error) && (
              <Button className="h-auto min-h-10 whitespace-normal secondary-button" onClick={() => setActive("identity")} variant="outline" type="button">
                <Users size={16} /> Ir a Usuarios
              </Button>
            )}
          </div>
        )}
        <div className="premium-operation-status" role="status" aria-live="polite" aria-atomic="true">{caseTask ? `${caseTask}…` : caseFeedback}</div>
        {renderActive()}
        <Dialog open={Boolean(pendingNavigation)} onOpenChange={open => { if (!open) setPendingNavigation(null); }}>
          <DialogContent showCloseButton={false} className="max-w-md"><DialogHeader><DialogTitle>Hay un borrador abierto</DialogTitle><DialogDescription>Si cambiás de contexto, se descartarán los cambios sin guardar. Los registros de evidencia y custodia ya guardados se conservarán.</DialogDescription></DialogHeader>
            <DialogFooter><Button variant="outline" onClick={() => setPendingNavigation(null)} className="h-auto min-h-10 whitespace-normal">Seguir editando</Button><Button onClick={() => { const action = pendingNavigation; setPendingNavigation(null); setEditingParticipant(null); setEditingEvidence(null); setEditingCustody(null); setCustodyReason(""); setEvidenceForm({ description: "", responsible: "", custodian: "" }); setEvidenceFile(null); setEvidenceUploadVersion(version => version + 1); setExecutiveSummaryDraft(reportPreview?.executive_summary || ""); action?.(); }} className="h-auto min-h-10 whitespace-normal">Descartar borrador y continuar</Button></DialogFooter>
          </DialogContent>
        </Dialog>
    </ApplicationShell>
  );
}



