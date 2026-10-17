export async function fetchScopedDownload(url: string, token: string, isCurrent: () => boolean): Promise<Blob | null> {
  if (!token || !isCurrent()) return null;
  const response = await fetch(url, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store", redirect: "error" });
  if (!isCurrent()) return null;
  if (!response.ok) throw new Error(`No se pudo descargar el archivo (${response.status}). Verificá la sesión y el permiso de exportación.`);
  const blob = await response.blob();
  return isCurrent() ? blob : null;
}
