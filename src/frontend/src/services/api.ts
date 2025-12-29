/**
 * API Client for HealthCentral Backend
 * 
 * Base configuration and fetch wrapper for all API calls.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorBody = await response.text();
    let message = errorBody;
    try {
      const parsed = JSON.parse(errorBody);
      message = parsed.detail || parsed.message || errorBody;
    } catch {
      // Use raw text
    }
    throw new ApiError(response.status, response.statusText, message);
  }
  
  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }
  
  return response.json();
}

export async function apiGet<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE_URL}${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, value);
      }
    });
  }
  
  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });
  
  return handleResponse<T>(response);
}

export async function apiPost<T, D = unknown>(endpoint: string, data?: D): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: data ? JSON.stringify(data) : undefined,
  });
  
  return handleResponse<T>(response);
}

export async function apiPut<T, D = unknown>(endpoint: string, data: D): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });
  
  return handleResponse<T>(response);
}

export async function apiDelete(endpoint: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });
  
  return handleResponse<void>(response);
}

export async function apiUpload<T>(
  endpoint: string,
  file: File,
  params?: Record<string, string>
): Promise<T> {
  const url = new URL(`${API_BASE_URL}${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, value);
      }
    });
  }
  
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(url.toString(), {
    method: 'POST',
    credentials: 'include',
    body: formData,
  });
  
  return handleResponse<T>(response);
}
