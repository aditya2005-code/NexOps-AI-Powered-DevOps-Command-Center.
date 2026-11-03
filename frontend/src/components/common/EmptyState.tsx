import React from 'react'
import { Inbox } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface EmptyStateProps {
  title: string
  description: string
  icon?: React.ElementType
  actionLabel?: string
  onAction?: () => void
}

export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center rounded-lg border border-dashed border-[#1e2436] bg-[#121622]/50">
      <div className="p-3 rounded-full bg-[#1e2436]/50 text-slate-400 mb-3">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-base font-semibold text-slate-200">{title}</h3>
      <p className="mt-1 text-sm text-slate-400 max-w-sm">{description}</p>
      {actionLabel && onAction && (
        <Button onClick={onAction} variant="outline" className="mt-4 text-xs">
          {actionLabel}
        </Button>
      )}
    </div>
  )
}

