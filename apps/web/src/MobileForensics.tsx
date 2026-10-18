import { mobilePermissions } from "@/lib/mobile-permissions";
import { fetchScopedDownload } from "@/lib/scoped-download";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormEvent, useEffect, useRef, useState } from "react";
import { API_BASE, apiGet, apiPost, authHeaders, getAuthToken } from "./api";

type Device = { id: number; label: string; platform: string };
type Acquisition = { id: number; device_id: number; filename: string; format: string; sha256: string; size_bytes: number };
type Job = { id: number; acquisition_id: number; state: string; error_code: string; result_sha256: string; configuration: { demo_rules: boolean } };
type Result = { artifacts: { id: string; locator: string; kind: string; original: unknown; normalized: unknown }[];
  alerts: { id: string; explanation: string; synthetic: boolean; artifact_ids: string[] }[];
  timeline: { id: string; normalized_utc: string; original: string; uncertainty: string }[];
  coverage: { state: string; limitations: string[]; sources: { status: string; excluded: unknown[]; warnings: string[] }[] };
  detection_status: string; counts: { artifacts: number; alerts: number; timeline: number } };
type Detail = { projections: { id: number; finding_id: number; hypothesis_id: number; geo_analysis_id: number | null; snapshot_sha256: string }[]; integrations: { id: number; review_id: number; evidence_id: number; report_id: number; snapshot_sha256: string }[]; job: Job; result: Result | null; reviews: { id: number; reviewer_name: string; created_at: string; content_json: string }[];
  events: { id: number; state: string; reason: string }[]; exports: { id: number; format: string; sha256: string }[] };
type Legacy = { id: number; filename: string; declared_mvt_version: string; origin: string };
type Capability = { message: string; readers: { platform: string; format: string; version: string }[] };
const ACTIVE = ["pendiente", "preparando", "ejecutando"];

