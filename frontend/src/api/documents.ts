import { apiClient } from './client';
import type { DocumentListResponse, DocumentUploadResponse, DocumentDeleteResponse } from '../types/api';

export async function uploadDocument(file: File, collectionName: string = 'default'): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('collection_name', collectionName);
  const { data } = await apiClient.post<DocumentUploadResponse>('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120_000,
  });
  return data;
}

export async function listDocuments(collectionName: string = 'default'): Promise<DocumentListResponse> {
  const { data } = await apiClient.get<DocumentListResponse>('/documents/', {
    params: { collection_name: collectionName },
  });
  return data;
}

export async function deleteDocument(documentId: string, collectionName: string = 'default'): Promise<DocumentDeleteResponse> {
  const { data } = await apiClient.delete<DocumentDeleteResponse>(`/documents/${documentId}`, {
    params: { collection_name: collectionName },
  });
  return data;
}
