'use client'

import React, { useState, useEffect, useCallback, useMemo, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  CreditCard,
  Search,
  Filter,
  ArrowUpDown,
  Download,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  Clock,
  X,
  MapPin,
  Building,
  Activity,
  Layers,
  ChevronRight
} from 'lucide-react'
import { AppShell } from '../../components/AppShell'
import { TransactionRecord } from '../../components/TransactionStream'
import { api } from '../../lib/api'

function TransactionExplorerContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const inspectId = searchParams.get('inspect')

  const [transactions, setTransactions] = useState<TransactionRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'LEGITIMATE' | 'SUSPICIOUS' | 'FRAUD'>('ALL')
  const [minAmount, setMinAmount] = useState<number>(0)
  const [selectedTx, setSelectedTx] = useState<TransactionRecord | null>(null)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)

  const fetchTransactions = useCallback(async () => {
    try {
      const data = await api.get('/api/v1/transactions/recent?limit=100')
      if (Array.isArray(data)) {
        setTransactions(data)
      }
    } catch (err) {
      console.warn('Failed to fetch transactions:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTransactions()
    const interval = setInterval(fetchTransactions, 4000)
    return () => clearInterval(interval)
  }, [fetchTransactions])

  // Synchronize inspection drawer with URL query param for direct navigation and refresh persistence
  useEffect(() => {
    if (!inspectId) {
      setSelectedTx(null)
      return
    }

    if (selectedTx?.transaction_id === inspectId) {
      return
    }

    const localMatch = transactions.find(t => t.transaction_id === inspectId)
    if (localMatch) {
      setSelectedTx(localMatch)
    } else {
      setIsLoadingDetail(true)
      api.get(`/api/v1/transactions/${encodeURIComponent(inspectId)}`)
        .then(data => {
          if (data && data.transaction_id) {
            setSelectedTx(data)
          }
        })
        .catch(err => {
          console.warn('Failed to load transaction detail:', err)
        })
        .finally(() => {
          setIsLoadingDetail(false)
        })
    }
  }, [inspectId, transactions, selectedTx?.transaction_id])

  const handleInspect = (tx: TransactionRecord) => {
    setSelectedTx(tx)
    router.replace(`/transactions?inspect=${encodeURIComponent(tx.transaction_id)}`, { scroll: false })
  }

  const handleCloseInspect = () => {
    setSelectedTx(null)
    router.replace('/transactions', { scroll: false })
  }

  const filteredTransactions = useMemo(() => {
    return transactions.filter(tx => {
      // 1. Status Filter
      if (statusFilter !== 'ALL' && tx.fraud_decision !== statusFilter) {
        return false
      }
      // 2. Amount Filter
      if (minAmount > 0 && tx.amount < minAmount) {
        return false
      }
      // 3. Search Filter
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase()
        const idMatch = tx.transaction_id.toLowerCase().includes(term)
        const cardMatch = (tx.masked_card_id || tx.card_id || '').toLowerCase().includes(term)
        const merchantMatch = (tx.merchant_name || tx.merchant || '').toLowerCase().includes(term)
        const locationMatch = (tx.city || tx.location || '').toLowerCase().includes(term)
        return idMatch || cardMatch || merchantMatch || locationMatch
      }
      return true
    })
  }, [transactions, statusFilter, minAmount, searchTerm])

  const getStatusBadge = (decision?: string) => {
    switch (decision) {
      case 'FRAUD':
        return 'bg-red-50 text-red-700 border-red-200'
      case 'SUSPICIOUS':
        return 'bg-amber-50 text-amber-700 border-amber-200'
      case 'LEGITIMATE':
      default:
        return 'bg-emerald-50 text-emerald-700 border-emerald-200'
    }
  }

  return (
    <AppShell
      title="Transaction Explorer"
      subtitle="Comprehensive Real-Time Inspection & Audit Trail"
      actions={
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              const headers = ['Transaction ID', 'Card ID', 'Amount', 'Merchant', 'Decision', 'Score', 'Timestamp']
              const rows = filteredTransactions.map(t => [
                t.transaction_id,
                t.masked_card_id || t.card_id,
                t.amount,
                t.merchant_name || t.merchant || '',
                t.fraud_decision,
                t.final_fraud_score,
                t.timestamp
              ])
              const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n')
              const encodedUri = encodeURI(csvContent)
              const link = document.createElement('a')
              link.setAttribute('href', encodedUri)
              link.setAttribute('download', `sentinel_transactions_${Date.now()}.csv`)
              document.body.appendChild(link)
              link.click()
              document.body.removeChild(link)
            }}
            className="px-3 py-1.5 rounded-lg border border-surface-border-strong text-xs font-semibold text-ink-secondary hover:bg-surface-subtle transition-all flex items-center gap-1.5"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      }
    >
      {/* Search & Filter Bar */}
      <div className="bg-surface p-4 rounded-xl border border-surface-border shadow-card space-y-3">
        <div className="flex flex-col md:flex-row items-center gap-3">
          {/* Search Input */}
          <div className="relative flex-1 w-full">
            <Search className="h-4 w-4 absolute left-3 top-2.5 text-ink-muted" />
            <input
              type="text"
              placeholder="Search by Transaction ID, Card (e.g. CARD_007), Merchant, or City..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-canvas border border-surface-border-strong rounded-lg text-xs text-ink placeholder-ink-subtle focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
          </div>

          {/* Decision Status Filters */}
          <div className="flex items-center gap-1 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
            {(['ALL', 'FRAUD', 'SUSPICIOUS', 'LEGITIMATE'] as const).map(st => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                  statusFilter === st
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'bg-surface-subtle text-ink-secondary hover:bg-surface-border'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          {/* Minimum Amount Threshold Filter */}
          <div className="flex items-center gap-2 w-full md:w-auto">
            <span className="text-xs text-ink-muted whitespace-nowrap font-medium">Min $:</span>
            <input
              type="number"
              min="0"
              placeholder="0"
              value={minAmount || ''}
              onChange={e => setMinAmount(Number(e.target.value) || 0)}
              className="w-24 px-2.5 py-1.5 bg-canvas border border-surface-border-strong rounded-lg text-xs text-ink font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>

        {/* Filter Counters */}
        <div className="flex items-center justify-between text-xs text-ink-muted pt-1 border-t border-surface-border">
          <span>
            Showing <strong className="text-ink">{filteredTransactions.length}</strong> of{' '}
            <strong className="text-ink">{transactions.length}</strong> loaded stream events
          </span>
          <span className="text-[11px]">Auto-refreshes every 4s from persistent engine</span>
        </div>
      </div>

      {/* Transactions Data Table */}
      <div className="bg-surface rounded-xl border border-surface-border shadow-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-surface-border bg-canvas text-ink-muted uppercase font-semibold text-[10px] tracking-wider">
                <th className="py-3 px-4">Transaction ID</th>
                <th className="py-3 px-4">Cardholder Token</th>
                <th className="py-3 px-4">Merchant & Location</th>
                <th className="py-3 px-4 text-right">Amount</th>
                <th className="py-3 px-4 text-center">Composite Score</th>
                <th className="py-3 px-4 text-center">Decision</th>
                <th className="py-3 px-4 text-center">Latency</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {filteredTransactions.map(tx => (
                <tr
                  key={tx.transaction_id}
                  onClick={() => handleInspect(tx)}
                  className="hover:bg-surface-subtle/50 transition-colors cursor-pointer"
                >
                  <td className="py-3 px-4 font-mono font-medium text-brand-600">
                    {tx.transaction_id}
                  </td>
                  <td className="py-3 px-4 font-mono text-ink-secondary">
                    {tx.masked_card_id || tx.card_id}
                  </td>
                  <td className="py-3 px-4">
                    <div className="font-semibold text-ink">{tx.merchant_name || tx.merchant || 'Retail'}</div>
                    <div className="text-[10px] text-ink-muted flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      <span>{tx.city || tx.location || 'Unknown location'}</span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-right font-mono font-bold tabular-nums text-ink text-sm">
                    ${typeof tx.amount === 'number' ? tx.amount.toFixed(2) : '0.00'}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <div className="flex items-center justify-center gap-1.5 font-mono text-xs">
                      <span
                        className={`font-bold tabular-nums ${
                          typeof tx.final_fraud_score === 'number' && tx.final_fraud_score >= 0.7
                            ? 'text-red-600'
                            : typeof tx.final_fraud_score === 'number' && tx.final_fraud_score >= 0.4
                            ? 'text-amber-600'
                            : 'text-emerald-600'
                        }`}
                      >
                        {typeof tx.final_fraud_score === 'number'
                          ? `${(tx.final_fraud_score * 100).toFixed(0)}%`
                          : '—'}
                      </span>
                    </div>
                    <span className="text-[10px] text-ink-muted font-mono block">
                      ML: {typeof tx.ml_score === 'number' ? `${(tx.ml_score * 100).toFixed(0)}%` : '—'} · Rule: {typeof tx.rule_score === 'number' ? `${(tx.rule_score * 100).toFixed(0)}%` : '—'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${getStatusBadge(
                        tx.fraud_decision
                      )}`}
                    >
                      {tx.fraud_decision || 'LEGITIMATE'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center font-mono text-[11px] text-ink-muted">
                    {typeof tx.processing_latency_ms === 'number' ? `${tx.processing_latency_ms.toFixed(1)} ms` : '—'}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleInspect(tx)
                      }}
                      className="text-brand-600 hover:text-brand-700 font-semibold text-xs flex items-center gap-0.5 ml-auto"
                    >
                      <span>Inspect</span>
                      <ChevronRight className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))}

              {filteredTransactions.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-ink-muted">
                    {isLoading
                      ? 'Loading live transactions from API...'
                      : 'No transactions match the selected filters.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Transaction Inspection Slide-Over Drawer */}
      {selectedTx && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-black/40 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-lg bg-surface shadow-2xl border-l border-surface-border p-6 flex flex-col justify-between overflow-y-auto">
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-surface-border mb-5">
                <div>
                  <h3 className="text-base font-bold text-ink">Transaction Evidence Detail</h3>
                  <p className="text-xs text-ink-muted font-mono">{selectedTx.transaction_id}</p>
                </div>
                <button
                  onClick={handleCloseInspect}
                  className="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-surface-subtle"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Amount & Status Hero Card */}
              <div className="p-4 rounded-xl bg-canvas border border-surface-border mb-5 flex items-center justify-between">
                <div>
                  <span className="text-xs text-ink-muted block">Transaction Amount</span>
                  <span className="text-2xl font-black font-mono tabular-nums text-ink">
                    ${typeof selectedTx.amount === 'number' ? selectedTx.amount.toFixed(2) : '0.00'}
                  </span>
                </div>
                <div className="text-right">
                  <span
                    className={`inline-block px-3 py-1 rounded-full text-xs font-bold uppercase border ${getStatusBadge(
                      selectedTx.fraud_decision
                    )}`}
                  >
                    {selectedTx.fraud_decision || 'LEGITIMATE'}
                  </span>
                  <span className="text-xs text-ink-muted block mt-1 font-mono">
                    Score:{' '}
                    {typeof selectedTx.final_fraud_score === 'number'
                      ? `${(selectedTx.final_fraud_score * 100).toFixed(1)}%`
                      : 'Unavailable'}
                  </span>
                </div>
              </div>

              {/* Hybrid Score Decomposition */}
              <div className="space-y-3 mb-5">
                <h4 className="text-xs font-bold text-ink-muted uppercase tracking-wider">
                  Hybrid Score Breakdown
                </h4>
                <div className="grid grid-cols-3 gap-2">
                  <div className="p-3 rounded-lg border border-surface-border bg-surface text-center">
                    <span className="text-[10px] text-ink-muted block">ML Component</span>
                    <span className="font-mono font-bold text-sm text-ink tabular-nums">
                      {typeof selectedTx.ml_score === 'number' ? `${(selectedTx.ml_score * 100).toFixed(0)}%` : 'Unavailable'}
                    </span>
                    <span className="text-[10px] text-ink-muted block">Weight 50%</span>
                  </div>
                  <div className="p-3 rounded-lg border border-surface-border bg-surface text-center">
                    <span className="text-[10px] text-ink-muted block">Rule Engine</span>
                    <span className="font-mono font-bold text-sm text-ink tabular-nums">
                      {typeof selectedTx.rule_score === 'number' ? `${(selectedTx.rule_score * 100).toFixed(0)}%` : 'Unavailable'}
                    </span>
                    <span className="text-[10px] text-ink-muted block">Weight 30%</span>
                  </div>
                  <div className="p-3 rounded-lg border border-surface-border bg-surface text-center">
                    <span className="text-[10px] text-ink-muted block">Behavioral</span>
                    <span className="font-mono font-bold text-sm text-ink tabular-nums">
                      {typeof selectedTx.behavior_score === 'number' ? `${(selectedTx.behavior_score * 100).toFixed(0)}%` : 'Unavailable'}
                    </span>
                    <span className="text-[10px] text-ink-muted block">Weight 20%</span>
                  </div>
                </div>
              </div>

              {/* Detection Explanation */}
              <div className="space-y-1.5 mb-5">
                <h4 className="text-xs font-bold text-ink-muted uppercase tracking-wider">
                  Detection Evidence & Explanation
                </h4>
                <p className="p-3 rounded-xl bg-surface-subtle border border-surface-border text-xs text-ink leading-relaxed">
                  {selectedTx.explanation || 'Composite scoring evidence derived from machine learning classification, customer profile divergence, and deterministic logic.'}
                </p>
              </div>

              {/* Transaction Metadata */}
              <div className="space-y-3 mb-5">
                <h4 className="text-xs font-bold text-ink-muted uppercase tracking-wider">
                  Payment Details
                </h4>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1.5 border-b border-surface-border">
                    <span className="text-ink-muted">Card Identifier:</span>
                    <span className="font-mono font-bold text-ink">{selectedTx.masked_card_id || selectedTx.card_id || 'Unavailable'}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-surface-border">
                    <span className="text-ink-muted">Merchant:</span>
                    <span className="font-medium text-ink">{selectedTx.merchant_name || selectedTx.merchant || 'Unavailable'}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-surface-border">
                    <span className="text-ink-muted">Location / Origin:</span>
                    <span className="font-medium text-ink">{selectedTx.city || selectedTx.location || 'Unavailable'}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-surface-border">
                    <span className="text-ink-muted">Timestamp:</span>
                    <span className="font-mono text-ink">{selectedTx.timestamp || 'Unavailable'}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-surface-border">
                    <span className="text-ink-muted">Inference Latency:</span>
                    <span className="font-mono text-ink">
                      {typeof selectedTx.processing_latency_ms === 'number' ? `${selectedTx.processing_latency_ms.toFixed(1)} ms` : 'Unavailable'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Triggered Rules */}
              {selectedTx.triggered_rules && selectedTx.triggered_rules.length > 0 && (
                <div className="p-3 rounded-lg bg-red-50 border border-red-200">
                  <h4 className="text-xs font-bold text-red-800 mb-1 flex items-center gap-1.5">
                    <AlertTriangle className="h-4 w-4" />
                    Triggered Deterministic Rules
                  </h4>
                  <ul className="list-disc list-inside text-xs text-red-700 space-y-0.5">
                    {selectedTx.triggered_rules.map((rule, idx) => (
                      <li key={idx} className="font-mono text-[11px]">{rule}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-surface-border mt-4">
              <button
                onClick={handleCloseInspect}
                className="w-full py-2.5 px-4 rounded-lg bg-surface-subtle hover:bg-surface-border text-ink-secondary text-xs font-semibold transition-colors border border-surface-border"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  )
}

export default function TransactionExplorerPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-ink-muted">Loading Transaction Explorer...</div>}>
      <TransactionExplorerContent />
    </Suspense>
  )
}
