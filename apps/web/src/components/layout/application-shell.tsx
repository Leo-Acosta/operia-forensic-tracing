import { useEffect, useRef, useState, type ReactNode } from "react";
import { ChevronRight, Fingerprint, Menu, ShieldCheck, UserRound, X, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";

export type NavigationItem<K extends string> = { key: K; label: string; icon: LucideIcon; section: string };
type Props<K extends string> = {
  active: K; items: NavigationItem<K>[]; sections: string[]; onNavigate: (key: K) => void;
  user?: { name: string; role: string; organization_id?: number } | null;
  caseCode?: string; loading: boolean; onIdentity: () => void; children: ReactNode;
};

export function ApplicationShell<K extends string>({ active, items, sections, onNavigate, user, caseCode, loading, onIdentity, children }: Props<K>) {
  const mainRef = useRef<HTMLElement>(null);
  const previousActive = useRef(active);
  const mobileNavigated = useRef(false);
  useEffect(() => { if (previousActive.current !== active) { previousActive.current = active; mainRef.current?.focus(); } }, [active]);
  const [open, setOpen] = useState(false);
  const current = items.find(item => item.key === active);
  const go = (key: K) => { mobileNavigated.current = key !== active; onNavigate(key); setOpen(false); };
  const navigation = (mobile = false) => <>
    <div className="premium-brand"><span className="premium-brand-mark"><Fingerprint size={28} strokeWidth={1.5} /></span>
      <div><strong>OPERIA<span>®</span></strong><p>FORENSIC TRACING</p></div>
    </div>
    <div className="premium-workspace"><span className="premium-workspace-icon">O</span><div><strong>Espacio de investigación</strong><span>{user?.organization_id ? `Organización ${user.organization_id}` : "Acceso local"}</span></div><ShieldCheck size={15} /></div>
    <nav aria-label={mobile ? "Navegación móvil" : "Navegación principal"} className="premium-navigation">
      {sections.map(section => <div className="premium-nav-group" key={section}>
        <span className="premium-nav-label">{section}</span>
        {items.filter(item => item.section === section).map(item => <button type="button" className="premium-nav-item" key={item.key}
          aria-current={active === item.key ? "page" : undefined} onClick={() => go(item.key)}>
          <item.icon size={17} strokeWidth={1.7} aria-hidden="true" /><span>{item.label}</span>
          {active === item.key && <span className="premium-nav-active-dot" aria-hidden="true" />}
        </button>)}
      </div>)}
    </nav>
    <div className="premium-sidebar-footer"><ShieldCheck size={17} /><div><strong>Entorno local</strong><span>Acceso sujeto a permisos</span></div></div>
  </>;
  return <div className="premium-shell">
    <a className="premium-skip-link" href="#main-content">Saltar al contenido</a>
    <aside className="premium-sidebar">{navigation()}</aside>
    <div className="premium-body">
      <div className="premium-topbar">
        <div className="flex min-w-0 items-center gap-3">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild><Button variant="ghost" size="icon" className="hidden max-[900px]:inline-flex" aria-label="Abrir navegación"><Menu /></Button></SheetTrigger>
            <SheetContent side="left" className="premium-mobile-sheet w-[290px] gap-0 bg-[#101e2e] p-0 text-slate-200" showCloseButton={false} onCloseAutoFocus={event => { if (mobileNavigated.current) { event.preventDefault(); mobileNavigated.current = false; mainRef.current?.focus(); } }}>
              <SheetHeader className="sr-only"><SheetTitle>Navegación de OPERIA</SheetTitle><SheetDescription>Acceso a los módulos de investigación.</SheetDescription></SheetHeader>
              <Button variant="ghost" size="icon" className="premium-mobile-close" onClick={() => setOpen(false)} aria-label="Cerrar navegación"><X /></Button>
              {navigation(true)}
            </SheetContent>
          </Sheet>
          <nav aria-label="Ruta actual" className="premium-breadcrumb"><span>Área de trabajo</span><ChevronRight size={13} /><strong>{current?.label || "OPERIA"}</strong></nav>
        </div>
        <div className="premium-topbar-actions">
          {caseCode && <span className="premium-case-context"><span />{caseCode}</span>}
          <Button variant="ghost" className="premium-user-button" onClick={onIdentity} aria-label={user ? `Cuenta de ${user.name}` : "Iniciar sesión"}>
            <span className="premium-avatar">{user?.name?.trim().charAt(0).toUpperCase() || <UserRound size={16} />}</span>
            <span className="premium-user-copy"><strong>{user?.name || "Iniciar sesión"}</strong><small>{user?.role || "Sin sesión"}</small></span>
          </Button>
        </div>
      </div>
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">{loading ? "Actualizando datos…" : ""}</div>
      <main ref={mainRef} id="main-content" tabIndex={-1} className="premium-main" aria-busy={loading} aria-labelledby="workspace-title">
        <div className="premium-page-heading"><div><p className="premium-eyebrow">{current?.section || "OPERIA"} / ESPACIO DE TRABAJO</p><h1 id="workspace-title">{current?.label || "OPERIA"}</h1></div>
          {loading && <span className="premium-loading-label" aria-hidden="true"><span />Actualizando datos…</span>}
        </div>
        {children}
        <footer className="premium-content-footer"><span>OPERIA · Forensic Tracing</span><span>Investigación documentada. Evidencia preservada.</span></footer>
      </main>
    </div>
  </div>;
}
