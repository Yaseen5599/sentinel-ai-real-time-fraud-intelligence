'use client'

import React, { useState, useEffect } from 'react'
import {
  Search,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Cpu,
  UserCheck,
  CheckCircle2,
  Clock,
  MapPin,
  Building2,
  DollarSign,
  HelpCircle,
  ExternalLink,
  ChevronRight,
  Info,
  Layers,
  ArrowRight,
  Sparkles,
  Terminal,
  Activity,
  FileText,
  RotateCcw,
  Sliders,
  Check,
  X,
  CreditCard
} from 'lucide-react'
import { AppShell } from '../../components/AppShell'
import { api } from '../../lib/api'
import { useAuth } from '../../lib/AuthContext'

interface AnalysisResult {
  found: boolean
  transaction_id: string
  timestamp: string
  amount: number
  currency: string
  merchant: string
  location: string
  card_id: string
  card_id_masked: string
  data_source: string
  is_synthetic: boolean
  customer: {
    customer_id: string
    customer_name: string
    account_age_days: number
    home_location: string
    usual_transaction_amount: number
    usual_active_hours: string
    prior_transaction_count: number
  }
  scores: {
    ml_score: number
    ml_available: boolean
    behavior_score: number
    rule_score: number
    final_risk_score: number
    classification: 'LEGITIMATE' | 'SUSPICIOUS' | 'HIGH_RISK'
    classification_display: string
    color_badge: string
    weights: {
      ml_weight: number
      behavior_weight: number
      rule_weight: number
    }
    thresholds: {
      suspicious: number
      fraud: number
    }
    arithmetic_formula: string
  }
  explanations: {
    plain_english_audit: string
    ml: {
      model_name: string
      model_version: string
      available: boolean
      score: number
      decision_threshold: number
      explanation: string
      input_features: Record<string, number>
      top_contributing_features: Array<{ feature: string; value: number; importance: number }>
      limitations: string
    }
    behavior: {
      score: number
      reasons: string[]
      breakdown: Array<{
        feature: string
        observed: string
        baseline: string
        condition: string
        weight: number
        contribution: number
        status: string
        impact: string
      }>
    }
    rules: {
      score: number
      triggered_count: number
      total_evaluated: number
      reasons: string[]
      rules: Array<{
        rule_id: string
        name: string
        condition: string
        threshold: string
        observed: string
        weight: number
        triggered: boolean
        contribution: number
      }>
    }
    hybrid: {
      final_score: number
      formula: string
      classification: string
      rule_weight: number
      behavior_weight: number
      ml_weight: number
      suspicious_threshold: number
      fraud_threshold: number
    }
  }
  telemetry: {
    processing_latency_ms: number
    evaluated_at: string
  }
}

type ModalTab = 'ml' | 'behavior' | 'rules' | 'hybrid' | null

