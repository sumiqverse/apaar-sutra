/**
 * Production API client for APAAR-Sutra with automatic Request-ID tracing,
 * Authorization token injection, and silent token rotation on 401 Unauthorized.
 */

export interface ApiError {
  code: string;
  message: string;
  details: Record<string, any>;
  request_id: string;
}

export class ApiException extends Error {
  error: ApiError;
  status: number;

  constructor(status: number, error: ApiError) {
    super(error.message);
    this.name = "ApiException";
    this.status = status;
    this.error = error;
  }
}

const ACCESS_TOKEN_KEY = "apaar_access_token";
const REFRESH_TOKEN_KEY = "apaar_refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setAuthTokens(accessToken: string, refreshToken?: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  if (refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }
}

export function clearAuthTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: any) => void;
}> = [];

function processQueue(error: any, token: string | null = null) {
  failedQueue.forEach((prom) => {
    if (token) {
      prom.resolve(token);
    } else {
      prom.reject(error);
    }
  });
  failedQueue = [];
}

export async function apiClient<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const reqId = "req-" + Math.random().toString(36).substring(2, 10);

  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (!headers.has("X-Request-ID")) {
    headers.set("X-Request-ID", reqId);
  }

  // Attach access token if present
  const accessToken = getAccessToken();
  if (accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  let response = await fetch(endpoint, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized with token refresh (avoid infinite loops on auth endpoints)
  if (response.status === 401 && !endpoint.includes("/auth/login") && !endpoint.includes("/auth/refresh")) {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      clearAuthTokens();
      window.dispatchEvent(new CustomEvent("apaar:session_expired"));
      throw new ApiException(401, {
        code: "SESSION_EXPIRED",
        message: "Session has expired. Please log in again.",
        details: {},
        request_id: reqId,
      });
    }

    if (isRefreshing) {
      // Queue incoming requests while refresh is in progress
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((newToken) => {
        headers.set("Authorization", `Bearer ${newToken}`);
        return fetch(endpoint, { ...options, headers }).then((res) => res.json() as Promise<T>);
      });
    }

    isRefreshing = true;

    try {
      const refreshRes = await fetch("/api/v1/auth/refresh", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Request-ID": reqId,
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!refreshRes.ok) {
        throw new Error("Refresh token expired or invalid");
      }

      const refreshData = await refreshRes.json();
      setAuthTokens(refreshData.access_token, refreshData.refresh_token);
      processQueue(null, refreshData.access_token);

      // Retry original request with fresh token
      headers.set("Authorization", `Bearer ${refreshData.access_token}`);
      response = await fetch(endpoint, {
        ...options,
        headers,
      });
    } catch (refreshErr) {
      processQueue(refreshErr, null);
      clearAuthTokens();
      window.dispatchEvent(new CustomEvent("apaar:session_expired"));
      throw new ApiException(401, {
        code: "SESSION_TERMINATED",
        message: "Your session has expired. Please log in again.",
        details: {},
        request_id: reqId,
      });
    } finally {
      isRefreshing = false;
    }
  }

  if (!response.ok) {
    let errorDetail: ApiError = {
      code: "UNKNOWN_ERROR",
      message: response.statusText || "Request failed",
      details: {},
      request_id: response.headers.get("X-Request-ID") || reqId,
    };

    try {
      const data = await response.json();
      if (data && data.error) {
        errorDetail = data.error;
      }
    } catch {
      // Fallback to generic message
    }

    throw new ApiException(response.status, errorDetail);
  }

  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(endpoint: string, options: { params?: Record<string, any>; headers?: Record<string, string> } = {}) => {
    let url = endpoint;
    if (options.params) {
      const searchParams = new URLSearchParams();
      for (const [k, v] of Object.entries(options.params)) {
        if (v !== undefined && v !== null && v !== "") searchParams.append(k, String(v));
      }
      const qs = searchParams.toString();
      if (qs) url += (url.includes("?") ? "&" : "?") + qs;
    }
    return apiClient<T>(url, { method: "GET", headers: options.headers }).then((data) => ({ data }));
  },
  post: <T>(endpoint: string, body?: any, options: { headers?: Record<string, string> } = {}) => {
    return apiClient<T>(endpoint, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
      headers: options.headers,
    }).then((data) => ({ data }));
  },
};
