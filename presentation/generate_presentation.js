const pptxgen = require('pptxgenjs');
const fs = require('fs');
const path = require('path');

const FONT_NAME = 'Times New Roman';
const COLOR_TEXT = '000000';
const COLOR_BG = 'FFFFFF';
const COLOR_CARD_BG = 'F8F9FA';
const COLOR_BORDER = '000000';

function initSlide(pres, titleText) {
  const slide = pres.addSlide();
  slide.background = { color: COLOR_BG };
  
  // Topmost Institution Header: Centered horizontally, Bold, 24 pt, exactly 1 line
  slide.addText('ST. THOMAS INSTITUTE FOR SCIENCE AND TECHNOLOGY', {
    x: 0.1,
    y: 0.18,
    w: 9.8,
    h: 0.40,
    fontFace: FONT_NAME,
    fontSize: 24,
    bold: true,
    color: COLOR_TEXT,
    align: 'center',
    valign: 'middle',
    margin: 0
  });
  
  // Slide Heading: Top-Left, immediately below institution header, Bold, 22 pt
  slide.addText(titleText, {
    x: 0.6,
    y: 0.66,
    w: 8.8,
    h: 0.36,
    fontFace: FONT_NAME,
    fontSize: 22,
    bold: true,
    color: COLOR_TEXT,
    align: 'left',
    valign: 'middle',
    margin: 0
  });
  
  return slide;
}

// SLIDE 1: Introduction
function buildSlide1(pres, slide) {
  const bulletText = [
    {
      text: 'Financial Fraud Detection & Support: ',
      options: { bold: true, bullet: true }
    },
    {
      text: 'Automated real-time intelligence system inspecting payment transactions.',
      options: { breakLine: true }
    },
    {
      text: 'Hybrid Decision Intelligence: ',
      options: { bold: true, bullet: true }
    },
    {
      text: 'Synthesizes supervised machine learning, behavioral baselines, and fraud rules.',
      options: { breakLine: true }
    },
    {
      text: 'Streaming Processing Pipeline: ',
      options: { bold: true, bullet: true }
    },
    {
      text: 'Evaluates high-volume financial traffic with sub-15ms streaming latency.',
      options: { breakLine: true }
    },
    {
      text: 'Investigator Decision Support: ',
      options: { bold: true, bullet: true }
    },
    {
      text: 'Delivers plain-language risk explanations without halting banking operations.',
      options: { breakLine: false }
    }
  ];
  
  slide.addText(bulletText, {
    x: 0.6,
    y: 1.15,
    w: 4.7,
    h: 4.0,
    fontFace: FONT_NAME,
    fontSize: 17,
    color: COLOR_TEXT,
    paraSpaceAfter: 12,
    valign: 'top',
    margin: 0
  });
  
  const diagX = 5.5;
  const diagW = 3.9;
  
  // Box 1: Incoming Transaction
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: diagX,
    y: 1.15,
    w: diagW,
    h: 1.05,
    fill: { color: COLOR_CARD_BG },
    line: { color: COLOR_BORDER, width: 1.5 },
    rectRadius: 0.08
  });
  slide.addText([
    { text: 'Incoming Card Transaction', options: { bold: true, fontSize: 14.5, breakLine: true } },
    { text: 'Card ID: 999   •   Amount: $750.00', options: { fontSize: 12, breakLine: true } },
    { text: 'Merchant: LuxuryJewelry   •   Loc: Singapore', options: { fontSize: 12 } }
  ], {
    x: diagX + 0.1,
    y: 1.18,
    w: diagW - 0.2,
    h: 0.98,
    fontFace: FONT_NAME,
    color: COLOR_TEXT,
    align: 'center',
    valign: 'middle',
    margin: 0
  });
  
  // Arrow 1
  slide.addShape(pres.shapes.LINE, {
    x: diagX + diagW / 2,
    y: 2.23,
    w: 0,
    h: 0.30,
    line: { color: COLOR_BORDER, width: 1.8, endArrowType: 'triangle' }
  });
  
  // Box 2: Fraud Detection System
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: diagX,
    y: 2.56,
    w: diagW,
    h: 1.45,
    fill: { color: 'FFFFFF' },
    line: { color: COLOR_BORDER, width: 1.8 },
    rectRadius: 0.08
  });
  slide.addText([
    { text: 'Sentinel AI Detection Engine', options: { bold: true, fontSize: 14.5, breakLine: true } },
    { text: '• Supervised ML: Random Forest (0.50 weight)', options: { fontSize: 12, breakLine: true } },
    { text: '• Behavioral Baseline: Causal Windows (0.30 weight)', options: { fontSize: 12, breakLine: true } },
    { text: '• Deterministic Rules: 7 Business Logic Checks (0.20)', options: { fontSize: 12 } }
  ], {
    x: diagX + 0.15,
    y: 2.60,
    w: diagW - 0.3,
    h: 1.35,
    fontFace: FONT_NAME,
    color: COLOR_TEXT,
    align: 'left',
    valign: 'middle',
    margin: 5
  });
  
  // Arrow 2
  slide.addShape(pres.shapes.LINE, {
    x: diagX + diagW / 2,
    y: 4.04,
    w: 0,
    h: 0.30,
    line: { color: COLOR_BORDER, width: 1.8, endArrowType: 'triangle' }
  });
  
  // Box 3: Decision & Case Support
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: diagX,
    y: 4.37,
    w: diagW,
    h: 1.05,
    fill: { color: COLOR_CARD_BG },
    line: { color: COLOR_BORDER, width: 1.5 },
    rectRadius: 0.08
  });
  slide.addText([
    { text: 'Risk Score & Investigation Alert', options: { bold: true, fontSize: 14.5, breakLine: true } },
    { text: 'Decision: SUSPICIOUS (Score: 0.55)', options: { fontSize: 12.5, bold: true, breakLine: true } },
    { text: 'Reason: Impossible travel & amount 12.7x customer average', options: { fontSize: 11.5 } }
  ], {
    x: diagX + 0.1,
    y: 4.40,
    w: diagW - 0.2,
    h: 0.98,
    fontFace: FONT_NAME,
    color: COLOR_TEXT,
    align: 'center',
    valign: 'middle',
    margin: 0
  });
}