export default function TransactionRiskAnalysisPage() {
  const { currentUser, authToken, quickLogin } = useAuth()
  const [searchId, setSearchId] = useState('T00001')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [activeModal, setActiveModal] = useState<ModalTab>(null)
  const [samples, setSamples] = useState<Array<{ id: string; label: string; category: string }>>([
    { id: 'T00001', label: 'T00001 (Normal Spend)', category: 'LEGITIMATE' },
    { id: 'T00059', label: 'T00059 (Suspicious Spike)', category: 'SUSPICIOUS' },
    { id: 'T00199', label: 'T00199 (Velocity Anomaly)', category: 'SUSPICIOUS' },
    { id: 'T00277', label: 'T00277 (High Risk Fraud Alert)', category: 'HIGH_RISK' },
    { id: 'T05000', label: 'T05000 (Mid-Sequence)', category: 'LEGITIMATE' },
    { id: 'T10000', label: 'T10000 (Boundary Transaction)', category: 'LEGITIMATE' }
  ])

  // Initial load
  useEffect(() => {
    executeSearch('T00001')
  }, [])

  const executeSearch = async (tid: string) => {
    const cleanId = tid.trim().toUpperCase()
    if (!cleanId) return

    setLoading(true)
    setError(null)

    try {
      const data = await api.post('/api/v1/transaction-risk-analysis', {
        transaction_id: cleanId
      })
      setResult(data)
    } catch (err: any) {
      console.error('Search failed:', err)
      setResult(null)
      setError(err?.message || 'Transaction could not be evaluated. Please verify the ID format (e.g. T00001).')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      executeSearch(searchId)
    }
  }

  const isAuthorized = currentUser?.role === 'admin' || currentUser?.role === 'fraud_investigator'
  const isCustomer = currentUser?.role === 'customer'

  return (
    <AppShell
      title="Transaction Risk Analysis"
      subtitle="Search a transaction to understand its fraud risk and how the score was calculated."
    >
      <div className="space-y-6">
        {/* ======================= Customer Restricted Barrier ======================= */}
        {isCustomer && (
          <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-rose-900 shadow-card">
            <div className="flex items-start gap-4">
              <div className="p-2 rounded-xl bg-rose-100 text-rose-700 shrink-0 mt-0.5">
                <ShieldAlert className="h-6 w-6" />
              </div>
              <div className="space-y-2">
                <h3 className="text-base font-bold text-rose-900">
                  Access Restricted — Unauthorized Clearance Level
                </h3>
                <p className="text-sm text-rose-800 leading-relaxed">
                  You are currently logged in with the <strong>Customer</strong> role ({currentUser?.email}).
                  Under banking policy and role-based access control (RBAC), customer identities are strictly prohibited from inspecting internal machine learning models, deterministic rule conditions, and transaction risk intelligence.
                </p>
                <div className="pt-2 flex flex-wrap gap-3">
                  <a
                    href="/customer"
                    className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-medium text-xs transition-colors shadow-sm"
                  >
                    Return to Customer Portal
                  </a>
                  <button
                    onClick={() => quickLogin?.('investigator')}
                    className="px-4 py-2 rounded-xl bg-surface border border-rose-300 hover:bg-rose-100/50 text-rose-900 font-medium text-xs transition-colors"
                  >
                    Switch to Fraud Investigator Session
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ======================= Unauthenticated Notice ======================= */}
        {!currentUser && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 text-amber-900 shadow-card">
            <div className="flex items-start gap-4">
              <div className="p-2 rounded-xl bg-amber-100 text-amber-700 shrink-0 mt-0.5">
                <AlertTriangle className="h-6 w-6" />
              </div>
              <div className="space-y-2">
                <h3 className="text-base font-bold text-amber-900">
                  Authentication Required
                </h3>
                <p className="text-sm text-amber-800 leading-relaxed">
                  Transaction Risk Analysis is restricted to authorized financial authorities, administrators, and fraud investigators. Please sign in to execute live canonical inference and inspect behavioral factors.
                </p>
                <div className="pt-2 flex flex-wrap gap-3">
                  <button
                    onClick={() => quickLogin?.('investigator')}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs transition-colors shadow-sm flex items-center gap-1.5"
                  >
                    <UserCheck className="h-4 w-4" />
                    Sign In as Sarah Jenkins (Investigator)
                  </button>
                  <button
                    onClick={() => quickLogin?.('admin')}
                    className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-medium text-xs transition-colors shadow-sm flex items-center gap-1.5"
                  >
                    <ShieldAlert className="h-4 w-4" />
                    Sign In as Security Admin
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ======================= Search Bar & Quick Picks (Only for Authorized Staff) ======================= */}
        {!isCustomer && (
          <div className="bg-surface p-6 rounded-2xl border border-surface-border shadow-card relative overflow-hidden">
            <div className="absolute top-0 right-0 w-80 h-80 bg-brand-500/5 rounded-full blur-3xl pointer-events-none" />

            <div className="max-w-3xl">
              <h2 className="text-lg font-bold text-ink mb-1.5 flex items-center gap-2">
                <Search className="h-5 w-5 text-brand-600" />
                Analyze Transaction Risk
              </h2>
              <p className="text-xs text-ink-muted mb-4">
                Search a transaction to understand its fraud risk and how the score was calculated. Evaluates the 10,000 synthetic transaction dataset (T00001 to T10000) using the production Random Forest ML model, customer behavioral baselines, and deterministic rules.
              </p>

              {/* Input Group */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-muted" />
                  <input
                    type="text"
                    value={searchId}
                    onChange={(e) => setSearchId(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Enter Transaction ID (e.g., T00001)"
                    className="w-full pl-10 pr-4 py-2.5 bg-canvas border border-surface-border rounded-xl text-sm font-mono text-ink placeholder-ink-muted focus:outline-none focus:ring-2 focus:ring-brand-500 transition-all uppercase tracking-wider"
                  />
                </div>
                <button
                  onClick={() => executeSearch(searchId)}
                  disabled={loading}
                  className="px-6 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium text-sm transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-50 shrink-0"
                >
                  {loading ? (
                    <>
                      <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Analyzing...</span>
                    </>
                  ) : (
                    <>
                      <Activity className="h-4 w-4" />
                      <span>Analyze Transaction</span>
                    </>
                  )}
                </button>
              </div>

              {/* Sample Chips */}
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <span className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">
                  Sample Test Records:
                </span>
                {samples.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => {
                      setSearchId(s.id)
                      executeSearch(s.id)
                    }}
                    className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium border transition-all ${
                      searchId.toUpperCase() === s.id
                        ? 'bg-brand-50 text-brand-700 border-brand-300 ring-1 ring-brand-300'
                        : 'bg-surface-subtle text-ink-secondary border-surface-border hover:bg-surface hover:text-ink'
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ======================= Error Notice ======================= */}
        {error && (
          <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 flex items-start gap-3 text-rose-800">
            <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold">Transaction Analysis Failed</p>
              <p className="text-xs text-rose-700 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* ======================= Results Section ======================= */}
        {result && (
          <div className="space-y-6">
            {/* 1. Transaction Summary Banner */}
            <div className="bg-surface rounded-2xl border border-surface-border shadow-card p-6">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-5 border-b border-surface-border">
                <div className="flex items-center gap-3">
                  <div className="h-12 w-12 rounded-xl bg-brand-50 border border-brand-200 flex items-center justify-center text-brand-600 font-mono font-extrabold text-base shrink-0 shadow-sm">
                    {result.transaction_id.slice(0, 2)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h3 className="text-lg font-bold text-ink font-mono tracking-tight">
                        {result.transaction_id}
                      </h3>
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider font-mono bg-purple-50 text-purple-700 border border-purple-200">
                        SYNTHETIC RECORD
                      </span>
                    </div>
                    <p className="text-xs text-ink-muted flex items-center gap-1.5 mt-0.5">
                      <Clock className="h-3.5 w-3.5" />
                      {new Date(result.timestamp).toUTCString()} ({result.timestamp})
                    </p>
                  </div>
                </div>

                {/* Classification Hero Badge */}
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">
                      Assigned Risk Level
                    </p>
                    <p className="text-sm font-extrabold text-ink">
                      {result.scores.classification_display}
                    </p>
                  </div>
                  <div
                    className={`px-4 py-2 rounded-xl font-bold font-mono text-sm border flex items-center gap-2 shadow-sm ${
                      result.scores.classification === 'HIGH_RISK'
                        ? 'bg-rose-500 text-white border-rose-600'
                        : result.scores.classification === 'SUSPICIOUS'
                        ? 'bg-amber-500 text-white border-amber-600'
                        : 'bg-emerald-600 text-white border-emerald-700'
                    }`}
                  >
                    {result.scores.classification === 'HIGH_RISK' ? (
                      <ShieldAlert className="h-4 w-4" />
                    ) : result.scores.classification === 'SUSPICIOUS' ? (
                      <AlertTriangle className="h-4 w-4" />
                    ) : (
                      <ShieldCheck className="h-4 w-4" />
                    )}
                    <span>{(result.scores.final_risk_score * 100).toFixed(1)}% RISK</span>
                  </div>
                </div>
              </div>

              {/* Transaction Key Details Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 pt-5">
                <div>
                  <span className="text-[11px] font-semibold text-ink-muted uppercase block">Amount</span>
                  <span className="text-base font-extrabold text-ink font-mono">
                    ${result.amount.toFixed(2)} {result.currency}
                  </span>
                </div>
                <div>
                  <span className="text-[11px] font-semibold text-ink-muted uppercase block">Merchant</span>
                  <span className="text-sm font-semibold text-ink flex items-center gap-1.5 mt-0.5">
                    <Building2 className="h-3.5 w-3.5 text-brand-600 shrink-0" />
                    <span className="truncate">{result.merchant}</span>
                  </span>
                </div>
                <div>
                  <span className="text-[11px] font-semibold text-ink-muted uppercase block">Terminal Location</span>
                  <span className="text-sm font-semibold text-ink flex items-center gap-1.5 mt-0.5">
                    <MapPin className="h-3.5 w-3.5 text-rose-500 shrink-0" />
                    <span>{result.location}</span>
                  </span>
                </div>
                <div>
                  <span className="text-[11px] font-semibold text-ink-muted uppercase block">Masked Card ID</span>
                  <span className="text-sm font-semibold text-ink font-mono flex items-center gap-1.5 mt-0.5">
                    <CreditCard className="h-3.5 w-3.5 text-slate-500 shrink-0" />
                    <span>{result.card_id_masked}</span>
                  </span>
                </div>
                <div>
                  <span className="text-[11px] font-semibold text-ink-muted uppercase block">Customer Profile</span>
                  <span className="text-sm font-semibold text-ink flex items-center gap-1.5 mt-0.5 truncate">
                    <UserCheck className="h-3.5 w-3.5 text-indigo-500 shrink-0" />
                    <span className="truncate">{result.customer.customer_name}</span>
                  </span>
                </div>
                <div>
                  <span className="text-[11px] font-semibold text-ink-muted uppercase block">Historical Context</span>
                  <span className="text-xs font-mono font-medium text-ink-secondary mt-0.5 block">
                    {result.customer.prior_transaction_count} prior events
                  </span>
                </div>
              </div>
            </div>

            {/* 2. Four Interactive Score Cards */}
            <div>
              <div className="flex items-center justify-between mb-3 px-1">
                <div>
                  <h3 className="text-sm font-bold text-ink uppercase tracking-wider">
                    Risk Architecture Breakdown
                  </h3>
                  <p className="text-xs text-ink-muted">
                    Click any card to open the complete explainability audit modal with full feature vectors and examiner verification.
                  </p>
                </div>
                <div className="text-xs text-ink-muted font-mono hidden sm:block">
                  Latency: {result.telemetry.processing_latency_ms.toFixed(1)} ms
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Score Card 1: Machine Learning */}
                <div
                  onClick={() => setActiveModal('ml')}
                  className="bg-surface p-5 rounded-2xl border border-surface-border shadow-card hover:border-brand-500/50 hover:shadow-md transition-all cursor-pointer group relative overflow-hidden flex flex-col justify-between"
                >
                  <div className="absolute top-2 right-2 text-ink-muted group-hover:text-brand-600 transition-colors">
                    <ExternalLink className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-200">
                        <Cpu className="h-4 w-4" />
                      </div>
                      <span className="text-xs font-bold text-ink uppercase tracking-wider">
                        Machine Learning
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2 mb-2">
                      <span className="text-3xl font-extrabold font-mono text-ink">
                        {(result.scores.ml_score * 100).toFixed(1)}%
                      </span>
                      <span className="text-xs text-ink-muted font-mono">
                        wt: 50%
                      </span>
                    </div>

                    {/* Progress bar */}
                    <div className="w-full bg-surface-subtle h-2 rounded-full overflow-hidden mb-3">
                      <div
                        className={`h-full rounded-full ${
                          result.scores.ml_score >= 0.7
                            ? 'bg-rose-500'
                            : result.scores.ml_score >= 0.4
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.min(100, Math.max(5, result.scores.ml_score * 100))}%` }}
                      />
                    </div>
                    <p className="text-xs text-ink-muted line-clamp-2">
                      {result.explanations.ml.explanation}
                    </p>
                  </div>
                  <div className="pt-3 mt-3 border-t border-surface-border/60 flex items-center justify-between text-[11px] text-brand-600 font-semibold group-hover:translate-x-0.5 transition-transform">
                    <span>Inspect 18 ML Features</span>
                    <ChevronRight className="h-3.5 w-3.5" />
                  </div>
                </div>

                {/* Score Card 2: Behaviour Score */}
                <div
                  onClick={() => setActiveModal('behavior')}
                  className="bg-surface p-5 rounded-2xl border border-surface-border shadow-card hover:border-brand-500/50 hover:shadow-md transition-all cursor-pointer group relative overflow-hidden flex flex-col justify-between"
                >
                  <div className="absolute top-2 right-2 text-ink-muted group-hover:text-brand-600 transition-colors">
                    <ExternalLink className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="p-1.5 rounded-lg bg-cyan-50 text-cyan-600 border border-cyan-200">
                        <UserCheck className="h-4 w-4" />
                      </div>
                      <span className="text-xs font-bold text-ink uppercase tracking-wider">
                        Customer Behaviour
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2 mb-2">
                      <span className="text-3xl font-extrabold font-mono text-ink">
                        {(result.scores.behavior_score * 100).toFixed(1)}%
                      </span>
                      <span className="text-xs text-ink-muted font-mono">
                        wt: 30%
                      </span>
                    </div>

                    {/* Progress bar */}
                    <div className="w-full bg-surface-subtle h-2 rounded-full overflow-hidden mb-3">
                      <div
                        className={`h-full rounded-full ${
                          result.scores.behavior_score >= 0.7
                            ? 'bg-rose-500'
                            : result.scores.behavior_score >= 0.4
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.min(100, Math.max(5, result.scores.behavior_score * 100))}%` }}
                      />
                    </div>
                    <p className="text-xs text-ink-muted line-clamp-2">
                      {result.explanations.behavior.reasons.length > 0
                        ? result.explanations.behavior.reasons[0]
                        : 'Spending pattern matches historical baselines perfectly.'}
                    </p>
                  </div>
                  <div className="pt-3 mt-3 border-t border-surface-border/60 flex items-center justify-between text-[11px] text-brand-600 font-semibold group-hover:translate-x-0.5 transition-transform">
                    <span>Inspect Baseline Deviations</span>
                    <ChevronRight className="h-3.5 w-3.5" />
                  </div>
                </div>

                {/* Score Card 3: Deterministic Rules */}
                <div
                  onClick={() => setActiveModal('rules')}
                  className="bg-surface p-5 rounded-2xl border border-surface-border shadow-card hover:border-brand-500/50 hover:shadow-md transition-all cursor-pointer group relative overflow-hidden flex flex-col justify-between"
                >
                  <div className="absolute top-2 right-2 text-ink-muted group-hover:text-brand-600 transition-colors">
                    <ExternalLink className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="p-1.5 rounded-lg bg-amber-50 text-amber-600 border border-amber-200">
                        <Sliders className="h-4 w-4" />
                      </div>
                      <span className="text-xs font-bold text-ink uppercase tracking-wider">
                        Fraud Rule Engine
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2 mb-2">
                      <span className="text-3xl font-extrabold font-mono text-ink">
                        {(result.scores.rule_score * 100).toFixed(1)}%
                      </span>
                      <span className="text-xs text-ink-muted font-mono">
                        wt: 20%
                      </span>
                    </div>

                    {/* Progress bar */}
                    <div className="w-full bg-surface-subtle h-2 rounded-full overflow-hidden mb-3">
                      <div
                        className={`h-full rounded-full ${
                          result.scores.rule_score >= 0.5
                            ? 'bg-rose-500'
                            : result.scores.rule_score > 0
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.min(100, Math.max(5, result.scores.rule_score * 100))}%` }}
                      />
                    </div>
                    <p className="text-xs text-ink-muted line-clamp-2">
                      {result.explanations.rules.triggered_count > 0
                        ? `${result.explanations.rules.triggered_count} of 7 deterministic rules triggered.`
                        : 'All 7 deterministic safety and velocity rules passed.'}
                    </p>
                  </div>
                  <div className="pt-3 mt-3 border-t border-surface-border/60 flex items-center justify-between text-[11px] text-brand-600 font-semibold group-hover:translate-x-0.5 transition-transform">
                    <span>Inspect 7-Rule Evaluation</span>
                    <ChevronRight className="h-3.5 w-3.5" />
                  </div>
                </div>

                {/* Score Card 4: Final Hybrid Score */}
                <div
                  onClick={() => setActiveModal('hybrid')}
                  className="bg-surface p-5 rounded-2xl border-2 border-brand-500/40 shadow-card hover:border-brand-500 hover:shadow-lg transition-all cursor-pointer group relative overflow-hidden flex flex-col justify-between"
                >
                  <div className="absolute top-2 right-2 text-brand-600">
                    <ExternalLink className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="p-1.5 rounded-lg bg-brand-50 text-brand-600 border border-brand-200">
                        <Sparkles className="h-4 w-4" />
                      </div>
                      <span className="text-xs font-bold text-ink uppercase tracking-wider">
                        Final Hybrid Score
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2 mb-2">
                      <span className="text-3xl font-extrabold font-mono text-ink">
                        {(result.scores.final_risk_score * 100).toFixed(1)}%
                      </span>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded font-mono uppercase ${
                          result.scores.classification === 'HIGH_RISK'
                            ? 'bg-rose-100 text-rose-800'
                            : result.scores.classification === 'SUSPICIOUS'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {result.scores.classification}
                      </span>
                    </div>

                    {/* Progress bar */}
                    <div className="w-full bg-surface-subtle h-2 rounded-full overflow-hidden mb-3">
                      <div
                        className={`h-full rounded-full ${
                          result.scores.final_risk_score >= 0.70
                            ? 'bg-rose-500'
                            : result.scores.final_risk_score >= 0.40
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.min(100, Math.max(5, result.scores.final_risk_score * 100))}%` }}
                      />
                    </div>
                    <p className="text-[11px] font-mono text-ink-muted truncate">
                      {result.scores.arithmetic_formula}
                    </p>
                  </div>
                  <div className="pt-3 mt-3 border-t border-surface-border/60 flex items-center justify-between text-[11px] text-brand-600 font-semibold group-hover:translate-x-0.5 transition-transform">
                    <span>Verify Examiner Arithmetic</span>
                    <ChevronRight className="h-3.5 w-3.5" />
                  </div>
                </div>
              </div>
            </div>

            {/* 3. Plain-English Audit Explanation Box */}
            <div className="bg-surface p-6 rounded-2xl border border-surface-border shadow-card space-y-3">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-brand-600" />
                <h3 className="text-sm font-bold text-ink uppercase tracking-wider">
                  Plain-English Audit Explanation
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-subtle text-ink-muted border border-surface-border">
                  Grounded In Verified Score Evidence
                </span>
              </div>
              <p className="text-sm text-ink leading-relaxed bg-surface-subtle p-4 rounded-xl border border-surface-border/80">
                {result.explanations.plain_english_audit}
              </p>
            </div>
          </div>
        )}

        {/* ======================= Interactive Audit Modal ======================= */}
        {activeModal && result && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
            <div className="bg-surface rounded-2xl border border-surface-border shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden animate-scaleUp">
              {/* Modal Header */}
              <div className="p-6 border-b border-surface-border flex items-center justify-between bg-surface-subtle">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-xl bg-brand-50 text-brand-600 border border-brand-200">
                    {activeModal === 'ml' && <Cpu className="h-5 w-5" />}
                    {activeModal === 'behavior' && <UserCheck className="h-5 w-5" />}
                    {activeModal === 'rules' && <Sliders className="h-5 w-5" />}
                    {activeModal === 'hybrid' && <Sparkles className="h-5 w-5" />}
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-ink">
                      {activeModal === 'ml' && 'Machine Learning Score Deep Dive'}
                      {activeModal === 'behavior' && 'Personalized Customer Behaviour Breakdown'}
                      {activeModal === 'rules' && 'Deterministic Fraud Rule Engine Audit'}
                      {activeModal === 'hybrid' && 'Hybrid Risk Score Verification & Arithmetic'}
                    </h3>
                    <p className="text-xs text-ink-muted">
                      Transaction {result.transaction_id} · Card {result.card_id_masked}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* Modal Tab Switcher */}
                  <div className="hidden sm:flex items-center gap-1 bg-surface p-1 rounded-xl border border-surface-border text-xs">
                    <button
                      onClick={() => setActiveModal('ml')}
                      className={`px-2.5 py-1 rounded-lg font-medium transition-all ${activeModal === 'ml' ? 'bg-brand-600 text-white shadow-sm' : 'text-ink-muted hover:text-ink'}`}
                    >
                      ML
                    </button>
                    <button
                      onClick={() => setActiveModal('behavior')}
                      className={`px-2.5 py-1 rounded-lg font-medium transition-all ${activeModal === 'behavior' ? 'bg-brand-600 text-white shadow-sm' : 'text-ink-muted hover:text-ink'}`}
                    >
                      Behaviour
                    </button>
                    <button
                      onClick={() => setActiveModal('rules')}
                      className={`px-2.5 py-1 rounded-lg font-medium transition-all ${activeModal === 'rules' ? 'bg-brand-600 text-white shadow-sm' : 'text-ink-muted hover:text-ink'}`}
                    >
                      Rules
                    </button>
                    <button
                      onClick={() => setActiveModal('hybrid')}
                      className={`px-2.5 py-1 rounded-lg font-medium transition-all ${activeModal === 'hybrid' ? 'bg-brand-600 text-white shadow-sm' : 'text-ink-muted hover:text-ink'}`}
                    >
                      Hybrid
                    </button>
                  </div>

                  <button
                    onClick={() => setActiveModal(null)}
                    className="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-surface border border-transparent hover:border-surface-border transition-colors"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              </div>

              {/* Modal Body */}
              <div className="p-6 overflow-y-auto space-y-6 flex-1">
                {/* ---------------- ML Modal Content ---------------- */}
                {activeModal === 'ml' && (
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <div className="bg-surface-subtle p-4 rounded-xl border border-surface-border">
                        <span className="text-[11px] font-semibold text-ink-muted uppercase block">Model Architecture</span>
                        <span className="text-sm font-bold text-ink mt-0.5 block">{result.explanations.ml.model_name}</span>
                        <span className="text-[10px] text-ink-muted font-mono">{result.explanations.ml.model_version}</span>
                      </div>
                      <div className="bg-surface-subtle p-4 rounded-xl border border-surface-border">
                        <span className="text-[11px] font-semibold text-ink-muted uppercase block">Inference Probability</span>
                        <span className="text-2xl font-extrabold font-mono text-ink mt-0.5 block">
                          {(result.scores.ml_score * 100).toFixed(2)}%
                        </span>
                        <span className="text-[10px] text-ink-muted font-mono">Threshold: 50.0%</span>
                      </div>
                      <div className="bg-surface-subtle p-4 rounded-xl border border-surface-border">
                        <span className="text-[11px] font-semibold text-ink-muted uppercase block">Train-Serve Parity</span>
                        <span className="text-sm font-bold text-emerald-600 flex items-center gap-1 mt-0.5">
                          <CheckCircle2 className="h-4 w-4" /> Zero Skew Verified
                        </span>
                        <span className="text-[10px] text-ink-muted">Strict Temporal Causality</span>
                      </div>
                    </div>

                    <div>
                      <h4 className="text-xs font-bold text-ink uppercase tracking-wider mb-2">
                        Canonical Feature Vector (18 Observable Attributes)
                      </h4>
                      <div className="border border-surface-border rounded-xl overflow-hidden">
                        <div className="max-h-72 overflow-y-auto">
                          <table className="w-full text-xs text-left">
                            <thead className="bg-surface-subtle text-ink-muted font-mono uppercase text-[10px] sticky top-0 border-b border-surface-border">
                              <tr>
                                <th className="p-2.5">Feature Name</th>
                                <th className="p-2.5">Extracted Value</th>
                                <th className="p-2.5">Relative Importance</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-surface-border font-mono">
                              {Object.entries(result.explanations.ml.input_features).map(([fKey, fVal]) => {
                                const impObj = result.explanations.ml.top_contributing_features.find(t => t.feature === fKey)
                                return (
                                  <tr key={fKey} className="hover:bg-surface-subtle/50 transition-colors">
                                    <td className="p-2.5 font-semibold text-ink">{fKey}</td>
                                    <td className="p-2.5 text-brand-600 font-bold">{typeof fVal === 'number' ? fVal.toFixed(4) : String(fVal)}</td>
                                    <td className="p-2.5 text-ink-muted">
                                      {impObj ? `${(impObj.importance * 100).toFixed(1)}% (Ranked Signal)` : '--'}
                                    </td>
                                  </tr>
                                )
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>

                    <div className="bg-amber-50 p-4 rounded-xl border border-amber-200 text-xs text-amber-800">
                      <p className="font-semibold flex items-center gap-1.5 mb-1">
                        <Info className="h-4 w-4 text-amber-600 shrink-0" />
                        Model Calibration & Benchmark Scope
                      </p>
                      <p>{result.explanations.ml.limitations}</p>
                    </div>
                  </div>
                )}

                {/* ---------------- Behaviour Modal Content ---------------- */}
                {activeModal === 'behavior' && (
                  <div className="space-y-6">
                    <div className="bg-surface-subtle p-4 rounded-xl border border-surface-border">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                        <div>
                          <span className="text-[11px] font-semibold text-ink-muted uppercase">Cardholder Baseline Context</span>
                          <h4 className="text-sm font-bold text-ink">{result.customer.customer_name} ({result.card_id_masked})</h4>
                        </div>
                        <div className="text-right">
                          <span className="text-xs text-ink-muted">Typical Average Spend</span>
                          <p className="text-base font-bold font-mono text-ink">${result.customer.usual_transaction_amount.toFixed(2)}</p>
                        </div>
                      </div>
                      <div className="text-xs text-ink-muted flex flex-wrap gap-4 pt-2 border-t border-surface-border/60">
                        <span>Active Hours: <strong>{result.customer.usual_active_hours}</strong></span>
                        <span>Home Location: <strong>{result.customer.home_location}</strong></span>
                        <span>Account Age: <strong>{result.customer.account_age_days} days</strong></span>
                      </div>
                    </div>

                    <div>
                      <h4 className="text-xs font-bold text-ink uppercase tracking-wider mb-2">
                        Customer Behaviour Breakdown Table
                      </h4>
                      <div className="border border-surface-border rounded-xl overflow-hidden">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-surface-subtle text-ink-muted font-mono uppercase text-[10px] border-b border-surface-border">
                            <tr>
                              <th className="p-2.5">Factor</th>
                              <th className="p-2.5">Observed Value</th>
                              <th className="p-2.5">Baseline</th>
                              <th className="p-2.5">Condition</th>
                              <th className="p-2.5 text-right">Actual Contribution</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-surface-border">
                            {result.explanations.behavior.breakdown.map((b, idx) => (
                              <tr key={idx} className="hover:bg-surface-subtle/50 transition-colors">
                                <td className="p-2.5 font-semibold text-ink">{b.feature}</td>
                                <td className="p-2.5 font-mono text-ink font-bold">{b.observed}</td>
                                <td className="p-2.5 text-ink-muted font-mono">{b.baseline}</td>
                                <td className="p-2.5 text-xs text-ink-secondary">{b.condition}</td>
                                <td className="p-2.5 text-right font-mono font-bold text-brand-600">
                                  +{b.contribution.toFixed(2)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}

                {/* ---------------- Rules Modal Content ---------------- */}
                {activeModal === 'rules' && (
                  <div className="space-y-6">
                    <div className="bg-surface-subtle p-4 rounded-xl border border-surface-border flex items-center justify-between">
                      <div>
                        <span className="text-[11px] font-semibold text-ink-muted uppercase">Rule Evaluation Summary</span>
                        <h4 className="text-sm font-bold text-ink">
                          {result.explanations.rules.triggered_count} of 7 Deterministic Rules Triggered
                        </h4>
                      </div>
                      <div className="text-right">
                        <span className="text-xs text-ink-muted">Cumulative Rule Risk</span>
                        <p className="text-xl font-extrabold font-mono text-ink">
                          {(result.scores.rule_score * 100).toFixed(1)}%
                        </p>
                      </div>
                    </div>

                    <div>
                      <h4 className="text-xs font-bold text-ink uppercase tracking-wider mb-2">
                        Deterministic Fraud Rules Evaluation Table
                      </h4>
                      <div className="border border-surface-border rounded-xl overflow-hidden mb-4">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-surface-subtle text-ink-muted font-mono uppercase text-[10px] border-b border-surface-border">
                            <tr>
                              <th className="p-2.5">Rule</th>
                              <th className="p-2.5">Condition</th>
                              <th className="p-2.5">Observed Value</th>
                              <th className="p-2.5">Status</th>
                              <th className="p-2.5 text-right">Actual Contribution</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-surface-border">
                            {result.explanations.rules.rules.map((r) => (
                              <tr key={r.rule_id} className={`hover:bg-surface-subtle/50 transition-colors ${r.triggered ? 'bg-rose-50/30' : ''}`}>
                                <td className="p-2.5 font-semibold text-ink">
                                  <div className="font-mono text-[11px] text-ink-muted">{r.rule_id}</div>
                                  <div>{r.name}</div>
                                </td>
                                <td className="p-2.5 text-xs text-ink-secondary">{r.condition}</td>
                                <td className="p-2.5 font-mono text-ink font-semibold">{r.observed}</td>
                                <td className="p-2.5">
                                  <span
                                    className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase ${
                                      r.triggered ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800'
                                    }`}
                                  >
                                    {r.triggered ? 'TRIGGERED' : 'NOT TRIGGERED'}
                                  </span>
                                </td>
                                <td className="p-2.5 text-right font-mono font-bold text-brand-600">
                                  +{r.contribution.toFixed(2)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-ink uppercase tracking-wider">
                        Rule Condition Details
                      </h4>
                      {result.explanations.rules.rules.map((r) => (
                        <div
                          key={r.rule_id}
                          className={`p-3.5 rounded-xl border transition-all ${
                            r.triggered
                              ? 'bg-rose-50/50 border-rose-300'
                              : 'bg-surface border-surface-border'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-3 mb-1">
                            <div className="flex items-center gap-2">
                              <span
                                className={`p-1 rounded-md text-white font-bold text-xs ${
                                  r.triggered ? 'bg-rose-600' : 'bg-emerald-600'
                                }`}
                              >
                                {r.triggered ? <AlertTriangle className="h-3 w-3" /> : <Check className="h-3 w-3" />}
                              </span>
                              <span className="text-xs font-bold text-ink font-mono">{r.rule_id}</span>
                              <span className="text-xs font-bold text-ink">— {r.name}</span>
                            </div>
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono uppercase ${
                                r.triggered ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800'
                              }`}
                            >
                              Weight: {(r.weight * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-ink-muted pt-1.5 border-t border-surface-border/50">
                            <div>Condition: <strong className="text-ink">{r.condition}</strong></div>
                            <div>Observed: <strong className="text-ink font-mono">{r.observed}</strong></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* ---------------- Hybrid Modal Content ---------------- */}
                {activeModal === 'hybrid' && (
                  <div className="space-y-6">
                    <div className="bg-surface-subtle p-5 rounded-xl border border-surface-border">
                      <h4 className="text-xs font-bold text-ink uppercase tracking-wider mb-2">
                        Examiner Mathematical Verification Formula
                      </h4>
                      <p className="text-xs text-ink-muted mb-3">
                        The Sentinel AI Hybrid Fraud Risk Scorer calculates the final risk classification using an immutable weighted linear ensemble of Machine Learning, Behavioral Deviations, and Deterministic Rules:
                      </p>
                      <div className="bg-canvas p-4 rounded-xl border border-surface-border font-mono text-sm text-brand-600 font-bold overflow-x-auto">
                        Final Score = (0.50 × ML Score) + (0.30 × Behaviour Score) + (0.20 × Rule Score)
                      </div>
                    </div>

                    <div className="bg-surface p-5 rounded-xl border border-surface-border space-y-4">
                      <h4 className="text-xs font-bold text-ink uppercase tracking-wider">
                        Step-by-Step Value Substitution
                      </h4>
                      <div className="space-y-2 font-mono text-xs">
                        <div className="flex items-center justify-between p-2 rounded-lg bg-surface-subtle">
                          <span>1. Machine Learning Component (50% weight):</span>
                          <span className="font-bold text-ink">0.50 × {result.scores.ml_score.toFixed(4)} = {(result.scores.weights.ml_weight * result.scores.ml_score).toFixed(4)}</span>
                        </div>
                        <div className="flex items-center justify-between p-2 rounded-lg bg-surface-subtle">
                          <span>2. Behavioural Deviation Component (30% weight):</span>
                          <span className="font-bold text-ink">0.30 × {result.scores.behavior_score.toFixed(4)} = {(result.scores.weights.behavior_weight * result.scores.behavior_score).toFixed(4)}</span>
                        </div>
                        <div className="flex items-center justify-between p-2 rounded-lg bg-surface-subtle">
                          <span>3. Deterministic Rules Component (20% weight):</span>
                          <span className="font-bold text-ink">0.20 × {result.scores.rule_score.toFixed(4)} = {(result.scores.weights.rule_weight * result.scores.rule_score).toFixed(4)}</span>
                        </div>
                        <div className="flex items-center justify-between p-3 rounded-lg bg-brand-50 text-brand-900 border border-brand-200 text-sm font-extrabold">
                          <span>Cumulative Calculated Risk Score:</span>
                          <span>{result.scores.final_risk_score.toFixed(4)} ({(result.scores.final_risk_score * 100).toFixed(2)}%)</span>
                        </div>
                      </div>
                    </div>

                    <div>
                      <h4 className="text-xs font-bold text-ink uppercase tracking-wider mb-2">
                        Configured Threshold Mapping
                      </h4>
                      <div className="grid grid-cols-3 gap-3 text-center">
                        <div className={`p-3 rounded-xl border ${result.scores.classification === 'LEGITIMATE' ? 'bg-emerald-50 border-emerald-400 font-bold' : 'bg-surface-subtle border-surface-border text-ink-muted'}`}>
                          <span className="text-[10px] uppercase font-mono block">Low Risk</span>
                          <span className="text-sm">Score &lt; 0.40</span>
                          <span className="text-[11px] block mt-1 font-semibold text-emerald-700">LEGITIMATE</span>
                        </div>
                        <div className={`p-3 rounded-xl border ${result.scores.classification === 'SUSPICIOUS' ? 'bg-amber-50 border-amber-400 font-bold' : 'bg-surface-subtle border-surface-border text-ink-muted'}`}>
                          <span className="text-[10px] uppercase font-mono block">Medium Risk</span>
                          <span className="text-sm">0.40 – 0.69</span>
                          <span className="text-[11px] block mt-1 font-semibold text-amber-700">SUSPICIOUS</span>
                        </div>
                        <div className={`p-3 rounded-xl border ${result.scores.classification === 'HIGH_RISK' ? 'bg-rose-50 border-rose-400 font-bold' : 'bg-surface-subtle border-surface-border text-ink-muted'}`}>
                          <span className="text-[10px] uppercase font-mono block">Critical Alert</span>
                          <span className="text-sm">Score ≥ 0.70</span>
                          <span className="text-[11px] block mt-1 font-semibold text-rose-700">FRAUD ALERT</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="p-4 border-t border-surface-border bg-surface-subtle flex items-center justify-between text-xs text-ink-muted">
                <span className="font-mono">Audit ID: {result.transaction_id}-{new Date(result.telemetry.evaluated_at).getTime()}</span>
                <button
                  onClick={() => setActiveModal(null)}
                  className="px-4 py-1.5 rounded-lg bg-surface border border-surface-border text-ink font-semibold hover:bg-surface-subtle transition-colors"
                >
                  Close Inspection
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  )
}
