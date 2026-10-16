import { FormEvent, useEffect, useRef, useState } from "react";
import { API_BASE, apiGet, apiPost, authHeaders } from "./api";

type Device = { id: number; label: string; platform: string };
type Exam = { id: number; device_id: number; filename: string; sha256: string; coverage: string;
  candidate_count: number; record_count: number; limitations: string };
type Review = { id: number; conclusion: string; reviewer_name: string; created_at: string; rationale: string };
type Detail = { exam: Exam; records: { index: number; pointer: string; record: unknown; assessment: string }[]; reviews: Review[] };

async function download(path: string, name: string) {
  const response = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  if (!response.ok) throw new Error(`No se pudo descargar (${response.status}). Revisá sesión, permisos e integridad.`);
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = name; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function MobileForensics({ caseId }: { caseId: number }) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [exams, setExams] = useState<Exam[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [examId, setExamId] = useState(0);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [engine, setEngine] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [offset, setOffset] = useState(0);
  const panel = useRef<HTMLElement>(null);
  const [canWrite, setCanWrite] = useState(false);
  const root = `/mobile-forensics/cases/${caseId}`;

  useEffect(() => {
    let alive = true;
    Promise.all([apiGet<Device[]>(`${root}/devices`), apiGet<Exam[]>(`${root}/exams`),
      apiGet<{ message: string }>("/mobile-forensics/engine"),
      apiGet<{ user: { role: string } | null }>("/identity/me"),
      apiGet<Record<string, string[]>>("/identity/permissions")]).then(([d, e, status, identity, roles]) => {
      if (alive) {
        setDevices(d); setExams(e); setEngine(status.message);
        const permissions = roles[identity.user?.role || ""] || [];
        setCanWrite(permissions.includes("*") || permissions.includes("evidence:write"));
      }
    }).catch(e => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [root]);
  useEffect(() => {
    let alive = true; setDetail(null);
    if (examId) apiGet<Detail>(`${root}/exams/${examId}?offset=${offset}`).then(data => {
      if (alive) setDetail(data);
    }).catch(e => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [root, examId, offset]);
  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => { if (dirty) { event.preventDefault(); event.returnValue = ""; } };
    const navigate = (event: MouseEvent) => {
      if (dirty && event.target instanceof Element && event.target.closest(".sidebar button")) {
        event.preventDefault(); event.stopPropagation();
        setError("Guardá o descartá los cambios del módulo antes de navegar.");
      }
    };
    window.addEventListener("beforeunload", handler);
    document.addEventListener("click", navigate, true);
    return () => { window.removeEventListener("beforeunload", handler); document.removeEventListener("click", navigate, true); };
  }, [dirty]);

  async function run(action: () => Promise<void>) {
    setError(""); setBusy(true);
    try { await action(); } catch (e) { setError(e instanceof Error ? e.message : "Error de operación"); }
    finally { setBusy(false); }
  }

  function createDevice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    void run(async () => {
      const device = await apiPost<Device>(`${root}/devices`, Object.fromEntries(data));
      setDevices(previous => [...previous, device]); setDeviceId(String(device.id)); form.reset(); setDirty(false);
    });
  }

  function importFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    void run(async () => {
      const file = data.get("file") as File;
      if (!file || !file.size) throw new Error("Seleccioná un JSON MVT. Un archivo de cero bytes no es válido.");
      if (file.size > 5 * 1024 * 1024) throw new Error("La interfaz admite hasta 5 MiB por archivo.");
      const bytes = new Uint8Array(await file.arrayBuffer());
      let binary = "";
      for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
      const metadata = Object.fromEntries(data); delete metadata.file;
      const exam = await apiPost<Exam>(`${root}/devices/${deviceId}/imports`, {
        metadata: { ...metadata, data_owner_consent: data.get("data_owner_consent") === "on" },
        filename: file.name, content_base64: btoa(binary)
      });
      setExams(previous => [exam, ...previous]); setOffset(0); setExamId(exam.id); form.reset(); setDirty(false);
    });
  }

  function submitReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    void run(async () => {
      const text = String(data.get("record_indexes") || "").trim();
      const indexes = text ? text.split(",").map(value => Number(value.trim())) : [];
      if (indexes.some(value => !Number.isInteger(value))) throw new Error("Usá índices enteros separados por coma.");
      await apiPost(`${root}/exams/${examId}/reviews`, { ...Object.fromEntries(data), record_indexes: indexes });
      setDetail(await apiGet<Detail>(`${root}/exams/${examId}?offset=${offset}`)); form.reset(); setDirty(false);
    });
  }

  return <section className="panel mobile-forensics" ref={panel}>
    <h2>Forense móvil · piloto de importación</h2>
    <p>{engine || "Consultando estado del módulo…"}</p>
    <p>Preserva resultados recibidos y permite revisión local. No adquiere ni modifica dispositivos.
      Cobertura parcial; sin validación con dispositivos reales. El caso seleccionado define el ámbito.</p>
    {error && <p role="alert">{error}</p>}
    {!canWrite && <p>Modo de lectura. Tu rol no permite registrar dispositivos, importar ni agregar revisiones o exportaciones.</p>}
    {dirty && <p role="status">Hay cambios sin guardar. Guardalos antes de cambiar de caso o módulo.
      <button type="button" disabled={busy} onClick={() => {
        panel.current?.querySelectorAll("form").forEach(form => form.reset()); setDirty(false); setError("");
      }}>Descartar cambios pendientes</button></p>}
    <fieldset disabled={busy || !canWrite}>
      <legend>1. Registrar dispositivo</legend>
      <form onSubmit={createDevice} onChange={() => setDirty(true)} className="form-grid">
        <label>Nombre<input name="label" required maxLength={160} /></label>
        <label>Plataforma<select name="platform"><option value="ios">iOS</option><option value="android">Android</option></select></label>
        <label>Identificador<input name="identifier" required maxLength={160} placeholder="Identificador interno o no registrado" /></label>
        <button type="submit">Registrar dispositivo</button>
      </form>
    </fieldset>
    <fieldset disabled={busy || !devices.length || !canWrite}>
      <legend>2. Importar un archivo de una ejecución</legend>
      <label>Dispositivo<select value={deviceId} onChange={e => setDeviceId(e.target.value)}>
        <option value="">Seleccionar…</option>{devices.map(d => <option key={d.id} value={d.id}>{d.label} ({d.platform})</option>)}
      </select></label>
      <p>Admite sms.json y sms_detected.json; iOS también safari_history.json y safari_history_detected.json.
        Cada importación crea un examen independiente. No combines ejecuciones en un archivo.</p>
      <form onSubmit={importFile} onChange={() => setDirty(true)} className="form-grid">
        {([
          ["authorization", "Autorización y referencia del consentimiento"], ["scope", "Alcance autorizado"],
          ["provenance", "Procedencia y responsable de adquisición"], ["acquisition_method", "Método de adquisición"],
          ["acquisition_date", "Fecha original de adquisición (o desconocida)"], ["retention_policy", "Política de retención y eliminación informada"],
          ["declared_mvt_version", "Versión de MVT declarada"], ["declared_run_id", "Identificador de ejecución original"],
          ["indicators_description", "Indicadores usados, hashes y limitaciones (o desconocidos)"]
        ] as const).map(([name, label]) => <label key={name}>{label}<input name={name} required maxLength={name.includes("version") ? 80 : name === "acquisition_method" || name === "declared_run_id" ? 160 : name === "acquisition_date" ? 80 : 4000} /></label>)}
        <label className="mobile-consent"><input type="checkbox" name="data_owner_consent" required />El dueño de los datos prestó consentimiento explícito, libre e informado sobre privacidad, retención y eliminación.</label>
        <label>Resultado original (máximo 5 MiB)<input type="file" name="file" accept=".json" required /></label>
        <button type="submit" disabled={!deviceId}>Preservar e importar</button>
      </form>
    </fieldset>
    <h3>3. Exámenes y registros</h3>
    {!exams.length && <p>No hay exámenes. Registrá un dispositivo e importá un resultado autorizado.</p>}
    <label>Filtrar por dispositivo<select value={deviceId} onChange={e => setDeviceId(e.target.value)}>
      <option value="">Todos</option>{devices.map(d => <option key={d.id} value={d.id}>{d.label}</option>)}
    </select></label>
    <div>{exams.filter(e => !deviceId || e.device_id === Number(deviceId)).map(e => <button key={e.id}
      disabled={busy || dirty} onClick={() => { setOffset(0); setExamId(e.id); }}>
      Examen {e.id} · {e.filename} · {e.record_count} registros · {e.candidate_count} candidatos
    </button>)}</div>
    {detail && <>
      <p><strong>Cobertura: {detail.exam.coverage}</strong>. {detail.exam.limitations}</p>
      <p>SHA-256 de los bytes originales: <code>{detail.exam.sha256}</code></p>
      <button disabled={busy} onClick={() => void run(() => download(`${root}/exams/${examId}/original`, detail.exam.filename))}>Descargar original</button>
      {detail.records.map(r => <details key={r.index}><summary>Registro {r.pointer} · {r.assessment}</summary><pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{JSON.stringify(r.record, null, 2)}</pre></details>)}
      <button disabled={busy || dirty || offset === 0} onClick={() => setOffset(offset - 100)}>Anteriores</button>
      <button disabled={busy || dirty || offset + 100 >= detail.exam.record_count} onClick={() => setOffset(offset + 100)}>Siguientes</button>
      <h3>4. Revisión profesional con historial</h3>
      <p>Este piloto admite conclusiones preliminares. Confirmación de compromiso y ausencia de indicios requieren cobertura e indicadores verificables.</p>
      <form key={examId} onSubmit={submitReview} onChange={() => setDirty(true)} className="form-grid">
        <fieldset disabled={busy || !canWrite}>
          <label>Conclusión<select name="conclusion"><option value="inconcluso">Inconcluso</option><option value="actividad_sospechosa">Actividad sospechosa</option><option value="indicios_compatibles_con_compromiso">Indicios compatibles con compromiso</option></select></label>
          <label>Índices de respaldo separados por coma<input name="record_indexes" placeholder="0,1" /></label>
          {[["rationale", "Fundamento"], ["alternatives", "Explicaciones alternativas"], ["limitations", "Limitaciones"],
            ["current_activity", "Evaluación de actividad actual"], ["chronology", "Cronología e incertidumbre"], ["attribution", "Atribución y límites"]].map(([name, label]) =>
            <label key={name}>{label}<textarea name={name} minLength={10} maxLength={4000} required /></label>)}
          <button type="submit">Agregar revisión (conserva las anteriores)</button>
        </fieldset>
      </form>
      {detail.reviews.map(r => <article key={r.id}><strong>Revisión {r.id}: {r.conclusion}</strong><p>{r.reviewer_name} · {r.created_at} UTC</p><p>{r.rationale}</p></article>)}
      <h3>5. Exportación JSON del piloto</h3>
      <button disabled={busy || dirty || !canWrite} onClick={() => void run(async () => {
        const result = await apiPost<{ id: number }>(`${root}/exams/${examId}/exports`, {});
        await download(`${root}/exams/${examId}/exports/${result.id}`, `mobile-${examId}-export-${result.id}.json`);
      })}>Crear y descargar copia versionada</button>
    </>}
    {busy && <p role="status">Procesando…</p>}
  </section>;
}
