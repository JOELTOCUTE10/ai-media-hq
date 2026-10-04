const API_URL = (import.meta as any).env?.VITE_API_URL ?? "https://ai-media-hq-production.up.railway.app";

function sanitizeToken(value: string): string {
  return value.replace(/[\s\u200B-\u200D\uFEFF]+/g, "");
}

let token: string = sanitizeToken(localStorage.getItem("token") ?? "");

export function setToken(value: string) {
  token = sanitizeToken(value);
  localStorage.setItem("token", token);
}

export function clearToken() {
  token = "";
  localStorage.removeItem("token");
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  token = sanitizeToken(token || localStorage.getItem("token") || "");
  const res = await fetch(API_URL + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: "Bearer " + token } : {}),
      ...(options.headers ?? {}),
    },
  });
  if (res.status === 401) {
    clearToken();
    throw new ApiError(401, "Not authenticated");
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {}
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return {} as T;
  return res.json();
}
