'use client'

import React, { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import {
  FileWarning,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  Send,
  Lock,
  PhoneCall,
  ArrowLeft
} from 'lucide-react'
import { AppShell } from '../../../components/AppShell'
import { useAuth } from '../../../lib/AuthContext'
import { api, ApiError } from '../../../lib/api'

function ReportSuspiciousContent() {
  const searchParams = useSearchParams()
  const { currentUser } = useAuth()

  const prefillTx = searchParams.get('tx') || ''
  const prefillAmount = searchParams.get('amount') || ''
  const prefillMerchant = searchParams.get('merchant') || ''

  const [transactionRef, setTransactionRef] = useState(prefillTx)
  const [merchantName, setMerchantName] = useState(prefillMerchant)
  const [chargeAmount, setChargeAmount] = useState(prefillAmount)
  const [disputeReason, setDisputeReason] = useState('UNRECOGNIZED_TRANSACTION')
  const [notes, setNotes] = useState('')
  const [freezeCard, setFreezeCard] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [submittedTicket, setSubmittedTicket] = useState<any | null>(null)
  const [tickets, setTickets] = useState<any[]>([])

  const loadTickets = async () => {
    try {
      const data = await api.get('/api/v1/customer/disputes')
      if (Array.isArray(data)) {
        setTickets(data.map((d: any) => ({
          ticketId: d.ticket_id || d.case_id,
          transactionId: d.transaction_id,
          merchant: d.merchant || 'Reported Charge',
          amount: typeof d.amount === 'number' ? `$${d.amount.toFixed(2)}` : (d.amount || '$0.00'),
          reason: d.analyst_notes || 'Customer dispute',
          status: d.status || 'OPEN',
          openedAt: d.opened_at ? new Date(d.opened_at).toLocaleDateString() : 'Recent'
        })))
      }
    } catch (err) {
      console.warn('Failed to load dispute tickets:', err)
    }
  }

  useEffect(() => {
    loadTickets()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)

    if (!transactionRef.trim()) {
      setErrorMessage('Please provide a valid transaction reference to file a dispute.')
      return
    }

    setIsSubmitting(true)

    try {
      const res = await api.post('/api/v1/customer/report', {
        transaction_id: transactionRef.trim(),
        reason: disputeReason,
        notes: notes.trim() || undefined,
        freeze_card: freezeCard
      })

      const newTicket = {
        ticketId: res.ticket_id || `DISP-${transactionRef.slice(-6)}`,
        transactionId: res.transaction_id || transactionRef,
        merchant: merchantName || 'Reported Merchant',
        amount: chargeAmount ? `$${chargeAmount}` : '$0.00',
        reason: disputeReason.replace(/_/g, ' '),
        status: res.investigation_status || 'OPEN',
        openedAt: 'Just now'
      }

      setSubmittedTicket(newTicket)
      await loadTickets()
    } catch (err: any) {
      setErrorMessage(err.detail || err.message || 'Failed to submit dispute. Please verify transaction details.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Submitted Ticket Confirmation Hero */}
      {submittedTicket && (
        <div className="p-5 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 shadow-sm">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="h-6 w-6 text-emerald-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-base font-bold text-emerald-950">
                Dispute Ticket Created: {submittedTicket.ticketId}
              </h3>
              <p className="text-xs text-emerald-800 mt-1">
                Your report for <strong>{submittedTicket.merchant}</strong> ({submittedTicket.amount}) has been submitted to Sentinel AI Fraud Operations.
                {freezeCard && ' Emergency freeze request submitted to fraud operations. Note: Live card-network freeze is pending payment-gateway authorization.'}
              </p>
              <div className="mt-3 flex items-center gap-3 text-xs">
                <span className="font-semibold text-emerald-900">Estimated Review Time: &lt; 2 hours</span>
                <button
                  onClick={() => setSubmittedTicket(null)}
                  className="text-xs font-semibold text-emerald-700 underline"
                >
                  File another report
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form Container (2 cols) */}
        <div className="lg:col-span-2 bg-surface p-6 rounded-xl border border-surface-border shadow-card">
          <div className="flex items-center justify-between pb-4 border-b border-surface-border mb-5">
            <div>
              <h3 className="text-base font-bold text-ink">Submit Fraud Dispute</h3>
              <p className="text-xs text-ink-muted">
                Report unauthorized charges or suspicious card activity for immediate investigator review
              </p>
            </div>
            <Link
              href="/customer/transactions"
              className="text-xs font-semibold text-brand-600 hover:text-brand-700 flex items-center gap-1"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Back to history</span>
            </Link>
          </div>

          {errorMessage && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-900 text-xs flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-semibold text-ink-secondary mb-1">
                  Transaction Reference
                </label>
                <input
                  type="text"
                  placeholder="e.g. TXN_00289"
                  value={transactionRef}
                  onChange={e => setTransactionRef(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-surface-border-strong text-ink font-mono text-xs focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-ink-secondary mb-1">
                  Merchant Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Unknown Retail Store"
                  value={merchantName}
                  onChange={e => setMerchantName(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-surface-border-strong text-ink text-xs focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
            </div>

            <div>
              <label className="block font-semibold text-ink-secondary mb-1">
                Disputed Amount ($ USD)
              </label>
              <input
                type="number"
                step="0.01"
                placeholder="e.g. 150.00"
                value={chargeAmount}
                onChange={e => setChargeAmount(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-surface-border-strong text-ink font-mono text-xs focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-ink-secondary mb-1">
                Primary Reason for Dispute
              </label>
              <select
                value={disputeReason}
                onChange={e => setDisputeReason(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-surface-border-strong text-ink text-xs focus:outline-none focus:ring-2 focus:ring-brand-500 bg-surface"
              >
                <option value="UNRECOGNIZED_TRANSACTION">I do not recognize this transaction or merchant</option>
                <option value="INCORRECT_AMOUNT">I was charged an incorrect amount</option>
                <option value="DUPLICATE_CHARGE">I was charged more than once for a single purchase</option>
                <option value="LOST_OR_STOLEN_CARD">My card was lost or stolen</option>
                <option value="SUSPECTED_SKIMMING">Suspected ATM or terminal card skimming</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-ink-secondary mb-1">
                Additional Details / Location Context
              </label>
              <textarea
                rows={3}
                placeholder="Describe when you noticed the charge, if you were in the reported location, or any other details..."
                value={notes}
                onChange={e => setNotes(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-surface-border-strong text-ink text-xs focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            {/* Instant Safety Toggles */}
            <div className="p-3.5 rounded-xl bg-canvas border border-surface-border space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={freezeCard}
                  onChange={e => setFreezeCard(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-xs font-semibold text-ink">
                  Request emergency card freeze with fraud operations
                </span>
              </label>
              <p className="text-[11px] text-ink-muted pl-5">
                A freeze request will be recorded with your dispute ticket. Direct network card freezing requires payment-gateway / issuer processor integration.
              </p>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 rounded-lg bg-red-600 hover:bg-red-700 text-white font-semibold text-xs shadow-sm transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Send className="h-3.5 w-3.5" />
              <span>{isSubmitting ? 'Submitting Dispute...' : 'Submit Fraud Dispute Ticket'}</span>
            </button>
          </form>
        </div>

        {/* Right Sidebar: Active Tickets & Emergency Contacts */}
        <div className="space-y-6">
          {/* Active Dispute Tickets */}
          <div className="bg-surface p-5 rounded-xl border border-surface-border shadow-card">
            <h3 className="text-sm font-bold text-ink mb-1">Your Dispute Tickets</h3>
            <p className="text-xs text-ink-muted mb-3">Live status tracking</p>

            <div className="space-y-3">
              {tickets.map(t => (
                <div key={t.ticketId} className="p-3 rounded-lg border border-surface-border bg-canvas text-xs space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="font-mono font-bold text-ink">{t.ticketId}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-50 text-amber-700 border border-amber-200">
                      {t.status}
                    </span>
                  </div>
                  <p className="font-semibold text-ink truncate">{t.merchant}</p>
                  <div className="flex justify-between text-[11px] text-ink-muted">
                    <span>{t.amount}</span>
                    <span className="font-mono">{t.openedAt}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Urgent Support Helpline */}
          <div className="bg-surface p-5 rounded-xl border border-surface-border shadow-card">
            <h3 className="text-sm font-bold text-ink mb-1 flex items-center gap-1.5">
              <PhoneCall className="h-4 w-4 text-emerald-600" />
              24/7 Fraud Emergency Line
            </h3>
            <p className="text-xs text-ink-muted mb-3">
              If your card was stolen or you suspect active account takeover:
            </p>
            <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 font-mono font-bold text-center">
              1-800-SENTINEL (Toll-Free)
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function SuspiciousReportingPage() {
  return (
    <AppShell
      title="Suspicious Activity & Fraud Reporting"
      subtitle="Self-Service Transaction Dispute Submission & Dispute Ticket Tracking"
    >
      <Suspense fallback={<div className="p-8 text-center text-xs text-ink-muted">Loading reporting workspace...</div>}>
        <ReportSuspiciousContent />
      </Suspense>
    </AppShell>
  )
}
