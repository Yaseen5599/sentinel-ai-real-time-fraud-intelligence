'use client'

import React, { useState } from 'react'
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  MapPin,
  Clock,
  CreditCard,
  Building,
  UserCheck
} from 'lucide-react'

export interface TransactionRecord {
  transaction_id: string
  card_id: string
  masked_card_id?: string
  amount: number
  currency?: string
  merchant?: string
  merchant_name?: string
  location?: string
  city?: string
  channel?: string
  timestamp: string
  ml_score?: number | null
  behavior_score?: number | null
  rule_score?: number | null
  final_fraud_score: number
  fraud_decision: 'LEGITIMATE' | 'SUSPICIOUS' | 'FRAUD' | string
  explanation?: string
  triggered_rules?: string[]
  processing_latency_ms?: number | null
  case_id?: string
  investigation_status?: string
}

interface TransactionStreamProps {
  transactions: TransactionRecord[]
  onOpenCase: (tx: TransactionRecord) => void
}

export const TransactionStream: React.FC<TransactionStreamProps> = ({
  transactions,
  onOpenCase
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [filter, setFilter] = useState<'ALL' | 'FLAGGED'>('ALL')

  const filteredTxns = transactions.filter(t => {
    if (filter === 'FLAGGED') {
      return t.fraud_decision === 'FRAUD' || t.fraud_decision === 'SUSPICIOUS'
    }
    return true
  })

  const toggleExpand = (id: string) => {
    setExpandedId(prev => (prev === id ? null : id))
  }

  const getDecisionBadge = (decision: string, score: number) => {
    if (decision === 'FRAUD') {
      return (
        <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-red-500/10 text-red-400 border border-red-500/30 flex items-center gap-1.5 shadow-glow-fraud">
          <ShieldAlert className="h-3.5 w-3.5" />
          FRAUD ({score.toFixed(2)})
        </span>
      )
    }
    if (decision === 'SUSPICIOUS') {
      return (
        <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1.5">
          <AlertTriangle className="h-3.5 w-3.5" />
          SUSPICIOUS ({score.toFixed(2)})
        </span>
      )
    }
    return (
      <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
        <ShieldCheck className="h-3.5 w-3.5" />
        LEGITIMATE ({score.toFixed(2)})
      </span>
    )
  }

  return (
    <div className="glass-panel rounded-xl border border-slate-800 p-4">
      {/* Stream Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            Real-Time Ingestion Stream
            <span className="text-xs font-normal text-slate-400 font-mono">
              ({filteredTxns.length} events)
            </span>
          </h3>
          <p className="text-xs text-slate-400">
            Streaming inference events scored via Hybrid Risk Model (0.50 ML + 0.30 Behavior + 0.20 Rules)
          </p>
        </div>

        {/* Filter Buttons */}
        <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs">
          <button
            onClick={() => setFilter('ALL')}
            className={`px-3 py-1 rounded font-medium transition-all ${
              filter === 'ALL'
                ? 'bg-slate-800 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All Stream
          </button>
          <button
            onClick={() => setFilter('FLAGGED')}
            className={`px-3 py-1 rounded font-medium transition-all ${
              filter === 'FLAGGED'
                ? 'bg-red-950 text-red-300 border border-red-800/50'
                : 'text-slate-400 hover:text-red-300'
            }`}
          >
            Flagged Alerts Only
          </button>
        </div>
      </div>

      {/* Transaction Feed */}
      <div className="space-y-2.5 max-h-[600px] overflow-y-auto pr-1">
        {filteredTxns.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-sm">
            No transactions match the selected filter. Trigger a scenario above to observe live telemetry.
          </div>
        ) : (
          filteredTxns.map(tx => {
            const isExpanded = expandedId === tx.transaction_id
            const isFlagged = tx.fraud_decision === 'FRAUD' || tx.fraud_decision === 'SUSPICIOUS'

            return (
              <div
                key={tx.transaction_id}
                className={`rounded-xl border transition-all ${
                  isFlagged
                    ? tx.fraud_decision === 'FRAUD'
                      ? 'bg-red-950/15 border-red-900/40 hover:border-red-700/60'
                      : 'bg-amber-950/15 border-amber-900/40 hover:border-amber-700/60'
                    : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700/80'
                }`}
              >
                {/* Main Row */}
                <div
                  onClick={() => toggleExpand(tx.transaction_id)}
                  className="p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700/60">
                      <CreditCard className="h-4 w-4 text-slate-300" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-bold text-white">
                          {tx.card_id}
                        </span>
                        <span className="text-[11px] font-mono text-slate-400">
                          {tx.transaction_id}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                        <span className="flex items-center gap-1">
                          <Building className="h-3 w-3 text-slate-500" />
                          {tx.merchant_name || tx.merchant || 'Unknown'}
                        </span>
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3 w-3 text-slate-500" />
                          {tx.city || tx.location || 'Unknown'}
                        </span>
                        <span className="flex items-center gap-1 font-mono text-[11px]">
                          <Clock className="h-3 w-3 text-slate-500" />
                          {new Date(tx.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 self-end sm:self-center">
                    <div className="text-right">
                      <div className="font-mono text-base font-bold text-white">
                        ${tx.amount.toFixed(2)}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {tx.processing_latency_ms}ms
                      </div>
                    </div>

                    {getDecisionBadge(tx.fraud_decision, tx.final_fraud_score)}

                    {isExpanded ? (
                      <ChevronUp className="h-4 w-4 text-slate-400" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-slate-400" />
                    )}
                  </div>
                </div>

                {/* Expanded Explainability Details */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-2 border-t border-slate-800/80 bg-slate-950/40 rounded-b-xl space-y-3">
                    {/* Sub-Score Breakdown */}
                    <div className="grid grid-cols-3 gap-2">
                      <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                        <div className="text-[10px] uppercase font-semibold text-slate-400">
                          ML Model (50%)
                        </div>
                        <div className="font-mono text-sm font-bold text-indigo-400 mt-0.5">
                          {typeof tx.ml_score === 'number' ? `${(tx.ml_score * 100).toFixed(1)}%` : '—'}
                        </div>
                        <div className="w-full bg-slate-800 h-1 rounded-full mt-1.5 overflow-hidden">
                          <div
                            className="bg-indigo-500 h-full rounded-full"
                            style={{ width: `${Math.min(100, (tx.ml_score ?? 0) * 100)}%` }}
                          />
                        </div>
                      </div>

                      <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                        <div className="text-[10px] uppercase font-semibold text-slate-400">
                          Behavioral Anomaly (30%)
                        </div>
                        <div className="font-mono text-sm font-bold text-amber-400 mt-0.5">
                          {typeof tx.behavior_score === 'number' ? `${(tx.behavior_score * 100).toFixed(1)}%` : '—'}
                        </div>
                        <div className="w-full bg-slate-800 h-1 rounded-full mt-1.5 overflow-hidden">
                          <div
                            className="bg-amber-500 h-full rounded-full"
                            style={{ width: `${Math.min(100, (tx.behavior_score ?? 0) * 100)}%` }}
                          />
                        </div>
                      </div>

                      <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                        <div className="text-[10px] uppercase font-semibold text-slate-400">
                          Deterministic Rules (20%)
                        </div>
                        <div className="font-mono text-sm font-bold text-rose-400 mt-0.5">
                          {typeof tx.rule_score === 'number' ? `${(tx.rule_score * 100).toFixed(1)}%` : '—'}
                        </div>
                        <div className="w-full bg-slate-800 h-1 rounded-full mt-1.5 overflow-hidden">
                          <div
                            className="bg-rose-500 h-full rounded-full"
                            style={{ width: `${Math.min(100, (tx.rule_score ?? 0) * 100)}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Explanation */}
                    {tx.explanation && (
                      <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs text-slate-300">
                        <span className="font-semibold text-slate-200">Investigation Reason: </span>
                        {tx.explanation}
                      </div>
                    )}

                    {/* Action Bar */}
                    {isFlagged && (
                      <div className="flex items-center justify-between pt-1">
                        <span className="text-[11px] text-slate-400">
                          Status:{' '}
                          <span className="font-semibold text-amber-400">
                            {tx.investigation_status || 'Awaiting Triage'}
                          </span>
                        </span>
                        <button
                          onClick={e => {
                            e.stopPropagation()
                            onOpenCase(tx)
                          }}
                          className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm"
                        >
                          <UserCheck className="h-3.5 w-3.5" />
                          Triage & Resolve Alert
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
