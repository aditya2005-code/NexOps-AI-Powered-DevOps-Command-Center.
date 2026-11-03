import { Link } from 'react-router-dom'
import { AlertCircle, ArrowLeft, LayoutDashboard } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center p-6">
      <div className="p-4 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 mb-4">
        <AlertCircle className="w-8 h-8" />
      </div>
      <span className="text-xs font-mono font-bold text-rose-400 uppercase tracking-widest">
        404 — Route Not Found
      </span>
      <h1 className="mt-2 text-2xl font-bold text-white tracking-tight sm:text-3xl">
        Command Center Location Missing
      </h1>
      <p className="mt-2 text-sm text-slate-400 max-w-md">
        The requested operations endpoint does not exist or has been relocated by cluster routing.
      </p>

      <div className="mt-6 flex items-center gap-3">
        <Link to="/dashboard">
          <Button className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs gap-1.5">
            <LayoutDashboard className="w-3.5 h-3.5" />
            Back to Dashboard
          </Button>
        </Link>
        <Button
          variant="outline"
          className="text-xs border-[#29344e] text-slate-300 hover:text-white gap-1.5"
          onClick={() => window.history.back()}
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Previous Page
        </Button>
      </div>
    </div>
  )
}

