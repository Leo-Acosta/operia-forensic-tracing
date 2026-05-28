import { useEffect, useState } from "react";
import {
  BarChart3,
  Briefcase,
  Calculator,
  FileArchive,
  FileText,
  Fingerprint,
  Gavel,
  Map,
  Navigation,
  Settings,
  Shield,
  Wrench
} from "lucide-react";
import { apiGet } from "./api";

type ModuleKey =
  | "dashboard"
  | "usersCases"
  | "evidence"
  | "cybercrime"
  | "legalReport"
  | "geoTrace"
  | "geoProximity"
  | "reports"
  | "exports"
  | "settings";

const modules: Array<{ key: ModuleKey; label: string; path: string; icon: typeof BarChart3 }> = [
  { key: "dashboard", label: "Dashboard", path: "/dashboard", icon: BarChart3 },
  { key: "usersCases", label: "Usuarios y Casos", path: "/users-cases", icon: Briefcase },
  { key: "evidence", label: "Evidencia", path: "/evidence", icon: Fingerprint },
  { key: "cybercrime", label: "Cybercrime Intelligence", path: "/cybercrime", icon: Shield },
  { key: "legalReport", label: "Forensic Legal Report", path: "/legal-report", icon: Gavel },
  { key: "geoTrace", label: "Geo Trace", path: "/geo-trace", icon: Map },
  { key: "geoProximity", label: "Geo Proximity", path: "/geo-proximity", icon: Navigation },
  { key: "reports", label: "Informes", path: "/reports", icon: FileText },
  { key: "exports", label: "Exportaciones", path: "/exports", icon: FileArchive },
  { key: "settings", label: "Configuración", path: "/settings", icon: Settings }
];

function titleForPayload(payload: unknown): string {
  if (payload && typeof payload === "object" && "module" in payload) {
    return String((payload as { module: string }).module);
  }
  return "OPERIA Forensic Tracing";
}

export function App() {
  const [active, setActive] = useState(modules[0]);
  const [payload, setPayload] = useState<unknown>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");
    apiGet(active.path)
      .then(setPayload)
      .catch((err: Error) => {
        setPayload(null);
        setError(err.message || "No se pudo conectar con la API.");
      });
  }, [active]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Wrench size={22} />
          <div>
            <strong>OPERIA</strong>
            <span>Forensic Tracing</span>
          </div>
        </div>
        <nav>
          {modules.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                className={active.key === item.key ? "active" : ""}
                onClick={() => setActive(item)}
              >
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>

      <main>
        <header>
          <div>
            <p>Arquitectura modular inicial</p>
            <h1>{titleForPayload(payload)}</h1>
          </div>
          <span className="status">Scaffold</span>
        </header>

        <section className="panel">
          <h2>{active.label}</h2>
          {error ? (
            <div className="error">{error}</div>
          ) : (
            <pre>{JSON.stringify(payload, null, 2)}</pre>
          )}
        </section>
      </main>
    </div>
  );
}

