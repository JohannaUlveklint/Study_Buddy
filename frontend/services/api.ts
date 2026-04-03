import type { Session, Task, TaskStartResponse } from "../types/study-buddy";


const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";


async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? "Request failed.");
  }

  return (await response.json()) as T;
}


export function createTask(title: string): Promise<Task> {
  return request<Task>("/tasks", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}


export function listTasks(): Promise<Task[]> {
  return request<Task[]>("/tasks", {
    method: "GET",
  });
}


export function startTask(taskId: string): Promise<TaskStartResponse> {
  return request<TaskStartResponse>(`/tasks/${taskId}/start`, {
    method: "POST",
  });
}


export function completeSession(sessionId: string): Promise<Session> {
  return request<Session>(`/sessions/${sessionId}/complete`, {
    method: "POST",
  });
}


export function abortSession(sessionId: string): Promise<Session> {
  return request<Session>(`/sessions/${sessionId}/abort`, {
    method: "POST",
  });
}