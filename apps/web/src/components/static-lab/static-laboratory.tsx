import { useEffect, useRef, useState } from "react";
import { FlaskConical, RefreshCw, ShieldCheck } from "lucide-react";
import { apiGet, apiPost, getAuthToken } from "@/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { FormField } from "@/components/forms/form-field";
import { ModuleSurface } from "@/components/layout/module-surface";

type Evidence = { id: number; description: string; sha256_hash: string };
type Review = { version: number; decision: string; rationale: string; actor_id: number; result_sha256: string };
type Job = { id: number; case_id: number; evidence_id: number; state: string; error_code: string; runtime_identity: string; result_sha256: string | null };
type Detail = Job & { report: null | { provider: string; provider_version: string; limitations: string; observations: Array<{ id: string; member: string; offset: number; text: string }> }; reviews: Review[]; events: Array<{ state: string; reason: string; recorded_at: string }> };
type Projection = { id: number; report_id: number; finding_id: number; snapshot_sha256: string };
type Provider = { execution_enabled: boolean; providers: Array<{ id: string; scope: string; ready: boolean }> };
export type LabData = { evidence: Evidence[]; jobs: Job[]; provider: Provider | null; detail: Detail | null; projections: Projection[] };
const empty: LabData = { evidence: [], jobs: [], provider: null, detail: null, projections: [] };
const states: Record<string,string> = { queued:"Pendiente",preparing:"Preparando",running:"En ejecución",completed:"Completado",failed:"Fallido",cancelled:"Cancelado",interrupted:"Interrumpido" };
const decisions: Record<string,string> = { accepted:"Aceptada",rejected:"Rechazada",needs_corroboration:"Requiere corroboración" };
export function labPermissions(role: string[], caps: string[]) {
  const has = (p:string) => role.includes("*") || role.includes(p);
  const cap = (p:string) => caps.includes(p);
  return { read:has("evidence:read") && cap("read"), analyze:has("evidence:write") && cap("analysis") && cap("evidence"),
    review:has("evidence:write") && cap("review"), project:has("evidence:write") && has("cases:write") && has("reports:write") && cap("analysis") && cap("evidence") && cap("reports") };
}
type Rights = ReturnType<typeof labPermissions>;
type ViewProps = { contextLabel?: string; data: LabData; rights: Rights; busy: boolean; message: string; error: string; evidenceId: string; rationale: string; decision: string; selected: string[];
  onEvidence:(id:string)=>void; onRationale:(text:string)=>void; onDecision:(text:string)=>void; onSelect:(id:string)=>void;
  onClear:()=>void; onLoad:(id?:number)=>void; onQueue:()=>void; onCancel:()=>void; onReview:()=>void; onProject:()=>void; onReports:()=>void };
