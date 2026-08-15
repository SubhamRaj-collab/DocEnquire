import { UploadZone } from './UploadZone';
import { DocumentList } from './DocumentList';

export function DocumentsPage() {
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Documents</h2>
        <p className="text-sm text-gray-500 mt-1">Upload and manage your knowledge base</p>
      </div>
      <UploadZone />
      <DocumentList />
    </div>
  );
}
