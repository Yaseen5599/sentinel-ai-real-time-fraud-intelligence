'use client'

import React, { useState } from 'react'
import { Play, Flame, Plane, DollarSign, Moon, ShieldAlert, RefreshCw } from 'lucide-react'

interface SimulationControlsProps {
  onSimulate: (scenario: string, count?: number, publishToKafka?: boolean) => Promise<void>
  isSimulating: boolean
}

export const SimulationControls: React.FC<SimulationControlsProps> = ({
  onSimulate,
  isSimulating
}) => {
  const [activeScenario, setActiveScenario] = useState<string | null>(null)
  const [publishToKafka, setPublishToKafka] = useState<boolean>(false)

  const handleTrigger = async (scenario: string, count: number = 5) => {
    setActiveScenario(scenario)
    try {
      await onSimulate(scenario, count, publishToKafka)
    } finally {
      setActiveScenario(null)
    }
  }

  return (
    <div className="glass-panel p-4 rounded-xl border border-slate-800">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-3">
        <div>
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Flame className="h-4 w-4 text-amber-400" />
            Live Scenario Injection & Stress Testing
          </h3>
          <p className="text-xs text-slate-400">
            Inject synthetic spending patterns and concrete financial fraud attack vectors into the live pipeline
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-slate-300 bg-slate-900/80 px-2.5 py-1.5 rounded-lg border border-slate-700 cursor-pointer hover:border-slate-500 transition-colors">
            <input
              type="checkbox"
              checked={publishToKafka}
              onChange={(e) => setPublishToKafka(e.target.checked)}
              className="rounded bg-slate-800 border-slate-600 text-brand-600 focus:ring-0"
            />
            <span className="font-mono text-[11px]">
              Route via Kafka <span className="text-purple-400 font-semibold">(canonical)</span>
            </span>
          </label>

          {isSimulating && (
            <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-xs">
              <RefreshCw className="h-3 w-3 animate-spin" />
              Processing stream...
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        {/* 1. Normal Spend */}
        <button
          disabled={isSimulating}
          onClick={() => handleTrigger('NORMAL', 5)}
          className={`px-3 py-2.5 rounded-lg border text-xs font-medium transition-all text-left flex flex-col justify-between ${
            activeScenario === 'NORMAL'
              ? 'bg-emerald-600 text-white border-emerald-500'
              : 'bg-slate-900/80 border-slate-800 text-slate-300 hover:border-emerald-500/40 hover:bg-slate-800/60'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-emerald-400">Normal Spend</span>
            <Play className="h-3 w-3 text-emerald-400" />
          </div>
          <span className="text-[10px] text-slate-400">5 regular txns</span>
        </button>

        {/* 2. Rapid Burst */}
        <button
          disabled={isSimulating}
          onClick={() => handleTrigger('RAPID_BURST', 6)}
          className={`px-3 py-2.5 rounded-lg border text-xs font-medium transition-all text-left flex flex-col justify-between ${
            activeScenario === 'RAPID_BURST'
              ? 'bg-red-600 text-white border-red-500'
              : 'bg-slate-900/80 border-slate-800 text-slate-300 hover:border-red-500/40 hover:bg-slate-800/60'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-red-400">Velocity Burst</span>
            <Flame className="h-3 w-3 text-red-400" />
          </div>
          <span className="text-[10px] text-slate-400">&gt;5 txns in 90 secs</span>
        </button>

        {/* 3. Impossible Travel */}
        <button
          disabled={isSimulating}
          onClick={() => handleTrigger('IMPOSSIBLE_TRAVEL', 2)}
          className={`px-3 py-2.5 rounded-lg border text-xs font-medium transition-all text-left flex flex-col justify-between ${
            activeScenario === 'IMPOSSIBLE_TRAVEL'
              ? 'bg-red-600 text-white border-red-500'
              : 'bg-slate-900/80 border-slate-800 text-slate-300 hover:border-red-500/40 hover:bg-slate-800/60'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-red-400">Impossible Travel</span>
            <Plane className="h-3 w-3 text-red-400" />
          </div>
          <span className="text-[10px] text-slate-400">NY to Singapore (15m)</span>
        </button>

        {/* 4. High Value Spike */}
        <button
          disabled={isSimulating}
          onClick={() => handleTrigger('HIGH_VALUE_SPIKE', 1)}
          className={`px-3 py-2.5 rounded-lg border text-xs font-medium transition-all text-left flex flex-col justify-between ${
            activeScenario === 'HIGH_VALUE_SPIKE'
              ? 'bg-amber-600 text-white border-amber-500'
              : 'bg-slate-900/80 border-slate-800 text-slate-300 hover:border-amber-500/40 hover:bg-slate-800/60'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-amber-400">Value Surge</span>
            <DollarSign className="h-3 w-3 text-amber-400" />
          </div>
          <span className="text-[10px] text-slate-400">Amount &gt;6x baseline</span>
        </button>

        {/* 5. Account Takeover */}
        <button
          disabled={isSimulating}
          onClick={() => handleTrigger('ACCOUNT_TAKEOVER', 1)}
          className={`px-3 py-2.5 rounded-lg border text-xs font-medium transition-all text-left flex flex-col justify-between ${
            activeScenario === 'ACCOUNT_TAKEOVER'
              ? 'bg-red-600 text-white border-red-500'
              : 'bg-slate-900/80 border-slate-800 text-slate-300 hover:border-red-500/40 hover:bg-slate-800/60'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-red-400">Takeover (ATO)</span>
            <Moon className="h-3 w-3 text-red-400" />
          </div>
          <span className="text-[10px] text-slate-400">3 AM Tokyo Casino</span>
        </button>

        {/* 6. Card Testing */}
        <button
          disabled={isSimulating}
          onClick={() => handleTrigger('CARD_TESTING', 3)}
          className={`px-3 py-2.5 rounded-lg border text-xs font-medium transition-all text-left flex flex-col justify-between ${
            activeScenario === 'CARD_TESTING'
              ? 'bg-red-600 text-white border-red-500'
              : 'bg-slate-900/80 border-slate-800 text-slate-300 hover:border-red-500/40 hover:bg-slate-800/60'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-red-400">Card Testing</span>
            <ShieldAlert className="h-3 w-3 text-red-400" />
          </div>
          <span className="text-[10px] text-slate-400">2 Declines $\rightarrow$ $1,450 Charge</span>
        </button>
      </div>
    </div>
  )
}
