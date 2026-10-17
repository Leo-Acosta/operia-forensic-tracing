import { useMemo, useState, type ReactNode } from "react";
import { Download, Fingerprint, Search, ShieldCheck, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { FormField } from "@/components/forms/form-field";

export type EvidenceRecord = { id: number; case_id: number; evidence_type: string; description: string; sha256_hash: string; integrity_status: string; custodian?: string };
type Props = { items: EvidenceRecord[]; caseId: number | ""; caseCode?: string; loading: boolean; error?: string; canVerify: boolean; canDownload: boolean; busy: boolean;
  upload: ReactNode; onVerify: (id: number) => void; onDownload: (id: number) => void };

export function EvidenceWorkspace({ items, caseId, caseCode, loading, error, canVerify, canDownload, busy, upload, onVerify, onDownload }: Props) {
  const [query, setQuery] = useState("");
  const scoped = items.filter(item => item.case_id === caseId);
  const visible = useMemo(() => scoped.filter(item => `${item.description} ${item.evidence_type} ${item.sha256_hash}`.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().includes(query.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase())), [scoped, query]);
  return <section className="premium-record-workspace" aria-label="Gestión de evidencias">
    <div className="premium-section-intro"><div><h2>Evidencia preservada</h2><p>{caseCode ? `Expediente ${caseCode}` : "Seleccioná un expediente desde Casos para comenzar."}</p></div><Badge variant="outline"><ShieldCheck />Custodia vinculada</Badge></div>
    <div className="premium-evidence-layout">
      <Card className="premium-panel"><div className="premium-panel-heading"><Fingerprint /><div><h3>Inventario de evidencia</h3><p>El hash registrado y el resultado de una verificación son datos distintos.</p></div></div>
        <FormField label="Buscar evidencia"><Input placeholder="Descripción, tipo o SHA-256…" value={query} onChange={e => setQuery(e.target.value)} /></FormField>
        {loading ? <div role="status" aria-label="Cargando evidencia"><Skeleton className="h-24 w-full" /></div>
        : error ? <p role="alert">No se pudo consultar el inventario. Volvé a cargar el expediente.</p>
        : !caseId ? <p className="premium-empty-copy">No hay un expediente seleccionado.</p>
        : !visible.length ? <p role="status" className="premium-empty-copy">{scoped.length ? "No hay coincidencias. Probá otra búsqueda." : "Todavía no hay evidencia registrada en este expediente."}</p>
        : <ul className="premium-record-list" aria-label="Evidencias del expediente">{visible.map(item => <li key={item.id}><article aria-labelledby={`evidence-title-${item.id}`}>
          <div className="premium-record-heading"><Badge variant="secondary">Evidencia #{item.id}</Badge><span>{item.evidence_type}</span></div>
          <h4 id={`evidence-title-${item.id}`}>{item.description}</h4>
          <dl className="premium-metadata"><div><dt>Estado registrado</dt><dd>{item.integrity_status || "Sin verificar"}</dd></div><div><dt>Custodio</dt><dd>{item.custodian || "Sin registrar"}</dd></div></dl>
          <div className="premium-hash"><span>SHA-256 registrado</span><code>{item.sha256_hash || "Sin hash registrado"}</code></div>
          <div className="premium-action-row"><Button variant="outline" disabled={!canVerify || busy} onClick={() => onVerify(item.id)} aria-label={`Verificar integridad de evidencia ${item.id}`}><Fingerprint />Verificar integridad</Button><Button variant="ghost" disabled={!canDownload || busy} onClick={() => onDownload(item.id)} aria-label={`Descargar evidencia ${item.id}`}><Download />Descargar original</Button></div>
        </article></li>)}</ul>}
        <p className="premium-result-count" role="status" aria-live="polite">{loading ? "Consultando evidencia…" : `${visible.length} de ${scoped.length} evidencias`}</p>
      </Card>
      <Card className="premium-panel premium-upload-panel"><div className="premium-panel-heading"><Upload /><div><h3>Incorporar evidencia</h3><p>El archivo y su custodia se registran en el expediente activo.</p></div></div>{upload}</Card>
    </div>
  </section>;
}
