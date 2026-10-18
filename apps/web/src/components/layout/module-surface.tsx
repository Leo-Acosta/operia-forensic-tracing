import type { HTMLAttributes } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export const moduleSurfaces = {
  dashboard: "Dashboard operativo", history: "Historial de expedientes",
  legalKnowledge: "Biblioteca legal", cybercrime: "Análisis de indicadores",
  deepfakeMedia: "Deepfake y autenticación de medios", blockchainForensics: "Investigación blockchain",
  iotForensics: "Dispositivos IoT", externalTools: "Herramientas externas",
  ai: "Asistente de análisis", aiSecurity: "Seguridad de IA", identity: "Identidad y permisos",
  settings: "Configuración", casePresentation: "Exposición del expediente", mind: "Memoria forense",
  staticLab: "Laboratorio estático", mobileForensics: "Forense móvil", status: "Estado del módulo",
} as const;

export function ModuleSurface({ moduleId, className, children, ...props }: HTMLAttributes<HTMLElement> & { moduleId: keyof typeof moduleSurfaces }) {
  return <section aria-label={moduleSurfaces[moduleId]} data-module={moduleId} className={cn("premium-module", className)} {...props}>
    <Card className="premium-module-surface gap-0 py-0">{children}</Card>
  </section>;
}
