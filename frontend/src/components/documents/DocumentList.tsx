import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Trash2, FileText, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { listDocuments, deleteDocument } from '../../api/documents';
import { useChatStore } from '../../store/chatStore';
import { formatDate } from '../../lib/formatters';

const DOC_TYPE_COLORS: Record<string, string> = {
  pdf: 'bg-red-100 text-red-700',
  docx: 'bg-blue-100 text-blue-700',
  pptx: 'bg-orange-100 text-orange-700',
  xlsx: 'bg-green-100 text-green-700',
  html: 'bg-purple-100 text-purple-700',
  md: 'bg-gray-100 text-gray-700',
  txt: 'bg-yellow-100 text-yellow-700',
};

export function DocumentList() {
  const queryClient = useQueryClient();
  const collection = useChatStore((s) => s.activeCollection);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['documents', collection],
    queryFn: () => listDocuments(collection),
    refetchInterval: 10_000,
  });

  const deleteMutation = useMutation({
    mutationFn: (docId: string) => deleteDocument(docId, collection),
    onSuccess: (data) => {
      toast.success(`Deleted "${data.filename}"`);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setConfirmId(null);
    },
    onError: (err) => {
      toast.error(`Delete failed: ${(err as Error).message}`);
    },
    onSettled: () => setDeletingId(null),
  });

  const handleDelete = (docId: string) => {
    if (confirmId === docId) {
      setDeletingId(docId);
      deleteMutation.mutate(docId);
    } else {
      setConfirmId(docId);
      setTimeout(() => setConfirmId(null), 3000);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="animate-spin text-gray-400" size={24} />
      </div>
    );
  }

  const docs = data?.documents ?? [];

  if (docs.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <FileText size={48} className="mx-auto mb-3 text-gray-300" />
        <p className="text-sm">No documents uploaded yet</p>
        <p className="text-xs mt-1">Upload files above to get started</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            <th className="px-4 py-3">Document</th>
            <th className="px-4 py-3">Type</th>
            <th className="px-4 py-3">Chunks</th>
            <th className="px-4 py-3">Uploaded</th>
            <th className="px-4 py-3 w-16"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {docs.map((doc) => (
            <tr key={doc.document_id} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3 font-medium text-gray-900">{doc.filename}</td>
              <td className="px-4 py-3">
                <span
                  className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                    DOC_TYPE_COLORS[doc.doc_type] ?? 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {doc.doc_type.toUpperCase()}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-600">{doc.chunk_count}</td>
              <td className="px-4 py-3 text-gray-500">{formatDate(doc.upload_timestamp)}</td>
              <td className="px-4 py-3">
                <button
                  onClick={() => handleDelete(doc.document_id)}
                  disabled={deletingId === doc.document_id}
                  className={`p-1.5 rounded-lg transition-colors ${
                    confirmId === doc.document_id
                      ? 'bg-red-100 text-red-600 hover:bg-red-200'
                      : 'text-gray-400 hover:text-red-600 hover:bg-red-50'
                  }`}
                  title={confirmId === doc.document_id ? 'Click again to confirm' : 'Delete'}
                >
                  {deletingId === doc.document_id ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Trash2 size={16} />
                  )}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
