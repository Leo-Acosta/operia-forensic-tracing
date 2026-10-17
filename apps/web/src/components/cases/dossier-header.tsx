import { ArrowLeft, FileText, Fingerprint, LockKeyhole, Scale, Workflow } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { CaseListItem } from "./case-list-model";
import { formatCaseDate } from "./case-list-model";

type Props = { item?: CaseListItem; cases: CaseListItem[]; selectedId: number | ""; onSelect: (id: number | "") => void;
  onBack: () => void; onWorkflow: () => void; onReports: () => void; onLegal: () => void;
  counts: { evidence: number; custody: number; reports: number; participants: number }; loading: boolean; readOnly: boolean };

export function DossierHeader({ item, cases, selectedId, onSelect, onBack, onWorkflow, onReports, onLegal, counts, loading, readOnly }: Props) {
  return <section className="premium-dossier-header">
    <div className="premium-dossier-top"><Button variant="ghost" size="sm" onClick={onBack}><ArrowLeft />Todos los expedientes</Button>
      <label className="premium-dossier-selector"><span className="sr-only">Cambiar expediente</span><select aria-label="Cambiar expediente" value={selectedId} onChange={event => onSelect(Number(event.target.value) || "")}><option value="">Seleccionar expediente</option>{cases.map(value => <option key={value.id} value={value.id}>{value.case_code}</option>)}</select></label></div>
    {item ? <><div className="premium-dossier-title-row"><div><div className="flex flex-wrap items-center gap-3"><span className="premium-case-code">{item.case_code}</span><Badge variant="outline" className={item.status === "cerrado" ? "premium-status-closed" : "premium-status-open"}>{item.status}</Badge>{readOnly && <Badge variant="secondary"><LockKeyhole size={12} />Solo lectura</Badge>}</div><h2>{item.title}</h2><p>{item.description || "Este expediente todavía no tiene una descripción inicial registrada."}</p></div><span className="premium-dossier-emblem"><Fingerprint size={32} strokeWidth={1.25} /></span></div>
      <div className="premium-dossier-meta"><span>{item.incident_type}</span><span>Última actividad · {formatCaseDate(item.updated_at || item.created_at)}</span></div>
      <div className="premium-dossier-bottom"><div className="premium-dossier-counts" aria-label="Registros del expediente">{Object.entries({ Evidencias: counts.evidence, "Eventos de custodia": counts.custody, Informes: counts.reports, Personas: counts.participants }).map(([label, value]) => <span key={label}><strong>{loading ? "—" : value}</strong>{label}</span>)}</div>
        <div className="flex flex-wrap gap-2"><Button variant="outline" size="sm" onClick={onLegal}><Scale />Legal</Button><Button variant="outline" size="sm" onClick={onReports}><FileText />Informes</Button><Button size="sm" onClick={onWorkflow}><Workflow />Flujo de trabajo</Button></div></div>
    </> : <div className="premium-empty"><Fingerprint /><h2>Seleccioná un expediente</h2><p>Su evidencia, custodia e informes aparecerán según tus permisos.</p><Button onClick={onBack}>Ver expedientes</Button></div>}
  </section>;
}