// SLIDE 2: Abstract
function buildSlide2(pres, slide) {
  const abstractPoints = [
    {
      text: 'The Fraud Problem: ',
      options: { bold: true, bullet: true }
    },
    {
      text: 'Surging electronic transactions require automated, low-latency detection of unauthorized card activity.',
      options: { breakLine: true }
    },
    {
      text: 'Personalized Behavioral Analytics: ',
      options: { bold: true, bullet: true }
    },
    {
      text: 'Combines ML models with dynamic cardholder spending baselines across sliding 1m, 10m, and 24h causal windows.',
      options: { breakLine: true }
    },
    {
      text: 'Real-Time Streaming Infrastructure: ',
      options: { bold: true, bullet: true }
    },
    {
      text: 'Engineered on Apache Kafka and Spark Structured Streaming to evaluate transactions in under 15 milliseconds.',
      options: { breakLine: true }
    },
    {
      text: 'Investigator Enablement: ',
      options: { bold: true, bullet: true }
    },
    {
      text: 'Produces composite risk scores alongside transparent, plain-English audit reasons for rapid dispute resolution.',
      options: { breakLine: false }
    }
  ];
  
  slide.addText(abstractPoints, {
    x: 0.6,
    y: 1.15,
    w: 8.8,
    h: 2.15,
    fontFace: FONT_NAME,
    fontSize: 16,
    color: COLOR_TEXT,
    paraSpaceAfter: 5,
    valign: 'top',
    margin: 0
  });
  
  const flowY = 3.65;
  const cardH = 1.65;
  const cardW = 1.88;
  const gap = 0.42;
  
  const steps = [
    {
      title: '1. Transaction',
      sub1: 'Event Ingestion',
      sub2: 'Kafka streaming buffer ensures zero packet loss.'
    },
    {
      title: '2. Analysis',
      sub1: 'Temporal Windows',
      sub2: 'Extracts features & checks 1m/10m/24h velocity.'
    },
    {
      title: '3. Risk Score',
      sub1: 'Hybrid Engine',
      sub2: 'Weights ML (0.50), behavior (0.30) & rules (0.20).'
    },
    {
      title: '4. Investigation',
      sub1: 'Decision Support',
      sub2: 'Opens case with plain-English audit reasons.'
    }
  ];
  
  steps.forEach((step, idx) => {
    const cardX = 0.6 + idx * (cardW + gap);
    
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: cardX,
      y: flowY,
      w: cardW,
      h: cardH,
      fill: { color: COLOR_CARD_BG },
      line: { color: COLOR_BORDER, width: 1.5 },
      rectRadius: 0.08
    });
    
    slide.addText([
      { text: step.title, options: { bold: true, fontSize: 14.5, breakLine: true } },
      { text: step.sub1, options: { bold: true, fontSize: 12.5, breakLine: true } },
      { text: step.sub2, options: { fontSize: 11 } }
    ], {
      x: cardX + 0.08,
      y: flowY + 0.08,
      w: cardW - 0.16,
      h: cardH - 0.16,
      fontFace: FONT_NAME,
      color: COLOR_TEXT,
      align: 'center',
      valign: 'middle',
      margin: 0
    });
    
    if (idx < steps.length - 1) {
      const arrowX = cardX + cardW + 0.05;
      slide.addShape(pres.shapes.LINE, {
        x: arrowX,
        y: flowY + cardH / 2,
        w: gap - 0.1,
        h: 0,
        line: { color: COLOR_BORDER, width: 2.0, endArrowType: 'triangle' }
      });
    }
  });
}

