import { useQuery } from '@tanstack/react-query';
import { Database, Cpu, HardDrive, RefreshCw } from 'lucide-react';
import { getHealth, getCollections } from '../../api/health';
import { useChatStore } from '../../store/chatStore';

export function SettingsPage() {
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
  });

  const { data: collectionsData } = useQuery({
    queryKey: ['collections'],
    queryFn: getCollections,
  });

  const activeCollection = useChatStore((s) => s.activeCollection);
  const setActiveCollection = useChatStore((s) => s.setActiveCollection);
  const clearMessages = useChatStore((s) => s.clearMessages);

  const collections = collectionsData?.collections ?? [];

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Settings</h2>
        <p className="text-sm text-gray-500 mt-1">System configuration and status</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <div className="flex items-center gap-2 text-sm font-medium text-gray-900">
          <Database size={16} />
          Active Collection
        </div>
        <select
          value={activeCollection}
          onChange={(e) => setActiveCollection(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {collections.length > 0 ? (
            collections.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name} ({c.document_count} docs)
              </option>
            ))
          ) : (
            <option value="default">default</option>
          )}
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <div className="flex items-center gap-2 text-sm font-medium text-gray-900">
          <Cpu size={16} />
          Model Information
        </div>
        {healthLoading ? (
          <p className="text-sm text-gray-400">Loading...</p>
        ) : health ? (
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-500">LLM Provider:</span>
              <p className="font-medium">{health.llm_provider}</p>
            </div>
            <div>
              <span className="text-gray-500">LLM Model:</span>
              <p className="font-medium">{health.llm_model}</p>
            </div>
            <div>
              <span className="text-gray-500">Embedding Provider:</span>
              <p className="font-medium">{health.embedding_provider}</p>
            </div>
            <div>
              <span className="text-gray-500">Embedding Model:</span>
              <p className="font-medium">{health.embedding_model}</p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-red-500">Unable to connect to backend</p>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <div className="flex items-center gap-2 text-sm font-medium text-gray-900">
          <HardDrive size={16} />
          System Status
        </div>
        {health && (
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-500">Status:</span>
              <p className="font-medium">
                <span className={`inline-block w-2 h-2 rounded-full mr-1.5 ${
                  health.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                }`} />
                {health.status}
              </p>
            </div>
            <div>
              <span className="text-gray-500">Version:</span>
              <p className="font-medium">{health.version}</p>
            </div>
            <div>
              <span className="text-gray-500">Total Chunks:</span>
              <p className="font-medium">{health.document_count}</p>
            </div>
            <div>
              <span className="text-gray-500">Collections:</span>
              <p className="font-medium">{health.collection_count}</p>
            </div>
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm font-medium text-gray-900">
              <RefreshCw size={16} />
              Chat History
            </div>
            <p className="text-xs text-gray-500 mt-1">Clear all messages from the current session</p>
          </div>
          <button onClick={clearMessages} className="btn-secondary text-sm">
            Clear Chat
          </button>
        </div>
      </div>
    </div>
  );
}
