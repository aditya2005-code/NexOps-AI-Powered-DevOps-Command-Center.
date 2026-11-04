import { useState } from 'react'
import { Sliders, Bell, Palette, Radio, Save, Shield } from 'lucide-react'
import { PageHeader } from '@/components/common/PageHeader'
import { Button } from '@/components/ui/button'
import { SwitchOverviewCard } from '@/components/integrations/SwitchOverviewCard'

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'general' | 'appearance' | 'notifications' | 'integrations'>('general')

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings & Workspace Configuration"
        subtitle="Manage command center preferences, telemetry webhooks, and agent automation thresholds."
      />

      <div className="flex flex-col md:flex-row gap-6">
        {/* Settings Navigation Tabs */}
        <aside className="w-full md:w-56 shrink-0">
          <nav className="flex md:flex-col gap-1 p-1 rounded-lg border border-[#1e2436] bg-[#121622]">
            <button
              onClick={() => setActiveTab('general')}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium text-left transition-colors ${
                activeTab === 'general'
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-[#1a2030] border border-transparent'
              }`}
            >
              <Sliders className="w-4 h-4" />
              General
            </button>
            <button
              onClick={() => setActiveTab('appearance')}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium text-left transition-colors ${
                activeTab === 'appearance'
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-[#1a2030] border border-transparent'
              }`}
            >
              <Palette className="w-4 h-4" />
              Appearance
            </button>
            <button
              onClick={() => setActiveTab('notifications')}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium text-left transition-colors ${
                activeTab === 'notifications'
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-[#1a2030] border border-transparent'
              }`}
            >
              <Bell className="w-4 h-4" />
              Notifications
            </button>
            <button
              onClick={() => setActiveTab('integrations')}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium text-left transition-colors ${
                activeTab === 'integrations'
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-[#1a2030] border border-transparent'
              }`}
            >
              <Radio className="w-4 h-4" />
              Integrations
            </button>
          </nav>
        </aside>

        {/* Tab Content Panes */}
        <div className="flex-1 rounded-lg border border-[#1e2436] bg-[#121622] p-6 space-y-6">
          {activeTab === 'general' && (
            <div className="space-y-5">
              <div>
                <h3 className="text-base font-semibold text-white">General Preferences</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Workspace metadata and incident response thresholds
                </p>
              </div>

              <div className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Workspace Identifier
                  </label>
                  <input
                    type="text"
                    defaultValue="NexOps Command Center (Production Cluster)"
                    className="w-full max-w-md h-8.5 px-3 rounded-md border border-[#1e2436] bg-[#0c0e15] text-slate-200"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Autonomous Fix Approval Policy
                  </label>
                  <select
                    defaultValue="human-required"
                    className="w-full max-w-md h-8.5 px-3 rounded-md border border-[#1e2436] bg-[#0c0e15] text-slate-200"
                  >
                    <option value="human-required">Require Operator Approval for all Patches (Safe)</option>
                    <option value="low-auto">Auto-apply Low-Risk Configuration Adjustments</option>
                    <option value="full-autonomous">Fully Autonomous Sandbox Validation</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Default Telemetry Refresh Interval
                  </label>
                  <select
                    defaultValue="15s"
                    className="w-full max-w-md h-8.5 px-3 rounded-md border border-[#1e2436] bg-[#0c0e15] text-slate-200"
                  >
                    <option value="5s">Every 5 seconds</option>
                    <option value="15s">Every 15 seconds (Recommended)</option>
                    <option value="60s">Every 60 seconds</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'appearance' && (
            <div className="space-y-5">
              <div>
                <h3 className="text-base font-semibold text-white">Interface Appearance</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Visual theme and console density settings
                </p>
              </div>

              <div className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Color Theme</label>
                  <div className="grid grid-cols-2 max-w-md gap-3">
                    <div className="p-3 rounded-md border border-indigo-500 bg-[#090b11] text-left cursor-pointer">
                      <span className="font-semibold text-white block">Deep Charcoal (Dark)</span>
                      <span className="text-[11px] text-indigo-400">Default Enterprise Theme</span>
                    </div>
                    <div className="p-3 rounded-md border border-[#1e2436] bg-[#121622] text-left opacity-50 cursor-not-allowed">
                      <span className="font-semibold text-slate-300 block">High Contrast</span>
                      <span className="text-[11px] text-slate-500">Coming soon</span>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Data Table Density</label>
                  <select
                    defaultValue="compact"
                    className="w-full max-w-md h-8.5 px-3 rounded-md border border-[#1e2436] bg-[#0c0e15] text-slate-200"
                  >
                    <option value="compact">Compact (DevOps default)</option>
                    <option value="comfortable">Comfortable</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="space-y-5">
              <div>
                <h3 className="text-base font-semibold text-white">Alert Dispatch & Notification Channels</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Configure where incident notifications and approval requests are delivered
                </p>
              </div>

              <div className="space-y-3 text-xs">
                <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                  <input type="checkbox" defaultChecked className="rounded border-[#1e2436] text-indigo-600" />
                  <span>Notify immediately on <strong>Critical</strong> severity alerts</span>
                </label>
                <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                  <input type="checkbox" defaultChecked className="rounded border-[#1e2436] text-indigo-600" />
                  <span>Prompt operator when Fix Agent generates candidate pull request</span>
                </label>
                <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                  <input type="checkbox" defaultChecked className="rounded border-[#1e2436] text-indigo-600" />
                  <span>Daily operational resolution digest</span>
                </label>
              </div>
            </div>
          )}

          {activeTab === 'integrations' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-base font-semibold text-white">Connected Integrations</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Live connection health for official Switch Agent Bridge and database telemetry
                </p>
              </div>

              {/* Real Switch Integration Card */}
              <SwitchOverviewCard />

              <div className="rounded-xl border border-[#1e2436] bg-[#0c0e15] p-4 text-xs space-y-2">
                <div className="flex items-center gap-2.5">
                  <Shield className="w-4 h-4 text-indigo-400" />
                  <div>
                    <span className="font-semibold text-white block">Neon PostgreSQL Database</span>
                    <span className="text-[11px] text-slate-400">
                      Primary telemetry and incident persistence layer (Active)
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="pt-4 border-t border-[#1e2436] flex justify-end">
            <Button
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs gap-1.5"
              onClick={() => alert('Settings saved (Simulation mode)')}
            >
              <Save className="w-3.5 h-3.5" />
              Save Preferences
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
