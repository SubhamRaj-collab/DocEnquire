import { NavLink } from 'react-router-dom';
import { MessageSquare, FileText, Settings, Activity } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { getHealth } from '../../api/health';

const navItems = [
  { to: '/', icon: MessageSquare, label: 'Chat' },
  { to: '/documents', icon: FileText, label: 'Documents' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export function Sidebar() {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30_000,
    retry: false,
  });

  const isHealthy = health?.status === 'healthy';

  return (
    <aside className="hidden lg:flex flex-col w-64 bg-white border-r border-gray-200 h-screen fixed left-0 top-0">
      <div className="p-6 border-b border-gray-100">
        <h1 className="text-lg font-bold text-brand-900">Document Q&A</h1>
        <p className="text-xs text-gray-500 mt-1">Enterprise RAG System</p>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-brand-50 text-brand-700 border-l-3 border-brand-600'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-gray-100">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Activity size={14} />
          <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-green-500' : 'bg-red-500'}`} />
          <span>{isHealthy ? 'System Healthy' : 'Disconnected'}</span>
        </div>
      </div>
    </aside>
  );
}
