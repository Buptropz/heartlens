import type { AnalyzeResponse } from './types';

const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: 'unknown', detail: 'Unknown error' }));
    throw body;
  }
  return res.json();
}

export async function analyze(formData: FormData): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>('/analyze', {
    method: 'POST',
    body: formData,
  });
}

export async function getReport(id: string): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>(`/report/${id}`);
}