// SLIDE 3: Problem Statement
function buildSlide3(pres, slide) {
  const topBullets = [
    { text: 'Massive Volumes: ', options: { bold: true, bullet: true } },
    { text: 'Millions of daily transactions make manual analyst review impossible.', options: { breakLine: true } },
    { text: 'Static Rule Limits: ', options: { bold: true, bullet: true } },
    { text: 'Rigid threshold rules miss complex schemes and trigger excessive false declines.', options: { breakLine: true } },
    { text: 'Latency & Explainability: ', options: { bold: true, bullet: true } },
    { text: 'Batch detection delays response, while black-box models lack clear audit trails.', options: { breakLine: false } }
  ];
  
  slide.addText(topBullets, {
    x: 0.6,
    y: 1.05,
    w: 8.8,
    h: 0.90,
    fontFace: FONT_NAME,
    fontSize: 14.5,
    color: COLOR_TEXT,
    paraSpaceAfter: 3,
    valign: 'top',
    margin: 0
  });
  
  const cardY = 2.05;
  const cardH = 3.35;
  const cardW = 4.25;
  
  // Left: Traditional Limitations
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.6,
    y: cardY,
    w: cardW,
    h: cardH,
    fill: { color: COLOR_CARD_BG },
    line: { color: COLOR_BORDER, width: 1.5 },
    rectRadius: 0.08
  });
  
  slide.addText('Traditional Fraud Detection (Limitations)', {
    x: 0.75,
    y: cardY + 0.12,
    w: cardW - 0.3,
    h: 0.30,
    fontFace: FONT_NAME,
    fontSize: 14.5,
    bold: true,
    color: COLOR_TEXT,
    align: 'center',
    valign: 'middle',
    margin: 0
  });
  
  const leftItems = [
    { text: '• Massive Volume: ', options: { bold: true } },
    { text: 'Manual analyst review is impossible across millions of hourly charges.', options: { breakLine: true } },
    { text: '• Rigid Static Limits: ', options: { bold: true } },
    { text: 'Fixed global thresholds ignore individual habits, causing high false declines.', options: { breakLine: true } },
    { text: '• Black-Box AI: ', options: { bold: true } },
    { text: 'Opaque neural probabilities fail to explain why transactions were flagged.', options: { breakLine: true } },
    { text: '• Settlement Latency: ', options: { bold: true } },
    { text: 'Overnight batch processing discovers fraud hours or days after funds are lost.', options: { breakLine: false } }
  ];
  
  slide.addText(leftItems, {
    x: 0.8,
    y: cardY + 0.44,
    w: cardW - 0.4,
    h: 2.75,
    fontFace: FONT_NAME,
    fontSize: 12,
    color: COLOR_TEXT,
    paraSpaceAfter: 7,
    align: 'left',
    valign: 'top',
    margin: 5
  });
  
  // Right: Sentinel AI Solution
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 5.15,
    y: cardY,
    w: cardW,
    h: cardH,
    fill: { color: 'FFFFFF' },
    line: { color: COLOR_BORDER, width: 1.5 },
    rectRadius: 0.08
  });
  
  slide.addText('Sentinel AI Approach (Solutions)', {
    x: 5.30,
    y: cardY + 0.12,
    w: cardW - 0.3,
    h: 0.30,
    fontFace: FONT_NAME,
    fontSize: 14.5,
    bold: true,
    color: COLOR_TEXT,
    align: 'center',
    valign: 'middle',
    margin: 0
  });
  
  const rightItems = [
    { text: '• Automated Ingestion: ', options: { bold: true } },
    { text: 'Apache Kafka buffers high-throughput transaction streams with zero data loss.', options: { breakLine: true } },
    { text: '• Personalized Baselines: ', options: { bold: true } },
    { text: 'Dynamic spending profiles track customer-specific normal behavior in causal windows.', options: { breakLine: true } },
    { text: '• Explainable Hybrid Scoring: ', options: { bold: true } },
    { text: 'Combines ML, behavior, and 7 business rules with plain-language explanations.', options: { breakLine: true } },
    { text: '• Millisecond Response: ', options: { bold: true } },
    { text: 'Sub-15ms evaluation latency delivers immediate risk intelligence to analysts.', options: { breakLine: false } }
  ];
  
  slide.addText(rightItems, {
    x: 5.35,
    y: cardY + 0.44,
    w: cardW - 0.4,
    h: 2.75,
    fontFace: FONT_NAME,
    color: COLOR_TEXT,
    fontSize: 12,
    paraSpaceAfter: 7,
    align: 'left',
    valign: 'top',
    margin: 5
  });
}

