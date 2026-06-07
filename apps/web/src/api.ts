export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8020/api";
const TOKEN_KEY = "operia_access_token";

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setAuthToken(token: string) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function authHeaders(extra: HeadersInit = {}) {
  const token = getAuthToken();
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra;
}

function cleanMessage(value: unknown): string {
  if (!value) return "";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(cleanMessage).filter(Boolean).join("; ");
  if (typeof value === "object") {
    const objectValue = value as Record<string, unknown>;
    for (const key of ["message", "detail", "error", "title"]) {
      const message = cleanMessage(objectValue[key]);
      if (message) return message;
    }
    const missing = cleanMessage(objectValue.missing);
    if (missing) return `Faltan condiciones para completar la acción: ${missing}`;
    const checklist = objectValue.checklist as Record<string, unknown> | undefined;
    const checklistMissing = cleanMessage(checklist?.missing);
    if (checklistMissing) return `Faltan condiciones para completar la acción: ${checklistMissing}`;
  }
  return "";
}

async function parseResponse(response: Response) {
  const contentType = response.headers.get("content-type") ?? "";
  if (!response.ok) {
    const raw = await response.text();
    let message = raw || `Error HTTP ${response.status}`;
    if (contentType.includes("application/json")) {
      try {
        const data = JSON.parse(raw);
        const detail = data.detail || data.message;
        message = cleanMessage(detail) || cleanMessage(data) || message;
      } catch {
        message = raw || message;
      }
    }
    if (response.status === 401) {
      setAuthToken("");
      if (!message.toLowerCase().includes("credencial")) {
        message = "Sesión requerida o vencida. Inicia sesión en Usuarios o usa Recuperar acceso local.";
      }
    }
    if (response.status === 403 && !message) {
      message = "No tenés permisos suficientes para ejecutar esta acción.";
    }
    throw new Error(message);
  }
  if (contentType.includes("application/json")) return response.json();
  return response.text();
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  return parseResponse(response) as Promise<T>;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  return parseResponse(response) as Promise<T>;
}

export async function apiPostForm<T>(path: string, body: FormData): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders(),
    body
  });
  return parseResponse(response) as Promise<T>;
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body)
  });
  return parseResponse(response) as Promise<T>;
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body)
  });
  return parseResponse(response) as Promise<T>;
}

export async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: authHeaders()
  });
  return parseResponse(response) as Promise<T>;
}
