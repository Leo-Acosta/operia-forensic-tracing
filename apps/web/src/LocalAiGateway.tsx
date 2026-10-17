import { useEffect, useRef, useState } from "react";
import { apiPost, getAuthToken } from "./api";

type Answer = { id: number; case_id: number; response: string; status: string; requires_human_review: boolean };

export default function LocalAiGateway({ caseId, allowed, sessionKey }: { caseId: number | ""; allowed: boolean; sessionKey: string }) {
  const [prompt, setPrompt] = useState("");
  const [includeContext, setIncludeContext] = useState(false);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const revision = useRef(0);
  useEffect(() => {
    revision.current += 1;
    setPrompt(""); setIncludeContext(false); setAnswer(null); setMessage(""); setPending(false);
    return () => { revision.current += 1; };
  }, [caseId, sessionKey]);

  async function consult() {
    if (!caseId || !allowed || pending || !prompt.trim()) return;
    const request = ++revision.current;
    const token = getAuthToken();
    setPending(true); setAnswer(null); setMessage("");
    try {
      const result = await apiPost<Answer>("/ai/assist", { case_id: caseId, model_name: "mistral", prompt, include_case_context: includeContext });
      if (request !== revision.current || token !== getAuthToken()) return;
      if (result.status === "completed") setAnswer(result);
      else setMessage("La IA local no está disponible o no está autorizada para este caso. La solicitud quedó registrada sin una respuesta generada.");
    } catch {
      if (request === revision.current && token === getAuthToken()) setMessage("No se pudo completar la consulta de IA local.");
    } finally {
      if (request === revision.current && token === getAuthToken()) setPending(false);
    }
  }

  return <section className="detail-panel">
    <h3>Consulta a IA local</h3>
    <p>Consulta independiente del caso seleccionado. La respuesta requiere revisión humana y no modifica evidencia ni informes.</p>
    {!caseId && <p>Seleccioná un caso para consultar.</p>}
    <label>Consulta
      <textarea value={prompt} maxLength={16000} disabled={pending || !allowed || !caseId} onChange={(event) => setPrompt(event.target.value)} />
    </label>
    <label><input type="checkbox" checked={includeContext} disabled={pending || !caseId || !allowed} onChange={(event) => setIncludeContext(event.target.checked)} /> Incluir resumen, descripciones de evidencia y hallazgos del caso seleccionado</label>
    <p>Sin adjuntos originales, herramientas ni memoria de conversaciones anteriores. La pasarela debe estar habilitada por el operador y la organización.</p>
    <button onClick={consult} disabled={pending || !allowed || !caseId || !prompt.trim()}>{pending ? "Consultando…" : "Consultar IA local"}</button>
    {message && <p role="status">{message}</p>}
    {answer && answer.case_id === caseId && <div>
      <p>Interacción {answer.id} · Borrador generado, pendiente de revisión humana.</p>
      <pre style={{ whiteSpace: "pre-wrap" }}>{answer.response}</pre>
    </div>}
  </section>;
}
