'use client'

import React, { useState } from 'react'
import {
  X,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  UserCheck,
  FileText,
  Clock,
  MapPin,
  Building
} from 'lucide-react'
import { TransactionRecord } from './TransactionStream'

interface CaseTriageModalProps {
  transaction: TransactionRecord | null
  onClose: () => void
  onResolve: (caseId: string, decision: string, notes: string) => Promise<void>
}

export const CaseTriageModal: React.FC<CaseTriageModalProps> = ({
  transaction,
  onClose,
  onResolve
}) => {
  const [analystNotes, setAnalystNotes] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!transaction) return null

  const caseId = transaction.case_id || `CASE_${transaction.transaction_id}`

  const handleSubmit = async (decision: 'CONFIRMED_FRAUD' | 'FALSE_POSITIVE') => {
    setIsSubmitting(true)
    try {
      await onResolve(caseId, decision, analystNotes)
      onClose()
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="glass-panel-elevated max-w-2xl w-full rounded-2xl border border-slate-700/80 p-6 shadow-2xl relative">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                Fraud Incident Triage
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {caseId}
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Independent investigation workflow separating prediction from confirmed outcome
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Transaction Summary Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 my-4">
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <span className="text-[10px] uppercase font-semibold text-slate-400">Cardholder</span>
            <div className="font-mono text-sm font-bold text-white mt-0.5">{transaction.card_id}</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <span className="text-[10px] uppercase font-semibold text-slate-400">Amount</span>
            <div className="font-mono text-sm font-bold text-white mt-0.5">${transaction.amount.toFixed(2)}</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <span className="text-[10px] uppercase font-semibold text-slate-400">Merchant</span>
            <div className="text-sm font-semibold text-slate-200 mt-0.5 truncate">
              {transaction.merchant_name || transaction.merchant || 'Unknown'}
            </div>
          </div>
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <span className="text-[10px] uppercase font-semibold text-slate-400">Composite Risk</span>
            <div className="font-mono text-sm font-bold text-red-400 mt-0.5">
              {(transaction.final_fraud_score * 100).toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Scoring Evidence */}
        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2 mb-4">
          <h4 className="text-xs font-bold uppercase text-slate-300 flex items-center gap-1.5">
            <FileText className="h-3.5 w-3.5 text-indigo-400" />
            Detection Evidence & Explanation
          </h4>
          <p className="text-xs text-slate-300 leading-relaxed">
            {transaction.explanation || 'Composite anomalous risk score across machine learning and rules engine.'}
          </p>

          <div className="flex items-center gap-4 text-[11px] text-slate-400 pt-1 font-mono">
            <span>ML: {typeof transaction.ml_score === 'number' ? `${(transaction.ml_score * 100).toFixed(0)}%` : '—'}</span>
            <span>Behavior: {typeof transaction.behavior_score === 'number' ? `${(transaction.behavior_score * 100).toFixed(0)}%` : '—'}</span>
            <span>Rules: {typeof transaction.rule_score === 'number' ? `${(transaction.rule_score * 100).toFixed(0)}%` : '—'}</span>
          </div>
        </div>

        {/* Analyst Notes Input */}
        <div className="space-y-1.5 mb-5">
          <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
            <UserCheck className="h-3.5 w-3.5 text-slate-400" />
            Investigator Findings & Resolution Notes
          </label>
          <textarea
            rows={3}
            value={analystNotes}
            onChange={e => setAnalystNotes(e.target.value)}
            placeholder="Document customer contact, cardholder confirmation, device verification, or false alarm rationale..."
            className="w-full rounded-xl bg-slate-900 border border-slate-700/80 px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-all resize-none"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
          <button
            disabled={isSubmitting}
            onClick={() => handleSubmit('FALSE_POSITIVE')}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-emerald-500/20 text-xs font-semibold flex items-center gap-2 transition-all"
          >
            <ShieldCheck className="h-4 w-4" />
            Dismiss False Positive
          </button>

          <button
            disabled={isSubmitting}
            onClick={() => handleSubmit('CONFIRMED_FRAUD')}
            className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-semibold flex items-center gap-2 transition-all shadow-glow-fraud"
          >
            <ShieldAlert className="h-4 w-4" />
            Confirm Fraud Policy Outcome
          </button>
        </div>
      </div>
    </div>
  )
}
