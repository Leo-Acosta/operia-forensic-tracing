import { Download, FileSearch, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

type Report = { id: number; case_id: number; title: string; status: string; version?: string | number; review_score: number };
export function ReportRegister({ reports, caseId, canRead, canExport, busy, onPreview, onDownload }: { reports: Report[]; caseId: number | ""; canRead: boolean; canExport: boolean; busy: boolean; onPreview: (id: number) => void; onDownload: (id: number) => void }) {
  const items = reports.filter(item => item.case_id === caseId);
  return <Card className="premium-panel"><div className="premium-panel-heading"><FileText /><div><h3>Registro de informes</h3><p>Versiones conservadas y exportaciones sujetas a autorización.</p></div></div>
    {!items.length ? <p role="status" className="premium-empty-copy">Sin informes disponibles para este expediente.</p> : <ul className="premium-record-list">{items.map(item => <li key={item.id}><article>
      <div className="premium-record-heading"><Badge variant="outline">{item.status.replace(/_/g, " ")}</Badge><span>Versión {item.version ?? "sin registrar"}</span></div><h4>{item.title}</h4><p className="text-sm text-muted-foreground">Revisión registrada: {item.review_score}/100</p>
      <div className="premium-action-row"><Button variant="outline" disabled={!canRead || busy} onClick={() => onPreview(item.id)} aria-label={`Vista previa de informe ${item.id}`}><FileSearch />Vista previa</Button><Button variant="ghost" disabled={!canExport || busy} onClick={() => onDownload(item.id)} aria-label={`Descargar PDF de informe ${item.id}`}><Download />Borrador PDF</Button></div>
    </article></li>)}</ul>}
  </Card>;
}
