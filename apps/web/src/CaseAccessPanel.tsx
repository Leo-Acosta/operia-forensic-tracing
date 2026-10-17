import { FormEvent, useEffect, useRef, useState } from "react";
import { apiGet, apiPost, getAuthToken } from "./api";

const capabilities = { read: "Lectura", write: "Edición del expediente", evidence: "Evidencia y custodia",
  analysis: "Análisis e IA", review: "Revisión", participants: "Participantes", reports: "Informes",
  approve: "Aprobación", export: "Exportación y descargas" };
type AccessEvent = { id: number; user_id: number; actor_id: number; permission: string; access: string; reason: string; recorded_at: string };

export default function CaseAccessPanel({ caseId, users }: {
  caseId: number; users: { id: number; name: string; role: string; status?: string }[];
}) {
  const [events, setEvents] = useState<AccessEvent[]>([]);
  const [userId, setUserId] = useState("");
  const [selected, setSelected] = useState<string[]>(["read"]);
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    const token = getAuthToken();
    apiGet<AccessEvent[]>(`/cases/${caseId}/access`).then(value => {
      if (alive.current && token === getAuthToken()) setEvents(value);
    }).catch(error => { if (alive.current && token === getAuthToken()) setMessage(error.message); });
    return () => { alive.current = false; };
  }, [caseId]);
  async function change(event: FormEvent, revoke: boolean) {
    event.preventDefault();
    const token = getAuthToken();
    setBusy(true); setMessage("");
    try {
      await apiPost(`/cases/${caseId}/access`, { user_id: Number(userId), access: revoke ? "revoked" : "read", permissions: selected, reason });
      const value = await apiGet<AccessEvent[]>(`/cases/${caseId}/access`);
      if (alive.current && token === getAuthToken()) { setEvents(value); setReason(""); setMessage(revoke ? "Revocación registrada." : "Concesión registrada."); }
    } catch (error) {
      if (alive.current && token === getAuthToken()) setMessage(error instanceof Error ? error.message : "No se pudo registrar el cambio.");
    } finally { if (alive.current && token === getAuthToken()) setBusy(false); }
  }
  return <details className="work-surface compact-surface">
    <summary>Permisos del expediente</summary>
    <p>Denegación por defecto. Solo el administrador de la organización gestiona accesos. Cada decisión conserva autor, fecha y motivo. Los permisos del rol también se aplican.</p>
    <form onSubmit={event => change(event, false)}>
      <label>Usuario <select required value={userId} onChange={event => setUserId(event.target.value)}>
        <option value="">Seleccionar usuario</option>
        {users.filter(user => user.role !== "admin" && user.status === "active").map(user => <option key={user.id} value={user.id}>{user.name}</option>)}
      </select></label>
      <fieldset disabled={busy}><legend>Capacidades a conceder o revocar</legend>
        {Object.entries(capabilities).map(([key, label]) => <label key={key} style={{ display: "inline-flex", gap: 6, margin: 8 }}>
          <input type="checkbox" checked={selected.includes(key)} onChange={event => setSelected(event.target.checked ? [...selected, key] : selected.filter(value => value !== key))} />{label}
        </label>)}
      </fieldset>
      <label>Motivo obligatorio <textarea required maxLength={2000} value={reason} onChange={event => setReason(event.target.value)} /></label>
      <p>Conceder agrega las capacidades seleccionadas y lectura. Revocar lectura oculta todo el expediente y detiene sus análisis activos. Para retirar todo el acceso, seleccioná todas las capacidades y revocá.</p>
      <button disabled={busy || !userId || !selected.length || !reason.trim()}>Conceder seleccionados</button>{" "}
      <button type="button" className="secondary-button" disabled={busy || !userId || !selected.length || !reason.trim()} onClick={event => change(event, true)}>Revocar seleccionados</button>
    </form>
    {message && <p role="status">{message}</p>}
    <h4>Historial de decisiones</h4>
    <ul>{events.slice().reverse().map(item => <li key={item.id}>#{item.id} · Usuario {users.find(user => user.id === item.user_id)?.name || item.user_id} · {capabilities[item.permission as keyof typeof capabilities] || item.permission}: {item.access === "granted" ? "concedido" : "revocado"} · Autor #{item.actor_id} · {item.recorded_at} · {item.reason}</li>)}</ul>
  </details>;
}
