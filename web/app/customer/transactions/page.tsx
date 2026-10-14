'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  History,
  Search,
  Filter,
  Download,
  FileWarning,
  CreditCard,
  MapPin,
  Clock,
  X,
  ChevronRight,
  ShieldCheck,
  CheckCircle2
} from 'lucide-react'
import { AppShell } from '../../../components/AppShell'
import { useAuth } from '../../../lib/AuthContext'
import { api } from '../../../lib/api'

export default function CustomerTransactionsPage() {
  const { currentUser, authToken } = useAuth()
  const [transactions, setTransactions] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedTx, setSelectedTx] = useState<any | null>(null)

  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        const data = await api.get('/api/v1/customer/transactions?limit=50')
        setTransactions(data.transactions || (Array.isArray(data) ? data : []))
      } catch (err) {
        console.warn('Customer transactions fetch error:', err)
      } finally {
        setIsLoading(false)
      }
    }

    fetchTransactions()
  }, [authToken])

  const filtered = transactions.filter(t => {
    if (!searchTerm.trim()) return true
    const term = searchTerm.toLowerCase()
    const m = (t.merchant_name || t.merchant || '').toLowerCase()
    const id = (t.transaction_id || '').toLowerCase()
    return m.includes(term) || id.includes(term)
  })

  return (
    <AppShell
      title="Authorized Transaction History"
      subtitle="Personal Cardholder Statement & Detailed Receipt Breakdown"
    >
      {/* Search and Metadata Bar */}
      <div className="bg-surface p-4 rounded-xl border border-surface-border shadow-card flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative flex-1 w-full sm:max-w-md">
          <Search className="h-4 w-4 absolute left-3 top-2.5 text-ink-muted" />
          <input
            type="text"
            placeholder="Search by merchant, transaction reference..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-canvas border border-surface-border-strong rounded-lg text-xs text-ink placeholder-ink-subtle focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <div className="flex items-center gap-2 text-xs text-ink-muted">
          <span>Card: <strong className="font-mono text-ink">CARD_***_007</strong></span>
          <span className="text-surface-border-strong">|</span>
          <span>{filtered.length} transactions</span>
        </div>
      </div>

      {/* History Table */}
      <div className="bg-surface rounded-xl border border-surface-border shadow-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-canvas border-b border-surface-border text-ink-muted uppercase font-semibold text-[10px]">
              <tr>
                <th className="py-3 px-4">Transaction Reference</th>
                <th className="py-3 px-4">Merchant & Location</th>
                <th className="py-3 px-4">Channel</th>
                <th className="py-3 px-4 text-right">Amount</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {filtered.map((t, idx) => (
                <tr
                  key={idx}
                  onClick={() => setSelectedTx(t)}
                  className="hover:bg-surface-subtle cursor-pointer transition-colors"
                >
                  <td className="py-3 px-4 font-mono font-medium text-brand-600">
                    {(t.transaction_id || `TXN_${idx}`).slice(0, 12)}...
                  </td>
                  <td className="py-3 px-4">
                    <div className="font-semibold text-ink">{t.merchant_name || t.merchant || 'Merchant Retail'}</div>
                    <div className="text-[10px] text-ink-muted">{t.city || t.location || 'New York, US'}</div>
                  </td>
                  <td className="py-3 px-4 text-ink-muted text-[11px]">
                    {t.channel || 'ONLINE_ECOMMERCE'}
                  </td>
                  <td className="py-3 px-4 text-right font-mono font-bold tabular-nums text-ink text-sm">
                    ${(t.amount || 0).toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      SETTLED
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className="text-brand-600 font-semibold text-xs flex items-center justify-end gap-1">
                      <span>Receipt</span>
                      <ChevronRight className="h-3.5 w-3.5" />
                    </span>
                  </td>
                </tr>
              ))}

              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-10 text-ink-muted">
                    {isLoading ? 'Retrieving card records...' : 'No transactions found.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Slide-Over Receipt Drawer */}
      {selectedTx && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-black/40 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-md bg-surface shadow-2xl border-l border-surface-border p-6 flex flex-col justify-between overflow-y-auto">
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-surface-border mb-5">
                <div>
                  <h3 className="text-base font-bold text-ink">Transaction Receipt</h3>
                  <p className="text-xs text-ink-muted font-mono">{selectedTx.transaction_id || 'TXN_DETAIL'}</p>
                </div>
                <button
                  onClick={() => setSelectedTx(null)}
                  className="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-surface-subtle"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="p-4 rounded-xl bg-canvas border border-surface-border text-center mb-5">
                <span className="text-xs text-ink-muted uppercase font-semibold">Total Charged</span>
                <p className="text-3xl font-black font-mono text-ink mt-1 tabular-nums">
                  ${(selectedTx.amount || 0).toFixed(2)}
                </p>
                <span className="inline-block mt-2 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Authorized & Verified
                </span>
              </div>

              <div className="space-y-3 text-xs">
                <div className="flex justify-between py-1.5 border-b border-surface-border">
                  <span className="text-ink-muted">Merchant:</span>
                  <span className="font-semibold text-ink">{selectedTx.merchant_name || selectedTx.merchant}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-surface-border">
                  <span className="text-ink-muted">Card:</span>
                  <span className="font-mono text-ink">CARD_***_007</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-surface-border">
                  <span className="text-ink-muted">Payment Channel:</span>
                  <span className="text-ink">{selectedTx.channel || 'ONLINE_ECOMMERCE'}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-surface-border">
                  <span className="text-ink-muted">City / Region:</span>
                  <span className="text-ink">{selectedTx.city || selectedTx.location || 'New York, US'}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-surface-border">
                  <span className="text-ink-muted">Timestamp:</span>
                  <span className="font-mono text-ink">{selectedTx.timestamp || 'Recorded'}</span>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-surface-border mt-6 space-y-2">
              <Link
                href={`/customer/report?tx=${selectedTx.transaction_id || ''}&amount=${selectedTx.amount || ''}&merchant=${encodeURIComponent(selectedTx.merchant_name || selectedTx.merchant || '')}`}
                className="w-full py-2.5 px-4 rounded-lg bg-red-50 hover:bg-red-100 text-red-700 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors border border-red-200"
              >
                <FileWarning className="h-4 w-4" />
                <span>Dispute / Report as Fraudulent</span>
              </Link>
              <button
                onClick={() => setSelectedTx(null)}
                className="w-full py-2 px-4 rounded-lg border border-surface-border text-xs font-semibold text-ink-muted hover:bg-surface-subtle"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  )
}
