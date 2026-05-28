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
  Search,
  Settings,
  Shield,
  Upload,
  Users,
  Wrench
} from "lucide-react";
import { API_BASE, apiGet, apiPost, apiPostForm } from "./api";

type ModuleKey =
  | "workflow"
  | "dashboard"
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
};

type CustodyAction = {
  id: number;
  case_id: number;
  evidence_id?: number;
  action_type: string;
  detailed_description: string;
  hash_after?: string;
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
  role_description: string;
  relationship_to_case: string;
  sensitivity_level: string;
};

type ReportItem = {
  id: number;
  case_id: number;
  title: string;
  status: string;
  author: string;
  review_score: number;
};

type LegalArticle = {
  id: number;
  code: string;
  article_number: string;
  subsection: string;
  title: string;
  objective_elements: string;
  evidentiary_requirements: string;
  official_url: string;
};

type DashboardPayload = {
  metrics?: Record<string, number>;
  alerts?: string[];
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

const modules: Array<{ key: ModuleKey; label: string; icon: typeof BarChart3 }> = [
  { key: "workflow", label: "Flujo Operativo", icon: CheckCircle2 },
  { key: "dashboard", label: "Dashboard", icon: BarChart3 },
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
  const [evidenceForm, setEvidenceForm] = useState({ description: "", responsible: "", custodian: "" });
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [custodyForm, setCustodyForm] = useState({ action_type: "revision", detailed_description: "", user_responsible: "" });
  const [indicator, setIndicator] = useState("https://secure-login.example.com/verify");
  const [indicatorResult, setIndicatorResult] = useState<unknown>(null);
  const [legalQuery, setLegalQuery] = useState("phishing fraude acceso datos");
  const [legalRecommendation, setLegalRecommendation] = useState<unknown>(null);
  const [aiPrompt, setAiPrompt] = useState("Analiza el caso, evidencia cargada, riesgos y proximos pasos. No inventes normas legales.");
  const [aiResult, setAiResult] = useState<unknown>(null);
  const [reviewResult, setReviewResult] = useState<unknown>(null);
  const [closureStatus, setClosureStatus] = useState<ClosureStatus | null>(null);
  const [closureNote, setClosureNote] = useState("Cierre operativo con evidencia preservada, informe revisado y PDF exportado.");
  const [aiSecurityResult, setAiSecurityResult] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedCase = useMemo(() => cases.find((item) => item.id === Number(selectedCaseId)), [cases, selectedCaseId]);
  const latestReport = reports[0];
  const latestEvidence = evidence[0];

  async function refreshCaseCollections(caseId: number | "") {
    if (!caseId) {
      setEvidence([]);
      setParticipants([]);
      setReports([]);
      setCustody([]);
      setClosureStatus(null);
      return;
    }
    const [participantData, evidenceData, reportData, custodyData] = await Promise.all([
      apiGet<CaseParticipant[]>(`/cases/${caseId}/participants`),
      apiGet<EvidenceItem[]>(`/evidence/case/${caseId}`),
      apiGet<ReportItem[]>(`/reports/case/${caseId}`),
      apiGet<CustodyAction[]>(`/evidence/case/${caseId}/custody-actions`)
    ]);
    setParticipants(participantData);
    setEvidence(evidenceData);
    setReports(reportData);
    setCustody(custodyData);
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
        settings: "/settings/"
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

  async function analyzeIndicator() {
    setIndicatorResult(await apiPost("/cybercrime/analyze-indicator", { case_id: selectedCaseId || undefined, indicator }));
    if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
  }

  async function searchLegal() {
    const [found, recommended] = await Promise.all([
      apiGet<LegalArticle[]>(`/legal-knowledge/articles?q=${encodeURIComponent(legalQuery)}`),
      apiPost("/legal-knowledge/articles/recommend", { incident_text: legalQuery })
    ]);
    setArticles(found);
    setLegalRecommendation(recommended);
  }

  async function runAiAssist() {
    setAiResult(await apiPost("/ai/assist", { case_id: selectedCaseId || undefined, model_name: "mistral", prompt: aiPrompt }));
  }

  async function generateReport() {
    if (!selectedCaseId) return;
    const report = await apiPost<ReportItem>(`/reports/case/${selectedCaseId}/generate?author=OPERIA`);
    await refreshCaseCollections(selectedCaseId);
    setReviewResult({ generated_report_id: report.id, status: "generated" });
  }

  async function reviewReport() {
    if (!latestReport) return;
    setReviewResult(await apiPost(`/reports/${latestReport.id}/review`));
    if (selectedCaseId) await refreshCaseCollections(selectedCaseId);
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
              <input placeholder="Tipo de incidente" value={caseForm.incident_type} onChange={(e) => setCaseForm({ ...caseForm, incident_type: e.target.value })} />
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

          <StepCard number={7} title="Pedir asistencia IA local con Mistral" done={Boolean(aiResult)}>
            <div className="compact-form">
              <textarea value={aiPrompt} onChange={(e) => setAiPrompt(e.target.value)} />
              <button onClick={runAiAssist}><Bot size={17} /> Consultar Mistral local</button>
            </div>
            <JsonPanel data={aiResult} />
          </StepCard>

          <StepCard number={8} title="Generar informe" done={reports.length > 0}>
            <button onClick={generateReport} disabled={!selectedCaseId}><FileText size={17} /> Generar informe integral</button>
            {latestReport && <p className="notice">Ultimo informe: {latestReport.title}</p>}
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
            <p>Generacion, revision y exportacion desde reportes canonicos.</p>
          </div>
          <button onClick={generateReport} disabled={!selectedCaseId}><FileText size={17} /> Generar informe</button>
        </div>
        <div className="table">
          {reports.map((item) => (
            <div className="record record-grid" key={item.id}>
              <strong>{item.title}</strong>
              <span>{item.status}</span>
              <em>Score {item.review_score}</em>
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
            <p>Busqueda estructurada sobre fuentes registradas.</p>
          </div>
          <div className="search">
            <input value={legalQuery} onChange={(e) => setLegalQuery(e.target.value)} />
            <button className="icon-button" onClick={searchLegal} title="Buscar"><Search size={18} /></button>
          </div>
        </div>
        <div className="article-list">
          {articles.map((item) => (
            <article key={item.id}>
              <div>
                <span>{item.code} art. {item.article_number}{item.subsection ? ` inc. ${item.subsection}` : ""}</span>
                <h3>{item.title}</h3>
              </div>
              <p>{item.objective_elements}</p>
              <small>{item.evidentiary_requirements}</small>
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
            <h2>Asistente IA Local</h2>
            <p>Mistral via Ollama con guardrails, contexto legal y revision humana.</p>
          </div>
        </div>
        <div className="split">
          <div className="form">
            <textarea value={aiPrompt} onChange={(e) => setAiPrompt(e.target.value)} />
            <button onClick={runAiAssist}><Bot size={17} /> Analizar con IA</button>
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
