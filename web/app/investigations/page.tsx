'use client'

import React, { useState, useEffect, useCallback, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  UserCheck,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  Clock,
  AlertTriangle,
  X,
  Send,
  Filter,
  Search,
  MessageSquare,
  FileText,
  BadgeAlert
} from 'lucide-react'
import { AppShell } from '../../components/AppShell'
import { useAuth } from '../../lib/AuthContext'
import { api } from '../../lib/api'

interface CaseRecord {
  case_id: string
  transaction_id: string
  card_id: string
  masked_card_id?: string
  amount: number
  merchant: string
  location: string
  final_fraud_score?: number
  ml_score?: number
  behavior_score?: number
  rule_score?: number
  fraud_decision?: string
  explanation?: string
  status: 'OPEN' | 'UNDER_REVIEW' | 'RESOLVED' | string
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | string
  assigned_analyst_id?: string
  analyst_decision?: string
  analyst_notes?: string
  opened_at: string
  resolved_at?: string
}

function InvestigationsContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const caseIdParam = searchParams.get('case_id')

  const { currentUser, authToken } = useAuth()
  const [cases, setCases] = useState<CaseRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'OPEN' | 'UNDER_REVIEW' | 'RESOLVED'>('ALL')
  const [selectedCase, setSelectedCase] = useState<CaseRecord | null>(null)
  const [resolutionDecision, setResolutionDecision] = useState<'CONFIRMED_FRAUD' | 'FALSE_POSITIVE'>('CONFIRMED_FRAUD')
  const [resolutionNotes, setResolutionNotes] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  const fetchCases = useCallback(async () => {
    try {
      const data = await api.get('/api/v1/cases?limit=100')
      if (Array.isArray(data)) {
        setCases(data)
      }
    } catch (err) {
      console.warn('Failed to fetch cases:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCases()
    const interval = setInterval(fetchCases, 4000)
    return () => clearInterval(interval)
  }, [fetchCases])

  // Synchronize modal state with URL query parameter for direct navigation and refresh persistence
  useEffect(() => {
    if (!caseIdParam) {
      setSelectedCase(null)
      return
    }

    if (selectedCase?.case_id === caseIdParam) {
      return
    }

    const localMatch = cases.find(c => c.case_id === caseIdParam)
    if (localMatch) {
      setSelectedCase(localMatch)
    } else {
      api.get(`/api/v1/cases/${encodeURIComponent(caseIdParam)}`)
        .then(data => {
          if (data && data.case_id) {
            setSelectedCase(data)
          }
        })
        .catch(err => {
          console.warn('Failed to load specific case:', err)
        })
    }
  }, [caseIdParam, cases, selectedCase?.case_id])

  const handleSelectCase = (c: CaseRecord) => {
    setSelectedCase(c)
    router.replace(`/investigations?case_id=${encodeURIComponent(c.case_id)}`, { scroll: false })
  }

  const handleCloseCase = () => {
    setSelectedCase(null)
    router.replace('/investigations', { scroll: false })
  }

  const handleResolveCase = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedCase) return

    setIsSubmitting(true)
    setActionSuccess(null)

    try {
      await api.patch(`/api/v1/cases/${selectedCase.case_id}`, {
        analyst_id: currentUser?.email || 'analyst.sarah@sentinel.ai',
        decision: resolutionDecision,
        notes: resolutionNotes || `Case investigated and resolved by ${currentUser?.name || 'Analyst'}`,
        status: 'RESOLVED'
      })

      setActionSuccess(`Case ${selectedCase.case_id.slice(0, 8)} successfully resolved as ${resolutionDecision}!`)
      handleCloseCase()
      setResolutionNotes('')
      await fetchCases()
    } catch (err: any) {
      alert(`Resolution failed: ${err.message || 'Authorization error'}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  const filteredCases = cases.filter(c => {
    if (statusFilter === 'ALL') return true
    return c.status === statusFilter
  })

  const openCasesCount = cases.filter(c => c.status === 'OPEN').length
  const resolvedCasesCount = cases.filter(c => c.status === 'RESOLVED').length

  const getPriorityBadge = (p: string) => {
    switch (p) {
      case 'CRITICAL':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'HIGH':
        return 'bg-amber-100 text-amber-800 border-amber-300'
      case 'MEDIUM':
      default:
        return 'bg-blue-100 text-blue-800 border-blue-300'
    }
  }

  return (
    <AppShell
      title="Fraud Investigation Workspace"
      subtitle="Analyst Triage Queue, Evidence Inspection & Ground Truth Resolution"
    >
      {/* Overview Triage Metric Tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-surface p-4 rounded-xl border border-surface-border shadow-card">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-ink-muted">Awaiting Triage</span>
            <AlertTriangle className="h-4 w-4 text-amber-500" />
          </div>
          <span className="text-2xl font-black text-ink tabular-nums">{openCasesCount}</span>
          <p className="text-[11px] text-ink-muted mt-1">Pending human verification</p>
        </div>

        <div className="bg-surface p-4 rounded-xl border border-surface-border shadow-card">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-ink-muted">Resolved Cases</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          </div>
          <span className="text-2xl font-black text-emerald-600 tabular-nums">{resolvedCasesCount}</span>
          <p className="text-[11px] text-ink-muted mt-1">Ground truth finalized</p>
        </div>

        <div className="bg-surface p-4 rounded-xl border border-surface-border shadow-card">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-ink-muted">Total Audit Cases</span>
            <FileText className="h-4 w-4 text-brand-600" />
          </div>
          <span className="text-2xl font-black text-ink tabular-nums">{cases.length}</span>
          <p className="text-[11px] text-ink-muted mt-1">Immutable forensic tracking</p>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            <span>{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-emerald-700 hover:text-emerald-900 font-bold">
            &times;
          </button>
        </div>
      )}

      {/* Case Filter Tabs */}
      <div className="flex items-center justify-between border-b border-surface-border pb-2">
        <div className="flex gap-2">
          {(['ALL', 'OPEN', 'UNDER_REVIEW', 'RESOLVED'] as const).map(st => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                statusFilter === st
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'bg-surface text-ink-muted hover:text-ink hover:bg-surface-subtle border border-surface-border'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
        <span className="text-xs text-ink-muted font-medium">
          Showing {filteredCases.length} of {cases.length} cases
        </span>
      </div>

      {/* Cases Table */}
      <div className="bg-surface rounded-xl border border-surface-border shadow-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-surface-border bg-canvas text-ink-muted uppercase font-semibold text-[10px] tracking-wider">
                <th className="py-3 px-4">Case ID</th>
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4">Cardholder Token</th>
                <th className="py-3 px-4">Merchant & Incident Context</th>
                <th className="py-3 px-4 text-right">Amount</th>
                <th className="py-3 px-4 text-center">Fraud Score</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {filteredCases.map(c => (
                <tr
                  key={c.case_id}
                  onClick={() => handleSelectCase(c)}
                  className="hover:bg-surface-subtle cursor-pointer transition-colors"
                >
                  <td className="py-3 px-4 font-mono font-medium text-brand-600">
                    {c.case_id}
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${getPriorityBadge(c.priority)}`}>
                      {c.priority}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-mono text-ink-secondary">{c.masked_card_id || c.card_id}</td>
                  <td className="py-3 px-4">
                    <div className="font-semibold text-ink">{c.merchant || 'Retail'}</div>
                    <div className="text-[10px] text-ink-muted truncate max-w-xs">{c.explanation || 'Anomalous transaction alert.'}</div>
                  </td>
                  <td className="py-3 px-4 text-right font-mono font-bold tabular-nums text-ink text-sm">
                    ${typeof c.amount === 'number' ? c.amount.toFixed(2) : 'Unavailable'}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className="font-mono font-bold text-xs text-red-600 tabular-nums">
                      {typeof c.final_fraud_score === 'number'
                        ? `${(c.final_fraud_score * 100).toFixed(0)}%`
                        : 'Unavailable'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${
                        c.status === 'OPEN'
                          ? 'bg-amber-50 text-amber-700 border-amber-200'
                          : c.status === 'RESOLVED'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-blue-50 text-blue-700 border-blue-200'
                      }`}
                    >
                      {c.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleSelectCase(c)
                      }}
                      className="px-2.5 py-1 rounded bg-brand-50 hover:bg-brand-100 text-brand-700 border border-brand-200 font-semibold text-xs transition-colors"
                    >
                      {c.status === 'OPEN' ? 'Review & Resolve' : 'Details'}
                    </button>
                  </td>
                </tr>
              ))}
              {filteredCases.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-ink-muted">
                    {isLoading ? 'Loading cases...' : 'No cases match the selected status filter.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Case Resolution Modal */}
      {selectedCase && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface rounded-2xl shadow-2xl border border-surface-border max-w-xl w-full p-6">
            <div className="flex items-center justify-between pb-3 border-b border-surface-border mb-4">
              <div>
                <h3 className="text-base font-bold text-ink">Investigate Fraud Case</h3>
                <p className="text-xs text-ink-muted font-mono">{selectedCase.case_id}</p>
              </div>
              <button onClick={handleCloseCase} className="p-1 rounded text-ink-muted hover:text-ink">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4 mb-5 text-xs">
              <div className="grid grid-cols-2 gap-3 p-3 bg-canvas rounded-xl border border-surface-border">
                <div>
                  <span className="text-ink-muted block text-[11px]">Merchant</span>
                  <strong className="text-ink text-sm">{selectedCase.merchant || 'Unavailable'}</strong>
                </div>
                <div>
                  <span className="text-ink-muted block text-[11px]">Amount</span>
                  <strong className="text-ink text-sm font-mono">
                    {typeof selectedCase.amount === 'number' ? `$${selectedCase.amount.toFixed(2)}` : 'Unavailable'}
                  </strong>
                </div>
                <div>
                  <span className="text-ink-muted block text-[11px]">Card ID</span>
                  <span className="font-mono text-ink">{selectedCase.masked_card_id || selectedCase.card_id || 'Unavailable'}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[11px]">Fraud Score</span>
                  <span className="font-mono font-bold text-red-600">
                    {typeof selectedCase.final_fraud_score === 'number'
                      ? `${(selectedCase.final_fraud_score * 100).toFixed(1)}%`
                      : 'Unavailable'}
                  </span>
                </div>
              </div>

              <div>
                <span className="text-ink-muted block font-semibold mb-1">Incident Explanation</span>
                <p className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-800 text-[11px]">
                  {selectedCase.explanation || 'Composite anomalous risk alert generated by detection engine.'}
                </p>
              </div>

              {selectedCase.status === 'RESOLVED' ? (
                <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200">
                  <span className="text-emerald-800 font-bold block mb-1">Resolved Details</span>
                  <p className="text-emerald-700">Decision: <strong>{selectedCase.analyst_decision}</strong></p>
                  <p className="text-emerald-700 mt-1">Notes: {selectedCase.analyst_notes || 'No notes provided.'}</p>
                </div>
              ) : (
                <form onSubmit={handleResolveCase} className="space-y-4 pt-2">
                  <div>
                    <label className="block font-semibold text-ink mb-1.5">
                      Analyst Ground Truth Decision
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        type="button"
                        onClick={() => setResolutionDecision('CONFIRMED_FRAUD')}
                        className={`p-2.5 rounded-xl border text-xs font-bold transition-all ${
                          resolutionDecision === 'CONFIRMED_FRAUD'
                            ? 'bg-red-50 border-red-500 text-red-700 ring-2 ring-red-500/20 shadow-sm'
                            : 'border-surface-border text-ink-muted hover:bg-surface-subtle'
                        }`}
                      >
                        Confirm Fraud (Ground Truth)
                      </button>
                      <button
                        type="button"
                        onClick={() => setResolutionDecision('FALSE_POSITIVE')}
                        className={`p-2.5 rounded-xl border text-xs font-bold transition-all ${
                          resolutionDecision === 'FALSE_POSITIVE'
                            ? 'bg-emerald-50 border-emerald-500 text-emerald-700 ring-2 ring-emerald-500/20 shadow-sm'
                            : 'border-surface-border text-ink-muted hover:bg-surface-subtle'
                        }`}
                      >
                        False Positive (Legitimate)
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block font-semibold text-ink mb-1">
                      Investigation Notes / Evidence Audit Trail
                    </label>
                    <textarea
                      rows={2}
                      value={resolutionNotes}
                      onChange={e => setResolutionNotes(e.target.value)}
                      placeholder="Document merchant inquiry, customer callback, travel ticket verification..."
                      className="w-full p-2.5 bg-canvas border border-surface-border-strong rounded-xl text-ink text-xs focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                    />
                  </div>

                  <div className="flex gap-2 pt-2">
                    <button
                      type="button"
                      onClick={handleCloseCase}
                      className="flex-1 py-2 px-3 border border-surface-border rounded-xl text-xs font-semibold text-ink-secondary hover:bg-surface-subtle"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="flex-1 py-2 px-3 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
                    >
                      {isSubmitting ? 'Recording Outcome...' : 'Submit Resolution'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </AppShell>
  )
}

export default function InvestigationsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-ink-muted">Loading Investigation Workspace...</div>}>
      <InvestigationsContent />
    </Suspense>
  )
}
