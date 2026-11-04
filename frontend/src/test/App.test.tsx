import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppLayout } from '@/layouts/AppLayout'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'
import { ProjectsPage } from '@/pages/projects/ProjectsPage'
import { IncidentsPage } from '@/pages/incidents/IncidentsPage'
import { AgentsPage } from '@/pages/agents/AgentsPage'
import { SwitchIntegrationPage } from '@/pages/integrations/SwitchIntegrationPage'
import { AuditLogsPage } from '@/pages/audit-logs/AuditLogsPage'
import { SettingsPage } from '@/pages/settings/SettingsPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import App from '@/App'

function renderWithRouter(initialRoute = '/') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>
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
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('NexOps Frontend Architecture & Dashboard Tests', () => {
  it('1. Application renders successfully with branding and navigation', () => {
    render(<App />)
    expect(screen.getAllByText('NexOps').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Command Center').length).toBeGreaterThan(0)
  })

  it('2. Sidebar navigation links are present and accessible', () => {
    renderWithRouter('/dashboard')
    const nav = screen.getByRole('navigation')
    expect(within(nav).getByRole('link', { name: /dashboard/i })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: /projects/i })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: /incidents/i })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: /switch bridge/i })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: /ai agents/i })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: /audit logs/i })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: /settings/i })).toBeInTheDocument()
  })

  it('3. Dashboard renders all 4 KPI metric cards', () => {
    renderWithRouter('/dashboard')
    expect(screen.getByText('Active Incidents')).toBeInTheDocument()
    expect(screen.getByText('Projects Monitored')).toBeInTheDocument()
    expect(screen.getByText('AI Agents Active')).toBeInTheDocument()
    expect(screen.getByText('Successful Resolutions')).toBeInTheDocument()
    expect(screen.getByText('142')).toBeInTheDocument()
  })

  it('4. Dashboard renders Incident Overview Queue and AI Agent Swarm', () => {
    renderWithRouter('/dashboard')
    expect(screen.getByText('Active Incident Queue')).toBeInTheDocument()
    expect(screen.getByText('AI Agent Swarm')).toBeInTheDocument()
    expect(screen.getAllByText('Incident Manager').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Log Analyst').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Code Investigator').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Fix Agent').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Testing Agent').length).toBeGreaterThan(0)
  })

  it('5. Required routes render their respective view content', () => {
    // Projects route
    const { unmount: unmountProjects } = renderWithRouter('/projects')
    expect(screen.getAllByText('Monitored Projects').length).toBeGreaterThan(0)
    expect(screen.getByText('Core Platform Ingress')).toBeInTheDocument()
    unmountProjects()

    // Incidents route
    const { unmount: unmountIncidents } = renderWithRouter('/incidents')
    expect(screen.getAllByText('Incident Queue & Investigation').length).toBeGreaterThan(0)
    unmountIncidents()

    // Switch Integration route
    const { unmount: unmountSwitch } = renderWithRouter('/integrations/switch')
    expect(screen.getAllByText('Switch Collaboration Bridge').length).toBeGreaterThan(0)
    unmountSwitch()

    // Agents route
    const { unmount: unmountAgents } = renderWithRouter('/agents')
    expect(screen.getByText(/Specialized autonomous DevOps agents coordinated via LangGraph state machines/i)).toBeInTheDocument()
    unmountAgents()

    // Audit logs route
    const { unmount: unmountLogs } = renderWithRouter('/audit-logs')
    expect(screen.getAllByText('Audit Logs & Traceability').length).toBeGreaterThan(0)
    unmountLogs()

    // Settings route
    const { unmount: unmountSettings } = renderWithRouter('/settings')
    expect(screen.getAllByText('Settings & Workspace Configuration').length).toBeGreaterThan(0)
    unmountSettings()
  })

  it('6. Unknown routes display 404 Not Found error view', () => {
    renderWithRouter('/unknown-nonexistent-route')
    expect(screen.getByText('404 — Route Not Found')).toBeInTheDocument()
    expect(screen.getByText('Command Center Location Missing')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /back to dashboard/i })).toBeInTheDocument()
  })

  it('7. Responsive navigation and sidebar collapse toggle function properly', () => {
    renderWithRouter('/dashboard')
    const collapseToggle = screen.getByLabelText(/collapse sidebar/i)
    expect(collapseToggle).toBeInTheDocument()

    // Click collapse
    fireEvent.click(collapseToggle)
    expect(screen.getByLabelText(/expand sidebar/i)).toBeInTheDocument()

    // Click expand
    fireEvent.click(screen.getByLabelText(/expand sidebar/i))
    expect(screen.getByLabelText(/collapse sidebar/i)).toBeInTheDocument()
  })
})