// SLIDE 4: Architecture
function buildSlide4(pres, slide) {
  slide.addText('Event-driven, decoupled big-data architecture verified in project codebase and container deployment.', {
    x: 0.6,
    y: 1.10,
    w: 8.8,
    h: 0.28,
    fontFace: FONT_NAME,
    fontSize: 15,
    italic: true,
    color: COLOR_TEXT,
    align: 'left',
    margin: 0
  });
  
  const colY = 1.45;
  const colW = 2.55;
  
  // Col 1: Ingestion
  slide.addText('1. Ingestion & Streaming', {
    x: 0.60, y: colY, w: colW, h: 0.28,
    fontFace: FONT_NAME, fontSize: 14, bold: true, align: 'center', margin: 0
  });
  
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.60, y: colY + 0.32, w: colW, h: 1.45,
    fill: { color: COLOR_CARD_BG }, line: { color: COLOR_BORDER, width: 1.5 }, rectRadius: 0.06
  });
  slide.addText([
    { text: 'Transaction Generator / API', options: { bold: true, fontSize: 13.5, breakLine: true } },
    { text: '• Emits canonical JSON events', options: { fontSize: 11.5, breakLine: true } },
    { text: '• Simulates normal & attack traffic', options: { fontSize: 11.5, breakLine: true } },
    { text: '• Canonical schema validation', options: { fontSize: 11.5 } }
  ], {
    x: 0.68, y: colY + 0.36, w: colW - 0.16, h: 1.35,
    fontFace: FONT_NAME, color: COLOR_TEXT, align: 'left', valign: 'middle', margin: 5
  });
  
  slide.addShape(pres.shapes.LINE, {
    x: 0.60 + colW / 2, y: colY + 1.80, w: 0, h: 0.25,
    line: { color: COLOR_BORDER, width: 1.8, endArrowType: 'triangle' }
  });
  
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.60, y: colY + 2.08, w: colW, h: 1.55,
    fill: { color: 'FFFFFF' }, line: { color: COLOR_BORDER, width: 1.5 }, rectRadius: 0.06
  });
  slide.addText([
    { text: 'Apache Kafka 3.7 (KRaft)', options: { bold: true, fontSize: 13.5, breakLine: true } },
    { text: '• Topic: transactions-canonical', options: { fontSize: 11.5, breakLine: true } },
    { text: '• 3 Distributed partitions', options: { fontSize: 11.5, breakLine: true } },
    { text: '• Resilient streaming buffer', options: { fontSize: 11.5 } }
  ], {
    x: 0.68, y: colY + 2.12, w: colW - 0.16, h: 1.45,
    fontFace: FONT_NAME, color: COLOR_TEXT, align: 'left', valign: 'middle', margin: 5
  });
  
  slide.addShape(pres.shapes.LINE, {
    x: 0.60 + colW, y: colY + 2.85, w: 0.45, h: 0,
    line: { color: COLOR_BORDER, width: 2.0, endArrowType: 'triangle' }
  });
  
  // Col 2: Spark & Scoring
  const col2X = 3.65;
  slide.addText('2. Stream Processing & Scoring', {
    x: col2X, y: colY, w: colW + 0.2, h: 0.28,
    fontFace: FONT_NAME, fontSize: 14, bold: true, align: 'center', margin: 0
  });
  
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: col2X, y: colY + 0.32, w: colW + 0.2, h: 1.45,
    fill: { color: COLOR_CARD_BG }, line: { color: COLOR_BORDER, width: 1.5 }, rectRadius: 0.06
  });
  slide.addText([
    { text: 'Spark Structured Streaming', options: { bold: true, fontSize: 13.5, breakLine: true } },
    { text: '• Micro-batch processing engine', options: { fontSize: 11.5, breakLine: true } },
    { text: '• Feature normalization & MCC', options: { fontSize: 11.5, breakLine: true } },
    { text: '• Causal windows: 1m, 10m, 24h', options: { fontSize: 11.5 } }
  ], {
    x: col2X + 0.08, y: colY + 0.36, w: colW + 0.04, h: 1.35,
    fontFace: FONT_NAME, color: COLOR_TEXT, align: 'left', valign: 'middle', margin: 5
  });
  
  slide.addShape(pres.shapes.LINE, {
    x: col2X + (colW + 0.2) / 2, y: colY + 1.80, w: 0, h: 0.25,
    line: { color: COLOR_BORDER, width: 1.8, endArrowType: 'triangle' }
  });
  
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: col2X, y: colY + 2.08, w: colW + 0.2, h: 1.55,
    fill: { color: 'FFFFFF' }, line: { color: COLOR_BORDER, width: 1.8 }, rectRadius: 0.06
  });
  slide.addText([
    { text: 'Hybrid Fraud Scoring Engine', options: { bold: true, fontSize: 13.5, breakLine: true } },
    { text: '• 0.50 × Random Forest ML', options: { fontSize: 11.5, breakLine: true } },
    { text: '• 0.30 × Behavioral Anomaly Baseline', options: { fontSize: 11.5, breakLine: true } },
    { text: '• 0.20 × 7 Deterministic Fraud Rules', options: { fontSize: 11.5, breakLine: true } },
    { text: '• Produces plain-English audit reasons', options: { bold: true, fontSize: 11 } }
  ], {
    x: col2X + 0.08, y: colY + 2.12, w: colW + 0.04, h: 1.45,
    fontFace: FONT_NAME, color: COLOR_TEXT, align: 'left', valign: 'middle', margin: 5
  });
  
  slide.addShape(pres.shapes.LINE, {
    x: col2X + colW + 0.2, y: colY + 2.85, w: 0.45, h: 0,
    line: { color: COLOR_BORDER, width: 2.0, endArrowType: 'triangle' }
  });
  
  // Col 3: Storage & Apps
  const col3X = 6.85;
  slide.addText('3. Persistence & Interfaces', {
    x: col3X, y: colY, w: colW, h: 0.28,
    fontFace: FONT_NAME, fontSize: 14, bold: true, align: 'center', margin: 0
  });
  
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: col3X, y: colY + 0.32, w: colW, h: 1.45,
    fill: { color: COLOR_CARD_BG }, line: { color: COLOR_BORDER, width: 1.5 }, rectRadius: 0.06
  });
  slide.addText([
    { text: 'PostgreSQL 15 / Supabase', options: { bold: true, fontSize: 13.5, breakLine: true } },
    { text: '• Decoupled schema tables:\n   transactions, predictions, cases', options: { fontSize: 11, breakLine: true } },
    { text: '• Row-Level Security (RLS) policies', options: { fontSize: 11.5 } }
  ], {
    x: col3X + 0.08, y: colY + 0.36, w: colW - 0.16, h: 1.35,
    fontFace: FONT_NAME, color: COLOR_TEXT, align: 'left', valign: 'middle', margin: 5
  });
  
  slide.addShape(pres.shapes.LINE, {
    x: col3X + colW / 2, y: colY + 1.80, w: 0, h: 0.25,
    line: { color: COLOR_BORDER, width: 1.8, endArrowType: 'triangle' }
  });
  
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: col3X, y: colY + 2.08, w: colW, h: 1.55,
    fill: { color: 'FFFFFF' }, line: { color: COLOR_BORDER, width: 1.5 }, rectRadius: 0.06
  });
  slide.addText([
    { text: 'FastAPI & Web Applications', options: { bold: true, fontSize: 13.5, breakLine: true } },
    { text: '• FastAPI backend (JWT & RBAC)', options: { fontSize: 11.5, breakLine: true } },
    { text: '• Next.js 15 Investigator Portal', options: { fontSize: 11.5, breakLine: true } },
    { text: '• Streamlit Real-Time KPI Dashboard', options: { fontSize: 11.5 } }
  ], {
    x: col3X + 0.08, y: colY + 2.12, w: colW - 0.16, h: 1.45,
    fontFace: FONT_NAME, color: COLOR_TEXT, align: 'left', valign: 'middle', margin: 5
  });
}

