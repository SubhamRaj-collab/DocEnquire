import { apiClient } from './client';
import type { QueryRequest, QueryResponse } from '../types/api';

export async function queryDocuments(request: QueryRequest): Promise<QueryResponse> {
  const { data } = await apiClient.post<QueryResponse>('/query/', request);
  return data;
}

export function getStreamUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL || '/api/v1';
  return `${base}/query/stream`;
}
