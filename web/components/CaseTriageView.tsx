'use client'

import React, { useState } from 'react'
import { UserCheck, ShieldAlert, CheckCircle2, Clock, MapPin, Building, CreditCard } from 'lucide-react'
import { TransactionRecord } from './TransactionStream'

interface CaseRecord {
  case_id: string
  transaction_id: string
  card_id: string
  amount: number
  merchant: string
  location: string
  ml_score?: number | null
  behavior_score?: number | null
  rule_score?: number | null
  final_fraud_score: number
  fraud_decision: string
  explanation: string
  processing_latency_ms?: number | null
  status: 'OPEN' | 'UNDER_REVIEW' | 'RESOLVED' | string
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | string
  assigned_analyst_id?: string
  analyst_decision?: string
  analyst_notes?: string
  opened_at: string
  resolved_at?: string
}

interface CaseTriageViewProps {
  cases: CaseRecord[]
  onOpenCase: (tx: TransactionRecord) => void
}

export const CaseTriageView: React.FC<CaseTriageViewProps> = ({ cases, onOpenCase }) => {
  const [statusFilter, setStatusFilter] = useState<string>('ALL')

  const filteredCases = cases.filter(c => {
    if (statusFilter === 'ALL') return true
    return c.status === statusFilter
  })

  return (
    <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <UserCheck className="h-5 w-5 text-indigo-400" />
            Fraud Investigation Case Management
          </h2>
          <p className="text-xs text-slate-400">
            Decoupled workflow for human analyst review, ground truth confirmation, and chargeback tracking
          </p>
        </div>

        <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs">
          {['ALL', 'OPEN', 'RESOLVED'].map(st => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1 rounded font-medium transition-all ${
                statusFilter === st
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        {filteredCases.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-sm">
            No investigation cases match the selected status. Flagged suspicious and fraud incidents appear here automatically.
          </div>
        ) : (
          filteredCases.map(c => {
            const isResolved = c.status === 'RESOLVED'
            return (
              <div
                key={c.case_id}
                className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-xs font-bold text-indigo-400">{c.case_id}</span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                        c.priority === 'CRITICAL'
                          ? 'bg-red-500/10 text-red-400 border border-red-500/30'
                          : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                      }`}
                    >
                      {c.priority}
                    </span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                        isResolved
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                      }`}
                    >
                      {c.status}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-slate-300">
                    <span className="flex items-center gap-1 font-mono">
                      <CreditCard className="h-3.5 w-3.5 text-slate-500" />
                      {c.card_id}
                    </span>
                    <span className="font-mono font-bold text-white">${c.amount.toFixed(2)}</span>
                    <span className="flex items-center gap-1">
                      <Building className="h-3.5 w-3.5 text-slate-500" />
                      {c.merchant}
                    </span>
                    <span className="flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5 text-slate-500" />
                      {c.location}
                    </span>
                  </div>

                  <p className="text-xs text-slate-400 line-clamp-2">{c.explanation}</p>

                  {isResolved && (
                    <div className="text-[11px] text-emerald-400 font-semibold flex items-center gap-1 pt-1">
                      <CheckCircle2 className="h-3 w-3" />
                      Decision: {c.analyst_decision} {c.analyst_notes ? `— "${c.analyst_notes}"` : ''}
                    </div>
                  )}
                </div>

                <div className="self-end md:self-center shrink-0">
                  {!isResolved ? (
                    <button
                      onClick={() =>
                        onOpenCase({
                          transaction_id: c.transaction_id,
                          card_id: c.card_id,
                          amount: c.amount,
                          merchant: c.merchant,
                          location: c.location,
                          timestamp: c.opened_at,
                          ml_score: c.ml_score,
                          behavior_score: c.behavior_score,
                          rule_score: c.rule_score,
                          final_fraud_score: c.final_fraud_score,
                          fraud_decision: c.fraud_decision,
                          explanation: c.explanation,
                          processing_latency_ms: c.processing_latency_ms,
                          case_id: c.case_id
                        })
                      }
                      className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all"
                    >
                      <UserCheck className="h-3.5 w-3.5" />
                      Triage Case
                    </button>
                  ) : (
                    <span className="text-xs text-slate-500 font-mono">Resolved</span>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