// SLIDE 5: Methodology
function buildSlide5(pres, slide) {
  slide.addText('Transaction lifecycle: 6 sequential stages ensuring low-latency evaluation and explainable reasoning.', {
    x: 0.6,
    y: 1.10,
    w: 8.8,
    h: 0.28,
    fontFace: FONT_NAME,
    fontSize: 15,
    italic: true,
    color: COLOR_TEXT,
    margin: 0
  });
  
  const startY = 1.45;
  const boxW = 2.70;
  const boxH = 1.45;
  const gapX = 0.35;
  const gapY = 0.20;
  
  const stepsData = [
    {
      num: '1',
      title: 'Event Ingestion',
      desc: 'Validates canonical schema and buffers transaction in Kafka topic (transactions-canonical).'
    },
    {
      num: '2',
      title: 'Feature Extraction',
      desc: 'Computes normalized amount, log1p, cyclic time (hour sin/cos), MCC weight, and channel risk.'
    },
    {
      num: '3',
      title: 'Behavioral Profiling',
      desc: 'Evaluates spending velocity across sliding 1m, 10m, and 24h causal windows to detect deviations.'
    },
    {
      num: '4',
      title: 'Hybrid Risk Scoring',
      desc: 'Evaluates Random Forest (0.50), behavioral baseline (0.30), and 7 business rules (0.20).'
    },
    {
      num: '5',
      title: 'Database Persistence',
      desc: 'Persists records to decoupled PostgreSQL tables (transactions, predictions, fraud_cases).'
    },
    {
      num: '6',
      title: 'Investigator Telemetry',
      desc: 'Displays risk breakdown, telemetry, and plain-English audit reasons on the Next.js portal.'
    }
  ];
  
  stepsData.forEach((st, i) => {
    const row = Math.floor(i / 3);
    const col = i % 3;
    const x = 0.60 + col * (boxW + gapX);
    const y = startY + row * (boxH + gapY);
    
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: x,
      y: y,
      w: boxW,
      h: boxH,
      fill: { color: COLOR_CARD_BG },
      line: { color: COLOR_BORDER, width: 1.5 },
      rectRadius: 0.08
    });
    
    slide.addText([
      { text: `Step ${st.num}: ${st.title}`, options: { bold: true, fontSize: 14, breakLine: true } },
      { text: st.desc, options: { fontSize: 11.5 } }
    ], {
      x: x + 0.12,
      y: y + 0.08,
      w: boxW - 0.24,
      h: boxH - 0.16,
      fontFace: FONT_NAME,
      color: COLOR_TEXT,
      align: 'left',
      valign: 'middle',
      margin: 5
    });
  });
  
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.60,
    y: 4.80,
    w: 8.80,
    h: 0.65,
    fill: { color: 'FFFFFF' },
    line: { color: COLOR_BORDER, width: 1.5 },
    rectRadius: 0.06
  });
  
  slide.addText([
    { text: 'Implemented Scoring Formula: ', options: { bold: true, fontSize: 13 } },
    { text: 'Final Score = (0.50 × ML Score) + (0.30 × Behavior Score) + (0.20 × Rule Score)', options: { fontSize: 13, breakLine: true } },
    { text: 'Decision Boundaries: ', options: { bold: true, fontSize: 12.5 } },
    { text: 'Legitimate (< 0.40)   •   Suspicious (0.40 – 0.69)   •   Fraud (≥ 0.70)', options: { fontSize: 12.5 } }
  ], {
    x: 0.70,
    y: 4.83,
    w: 8.60,
    h: 0.58,
    fontFace: FONT_NAME,
    color: COLOR_TEXT,
    align: 'center',
    valign: 'middle',
    margin: 0
  });
}

