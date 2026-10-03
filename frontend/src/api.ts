const API_URL = (import.meta as any).env?.VITE_API_URL ?? "";

let token: string = localStorage.getItem("token") ?? "";

export function setToken(value: string) {
  token = value;
  localStorage.setItem("token", value);
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
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  });
  if (res.status === 401) {
    clearToken();
    window.location.hash = "#/login";
    throw new ApiError(401, "Not authenticated");
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* no body */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return {} as T;
  return res.json();
}

export interface Channel {
  id: number; name: string; slug: string; description: string; niche: string; audience: string;
  is_active: boolean; approval_required: boolean;
  content_rules: Record<string, unknown>; publishing_rules: Record<string, unknown>;
  style: Record<string, unknown>;
}
export interface Agent {
  id: number; key: string; name: string; role: string; description: string; department: string;
  capabilities: string[]; tools: string[]; permission_level: string; permissions: string[];
  status: string; current_task_id: number | null;
}
export interface Task {
  id: number; title: string; description: string; assigned_agent_id: number | null;
  channel_id: number | null; priority: string; status: string; input: Record<string, unknown>;
  output: Record<string, unknown>; error: string | null; retry_count: number;
  depends_on: number[]; created_at: string;
}
export interface EventItem {
  id: number; event_type: string; payload: Record<string, unknown>; created_at: string;
}
export interface Dashboard {
  channels: { total: number; active: number };
  agents: { total: number; active: number; paused: number };
  tasks: Record<string, number>;
  content: { in_production: number; awaiting_approval: number };
  integrations: Record<string, string>;
  costs: { month_to_date_usd: number; budget_usd: number };
  recent_events: EventItem[];
  recommendations: string[];
}
export interface SettingsBundle {
  organization: { id: number; name: string; settings: Record<string, any> };
  system: { ai_provider: string; ai_model: string; task_runner_enabled: boolean; monthly_budget_usd: number };
  integrations: { key: string; name: string; status: string }[];
}
