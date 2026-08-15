import { apiClient } from './client';
import type { HealthResponse, CollectionsResponse } from '../types/api';

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>('/health/');
  return data;
}

export async function getCollections(): Promise<CollectionsResponse> {
  const { data } = await apiClient.get<CollectionsResponse>('/collections/');
  return data;
}