// SLIDE 6: Use Case Diagram
function buildSlide6(pres, slide) {
  slide.addText('Standard UML Use Case Diagram matching implemented role permissions and PostgreSQL RLS security.', {
    x: 0.6,
    y: 1.10,
    w: 8.8,
    h: 0.28,
    fontFace: FONT_NAME,
    fontSize: 15,
    italic: true,
    color: COLOR_TEXT,
    margin: 0
  });
  
  const boundaryX = 2.40;
  const boundaryY = 1.48;
  const boundaryW = 5.20;
  const boundaryH = 3.95;
  
  slide.addShape(pres.shapes.RECTANGLE, {
    x: boundaryX,
    y: boundaryY,
    w: boundaryW,
    h: boundaryH,
    fill: { color: 'FFFFFF' },
    line: { color: COLOR_BORDER, width: 1.8 }
  });
  
  slide.addText('Sentinel AI System Boundary', {
    x: boundaryX + 0.20,
    y: boundaryY + 0.08,
    w: boundaryW - 0.40,
    h: 0.28,
    fontFace: FONT_NAME,
    fontSize: 14,
    bold: true,
    align: 'center',
    margin: 0
  });
  
  function addUseCaseEllipse(text, x, y, w, h) {
    slide.addShape(pres.shapes.OVAL, {
      x: x,
      y: y,
      w: w,
      h: h,
      fill: { color: COLOR_CARD_BG },
      line: { color: COLOR_BORDER, width: 1.3 }
    });
    slide.addText(text, {
      x: x + 0.05,
      y: y + 0.03,
      w: w - 0.10,
      h: h - 0.06,
      fontFace: FONT_NAME,
      fontSize: 11,
      bold: true,
      color: COLOR_TEXT,
      align: 'center',
      valign: 'middle',
      margin: 0
    });
  }
  
  // Ellipses inside boundary
  addUseCaseEllipse('Manage User Access\n& Storage', 2.65, 1.88, 2.25, 0.55);
  addUseCaseEllipse('View Analytics &\nModel Health', 5.10, 1.88, 2.25, 0.55);
  
  addUseCaseEllipse('Sign In &\nAuthenticate', 3.88, 2.58, 2.25, 0.52);
  
  addUseCaseEllipse('Monitor Live\nTransactions', 2.65, 3.25, 2.25, 0.55);
  addUseCaseEllipse('Inspect Transaction\nDetails', 2.65, 3.95, 2.25, 0.55);
  addUseCaseEllipse('Review & Resolve\nFraud Cases', 2.65, 4.65, 2.25, 0.55);
  
  addUseCaseEllipse('View Personal\nTransactions', 5.10, 3.45, 2.25, 0.55);
  addUseCaseEllipse('Report Unrecognized\nCharge', 5.10, 4.25, 2.25, 0.55);
  
  // ACTOR 1: Administrator
  slide.addShape(pres.shapes.OVAL, {
    x: 0.95, y: 1.65, w: 0.30, h: 0.30,
    fill: { color: 'FFFFFF' }, line: { color: COLOR_BORDER, width: 1.5 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 1.10, y: 1.95, w: 0, h: 0.30,
    line: { color: COLOR_BORDER, width: 1.5 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 0.90, y: 2.07, w: 0.40, h: 0,
    line: { color: COLOR_BORDER, width: 1.5 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 1.10, y: 2.25, w: -0.15, h: 0.22,
    line: { color: COLOR_BORDER, width: 1.5 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 1.10, y: 2.25, w: 0.15, h: 0.22,
    line: { color: COLOR_BORDER, width: 1.5 }
  });
  slide.addText('Administrator', {
    x: 0.30, y: 2.50, w: 1.60, h: 0.28,
    fontFace: FONT_NAME, fontSize: 13, bold: true, align: 'center', margin: 0
  });
  
  slide.addShape(pres.shapes.LINE, {
    x: 1.35, y: 2.05, w: 1.30, h: 0.10,
    line: { color: COLOR_BORDER, width: 1.2 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 1.35, y: 2.10, w: 2.53, h: 0.70,
    line: { color: COLOR_BORDER, width: 1.2 }
  });
  
  // ACTOR 2: Fraud Investigator
  slide.addShape(pres.shapes.OVAL, {
    x: 0.95, y: 3.50, w: 0.30, h: 0.30,
    fill: { color: 'FFFFFF' }, line: { color: COLOR_BORDER, width: 1.5 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 1.10, y: 3.80, w: 0, h: 0.30,
    line: { color: COLOR_BORDER, width: 1.5 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 0.90, y: 3.92, w: 0.40, h: 0,
    line: { color: COLOR_BORDER, width: 1.5 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 1.10, y: 4.10, w: -0.15, h: 0.22,
    line: { color: COLOR_BORDER, width: 1.5 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 1.10, y: 4.10, w: 0.15, h: 0.22,
    line: { color: COLOR_BORDER, width: 1.5 }
  });
  slide.addText('Fraud\nInvestigator', {
    x: 0.30, y: 4.35, w: 1.60, h: 0.45,
    fontFace: FONT_NAME, fontSize: 13, bold: true, align: 'center', margin: 0
  });
  
  slide.addShape(pres.shapes.LINE, {
    x: 1.35, y: 3.80, w: 1.30, h: -0.28,
    line: { color: COLOR_BORDER, width: 1.2 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 1.35, y: 3.95, w: 1.30, h: 0.25,
    line: { color: COLOR_BORDER, width: 1.2 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 1.35, y: 4.05, w: 1.30, h: 0.85,
    line: { color: COLOR_BORDER, width: 1.2 }
  });
  
  // ACTOR 3: Customer
  const custX = 8.65;
  slide.addShape(pres.shapes.OVAL, {
    x: custX - 0.15, y: 3.00, w: 0.30, h: 0.30,
    fill: { color: 'FFFFFF' }, line: { color: COLOR_BORDER, width: 1.5 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: custX, y: 3.30, w: 0, h: 0.30,
    line: { color: COLOR_BORDER, width: 1.5 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: custX - 0.20, y: 3.42, w: 0.40, h: 0,
    line: { color: COLOR_BORDER, width: 1.5 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: custX, y: 3.60, w: -0.15, h: 0.22,
    line: { color: COLOR_BORDER, width: 1.5 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: custX, y: 3.60, w: 0.15, h: 0.22,
    line: { color: COLOR_BORDER, width: 1.5 }
  });
  slide.addText('Customer\n(Cardholder)', {
    x: 7.85, y: 3.85, w: 1.60, h: 0.45,
    fontFace: FONT_NAME, fontSize: 13, bold: true, align: 'center', margin: 0
  });
  
  slide.addShape(pres.shapes.LINE, {
    x: 7.35, y: 3.65, w: 1.15, h: -0.10,
    line: { color: COLOR_BORDER, width: 1.2 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 7.35, y: 4.45, w: 1.15, h: -0.80,
    line: { color: COLOR_BORDER, width: 1.2 }
  });
}

// SLIDE 7: Conclusion
function buildSlide7(pres, slide) {
  const conclusionPoints = [
    {
      text: 'Hybrid AI Intelligence: ',
      options: { bold: true, bullet: true }
    },
    {
      text: 'Combines ML (0.50), behavioral baselines (0.30), and 7 fraud rules (0.20).',
      options: { breakLine: true }
    },
    {
      text: 'Streaming Pipeline: ',
      options: { bold: true, bullet: true }
    },
    {
      text: 'Demonstrates sub-15ms real-time processing via Apache Kafka and Spark.',
      options: { breakLine: true }
    },
    {
      text: 'Investigator Enablement: ',
      options: { bold: true, bullet: true }
    },
    {
      text: 'Generates composite risk scores and plain-language explainable audit reasons.',
      options: { breakLine: true }
    },
    {
      text: 'Production Extensibility: ',
      options: { bold: true, bullet: true }
    },
    {
      text: 'Modular foundation readily extensible to core banking APIs and active learning.',
      options: { breakLine: false }
    }
  ];
  
  slide.addText(conclusionPoints, {
    x: 0.6,
    y: 1.05,
    w: 8.8,
    h: 1.20,
    fontFace: FONT_NAME,
    fontSize: 14.5,
    color: COLOR_TEXT,
    paraSpaceAfter: 4,
    valign: 'top',
    margin: 0
  });
  
  const calloutY = 2.45;
  const calloutH = 2.90;
  
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.6,
    y: calloutY,
    w: 8.8,
    h: calloutH,
    fill: { color: COLOR_CARD_BG },
    line: { color: COLOR_BORDER, width: 1.5 },
    rectRadius: 0.08
  });
  
  slide.addText('Project Scope, Data Transparency & Academic Boundary', {
    x: 0.8,
    y: calloutY + 0.12,
    w: 8.4,
    h: 0.30,
    fontFace: FONT_NAME,
    fontSize: 14.5,
    bold: true,
    color: COLOR_TEXT,
    align: 'left',
    margin: 0
  });
  
  const scopeItems = [
    { text: '• Anonymized Benchmark Dataset: ', options: { bold: true } },
    { text: 'Offline model benchmarking conducted on public ULB Kaggle fraud dataset (284,807 transactions across 48 hours).', options: { breakLine: true } },
    { text: '• Synthetic Streaming Scenarios: ', options: { bold: true } },
    { text: 'Live demonstration identities (card_id), merchant names, and travel sequences are synthetic simulations.', options: { breakLine: true } },
    { text: '• Analytical Decision Support: ', options: { bold: true } },
    { text: 'Sentinel AI operates as an analytical investigation platform; it does not freeze bank accounts or connect to live card networks.', options: { breakLine: false } }
  ];
  
  slide.addText(scopeItems, {
    x: 0.8,
    y: calloutY + 0.46,
    w: 8.4,
    h: 2.25,
    fontFace: FONT_NAME,
    fontSize: 12.5,
    color: COLOR_TEXT,
    paraSpaceAfter: 8,
    align: 'left',
    valign: 'top',
    margin: 5
  });
}

async function main() {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_16x9';
  
  const s1 = initSlide(pres, 'Introduction');
  buildSlide1(pres, s1);
  
  const s2 = initSlide(pres, 'Abstract');
  buildSlide2(pres, s2);
  
  const s3 = initSlide(pres, 'Problem Statement');
  buildSlide3(pres, s3);
  
  const s4 = initSlide(pres, 'Architecture');
  buildSlide4(pres, s4);
  
  const s5 = initSlide(pres, 'Methodology');
  buildSlide5(pres, s5);
  
  const s6 = initSlide(pres, 'Use Case Diagram');
  buildSlide6(pres, s6);
  
  const s7 = initSlide(pres, 'Conclusion');
  buildSlide7(pres, s7);
  
  const outputPath = path.join(__dirname, 'Sentinel_AI_Presentation.pptx');
  await pres.writeFile({ fileName: outputPath });
  console.log(`Successfully generated full presentation: ${outputPath}`);
  
  // Single-slide exports for previewing
  const previewDir = path.join(__dirname, 'slides_preview');
  if (!fs.existsSync(previewDir)) fs.mkdirSync(previewDir, { recursive: true });
  
  const slidesList = [
    { num: 1, title: 'Introduction', fn: buildSlide1 },
    { num: 2, title: 'Abstract', fn: buildSlide2 },
    { num: 3, title: 'Problem Statement', fn: buildSlide3 },
    { num: 4, title: 'Architecture', fn: buildSlide4 },
    { num: 5, title: 'Methodology', fn: buildSlide5 },
    { num: 6, title: 'Use Case Diagram', fn: buildSlide6 },
    { num: 7, title: 'Conclusion', fn: buildSlide7 }
  ];
  
  for (const item of slidesList) {
    const single = new pptxgen();
    single.layout = 'LAYOUT_16x9';
    const s = initSlide(single, item.title);
    item.fn(single, s);
    const out = path.join(previewDir, `slide_${item.num}.pptx`);
    await single.writeFile({ fileName: out });
  }
  console.log(`Successfully generated all 7 single slide decks in ${previewDir}`);
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
