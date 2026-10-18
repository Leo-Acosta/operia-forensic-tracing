export function mobilePermissions(role: string[], capabilities: string[]) {
  const permits = (permission: string) => role.includes("*") || role.includes(permission);
  const has = (capability: string) => capabilities.includes(capability);
  return {
    acquire: permits("evidence:write") && has("evidence"),
    analyze: permits("evidence:write") && has("analysis"),
    review: permits("evidence:write") && has("review"),
    publish: permits("evidence:write") && permits("reports:write") && has("analysis") && has("evidence") && has("reports"),
    project: permits("evidence:write") && permits("cases:write") && has("analysis"),
    download: permits("evidence:read") && has("export"),
    generateExport: permits("evidence:write") && has("analysis") && has("export"),
  };
}
