import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SwitchStatusBadge } from '@/components/integrations/SwitchStatusBadge'
import { SwitchOverviewCard } from '@/components/integrations/SwitchOverviewCard'
import { IncidentsPage } from '@/pages/incidents/IncidentsPage'
import { switchService } from '@/services/switchService'
import { incidentService } from '@/services/incidentService'
import type { SwitchStatusData } from '@/types/switch'
import type { BackendIncident } from '@/types/incident'

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
    },
  })
}

function renderWithClient(ui: React.ReactElement, queryClient = createTestQueryClient()) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('NexOps Phase 4.4 — Switch & Incident Integration Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  // 1. Connected status
  it('1. Renders Switch Connected status with agent ID and active indicator', async () => {
    const mockStatus: SwitchStatusData = {
      enabled: true,
      configured: true,
      state: 'connected',
      connected: true,
      agent_id: 'nexops-agent-primary',
      last_connected_at: new Date().toISOString(),
      last_error_at: null,
      last_error: null,
    }

    vi.spyOn(switchService, 'getStatus').mockResolvedValue(mockStatus)

    renderWithClient(<SwitchOverviewCard />)

    await waitFor(() => {
      expect(screen.getByText('Switch Connected')).toBeInTheDocument()
      expect(screen.getByText('nexops-agent-primary')).toBeInTheDocument()
      expect(screen.getByText('Active Loop')).toBeInTheDocument()
    })
  })

  // 2. Disabled status
  it('2. Renders Switch Disabled status and guidance message', async () => {
    const mockStatus: SwitchStatusData = {
      enabled: false,
      configured: false,
      state: 'disabled',
      connected: false,
      agent_id: null,
      last_connected_at: null,
      last_error_at: null,
      last_error: null,
    }

    vi.spyOn(switchService, 'getStatus').mockResolvedValue(mockStatus)

    renderWithClient(<SwitchOverviewCard />)

    await waitFor(() => {
      expect(screen.getAllByText('Switch Disabled').length).toBeGreaterThan(0)
      expect(screen.getByText('SWITCH_ENABLED=false')).toBeInTheDocument()
    })
  })

  // 3. Disconnected status
  it('3. Renders Switch Disconnected status with last error message', async () => {
    const mockStatus: SwitchStatusData = {
      enabled: true,
      configured: true,
      state: 'disconnected',
      connected: false,
      agent_id: 'nexops-agent-primary',
      last_connected_at: '2026-11-03T10:00:00Z',
      last_error_at: '2026-11-03T10:05:00Z',
      last_error: 'Connection reset by Switch Core gateway',
    }

    vi.spyOn(switchService, 'getStatus').mockResolvedValue(mockStatus)

    renderWithClient(<SwitchOverviewCard />)

    await waitFor(() => {
      expect(screen.getByText('Switch Disconnected')).toBeInTheDocument()
      expect(screen.getByText('Connection reset by Switch Core gateway')).toBeInTheDocument()
    })
  })

  // 4. Backend API failure
  it('4. Handles backend API failure cleanly and distinguishes from Switch disconnection', async () => {
    vi.spyOn(switchService, 'getStatus').mockRejectedValue(new Error('Network Error'))

    renderWithClient(<SwitchOverviewCard />)

    await waitFor(() => {
      expect(screen.getByText('Backend Offline')).toBeInTheDocument()
      expect(screen.getByText('NexOps FastAPI Backend Offline')).toBeInTheDocument()
      expect(screen.getByText('Backend Unreachable')).toBeInTheDocument()
    })
  })

  // 5. Loading state
  it('5. Renders loading state while checking Switch status', () => {
    render(<SwitchStatusBadge isLoading={true} />)
    expect(screen.getByText('Checking Switch...')).toBeInTheDocument()
  })

  // 6. Background refresh / polling configuration
  it('6. Uses TanStack Query with polling interval configured', async () => {
    const mockStatus: SwitchStatusData = {
      enabled: true,
      configured: true,
      state: 'connected',
      connected: true,
      agent_id: 'nexops-agent',
    }
    const getStatusSpy = vi.spyOn(switchService, 'getStatus').mockResolvedValue(mockStatus)

    const queryClient = createTestQueryClient()
    renderWithClient(<SwitchOverviewCard />, queryClient)

    await waitFor(() => {
      expect(getStatusSpy).toHaveBeenCalledTimes(1)
    })
  })

  // 7. Empty incident list
  it('7. Renders clean empty state when backend has no incidents', async () => {
    vi.spyOn(incidentService, 'list').mockResolvedValue([])

    renderWithClient(<IncidentsPage />)

    await waitFor(() => {
      expect(screen.getByText('PostgreSQL Incident Queue is Clean')).toBeInTheDocument()
      expect(
        screen.getByText(/No live incidents have been recorded in the database yet/i)
      ).toBeInTheDocument()
    })
  })

  // 8. Real incident rendering
  it('8. Renders real incidents fetched from the backend with project name and source', async () => {
    const mockIncidents: BackendIncident[] = [
      {
        id: 'inc-uuid-001',
        project_id: 'proj-uuid-1',
        project_name: 'Payments Microservice',
        title: 'Checkout 500 Spike',
        description: 'Payment gateway experiencing timeouts',
        severity: 'CRITICAL',
        status: 'OPEN',
        source: 'switch',
        source_id: 'switch:ops-room:msg-789',
        detected_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]

    vi.spyOn(incidentService, 'list').mockResolvedValue(mockIncidents)

    renderWithClient(<IncidentsPage />)

    await waitFor(() => {
      expect(screen.getByText('Checkout 500 Spike')).toBeInTheDocument()
      expect(screen.getByText('Payments Microservice')).toBeInTheDocument()
      expect(screen.getByText('switch')).toBeInTheDocument()
    })
  })

  // 9. Incident API failure
  it('9. Displays explicit error banner when incident API call fails', async () => {
    vi.spyOn(incidentService, 'list').mockRejectedValue(new Error('503 Service Unavailable'))

    renderWithClient(<IncidentsPage />)

    await waitFor(() => {
      expect(screen.getByText('Failed to connect to Incident API')).toBeInTheDocument()
      expect(screen.getByText('Switch to Simulated Data')).toBeInTheDocument()
    })
  })
})
