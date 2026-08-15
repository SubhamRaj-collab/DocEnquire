import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Loader2 } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { uploadDocument } from '../../api/documents';
import { useChatStore } from '../../store/chatStore';

const ACCEPTED_TYPES: Record<string, string[]> = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'text/html': ['.html', '.htm'],
  'text/markdown': ['.md', '.markdown'],
  'text/plain': ['.txt'],
};

export function UploadZone() {
  const queryClient = useQueryClient();
  const collection = useChatStore((s) => s.activeCollection);
  const [uploading, setUploading] = useState<string[]>([]);

  const mutation = useMutation({
    mutationFn: (file: File) => uploadDocument(file, collection),
    onSuccess: (data) => {
      toast.success(`Uploaded "${data.filename}" (${data.chunk_count} chunks)`);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: (err, file) => {
      toast.error(`Failed to upload "${file.name}": ${(err as Error).message}`);
    },
  });

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setUploading(acceptedFiles.map((f) => f.name));
      for (const file of acceptedFiles) {
        await mutation.mutateAsync(file);
      }
      setUploading([]);
    },
    [mutation]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: 50 * 1024 * 1024,
  });

  const isUploading = uploading.length > 0;

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
        isDragActive
          ? 'border-brand-500 bg-brand-50'
          : 'border-gray-300 hover:border-gray-400 bg-white'
      } ${isUploading ? 'pointer-events-none opacity-60' : ''}`}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-3">
        {isUploading ? (
          <>
            <Loader2 size={32} className="text-brand-600 animate-spin" />
            <p className="text-sm text-gray-600">
              Uploading {uploading.length} file{uploading.length > 1 ? 's' : ''}...
            </p>
          </>
        ) : (
          <>
            <Upload size={32} className="text-gray-400" />
            <div>
              <p className="text-sm font-medium text-gray-700">
                {isDragActive ? 'Drop files here' : 'Drag & drop files, or click to browse'}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                PDF, DOCX, PPTX, XLSX, HTML, Markdown, TXT (max 50MB)
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