export function LaboratoryView(p: ViewProps) {
  const statusRef = useRef<HTMLParagraphElement>(null), errorRef = useRef<HTMLParagraphElement>(null), detailRef = useRef<HTMLHeadingElement>(null);
  useEffect(()=>{if(p.error)errorRef.current?.focus();else if(p.message)statusRef.current?.focus();},[p.error,p.message]);
  useEffect(()=>{if(p.data.detail)detailRef.current?.focus();},[p.data.detail?.id]);
  const latest = p.data.detail?.reviews[p.data.detail.reviews.length-1];
  const observations = p.data.detail?.report?.observations || [];
  const accepted = latest?.decision === "accepted" && latest.result_sha256 === p.data.detail?.result_sha256;
  const eligible = p.data.evidence.filter(e=>e.sha256_hash);
  return <ModuleSurface moduleId="staticLab" className="static-lab"><header className="static-lab-header"><div><p className="premium-eyebrow">ANÁLISIS CONTROLADO</p><h2>Laboratorio estático</h2><p className="static-lab-muted">{p.contextLabel || "Expediente seleccionado"}</p><p>De la muestra preservada a una observación revisada y trazable.</p></div><Button variant="outline" disabled={p.busy || !p.rights.read} onClick={()=>p.onLoad(p.data.detail?.id)}><RefreshCw aria-hidden="true"/>Actualizar laboratorio</Button></header>
    <div className="static-lab-scope"><ShieldCheck aria-hidden="true"/><p><strong>Fuente Python · CPython AST</strong><br/>Sin ejecución de muestras ni consultas de red. APK y ejecutables quedan fuera del alcance.</p><span>{p.data.provider?.execution_enabled ? "Runtime disponible" : "Runtime sin verificar"}</span></div>
    <p ref={statusRef} tabIndex={-1} role="status" aria-live="polite" aria-atomic="true">{p.busy ? "Actualizando laboratorio…" : p.message}</p>{p.error && <p ref={errorRef} tabIndex={-1} role="alert" className="premium-form-error">{p.error}</p>}
    {!p.rights.read ? <p className="premium-permissions-note">Iniciá sesión y seleccioná un expediente autorizado para consultar el laboratorio.</p> : <>
    <div className="static-lab-grid"><Card className="static-lab-card"><h3><FlaskConical aria-hidden="true"/>1. Muestra preservada</h3><p>Se copia el contenido verificado de evidencia. Máximo 128 KiB; solo fuente Python UTF-8.</p><FormField label="Evidencia para el análisis"><select value={p.evidenceId} disabled={p.busy || !p.rights.analyze} onChange={e=>p.onEvidence(e.target.value)}><option value="">Seleccionar evidencia</option>{eligible.map(e=><option key={e.id} value={e.id}>#{e.id} · {e.description}</option>)}</select></FormField><Button disabled={p.busy || !p.rights.analyze || !p.evidenceId || !p.data.provider?.execution_enabled} onClick={p.onQueue}>Encolar análisis</Button><p className="static-lab-muted">La cola es persistente. Un operador debe ejecutar el worker aislado; esta pantalla no inicia procesos.</p></Card>
    <Card className="static-lab-card"><h3>2. Trabajos del expediente</h3>{!p.data.jobs.length ? <p>{p.busy ? "Consultando trabajos…" : p.error ? "Listado no disponible. Volvé a actualizar." : "No hay trabajos disponibles para este expediente."}</p> : <ul className="static-job-list">{p.data.jobs.map(job=><li key={job.id}><Button variant="outline" aria-pressed={p.data.detail?.id===job.id} disabled={p.busy} onClick={()=>p.onLoad(job.id)}>Trabajo #{job.id} · Evidencia #{job.evidence_id}<span>{states[job.state] || job.state}</span></Button></li>)}</ul>}</Card></div>
    {p.data.detail && <Card className="static-lab-card"><div className="static-lab-header"><h3 ref={detailRef} tabIndex={-1}>Trabajo #{p.data.detail.id} · {states[p.data.detail.state] || p.data.detail.state}</h3>{["queued","preparing","running"].includes(p.data.detail.state) && <Button variant="outline" disabled={p.busy || !p.rights.analyze} onClick={p.onCancel}>Solicitar cancelación</Button>}</div>
      {p.data.detail.error_code && <p>El trabajo terminó sin resultado publicable. Código: <code>{p.data.detail.error_code}</code></p>}
      <details><summary>Procedencia y eventos</summary><p>Runtime: <code>{p.data.detail.runtime_identity}</code></p><p>SHA-256 del resultado: <code>{p.data.detail.result_sha256 || "Sin resultado"}</code></p><ol>{p.data.detail.events.map((event,i)=><li key={i}>{states[event.state] || event.state} · {event.recorded_at}{event.reason && ` · ${event.reason}`}</li>)}</ol></details>
      {p.data.detail.report && <><h3>3. Observaciones estáticas</h3><p>{p.data.detail.report.provider} {p.data.detail.report.provider_version}. {p.data.detail.report.limitations}</p><fieldset disabled={p.busy || !p.rights.project || !accepted}><legend>Elegí las observaciones para incorporar</legend>{observations.length ? observations.map(o=><label className="static-observation" key={o.id}><input type="checkbox" checked={p.selected.includes(o.id)} onChange={()=>p.onSelect(o.id)}/><span><strong>{o.text}</strong><small>{o.member} · offset {o.offset} bytes · {o.id}</small></span></label>) : <p>Sin observaciones en este resultado. No equivale a ausencia de riesgo.</p>}</fieldset>
      <div className="static-lab-grid"><section><h3>4. Revisión profesional</h3><p>{latest ? `Última revisión: v${latest.version} · ${decisions[latest.decision] || latest.decision}` : "Pendiente de revisión profesional"}</p><fieldset disabled={p.busy || !p.rights.review}><legend className="sr-only">Nueva revisión profesional</legend><FormField label="Decisión profesional"><select value={p.decision} onChange={e=>p.onDecision(e.target.value)}><option value="needs_corroboration">Requiere corroboración</option><option value="accepted">Aceptada</option><option value="rejected">Rechazada</option></select></FormField><FormField label="Fundamento de la revisión" hint="Indicá qué contrastaste y los límites de la observación."><textarea value={p.rationale} maxLength={4000} minLength={10} onChange={e=>p.onRationale(e.target.value)}/></FormField><Button disabled={p.rationale.trim().length<10} onClick={p.onReview}>Guardar nueva revisión</Button></fieldset></section>
      <section><h3>5. Incorporación al expediente</h3><p>Requiere la última revisión aceptada. Crea un hallazgo y un informe borrador nuevos, con snapshot de procedencia. No aprueba ni firma el informe.</p><Button disabled={p.busy || !p.rights.project || !accepted || !p.selected.length} onClick={p.onProject}>Incorporar selección a hallazgo e informe</Button>{!accepted && <p>La selección se habilita después de aceptar la revisión actual.</p>}</section></div>
      <Button variant="outline" disabled={p.busy || (!p.rationale && !p.selected.length)} onClick={p.onClear}>Limpiar borrador y selección</Button><details><summary>Historial de revisiones ({p.data.detail.reviews.length})</summary>{p.data.detail.reviews.map(r=><article key={r.version}><h4>Revisión {r.version} · {decisions[r.decision] || r.decision}</h4><p>{r.rationale}</p><small>Actor #{r.actor_id} · Resultado {r.result_sha256}</small></article>)}</details></>}
      {!!p.data.projections.length && <section><h3>Incorporaciones preservadas</h3>{p.data.projections.map(x=><p key={x.id}>Incorporación #{x.id} · Hallazgo #{x.finding_id} · Informe #{x.report_id}<br/><code>{x.snapshot_sha256}</code></p>)}<Button variant="outline" onClick={p.onReports}>Ir a informes del expediente</Button></section>}
    </Card>}</>}
  </ModuleSurface>;
}
export default function StaticLaboratory({caseId,sessionKey,role,caps,contextLabel,onDirtyChange,onReports}:{caseId:number|"";sessionKey:string;role:string[];caps:string[];contextLabel?:string;onDirtyChange?:(dirty:boolean)=>void;onReports:()=>void}) {
  const [data,setData]=useState<LabData>(empty),[busy,setBusy]=useState(false),[message,setMessage]=useState(""),[error,setError]=useState("");
  const [evidenceId,setEvidenceId]=useState(""),[rationale,setRationale]=useState(""),[decision,setDecision]=useState("needs_corroboration"),[selected,setSelected]=useState<string[]>([]);
  const alive=useRef(false),epoch=useRef(0),locked=useRef(false),requestKey=useRef("");
  const rights=labPermissions(role,caps),root=`/static-lab/cases/${caseId}`;
  const current=(ticket:number)=>alive.current && epoch.current===ticket && getAuthToken()===sessionKey;
  async function load(jobId?:number) {
    const ticket=++epoch.current;
    if (!caseId || !rights.read || !sessionKey) {setData(empty);setBusy(false);setError("");setMessage("");return;}
    setBusy(true);setError("");
    try {
      const [evidence,jobs,provider,detail,projections]=await Promise.all([apiGet<Evidence[]>(`/evidence/case/${caseId}`),apiGet<Job[]>(`${root}/jobs`),apiGet<Provider>(`${root}/providers`),jobId ? apiGet<Detail>(`${root}/jobs/${jobId}`) : Promise.resolve(null),jobId ? apiGet<Projection[]>(`${root}/jobs/${jobId}/projections`) : Promise.resolve([])]);
      if (current(ticket)) setData({evidence,jobs:jobs.filter(j=>j.case_id===caseId),provider,detail:detail?.case_id===caseId ? detail : null,projections});
    } catch {if(current(ticket)){setData(empty);setError("No se pudo consultar el laboratorio. Verificá el acceso al expediente y volvé a actualizar.");}}
    finally {if(current(ticket))setBusy(false);}
  }
  useEffect(()=>{alive.current=true;setData(empty);setSelected([]);setRationale("");void load();return()=>{alive.current=false;epoch.current++;};},[caseId,sessionKey,rights.read]);
  useEffect(()=>{onDirtyChange?.(!!rationale.trim() || !!selected.length);},[rationale,selected,onDirtyChange]);
  useEffect(()=>()=>onDirtyChange?.(false),[onDirtyChange]);
  async function action(work:()=>Promise<unknown>,success:string) {
    if(locked.current || busy) return;
    locked.current=true;setBusy(true);setError("");setMessage("");const ticket=++epoch.current;
    try {await work();if(current(ticket)){setRationale("");setSelected([]);await load(data.detail?.id);if(alive.current && getAuthToken()===sessionKey)setMessage(success);}}
    catch {if(current(ticket))setError("No se completó la operación. Revisá los permisos, el estado y la última revisión; luego actualizá el laboratorio.");}
    finally {locked.current=false;if(alive.current && getAuthToken()===sessionKey)setBusy(false);}
  }
  return <LaboratoryView contextLabel={contextLabel} data={rights.read ? data : empty} rights={rights} busy={busy} message={message} error={error} evidenceId={evidenceId} rationale={rationale} decision={decision} selected={selected}
    onEvidence={id=>{setEvidenceId(id);requestKey.current="";}} onRationale={setRationale} onDecision={setDecision}
    onSelect={id=>setSelected(ids=>ids.includes(id)?ids.filter(x=>x!==id):[...ids,id])}
    onLoad={id=>{if(rationale.trim() || selected.length){setError("Guardá la revisión o limpiá el borrador antes de cambiar de trabajo.");return;}void load(id);}}
    onQueue={()=>{if(!rights.analyze || !evidenceId)return;if(!requestKey.current)requestKey.current=crypto.randomUUID();void action(async()=>{await apiPost(`${root}/evidence/${evidenceId}/jobs`,{request_key:requestKey.current,provider:"cpython-ast"});requestKey.current="";},"Trabajo registrado. El operador puede procesarlo con el worker aislado.");}}
    onCancel={()=>{if(rights.analyze && data.detail)void action(()=>apiPost(`${root}/jobs/${data.detail!.id}/cancel`),"Cancelación registrada.");}}
    onReview={()=>{if(rights.review && data.detail)void action(()=>apiPost(`${root}/jobs/${data.detail!.id}/reviews`,{expected_version:data.detail!.reviews[data.detail!.reviews.length-1]?.version || 0,decision,rationale}),"Nueva revisión preservada.");}}
    onProject={()=>{if(rights.project && data.detail)void action(()=>apiPost(`${root}/jobs/${data.detail!.id}/projections`,{review_version:data.detail!.reviews[data.detail!.reviews.length-1]?.version,observation_ids:selected}),"Hallazgo e informe borrador incorporados. Los registros anteriores se conservan.");}}
    onClear={()=>{setRationale("");setSelected([]);setError("");}} onReports={onReports}/>;
}
