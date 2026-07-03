import type { ChatResponse, User, Video, VideoSummary } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

const TOKEN_KEY = "yt_recall_token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function authHeaders(token?: string): Record<string, string> {
  const t = token ?? localStorage.getItem(TOKEN_KEY);
  return t ? { Authorization: `Bearer ${t}` } : {};
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init.headers ?? {}),
    },
  });

  if (resp.status === 204) return undefined as T;

  if (!resp.ok) {
    let detail = `Request failed (${resp.status})`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(resp.status, detail);
  }

  return (await resp.json()) as T;
}

export async function fetchMe(token: string): Promise<User> {
  return request<User>("/api/me", { headers: authHeaders(token) });
}

export async function listVideos(): Promise<VideoSummary[]> {
  return request<VideoSummary[]>("/api/videos");
}

export async function createVideo(url: string): Promise<Video> {
  return request<Video>("/api/videos", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function getVideo(id: string): Promise<Video> {
  return request<Video>(`/api/videos/${id}`);
}

export async function updateNotes(id: string, notes: string): Promise<Video> {
  return request<Video>(`/api/videos/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ notes }),
  });
}

export async function sendChatMessage(
  id: string,
  message: string
): Promise<ChatResponse> {
  return request<ChatResponse>(`/api/videos/${id}/chat`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export async function deleteVideo(id: string): Promise<void> {
  await request<void>(`/api/videos/${id}`, { method: "DELETE" });
}
