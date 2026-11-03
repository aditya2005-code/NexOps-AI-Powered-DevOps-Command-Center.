import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Sidebar } from '@/components/layout/Sidebar'
import { Dashboard } from '@/pages/Dashboard'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="flex h-screen overflow-hidden bg-slate-50">
          <Sidebar />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/activity" element={<main className="flex-1 p-8"><h1 className="text-2xl font-bold">Activity</h1><p className="text-slate-500 mt-1">Coming soon.</p></main>} />
            <Route path="/settings" element={<main className="flex-1 p-8"><h1 className="text-2xl font-bold">Settings</h1><p className="text-slate-500 mt-1">Coming soon.</p></main>} />
          </Routes>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
