'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  CreditCard,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  History,
  FileWarning,
  DollarSign,
  TrendingUp,
  ArrowRight,
  Lock,
  CheckCircle2,
  Bell,
  Smartphone
} from 'lucide-react'
import { AppShell } from '../../components/AppShell'
import { useAuth } from '../../lib/AuthContext'
import { api } from '../../lib/api'

export default function CustomerDashboardPage() {
  const { currentUser, authToken, quickLogin } = useAuth()
  const [customerTxns, setCustomerTxns] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const isCustomer = currentUser?.role === 'customer'

  useEffect(() => {
    const fetchCustomerData = async () => {
      try {
        const data = await api.get('/api/v1/customer/transactions?limit=10')
        setCustomerTxns(data.transactions || (Array.isArray(data) ? data : []))
      } catch (err) {
        console.warn('Customer transactions fetch:', err)
      } finally {
        setIsLoading(false)
      }
    }

    fetchCustomerData()
  }, [authToken])

  const totalSpent = customerTxns.reduce((sum, t) => sum + (t.amount || 0), 0)
  const flaggedCount = customerTxns.filter(t => t.fraud_decision === 'FRAUD' || t.fraud_decision === 'SUSPICIOUS').length

  return (
    <AppShell
      title="Customer Banking & Security Portal"
      subtitle="Personal Card Protection, Account Activity & Threat Interception"
      actions={
        <Link
          href="/customer/report"
          className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors shadow-sm"
        >
          <FileWarning className="h-3.5 w-3.5" />
          <span>Report Unrecognized Charge</span>
        </Link>
      }
    >
      {/* Role Switcher helper if currently logged in as Staff */}
      {!isCustomer && (
        <div className="p-3.5 rounded-xl bg-blue-50 border border-blue-200 text-blue-900 flex items-center justify-between text-xs mb-2">
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-blue-600" />
            <span>
              You are currently viewing as <strong className="font-semibold">{currentUser?.name || 'Staff'}</strong> ({currentUser?.role}).
              Switch to cardholder James B. (Card 007) to test customer-scoped security.
            </span>
          </div>
          <button
            onClick={() => quickLogin('customer')}
            className="px-3 py-1 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-colors shadow-sm"
          >
            Authenticate as Cardholder
          </button>
        </div>
      )}

      {/* Hero Card & Protection Badge */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Virtual Card Tile */}
        <div className="bg-gradient-to-tr from-slate-900 via-slate-800 to-indigo-950 p-6 rounded-2xl text-white shadow-xl flex flex-col justify-between min-h-[190px] relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400">
                SENTINEL SECURE CREDIT
              </span>
              <p className="text-lg font-bold tracking-tight text-white mt-1">James B.</p>
            </div>
            <div className="h-8 w-11 rounded bg-amber-400/80 flex items-center justify-center text-[10px] font-bold text-amber-950 shadow-inner">
              CHIP
            </div>
          </div>

          <div className="my-3">
            <p className="font-mono text-base tracking-widest text-slate-200">
              •••• •••• •••• 0007
            </p>
          </div>

          <div className="flex justify-between items-end text-xs text-slate-400">
            <div>
              <span className="text-[9px] uppercase tracking-wider block">Valid Thru</span>
              <span className="font-mono text-white">09/29</span>
            </div>
            <span className="font-mono font-bold text-[10px] text-emerald-400 flex items-center gap-1">
              <ShieldCheck className="h-3 w-3" />
              AI Protected
            </span>
          </div>
        </div>

        {/* Protection Metric 1 */}
        <div className="bg-surface p-5 rounded-2xl border border-surface-border shadow-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-ink-muted">Card Defense Status</span>
              <ShieldCheck className="h-5 w-5 text-emerald-600" />
            </div>
            <h3 className="text-xl font-black text-emerald-700">Shield Active</h3>
            <p className="text-xs text-ink-secondary mt-1">
              Real-time heuristic & behavioral scoring is active on card <strong>CARD_007</strong>.
            </p>
          </div>
          <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-[11px] text-emerald-800 flex items-center gap-1.5 mt-3">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
            <span>Zero unauthorized charges approved this billing cycle.</span>
          </div>
        </div>

        {/* Protection Metric 2 */}
        <div className="bg-surface p-5 rounded-2xl border border-surface-border shadow-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-ink-muted">Recent Account Spend</span>
              <DollarSign className="h-5 w-5 text-brand-600" />
            </div>
            <h3 className="text-xl font-black text-ink font-mono tabular-nums">
              ${totalSpent.toFixed(2)}
            </h3>
            <p className="text-xs text-ink-secondary mt-1">
              Total volume across {customerTxns.length} authorized recent transactions.
            </p>
          </div>
          <Link
            href="/customer/transactions"
            className="mt-3 py-2 px-3 rounded-lg bg-surface-subtle hover:bg-surface-border text-xs font-semibold text-brand-600 flex items-center justify-between transition-colors border border-surface-border"
          >
            <span>Inspect Full History</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>

      {/* Security Alerts Feed */}
      <div className="bg-surface rounded-xl border border-surface-border p-5 shadow-card">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-ink flex items-center gap-2">
            <Bell className="h-4 w-4 text-brand-600" />
            Security & Activity Notifications
          </h3>
          <span className="text-xs text-ink-muted">Real-time alerts</span>
        </div>

        <div className="space-y-2.5">
          <div className="p-3.5 rounded-xl bg-canvas border border-surface-border flex items-start gap-3">
            <div className="h-8 w-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 mt-0.5">
              <Smartphone className="h-4 w-4" />
            </div>
            <div className="flex-1 text-xs">
              <strong className="text-ink block">Two-Factor Authentication Enforced</strong>
              <p className="text-ink-muted mt-0.5">
                Out-of-pattern or foreign location transactions will prompt an immediate push verification prompt.
              </p>
            </div>
            <span className="text-[10px] text-ink-muted font-mono">Policy Live</span>
          </div>

          <div className="p-3.5 rounded-xl bg-canvas border border-surface-border flex items-start gap-3">
            <div className="h-8 w-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0 mt-0.5">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div className="flex-1 text-xs">
              <strong className="text-ink block">Velocity Guard Active</strong>
              <p className="text-ink-muted mt-0.5">
                Maximum 5 transactions within 2 minutes allowed before challenge trigger.
              </p>
            </div>
            <span className="text-[10px] text-ink-muted font-mono">Standard Rule</span>
          </div>
        </div>
      </div>

      {/* Recent Activity Table */}
      <div className="bg-surface rounded-xl border border-surface-border shadow-card overflow-hidden">
        <div className="p-4 border-b border-surface-border flex items-center justify-between">
          <h3 className="text-sm font-bold text-ink">Recent Card Transactions</h3>
          <Link
            href="/customer/transactions"
            className="text-xs font-semibold text-brand-600 hover:text-brand-700 flex items-center gap-1"
          >
            <span>View all</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-canvas border-b border-surface-border text-ink-muted uppercase font-semibold text-[10px]">
              <tr>
                <th className="py-2.5 px-4">Merchant</th>
                <th className="py-2.5 px-4">Date</th>
                <th className="py-2.5 px-4 text-right">Amount</th>
                <th className="py-2.5 px-4 text-center">Status</th>
                <th className="py-2.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {customerTxns.slice(0, 5).map((t, idx) => (
                <tr key={idx} className="hover:bg-surface-subtle transition-colors">
                  <td className="py-3 px-4 font-semibold text-ink">
                    {t.merchant_name || t.merchant || 'Grocery & Retail'}
                  </td>
                  <td className="py-3 px-4 text-ink-muted font-mono text-[11px]">
                    {t.timestamp || 'Today'}
                  </td>
                  <td className="py-3 px-4 text-right font-mono font-bold text-ink tabular-nums">
                    ${(t.amount || 0).toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      AUTHORIZED
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <Link
                      href={`/customer/report?tx=${t.transaction_id || ''}`}
                      className="text-xs font-medium text-red-600 hover:text-red-700"
                    >
                      Report issue
                    </Link>
                  </td>
                </tr>
              ))}
              {customerTxns.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-ink-muted">
                    {isLoading ? 'Loading card activity...' : 'No transactions recorded on this card yet.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  )
}
