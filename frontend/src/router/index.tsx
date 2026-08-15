import { createBrowserRouter } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { ChatPage } from '../components/chat/ChatPage';
import { DocumentsPage } from '../components/documents/DocumentsPage';
import { SettingsPage } from '../components/settings/SettingsPage';

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { index: true, element: <ChatPage /> },
      { path: 'documents', element: <DocumentsPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
]);
