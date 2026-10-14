'use client'

import React, { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import {
  Activity,
  ShieldAlert,
  Zap,
  TrendingUp,
  DollarSign,
  AlertCircle,
  Play,
  Flame,
  Plane,
  Moon,
  Clock,
  ArrowRight,
  ExternalLink,
  RefreshCw,
  CheckCircle2,
  Filter
} from 'lucide-react'
import { AppShell } from '../components/AppShell'
import { useAuth } from '../lib/AuthContext'
import { TransactionRecord } from '../components/TransactionStream'
import { api } from '../lib/api'

export default function AuthorityConsolePage() {
  const { currentUser, authToken } = useAuth()
  const [transactions, setTransactions] = useState<TransactionRecord[]>([])
  const [flaggedTransactions, setFlaggedTransactions] = useState<TransactionRecord[]>([])
  const [cases, setCases] = useState<any[]>([])
  const [kpis, setKpis] = useState({
    total_transactions: 0,
    fraud_transactions: 0,
    fraud_rate_pct: 0.0,
    avg_latency_ms: 0.0
  })
  const [storageStatus, setStorageStatus] = useState<any>({
    is_database_connected: false,
    storage_mode: 'in_memory_buffer',
    backend: 'Ephemeral RAM Buffer'
  })
  const [preventedLoss, setPreventedLoss] = useState<number>(0)
  const [isSimulating, setIsSimulating] = useState(false)
  const [activeScenario, setActiveScenario] = useState<string | null>(null)
  const [routeViaKafka, setRouteViaKafka] = useState(false)

  const fetchTelemetry = useCallback(async () => {
    try {
      const [storageData, kpiData, txData, flaggedData, casesData] = await Promise.allSettled([
        api.get('/api/v1/storage/status'),
        api.get('/api/v1/analytics/kpis'),
        api.get('/api/v1/transactions/recent?limit=40'),
        api.get('/api/v1/transactions/recent?flagged_only=true&limit=10'),
        api.get('/api/v1/cases?limit=20')
      ])

      if (storageData.status === 'fulfilled' && storageData.value) {
        setStorageStatus(storageData.value)
      }
      if (kpiData.status === 'fulfilled' && kpiData.value) {
        const k = kpiData.value
        setKpis(k)
        if (typeof k.prevented_loss === 'number') {
          setPreventedLoss(k.prevented_loss)
        }
      }
      if (txData.status === 'fulfilled' && txData.value) {
        const txs = txData.value
        setTransactions(txs)
        // If API doesn't provide persistent prevented_loss, fallback to transaction sum
        if (kpiData.status !== 'fulfilled' || typeof kpiData.value?.prevented_loss !== 'number') {
          const loss = txs
            .filter((t: any) => t.fraud_decision === 'FRAUD' || t.fraud_decision === 'SUSPICIOUS')
            .reduce((sum: number, t: any) => sum + (t.amount || 0), 0)
          setPreventedLoss(loss)
        }
      }
      if (flaggedData.status === 'fulfilled' && Array.isArray(flaggedData.value)) {
        setFlaggedTransactions(flaggedData.value)
      } else if (txData.status === 'fulfilled' && Array.isArray(txData.value)) {
        setFlaggedTransactions(
          txData.value.filter(
            (t: any) => t.fraud_decision === 'FRAUD' || t.fraud_decision === 'SUSPICIOUS'
          )
        )
      }
      if (casesData.status === 'fulfilled' && casesData.value) {
        setCases(casesData.value)
      }
    } catch {
      // Offline fallback
    }
  }, [])

  useEffect(() => {
    fetchTelemetry()
    const interval = setInterval(fetchTelemetry, 3000)
    return () => clearInterval(interval)
  }, [fetchTelemetry])

  const handleSimulate = async (scenario: string, count: number = 5) => {
    setIsSimulating(true)
    setActiveScenario(scenario)
    try {
      await api.post('/api/v1/simulate', { scenario, count, publish_to_kafka: routeViaKafka })
      await fetchTelemetry()
    } catch (err) {
      console.error('Simulation error:', err)
    } finally {
      setIsSimulating(false)
      setActiveScenario(null)
    }
  }

  const openCases = cases.filter(c => c.status === 'OPEN')

  return (
    <AppShell
      title="Financial Authority Console"
      subtitle="Executive Real-Time Overview & Decision Center"
      actions={
        <div className="flex items-center gap-2">
          <Link
            href="/transactions"
            className="px-3 py-1.5 rounded-lg border border-surface-border-strong text-xs font-semibold text-ink-secondary hover:bg-surface-subtle transition-all"
          >
            Explorer
          </Link>
          <Link
            href="/investigations"
            className="px-3 py-1.5 rounded-lg bg-brand-600 text-white text-xs font-semibold hover:bg-brand-700 transition-all shadow-sm"
          >
            Review Queue ({openCases.length})
          </Link>
        </div>
      }
    >
      {/* Storage Mode Notice (if running ephemerally) */}
      {!storageStatus.is_database_connected && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 text-xs text-amber-900 flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <strong>Ephemeral Buffer Mode:</strong> PostgreSQL storage is currently offline. Real-time scoring and cases operate in memory buffer.
          </div>
        </div>
      )}

      {/* 5 Enterprise Executive KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* KPI 1 */}
        <div className="bg-surface p-4 rounded-xl border border-surface-border shadow-card hover:shadow-card-hover transition-all">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-ink-muted">Processed Volume</span>
            <Activity className="h-4 w-4 text-brand-600" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-ink tabular-nums">
              {kpis.total_transactions.toLocaleString()}
            </span>
            <span className="text-[10px] text-emerald-600 font-bold bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
              Live
            </span>
          </div>
          <p className="text-[11px] text-ink-muted mt-1">Total transactions ingested</p>
        </div>

        {/* KPI 2 */}
        <div className="bg-surface p-4 rounded-xl border border-red-200 shadow-card hover:shadow-card-hover transition-all">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-red-700">Flagged Incidents</span>
            <ShieldAlert className="h-4 w-4 text-red-600" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-red-600 tabular-nums">
              {kpis.fraud_transactions.toLocaleString()}
            </span>
            <span className="text-[10px] text-red-700 font-bold bg-red-50 px-1.5 py-0.5 rounded border border-red-200">
              High Risk
            </span>
          </div>
          <p className="text-[11px] text-ink-muted mt-1">Score &ge; 0.40 threshold</p>
        </div>

        {/* KPI 3 */}
        <div className="bg-surface p-4 rounded-xl border border-surface-border shadow-card hover:shadow-card-hover transition-all">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-amber-700">Detection Rate</span>
            <Zap className="h-4 w-4 text-amber-600" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-amber-600 tabular-nums">
              {kpis.fraud_rate_pct.toFixed(2)}%
            </span>
            <span className="text-[10px] text-ink-muted font-mono">portfolio %</span>
          </div>
          <p className="text-[11px] text-ink-muted mt-1">Ratio of suspicious/fraud</p>
        </div>

        {/* KPI 4 */}
        <div className="bg-surface p-4 rounded-xl border border-surface-border shadow-card hover:shadow-card-hover transition-all">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-ink-muted">Engine Latency</span>
            <Clock className="h-4 w-4 text-brand-600" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-ink tabular-nums">
              {kpis.avg_latency_ms.toFixed(1)} <span className="text-sm font-normal text-ink-muted">ms</span>
            </span>
            <span className="text-[10px] text-emerald-600 font-bold bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
              &lt;15ms SLA
            </span>
          </div>
          <p className="text-[11px] text-ink-muted mt-1">End-to-end inference time</p>
        </div>

        {/* KPI 5 */}
        <div className="bg-surface p-4 rounded-xl border border-emerald-200 shadow-card hover:shadow-card-hover transition-all">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-emerald-800">Flagged High-Risk Volume</span>
            <DollarSign className="h-4 w-4 text-emerald-600" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-emerald-700 tabular-nums">
              ${preventedLoss.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <p className="text-[10px] text-ink-muted mt-1 leading-tight">
            Simulated policy detection; acquiring decline requires payment processor integration
          </p>
        </div>
      </div>

      {/* Live Attack Scenario Simulation Bar */}
      <div className="bg-surface p-5 rounded-xl border border-surface-border shadow-card">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-3">
          <div>
            <h3 className="text-sm font-bold text-ink flex items-center gap-2">
              <Flame className="h-4 w-4 text-amber-500" />
              Live Scenario Injection & Stress Testing
            </h3>
            <p className="text-xs text-ink-muted">
              Trigger synthetic test scenarios into the live processing stream to observe real-time scoring response.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-xs text-ink-secondary bg-surface-subtle px-2.5 py-1.5 rounded-lg border border-surface-border cursor-pointer hover:border-brand-300 transition-colors">
              <input
                type="checkbox"
                checked={routeViaKafka}
                onChange={(e) => setRouteViaKafka(e.target.checked)}
                className="rounded border-surface-border text-brand-600 focus:ring-0"
              />
              <span className="font-mono text-[11px]">
                Route via Kafka <span className="text-purple-600 font-semibold">(canonical)</span>
              </span>
            </label>

            {isSimulating && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-brand-50 border border-brand-200 text-xs text-brand-700 font-semibold">
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                Simulating stream...
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {[
            { id: 'NORMAL', label: 'Normal Spend', icon: Play, desc: 'Everyday groceries' },
            { id: 'RAPID_BURST', label: 'Rapid Burst', icon: Zap, desc: '5 txns in 60s' },
            { id: 'IMPOSSIBLE_TRAVEL', label: 'Travel Anomaly', icon: Plane, desc: 'NYC -> Tokyo' },
            { id: 'HIGH_AMOUNT', label: 'High Amount', icon: DollarSign, desc: '3x baseline card' },
            { id: 'NIGHT_ANOMALY', label: 'Night Spend', icon: Moon, desc: '03:00 AM off-cycle' },
            { id: 'MERCHANT_SWARM', label: 'Card Swarm', icon: ShieldAlert, desc: '4 cards 1 merchant' },
          ].map(s => {
            const Icon = s.icon
            const isCurrent = activeScenario === s.id
            return (
              <button
                key={s.id}
                disabled={isSimulating}
                onClick={() => handleSimulate(s.id, 5)}
                className={`p-2.5 rounded-lg border text-left flex flex-col justify-between transition-all ${
                  isCurrent
                    ? 'bg-brand-600 text-white border-brand-700'
                    : 'bg-surface hover:bg-surface-subtle border-surface-border text-ink'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-xs">{s.label}</span>
                  <Icon className="h-3.5 w-3.5 opacity-70" />
                </div>
                <span className={`text-[10px] ${isCurrent ? 'text-brand-100' : 'text-ink-muted'}`}>
                  {s.desc}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Two Column Section: Recent Flagged Incidents & Investigation Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Flagged Transactions (2 cols) */}
        <div className="lg:col-span-2 bg-surface rounded-xl border border-surface-border p-5 shadow-card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-ink">Recent High-Risk Transactions</h3>
              <p className="text-xs text-ink-muted">Transactions evaluated with high final fraud score</p>
            </div>
            <Link
              href="/transactions"
              className="text-xs font-semibold text-brand-600 hover:text-brand-700 flex items-center gap-1"
            >
              <span>View all transactions</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-surface-border text-ink-muted uppercase font-semibold text-[10px]">
                  <th className="py-2 px-3">Transaction</th>
                  <th className="py-2 px-3">Card</th>
                  <th className="py-2 px-3">Merchant</th>
                  <th className="py-2 px-3 text-right">Amount</th>
                  <th className="py-2 px-3 text-center">Score</th>
                  <th className="py-2 px-3 text-center">Status</th>
                  <th className="py-2 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {flaggedTransactions.slice(0, 6).map(tx => (
                  <tr key={tx.transaction_id} className="hover:bg-surface-subtle transition-colors">
                    <td className="py-2.5 px-3 font-mono font-medium text-ink">
                      {tx.transaction_id.slice(0, 10)}...
                    </td>
                    <td className="py-2.5 px-3 font-mono text-ink-muted">{tx.card_id}</td>
                    <td className="py-2.5 px-3 font-medium text-ink">{tx.merchant_name || tx.merchant || 'Retail'}</td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold tabular-nums text-ink">
                      ${tx.amount.toFixed(2)}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <span className="font-mono font-bold text-xs text-red-600 tabular-nums">
                        {(tx.final_fraud_score * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-red-50 text-red-700 border border-red-200">
                        {tx.fraud_decision}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <Link
                        href={`/transactions?inspect=${encodeURIComponent(tx.transaction_id)}`}
                        className="inline-flex items-center gap-0.5 text-brand-600 hover:text-brand-700 font-semibold text-xs"
                      >
                        <span>Inspect</span>
                        <ArrowRight className="h-3 w-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
                {flaggedTransactions.length === 0 && (
                  <tr>
                    <td colSpan={7} className="text-center py-6 text-ink-muted">
                      No high-risk transactions detected. Click a simulation scenario above to test!
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Triage Overview (1 col) */}
        <div className="bg-surface rounded-xl border border-surface-border p-5 shadow-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-ink">Investigation Queue</h3>
              <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs font-bold border border-blue-200">
                {openCases.length} Open
              </span>
            </div>
            <p className="text-xs text-ink-muted mb-4">
              Cases awaiting human analyst decision and ground-truth confirmation.
            </p>

            <div className="space-y-3">
              {openCases.slice(0, 3).map(c => (
                <div
                  key={c.case_id}
                  className="p-3 rounded-lg border border-surface-border hover:border-surface-border-strong transition-all bg-canvas"
                >
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-mono font-bold text-ink">{c.case_id.slice(0, 8)}...</span>
                    <span className="font-mono font-bold text-red-600">
                      ${c.amount?.toFixed(2) || '0.00'}
                    </span>
                  </div>
                  <p className="text-[11px] text-ink-secondary truncate">{c.merchant}</p>
                  <div className="flex items-center justify-between mt-2 text-[10px] text-ink-muted">
                    <span>Priority: {c.priority}</span>
                    <span className="font-semibold text-brand-600">Review &rarr;</span>
                  </div>
                </div>
              ))}
              {openCases.length === 0 && (
                <div className="text-center py-8 text-xs text-ink-muted">
                  Queue is clear. No unassigned cases.
                </div>
              )}
            </div>
          </div>

          <div className="pt-4 border-t border-surface-border mt-4">
            <Link
              href="/investigations"
              className="w-full py-2 px-3 rounded-lg bg-surface-subtle hover:bg-surface-border text-xs font-semibold text-ink-secondary flex items-center justify-center gap-1.5 transition-colors border border-surface-border"
            >
              <span>Open Investigation Workspace</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
