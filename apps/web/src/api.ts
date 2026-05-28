export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8020/api";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

