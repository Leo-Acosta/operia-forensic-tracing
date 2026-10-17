export type CaseListItem = { id: number; case_code: string; title: string; description: string; incident_type: string; status: string; updated_at?: string; created_at?: string };
export function isClosedCase(item: CaseListItem) { return item.status.trim().toLowerCase() === "cerrado"; }
export function filterCases(items: CaseListItem[], query: string, status: string, sort: string) {
  const normalize = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es");
  const needle = normalize(query.trim());
  return items.filter(item => (!needle || normalize(`${item.case_code} ${item.title} ${item.incident_type}`).includes(needle)) &&
    (status === "all" || (status === "closed" ? isClosedCase(item) : !isClosedCase(item))))
    .sort((a, b) => sort === "code" ? a.case_code.localeCompare(b.case_code, "es", { numeric: true }) :
      (Date.parse(b.updated_at || b.created_at || "") || 0) - (Date.parse(a.updated_at || a.created_at || "") || 0) || b.id - a.id);
}
export function formatCaseDate(value?: string) {
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? new Intl.DateTimeFormat("es-AR", { day: "2-digit", month: "short", year: "numeric" }).format(date) : "Sin fecha registrada";
}
