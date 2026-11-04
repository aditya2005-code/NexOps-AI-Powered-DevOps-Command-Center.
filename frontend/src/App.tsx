import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { AppLayout } from '@/layouts/AppLayout'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'
import { ProjectsPage } from '@/pages/projects/ProjectsPage'
import { IncidentsPage } from '@/pages/incidents/IncidentsPage'
import { AgentsPage } from '@/pages/agents/AgentsPage'
import { AuditLogsPage } from '@/pages/audit-logs/AuditLogsPage'
import { SettingsPage } from '@/pages/settings/SettingsPage'
import { SwitchIntegrationPage } from '@/pages/integrations/SwitchIntegrationPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/incidents" element={<IncidentsPage />} />
            <Route path="/agents" element={<AgentsPage />} />
            <Route path="/integrations" element={<SwitchIntegrationPage />} />
            <Route path="/integrations/switch" element={<SwitchIntegrationPage />} />
            <Route path="/audit-logs" element={<AuditLogsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster
        theme="dark"
        position="top-right"
        toastOptions={{
          style: {
            background: '#121622',
            border: '1px solid #1e2436',
            color: '#e2e8f0',
          },
        }}
      />
    </QueryClientProvider>
  )
}
