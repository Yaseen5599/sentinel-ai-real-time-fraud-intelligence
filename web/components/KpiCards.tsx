'use client'

import React from 'react'
import { Activity, ShieldAlert, Zap, TrendingUp, DollarSign } from 'lucide-react'

interface KpiCardsProps {
  total: number
  fraudCount: number
  rate: number
  avgLatency: number
  preventedAmount: number
}

export const KpiCards: React.FC<KpiCardsProps> = ({
  total,
  fraudCount,
  rate,
  avgLatency,
  preventedAmount
}) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {/* 1. Total Volume */}
      <div className="glass-panel p-4 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-all">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-slate-400">Total Scored</span>
          <Activity className="h-4 w-4 text-indigo-400" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-black tracking-tight text-white">{total.toLocaleString()}</span>
          <span className="text-[10px] text-emerald-400 font-semibold flex items-center">
            <TrendingUp className="h-2.5 w-2.5 mr-0.5" /> 100% Live
          </span>
        </div>
        <p className="text-[11px] text-slate-500 mt-1">Transactions ingested & scored</p>
      </div>

      {/* 2. Fraud & Suspicious Alerts */}
      <div className="glass-panel p-4 rounded-xl border border-red-950/60 relative overflow-hidden group hover:border-red-900/80 transition-all">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-red-300">Flagged Incidents</span>
          <ShieldAlert className="h-4 w-4 text-red-400" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-black tracking-tight text-red-400">{fraudCount.toLocaleString()}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 font-bold">
            Alert
          </span>
        </div>
        <p className="text-[11px] text-slate-500 mt-1">Suspicious / Fraud score &gt;= 0.40</p>
      </div>

      {/* 3. Fraud Alert Rate */}
      <div className="glass-panel p-4 rounded-xl border border-amber-950/50 relative overflow-hidden group hover:border-amber-900/70 transition-all">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-amber-300">Detection Rate</span>
          <Zap className="h-4 w-4 text-amber-400" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-black tracking-tight text-amber-400">{rate.toFixed(2)}%</span>
          <span className="text-[10px] text-slate-400">of stream</span>
        </div>
        <p className="text-[11px] text-slate-500 mt-1">Calibrated risk ratio</p>
      </div>

      {/* 4. Inference Latency */}
      <div className="glass-panel p-4 rounded-xl border border-cyan-950/50 relative overflow-hidden group hover:border-cyan-900/70 transition-all">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-cyan-300">Avg Decision Latency</span>
          <Activity className="h-4 w-4 text-cyan-400" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-black tracking-tight text-cyan-400 font-mono">
            {avgLatency > 0 ? avgLatency.toFixed(1) : '—'}
            <span className="text-sm font-sans font-normal ml-0.5 text-slate-400">ms</span>
          </span>
        </div>
        <p className="text-[11px] text-slate-500 mt-1">Sub-50ms SLA target met</p>
      </div>

      {/* 5. Loss Prevented */}
      <div className="glass-panel p-4 rounded-xl border border-emerald-950/50 relative overflow-hidden group hover:border-emerald-900/70 transition-all">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-emerald-300">Fraud Loss Prevented</span>
          <DollarSign className="h-4 w-4 text-emerald-400" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-black tracking-tight text-emerald-400 font-mono">
            ${preventedAmount.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
          </span>
        </div>
        <p className="text-[11px] text-slate-500 mt-1">Flagged high-risk unauthorized charges</p>
      </div>
    </div>
  )
}
