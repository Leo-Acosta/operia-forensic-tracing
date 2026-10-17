import { useMemo, useState } from "react";
import { ArrowDownWideNarrow, ArrowUpRight, BriefcaseBusiness, CircleCheck, FolderClosed, FolderOpen, LayoutGrid, List, Plus, RefreshCw, Search, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { filterCases, formatCaseDate, isClosedCase, type CaseListItem } from "./case-list-model";

type Props = { cases: CaseListItem[]; selectedId: number | ""; loading: boolean; authenticated: boolean; canCreate: boolean; error?: string;
  onOpen: (id: number) => void; onCreate: () => void; onRefresh: () => void; onSignIn: () => void };

export function CasesWorkspace({ cases, selectedId, loading, authenticated, canCreate, error, onOpen, onCreate, onRefresh, onSignIn }: Props) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [sort, setSort] = useState("recent");
  const [view, setView] = useState<"list" | "grid">("list");
  const available = useMemo(() => authenticated ? cases : [], [authenticated, cases]);
  const visible = useMemo(() => filterCases(available, query, status, sort), [available, query, status, sort]);
  const closed = available.filter(isClosedCase).length;
  const stats = [{ label: "Expedientes disponibles", value: available.length, icon: BriefcaseBusiness, caption: "Según tus permisos de acceso" },
    { label: "En investigación", value: available.length - closed, icon: FolderOpen, caption: "Expedientes que no están cerrados" },
    { label: "Cerrados", value: closed, icon: CircleCheck, caption: "Disponibles para consulta autorizada" }];
  return <div className="premium-cases space-y-6">
    <div className="premium-section-intro"><div><h2>Tu espacio de investigación</h2><p>Organizá cada caso. Seguí la evidencia desde su origen hasta el informe.</p></div>
      <Button onClick={onCreate} disabled={!authenticated || !canCreate} title={!canCreate ? "Tu rol no permite crear expedientes" : undefined}><Plus />Nuevo expediente</Button></div>
    <div className="premium-stat-grid">{stats.map(stat => <Card key={stat.label} className="premium-stat-card flex-row"><div><span>{stat.label}</span><strong>{authenticated ? stat.value : "—"}</strong><small>{stat.caption}</small></div><span className="premium-stat-icon"><stat.icon size={20} strokeWidth={1.5} /></span></Card>)}</div>
    <Card className="premium-cases-card gap-0 overflow-hidden py-0">
      <div className="premium-cases-card-title"><div><h3>Expedientes</h3><Badge variant="secondary">{available.length}</Badge></div><span><ShieldCheck size={14} />Acceso por expediente</span></div>
      <div className="premium-case-toolbar flex-wrap min-[1201px]:flex-nowrap">
        <div className="relative w-full min-w-0 flex-none min-[1201px]:w-auto min-[1201px]:flex-1"><Search size={17} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" /><Input aria-label="Buscar expedientes" placeholder="Buscar por código, nombre o tipo…" value={query} onChange={e => setQuery(e.target.value)} className="pl-10" /></div>
        <label className="premium-filter min-w-36"><SlidersHorizontal size={15} /><span className="sr-only">Filtrar por estado</span><select aria-label="Filtrar por estado" value={status} onChange={e => setStatus(e.target.value)}><option value="all">Todos los estados</option><option value="open">En investigación</option><option value="closed">Cerrados</option></select></label>
        <label className="premium-filter min-w-36"><ArrowDownWideNarrow size={15} /><span className="sr-only">Ordenar expedientes</span><select aria-label="Ordenar expedientes" value={sort} onChange={e => setSort(e.target.value)}><option value="recent">Más recientes</option><option value="code">Por código</option></select></label>
        <div className="premium-view-controls" role="group" aria-label="Vista de expedientes"><Button variant="ghost" size="icon" aria-label="Vista de lista" aria-pressed={view === "list"} onClick={() => setView("list")}><List /></Button><Button variant="ghost" size="icon" aria-label="Vista de tarjetas" aria-pressed={view === "grid"} onClick={() => setView("grid")}><LayoutGrid /></Button></div>
        <Button variant="outline" size="icon" aria-label="Actualizar expedientes" disabled={loading} onClick={onRefresh}><RefreshCw className={loading ? "animate-spin" : ""} /></Button>
      </div>
      {!authenticated ? <div className="premium-empty"><ShieldCheck /><h3>Tu investigación empieza con un acceso seguro</h3><p>Iniciá sesión para consultar los expedientes habilitados para tu usuario.</p><Button onClick={onSignIn}>Iniciar sesión</Button></div>
      : loading && !available.length ? <div role="status" aria-label="Cargando expedientes" className="space-y-5 p-6">{[1, 2, 3].map(n => <Skeleton key={n} className="h-16 w-full" />)}</div>
      : error && !available.length ? <div className="premium-empty"><FolderClosed /><h3>No pudimos cargar tus expedientes</h3><p>Volvé a consultar para verificar la conexión y los permisos de tu sesión.</p><Button variant="outline" onClick={onRefresh}>Reintentar</Button></div>
      : !visible.length ? <div className="premium-empty"><FolderOpen /><h3>{available.length ? "No hay coincidencias" : "Todavía no hay expedientes disponibles"}</h3><p>{available.length ? "Probá otro término o quitá los filtros." : "Solo aparecen los expedientes a los que tenés acceso. Podés solicitar una concesión al administrador."}</p>{available.length > 0 && <Button variant="outline" onClick={() => { setQuery(""); setStatus("all"); }}>Limpiar filtros</Button>}</div>
      : view === "list" ? <div className="premium-table-scroll"><table className="premium-case-table"><caption className="sr-only">Expedientes autorizados para tu usuario</caption><thead><tr><th>Expediente</th><th>Tipo de investigación</th><th>Estado</th><th>Última actividad</th><th><span className="sr-only">Acciones</span></th></tr></thead><tbody>{visible.map(item => <tr key={item.id} data-selected={item.id === selectedId}>
        <td><div className="premium-case-identity"><span className="premium-folder-icon"><FolderClosed size={19} strokeWidth={1.5} /></span><div><span className="premium-case-code">{item.case_code}</span><button className="premium-case-title" onClick={() => onOpen(item.id)}>{item.title}</button></div></div></td>
        <td><span className="premium-incident-type">{item.incident_type}</span></td><td><Badge variant="outline" className={isClosedCase(item) ? "premium-status-closed" : "premium-status-open"}><span className="premium-status-dot" />{item.status}</Badge></td><td className="premium-date">{formatCaseDate(item.updated_at || item.created_at)}</td>
        <td><Button variant="ghost" size="icon" aria-label={`Abrir expediente ${item.case_code}`} onClick={() => onOpen(item.id)}><ArrowUpRight /></Button></td></tr>)}</tbody></table></div>
      : <div className="premium-case-card-grid">{visible.map(item => <article key={item.id} className="premium-case-tile"><div className="flex items-center justify-between"><FolderClosed className="text-muted-foreground" size={23} /><Badge variant="outline" className={isClosedCase(item) ? "premium-status-closed" : "premium-status-open"}>{item.status}</Badge></div><span className="premium-case-code">{item.case_code}</span><h3>{item.title}</h3><p>{item.description || "Sin descripción registrada."}</p><div className="premium-case-tile-footer"><span>{formatCaseDate(item.updated_at || item.created_at)}</span><Button variant="outline" size="sm" onClick={() => onOpen(item.id)}>Abrir<ArrowUpRight /></Button></div></article>)}</div>}
      <div className="premium-table-footer"><span role="status" aria-live="polite">{visible.length} de {available.length} expedientes disponibles</span><span>Historial vinculado a cada expediente</span></div>
    </Card>
  </div>;
}