async function downloadMobile(path: string, name: string, token: string, isCurrent: () => boolean) {
  const blob = await fetchScopedDownload(`${API_BASE}${path}`, token, isCurrent);
  if (!blob) return;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = name; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function MobileForensics({ caseId, caseCapabilities = [] }: { caseId: number; caseCapabilities?: string[] }) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [acquisitions, setAcquisitions] = useState<Acquisition[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [indicators, setIndicators] = useState<{ id: number; version: string; sha256: string }[]>([]);
  const [legacy, setLegacy] = useState<Legacy[]>([]);
  const [legacyDetail, setLegacyDetail] = useState<{ exam: Legacy; records: unknown[]; reviews: unknown[]; exports: { id: number }[] } | null>(null);
  const [deviceId, setDeviceId] = useState("");
  const [jobId, setJobId] = useState(0);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [capability, setCapability] = useState<Capability | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [dirtyForm, setDirtyForm] = useState("");
  const [rolePermissions, setRolePermissions] = useState<string[]>([]);
  const access = mobilePermissions(rolePermissions, caseCapabilities);
  const canWrite = access.acquire;
  const [sessionActive, setSessionActive] = useState(true);
  const [offset, setOffset] = useState(0);
  const panel = useRef<HTMLElement>(null);
  const mounted = useRef(true);
  const token = useRef(getAuthToken()).current;
  const download = (path: string, name: string, session: string) => {
    if (!access.download) throw new Error("No tenés permiso de exportación de este expediente.");
    return downloadMobile(path, name, session, () => mounted.current && getAuthToken() === session);
  };
  const root = `/mobile-forensics/cases/${caseId}`;
  const native = `/mobile-forensics/native/cases/${caseId}`;
  const selectedState = jobs.find(job => job.id === jobId)?.state;
  const hasActive = jobs.some(job => ACTIVE.includes(job.state));

  useEffect(() => {
    const changed = () => {
      if (getAuthToken() !== token) {
        setSessionActive(false); setDetail(null); setLegacyDetail(null); setAcquisitions([]);
        setJobs([]); setDevices([]); setIndicators([]); setLegacy([]); setRolePermissions([]); setDirty(false);
      }
    };
    window.addEventListener("operia:auth-changed", changed); window.addEventListener("storage", changed);
    return () => { window.removeEventListener("operia:auth-changed", changed); window.removeEventListener("storage", changed); };
  }, [token]);

  async function refresh() {
    const [d, a, j, i, h] = await Promise.all([apiGet<Device[]>(`${root}/devices`),
      apiGet<Acquisition[]>(`${native}/acquisitions`), apiGet<Job[]>(`${native}/jobs`),
      apiGet<typeof indicators>(`${native}/indicator-sets`), apiGet<Legacy[]>(`${root}/exams`)]);
    if (mounted.current && getAuthToken() === token) { setDevices(d); setAcquisitions(a); setJobs(j); setIndicators(i); setLegacy(h); }
  }
  useEffect(() => {
    mounted.current = true;
    void refresh().catch(e => { if (mounted.current) setError(e.message); });
    Promise.all([apiGet<Capability>("/mobile-forensics/native/capabilities"),
      apiGet<{ user: { role: string } | null }>("/identity/me"), apiGet<Record<string, string[]>>("/identity/permissions")])
      .then(([c, identity, roles]) => { if (mounted.current && getAuthToken() === token) {
        setCapability(c); const permissions = roles[identity.user?.role || ""] || [];
        setRolePermissions(permissions);
      } }).catch(e => { if (mounted.current) setError(e.message); });
    return () => { mounted.current = false; };
  }, [native, root, token]);
  useEffect(() => {
    if (!hasActive) return;
    const timer = window.setInterval(() => void refresh().catch(e => { if (mounted.current) setError(e.message); }), 2000);
    return () => window.clearInterval(timer);
  }, [hasActive, native, root, token]);
  useEffect(() => {
    let alive = true;
    if (jobId) apiGet<Detail>(`${native}/jobs/${jobId}?offset=${offset}`).then(data => {
      if (alive && getAuthToken() === token) setDetail(data);
    }).catch(e => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [native, jobId, selectedState, offset, token]);
  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => { if (dirty || busy) { event.preventDefault(); event.returnValue = ""; } };
    const navigate = (event: MouseEvent) => {
      if ((dirty || busy) && event.target instanceof Element && event.target.closest(".sidebar button")) {
        event.preventDefault(); event.stopPropagation(); setError("Guardá o descartá cambios y esperá la operación antes de navegar.");
      }
    };
    window.addEventListener("beforeunload", handler); document.addEventListener("click", navigate, true);
    return () => { window.removeEventListener("beforeunload", handler); document.removeEventListener("click", navigate, true); };
  }, [dirty, busy]);

  async function run(action: () => Promise<void>) {
    setError(""); setBusy(true);
    try { await action(); } catch (e) { if (mounted.current) setError(e instanceof Error ? e.message : "Error de operación"); }
    finally { if (mounted.current) { setBusy(false); if (getAuthToken() !== token) {
      setDetail(null); setLegacyDetail(null); setAcquisitions([]); setJobs([]); setDevices([]); setRolePermissions([]);
    } } }
  }
  async function fileBase64(file: File, max = 5 * 1024 * 1024) {
    if (!file || file.size > max) throw new Error("Archivo ausente o supera la cuota de bytes.");
    const bytes = new Uint8Array(await file.arrayBuffer()); let binary = "";
    for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
    return btoa(binary);
  }
  function createDevice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    void run(async () => {
      const device = await apiPost<Device>(`${root}/devices`, Object.fromEntries(data));
      if (!mounted.current || getAuthToken() !== token) return;
      await refresh(); setDeviceId(String(device.id)); form.reset(); setDirty(false);
    });
  }
  function preserve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    void run(async () => {
      const file = data.get("file") as File; const metadata = Object.fromEntries(data); delete metadata.file; delete metadata.format;
      await apiPost(`${native}/acquisitions`, { device_id: Number(deviceId), metadata, format: data.get("format"),
        filename: file.name, content_base64: await fileBase64(file) });
      if (!mounted.current || getAuthToken() !== token) return;
      await refresh(); form.reset(); setDirty(false);
    });
  }
  function enqueue(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    void run(async () => {
      const job = await apiPost<Job>(`${native}/jobs`, { acquisition_id: Number(data.get("acquisition_id")),
        indicator_set_id: data.get("indicator_set_id") ? Number(data.get("indicator_set_id")) : null, demo_rules: data.get("demo_rules") === "on" });
      if (!mounted.current || getAuthToken() !== token) return;
      await refresh(); setDetail(null); setOffset(0); setJobId(job.id);
    });
  }
  function review(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    void run(async () => {
      const ids = String(data.get("artifact_ids") || "").split(/[\s,]+/).filter(Boolean);
      await apiPost(`${native}/jobs/${jobId}/reviews`, { ...Object.fromEntries(data), artifact_ids: ids });
      if (!mounted.current || getAuthToken() !== token) return;
      setDetail(await apiGet<Detail>(`${native}/jobs/${jobId}?offset=${offset}`)); form.reset(); setDirty(false);
    });
  }

  if (!sessionActive) return <section className="panel mobile-forensics"><h2>Sesión cambiada o vencida</h2><p>Los datos del examen se retiraron de la pantalla. Iniciá sesión para continuar.</p></section>;
  return <section className="panel mobile-forensics" ref={panel}>
    <h2>Motor Forense Móvil de OPERIA</h2><p>{capability?.message || "Consultando capacidades…"}</p>
    <p>Caso {caseId}. Análisis posterior a adquisición, sin conexión al dispositivo ni servicios externos. Validación sintética; no es un detector certificado de spyware.</p>
    <p>Worker separado requerido: <code>python -m operia.forensic_jobs.worker</code>. Los trabajos permanecen pendientes si no está iniciado. El proceso local no constituye un sandbox.</p>
    {error && <p role="alert">{error}</p>}
    {!Object.values(access).some(Boolean) && <p>Modo de lectura o permisos aún sin verificar.</p>}
    {dirty && <p role="status">Hay cambios sin guardar. <Button disabled={busy} onClick={() => {
      panel.current?.querySelectorAll("form").forEach(form => form.reset()); setDirty(false); setError("");
    }} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">Descartar cambios pendientes</Button></p>}
    <fieldset disabled={busy || !canWrite || (dirty && dirtyForm !== "device")}><legend>1. Dispositivo · datos declarados</legend>
      <form className="form-grid" onSubmit={createDevice} onChange={() => { setDirty(true); setDirtyForm("device"); }}>
        <label>Nombre<Input name="label" required maxLength={160} /></label>
        <label>Plataforma<select name="platform"><option value="ios">iOS</option><option value="android">Android</option></select></label>
        <label>Identificador interno<Input name="identifier" required maxLength={160} /></label><Button variant="default" type="submit" className="h-auto min-h-10 whitespace-normal">Registrar dispositivo</Button>
      </form>
    </fieldset>
    <fieldset disabled={busy || !canWrite || !devices.length || (dirty && dirtyForm !== "acquisition")}><legend>2. Preservar adquisición autorizada</legend>
      <label>Dispositivo<select value={deviceId} disabled={dirty} onChange={e => setDeviceId(e.target.value)}><option value="">Seleccionar…</option>
        {devices.map(d => <option value={d.id} key={d.id}>{d.label} ({d.platform})</option>)}</select></label>
      <form className="form-grid" onSubmit={preserve} onChange={() => { setDirty(true); setDirtyForm("acquisition"); }}><fieldset disabled={!deviceId}>
        <label>Formato<select name="format" required key={deviceId}>
          {(capability?.readers || []).filter(r => r.platform === devices.find(d => d.id === Number(deviceId))?.platform).map(r => <option key={r.format} value={r.format}>{r.format} · lector {r.version}</option>)}
        </select></label>
        {[["authorization", "Autorización y fundamento documentado"], ["scope", "Alcance"], ["provenance", "Origen y operador de adquisición"],
          ["acquisition_method", "Método de adquisición"], ["acquisition_date_original", "Fecha original o desconocida"],
          ["retention_policy", "Retención y eliminación"], ["restrictions", "Restricciones de uso"], ["declared_os_version", "Versión de OS declarada o desconocida"]].map(([name, label]) =>
          <label key={name}>{label}<Input name={name} required maxLength={name === "acquisition_method" ? 160 : name === "acquisition_date_original" || name === "declared_os_version" ? 80 : 4000} /></label>)}
        <label>Archivo original · máximo 5 MiB<Input type="file" name="file" required accept=".plist,.mobileconfig,.txt,.log,.db,.sqlite,.sqlite3,.json" aria-describedby="mobile-source-help" /></label>
        <p id="mobile-source-help" className="text-sm text-muted-foreground">Para WAL/SHM, seleccioná el paquete JSON preservado del conjunto. La base y los sidecars sueltos no se combinan automáticamente.</p>
        <Button disabled={!deviceId} variant="default" type="submit" className="h-auto min-h-10 whitespace-normal">Preservar bytes originales</Button>
      </fieldset></form>
    </fieldset>
    <details><summary>Indicadores propios del caso · opcionales</summary>
      <p>JSON operia.indicators/1, hasta 256 KiB. Fuente, condiciones, versión y limitaciones obligatorias. No se descargan feeds.</p>
      <form onSubmit={event => { event.preventDefault(); const form = event.currentTarget; const file = new FormData(form).get("indicators") as File;
        void run(async () => { if (!file || file.size > 256 * 1024) throw new Error("Archivo de indicadores supera 256 KiB");
          const response = await fetch(`${API_BASE}${native}/indicator-sets`, { method: "POST", headers: authHeaders({ "Content-Type": "application/json" }), body: await file.arrayBuffer() });
          if (!response.ok) throw new Error(`Indicadores rechazados (${response.status})`); await refresh(); form.reset(); });
      }}><label>Conjunto exacto de indicadores<Input name="indicators" type="file" accept=".json" required disabled={!canWrite || busy} /></label>
        <Button disabled={!canWrite || busy || dirty} variant="default" type="submit" className="h-auto min-h-10 whitespace-normal">Registrar conjunto</Button></form>
      {indicators.map(i => <p key={i.id}>Conjunto {i.id} · versión {i.version} · SHA-256 {i.sha256}</p>)}
    </details>
    <fieldset disabled={busy || !access.analyze || !acquisitions.length || dirty}><legend>3. Crear examen y trabajo persistente</legend>
      <form className="form-grid" onSubmit={enqueue}>
        <label>Adquisición<select name="acquisition_id" required>{acquisitions.filter(a => !deviceId || a.device_id === Number(deviceId)).map(a =>
          <option key={a.id} value={a.id}>{a.id} · {a.filename} · {a.format}</option>)}</select></label>
        <label>Indicadores<select name="indicator_set_id"><option value="">Sin indicadores · cobertura de detección limitada</option>{indicators.map(i => <option key={i.id} value={i.id}>{i.id} · {i.version}</option>)}</select></label>
        <label className="mobile-consent"><input name="demo_rules" type="checkbox" />Activar reglas sintéticas de demostración (no firmas de malware)</label><Button variant="default" type="submit" className="h-auto min-h-10 whitespace-normal">Encolar examen</Button>
      </form>
    </fieldset>
    <h3>4. Trabajos, cobertura y resultados</h3>
    {!jobs.length && <p>Sin trabajos. Preservá un archivo y creá un examen.</p>}
    <Button disabled={busy || dirty} onClick={() => void run(refresh)} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">Actualizar trabajos</Button>
    <div>{jobs.map(job => <Button key={job.id} disabled={busy || dirty} onClick={() => { setDetail(null); setOffset(0); setJobId(job.id); }} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">
      Examen {job.id} · adquisición {job.acquisition_id} · {job.state}</Button>)}</div>
    {detail && <><p>Estado técnico: <strong>{detail.job.state}</strong> {detail.job.error_code}</p>
      {ACTIVE.includes(detail.job.state) && <Button disabled={busy || !access.analyze} onClick={() => void run(async () => { await apiPost(`${native}/jobs/${jobId}/cancel`, {}); await refresh(); })} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">Solicitar cancelación</Button>}
      {["fallido", "cancelado", "interrumpido"].includes(detail.job.state) && <Button disabled={busy || !access.analyze} onClick={() => void run(async () => { await apiPost(`${native}/jobs/${jobId}/retry`, {}); await refresh(); })} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">Reintentar con historial</Button>}
      <details><summary>Historial técnico del trabajo</summary>{detail.events.map(e => <p key={e.id}>{e.state} · {e.reason}</p>)}</details>
      {detail.result && <>
        <p>Cobertura: <strong>{detail.result.coverage.state}</strong>. Detección: {detail.result.detection_status}. Conclusión: requiere revisión.</p>
        {detail.result.coverage.sources.map((source, i) => <p key={i}>{source.status} · {source.excluded.length} exclusiones. {source.warnings.join(" ")}</p>)}
        <p>{detail.result.coverage.limitations.join(" ")}</p><p>Hash canónico del resultado: <code>{detail.job.result_sha256}</code></p>
        <Button disabled={busy || !access.download} onClick={() => void run(() => download(`${native}/acquisitions/${detail.job.acquisition_id}/original`, acquisitions.find(a => a.id === detail.job.acquisition_id)?.filename || "original.bin", token))} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">Descargar original</Button>
        <h4>Observaciones · {detail.result.counts.artifacts} artefactos</h4>
        {detail.result.artifacts.map(a => <details key={a.id}><summary>{a.kind} · {a.locator}</summary><p>ID: <code>{a.id}</code></p><pre>{JSON.stringify({ original: a.original, normalized: a.normalized }, null, 2)}</pre></details>)}
        <h4>Alertas · {detail.result.counts.alerts}</h4>{detail.result.alerts.map(a => <article key={a.id}><strong>{a.synthetic ? "DEMOSTRACIÓN SINTÉTICA" : "Coincidencia pendiente de corroboración"}</strong><p>{a.explanation}</p><code>{a.artifact_ids.join(", ")}</code></article>)}
        <h4>Cronología · {detail.result.counts.timeline} eventos</h4>{!detail.result.counts.timeline && <p>No hay tiempos normalizables para esta fuente. No se infiere inicio de ataque.</p>}
        {detail.result.timeline.map(t => <p key={t.id}>{t.normalized_utc} · original: {t.original} · {t.uncertainty}</p>)}
        <Button disabled={busy || dirty || offset === 0} onClick={() => setOffset(offset - 100)} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">Anteriores</Button>
        <Button disabled={busy || dirty || offset + 100 >= Math.max(...Object.values(detail.result.counts))} onClick={() => setOffset(offset + 100)} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">Siguientes</Button>
        <h3>5. Revisión profesional versionada</h3><p>La confirmación de compromiso requiere corroboración independiente y permanece fuera del alcance de este MVP.</p>
        <form key={jobId} className="form-grid" onSubmit={review} onChange={() => { setDirty(true); setDirtyForm("review"); }}><fieldset disabled={busy || !access.review || (dirty && dirtyForm !== "review")}>
          <label>Conclusión<select name="conclusion"><option value="inconcluso">Inconcluso</option><option value="actividad_sospechosa">Actividad sospechosa</option><option value="indicios_compatibles_con_compromiso">Indicios compatibles con compromiso</option><option value="sin_indicios_en_el_alcance_examinado">Sin indicios dentro del alcance (requiere cobertura y justificación)</option></select></label>
          <label>IDs de artefactos de respaldo, separados por coma<Input name="artifact_ids" /></label>
          {[["rationale", "Fundamentos"], ["alternatives", "Alternativas y contradicciones"], ["limitations", "Limitaciones"], ["current_activity", "Actividad actual"], ["chronology", "Cronología e incertidumbre"], ["attribution", "Atribución y límites"], ["coverage_justification", "Justificación expresa del alcance y cobertura"]].map(([name, label]) =>
            <label key={name}>{label}<textarea name={name} required minLength={10} maxLength={4000} /></label>)}<Button variant="default" type="submit" className="h-auto min-h-10 whitespace-normal">Agregar revisión</Button>
        </fieldset></form>
        {detail.reviews.map(r => <article key={r.id}><strong>Revisión {r.id} · {r.reviewer_name}</strong><p>{r.created_at} UTC</p><pre>{JSON.stringify(JSON.parse(r.content_json), null, 2)}</pre><Button type="button" disabled={busy || dirty || !access.publish} onClick={() => void run(async () => {
          await apiPost<{ evidence_id: number; report_id: number }>(`${native}/jobs/${jobId}/integrations?review_id=${r.id}`, {});
          if (!mounted.current || getAuthToken() !== token) return;
          setDetail(await apiGet<Detail>(`${native}/jobs/${jobId}?offset=${offset}`));
        })} variant="default" className="h-auto min-h-10 whitespace-normal">Incorporar revisión a evidencia, custodia e informe</Button></article>)}
        <h3>6. Informes y exportaciones</h3>{["json", "csv"].map(format => <Button key={format} disabled={busy || dirty || !access.generateExport} onClick={() => void run(async () => {
          const item = await apiPost<{ id: number }>(`${native}/jobs/${jobId}/exports`, { format });
          if (!mounted.current || getAuthToken() !== token) return;
          await download(`${native}/jobs/${jobId}/exports/${item.id}`, `operia-native-${jobId}-${item.id}.${format}`, token);
          setDetail(await apiGet<Detail>(`${native}/jobs/${jobId}?offset=${offset}`));
        })} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">Crear {format === "json" ? "informe JSON" : "CSV temporal"}</Button>)}
        {detail.integrations.map(i => <p key={i.id}>Revisión {i.review_id}: evidencia {i.evidence_id}, informe {i.report_id}. <Button disabled={busy || !access.download} onClick={() => void run(() => download(`${native}/jobs/${jobId}/integrations/${i.id}`, `operia-integration-${i.id}.json`, token))} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">Descargar instantánea preservada</Button><code>{i.snapshot_sha256}</code></p>)}
        <h3>7. Hallazgos, hipótesis y Geo Trace</h3><p>Seleccioná artefactos respaldados por una revisión ya incorporada. Geo Trace conserva referencias pasivas: no consulta URLs ni infiere ubicaciones o responsables.</p>
        <form key={`projection-${jobId}`} className="form-grid" onChange={() => { setDirty(true); setDirtyForm("projection"); }} onSubmit={event => {
          event.preventDefault(); const form = event.currentTarget; const values = new FormData(form);
          void run(async () => {
            await apiPost(`${native}/jobs/${jobId}/projections`, { integration_id: Number(values.get("integration_id")),
              artifact_ids: String(values.get("artifact_ids") || "").split(/[\s,]+/).filter(Boolean),
              hypothesis_text: values.get("hypothesis_text"), facts_to_prove: values.get("facts_to_prove"), create_geo: values.get("create_geo") === "on" });
            if (!mounted.current || getAuthToken() !== token) return;
            setDetail(await apiGet<Detail>(`${native}/jobs/${jobId}?offset=${offset}`)); form.reset(); setDirty(false);
          });
        }}><fieldset disabled={busy || !access.project || !detail.integrations.length || (dirty && dirtyForm !== "projection")}>
          <label>Incorporación de evidencia<select name="integration_id" required>{detail.integrations.map(i => <option key={i.id} value={i.id}>Incorporación {i.id} · revisión {i.review_id}</option>)}</select></label>
          <label>IDs de artefactos revisados<Input name="artifact_ids" required /></label>
          <label>Hipótesis profesional por contrastar<textarea name="hypothesis_text" minLength={20} maxLength={4000} required /></label>
          <label>Hechos y corroboración necesarios<textarea name="facts_to_prove" minLength={20} maxLength={4000} required /></label>
          <label><input type="checkbox" name="create_geo" />Crear Geo Trace pasivo de las URLs mencionadas (requiere referencias URL)</label>
          <Button variant="default" type="submit" className="h-auto min-h-10 whitespace-normal">Preservar hallazgo e hipótesis</Button>
        </fieldset></form>
        {detail.projections.map(p => <p key={p.id}>Hallazgo {p.finding_id}, hipótesis {p.hypothesis_id}, Geo Trace {p.geo_analysis_id ?? "no solicitado"}. <Button disabled={busy || !access.download} onClick={() => void run(() => download(`${native}/jobs/${jobId}/projections/${p.id}`, `operia-projection-${p.id}.json`, token))} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">Descargar respaldo de proyección</Button><code>{p.snapshot_sha256}</code></p>)}
        {detail.exports.map(e => <p key={e.id}><Button disabled={busy || !access.download} onClick={() => void run(() => download(`${native}/jobs/${jobId}/exports/${e.id}`, `operia-native-${jobId}-${e.id}.${e.format}`, token))} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">Descargar exportación {e.id} ({e.format})</Button><code>{e.sha256}</code></p>)}
      </>}
    </>}
    <details><summary>Resultados externos históricos · {legacy.length}</summary><p>Origen externo declarado. Se conservan herramienta, versión, bytes y reportes; no pertenecen al motor propio. El importador anterior fue retirado.</p>
      {legacy.map(e => <Button key={e.id} disabled={dirty || busy} onClick={() => void run(async () => {
        const data = await apiGet<typeof legacyDetail>(`${root}/exams/${e.id}`); if (mounted.current && getAuthToken() === token) setLegacyDetail(data);
      })} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">Histórico externo {e.id} · {e.filename} · {e.declared_mvt_version}</Button>)}
      {legacyDetail && <><p>{legacyDetail.exam.origin}</p><Button disabled={busy || !access.download} onClick={() => void run(() => download(`${root}/exams/${legacyDetail.exam.id}/original`, legacyDetail.exam.filename, token))} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">Original histórico</Button>
        <pre>{JSON.stringify({ records: legacyDetail.records, reviews: legacyDetail.reviews }, null, 2)}</pre>
        {legacyDetail.exports.map(e => <Button key={e.id} onClick={() => void run(() => download(`${root}/exams/${legacyDetail.exam.id}/exports/${e.id}`, `historico-${e.id}.json`, token))} variant="default" type="button" className="h-auto min-h-10 whitespace-normal">Reporte histórico {e.id}</Button>)}</>}
    </details>
    {busy && <p role="status">Procesando solicitud…</p>}
  </section>;
}
