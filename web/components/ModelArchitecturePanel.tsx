'use client'

import React from 'react'
import { Cpu, CheckCircle2, Layers, ShieldCheck, Database, GitMerge } from 'lucide-react'

export const ModelArchitecturePanel: React.FC = () => {
  const canonicalFeatures = [
    { name: 'amount', desc: 'Raw financial charge magnitude in USD' },
    { name: 'log_amount', desc: 'Normalized ln(1 + amount) variance stabilizer' },
    { name: 'hour_sin', desc: 'Diurnal cyclical encoding: sin(2π · hour / 24)' },
    { name: 'hour_cos', desc: 'Diurnal cyclical encoding: cos(2π · hour / 24)' },
    { name: 'day_of_week', desc: 'Day index [0..6] capturing weekly spending rhythms' },
    { name: 'is_weekend', desc: 'Binary flag for Saturday / Sunday off-cycle spend' },
    { name: 'velocity_1m', desc: 'Sliding window: transactions in last 60 seconds (burst)' },
    { name: 'velocity_5m', desc: 'Sliding window: transactions in last 300 seconds' },
    { name: 'velocity_24h', desc: 'Sliding window: transactions in last 24 hours' },
    { name: 'spend_velocity_24h', desc: 'Cumulative cardholder expenditure across 24h' },
    { name: 'amount_to_avg_ratio', desc: 'Deviation ratio: amount / cardholder historical mean' },
    { name: 'amount_z_score', desc: 'Standardized z-score against card baseline (μ, σ)' },
    { name: 'distance_from_last_km', desc: 'Great-circle Haversine distance from prior location' },
    { name: 'speed_kmh', desc: 'Transit velocity between successive card transactions' },
    { name: 'is_new_merchant', desc: 'Unfamiliar merchant flag (unseen in card history)' },
    { name: 'is_new_location', desc: 'Unfamiliar location flag (unseen city origin)' },
    { name: 'mcc_risk_weight', desc: 'Merchant Category Code risk scalar (crypto, jewelry, etc.)' },
    { name: 'channel_risk_weight', desc: 'Transaction channel risk weight (E-Comm vs Chip)' },
  ]

  const rules = [
    { id: 'RULE_1', name: 'BURST_TXNS', weight: '20%', desc: '>5 transactions from single card within 2 minutes' },
    { id: 'RULE_2', name: 'IMPOSSIBLE_TRAVEL', weight: '25%', desc: 'Distance >300km between locations within 30 minutes' },
    { id: 'RULE_3', name: 'HIGH_AMOUNT_MULTIPLE', weight: '15%', desc: 'Amount > 3.0x cardholder historical average' },
    { id: 'RULE_4', name: 'NEW_MERCHANT_HIGH_AMOUNT', weight: '15%', desc: 'Unseen merchant combined with amount > 2.0x average' },
    { id: 'RULE_5', name: 'DECLINED_FOLLOWED_BY_SUCCESS', weight: '10%', desc: 'Declined card-testing attempts followed by high success' },
    { id: 'RULE_6', name: 'MERCHANT_CARD_SWARM', weight: '5%', desc: '>=4 distinct cards used at same merchant in 5 minutes' },
    { id: 'RULE_7', name: 'UNUSUAL_TIME', weight: '10%', desc: 'Transaction initiated outside cardholder usual hours' },
  ]

  return (
    <div className="space-y-6">
      {/* Overview Banner */}
      <div className="glass-panel p-6 rounded-2xl border border-indigo-900/50 bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/40">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Cpu className="h-5 w-5 text-indigo-400" />
              <h2 className="text-lg font-bold text-white">Canonical Architecture & ML Feature Space</h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" />
                Zero Train-Serve Skew Verified
              </span>
            </div>
            <p className="text-xs text-slate-400 max-w-2xl">
              Sentinel AI operates on 18 observable canonical features extracted identically in batch (historical training)
              and real-time streaming (inference). Zero fabricated PCA components are referenced.
            </p>
          </div>

          <div className="flex items-center gap-3 bg-slate-950/80 p-3 rounded-xl border border-slate-800 font-mono text-xs text-slate-300">
            <div>
              <span className="text-slate-500 block text-[10px]">Active Model</span>
              <span className="text-white font-bold">RandomForest (100 est)</span>
            </div>
            <div className="h-6 w-px bg-slate-800" />
            <div>
              <span className="text-slate-500 block text-[10px]">Unsupervised</span>
              <span className="text-cyan-400 font-bold">IsolationForest</span>
            </div>
            <div className="h-6 w-px bg-slate-800" />
            <div>
              <span className="text-slate-500 block text-[10px]">Latency SLA</span>
              <span className="text-emerald-400 font-bold">&lt; 50 ms</span>
            </div>
          </div>
        </div>
      </div>

      {/* Hybrid Scoring Equation */}
      <div className="glass-panel p-5 rounded-xl border border-slate-800">
        <h3 className="text-sm font-bold text-white mb-2 flex items-center gap-2">
          <Layers className="h-4 w-4 text-indigo-400" />
          The Hybrid Scoring Formulation
        </h3>
        <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 font-mono text-sm text-center text-slate-200">
          <span className="text-indigo-400 font-bold">Risk Score</span> = (
          <span className="text-indigo-400 font-bold">0.50</span> × ML_Probability) + (
          <span className="text-amber-400 font-bold">0.30</span> × Behavioral_Anomaly) + (
          <span className="text-rose-400 font-bold">0.20</span> × Deterministic_Rules)
        </div>
        <div className="grid grid-cols-3 gap-3 mt-3 text-xs text-center text-slate-400">
          <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
            <span className="font-semibold text-emerald-400 block mb-0.5">LEGITIMATE</span>
            Score &lt; 0.40 (Auto-cleared)
          </div>
          <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
            <span className="font-semibold text-amber-400 block mb-0.5">SUSPICIOUS</span>
            0.40 &le; Score &lt; 0.70 (Review queue)
          </div>
          <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
            <span className="font-semibold text-rose-400 block mb-0.5">FRAUD</span>
            Score &ge; 0.70 (Block policy / Flagged)
          </div>
        </div>
      </div>

      {/* Grid: 18 Canonical Features & 7 Rules */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 18 Features */}
        <div className="glass-panel p-5 rounded-xl border border-slate-800">
          <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
            <Database className="h-4 w-4 text-cyan-400" />
            The 18 Canonical Features
          </h3>
          <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
            {canonicalFeatures.map((f, idx) => (
              <div
                key={f.name}
                className="p-2.5 rounded-lg bg-slate-900/70 border border-slate-800/80 flex items-start justify-between gap-3 text-xs"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-indigo-300">
                      #{idx + 1} {f.name}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">{f.desc}</p>
                </div>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono shrink-0">
                  Numeric
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* 7 Deterministic Rules */}
        <div className="glass-panel p-5 rounded-xl border border-slate-800">
          <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-rose-400" />
            The 7 Deterministic Fraud Rules
          </h3>
          <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
            {rules.map(r => (
              <div
                key={r.id}
                className="p-2.5 rounded-lg bg-slate-900/70 border border-slate-800/80 flex items-start justify-between gap-3 text-xs"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-rose-300">
                      {r.name}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-bold">
                      Weight: {r.weight}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">{r.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
