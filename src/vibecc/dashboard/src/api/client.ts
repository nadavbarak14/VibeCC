import type { APIResponse } from "../types/api";

const BASE_URL = "/api/v1";

class APIError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "APIError";
  }
}

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as APIResponse<null> | null;
    throw new APIError(
      response.status,
      body?.error ?? `Request failed with status ${response.status}`,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const json = (await response.json()) as APIResponse<T>;
  if (json.error) {
    throw new APIError(response.status, json.error);
  }
  return json.data as T;
}

export const apiClient = {
  get<T>(path: string): Promise<T> {
    return request<T>(path);
  },

  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  patch<T>(path: string, body: unknown): Promise<T> {
    return request<T>(path, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },

  delete(path: string): Promise<void> {
    return request<void>(path, { method: "DELETE" });
  },
};
