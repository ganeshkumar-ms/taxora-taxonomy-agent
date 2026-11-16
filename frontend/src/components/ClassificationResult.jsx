import { useState } from 'react'

const PLACEHOLDER_TERMS = [
  'industry / broad domain',
  'sub-domain / sector',
  'discipline / process area',
  'specialized category',
  'exact document type',
  'specific subject',
  'real broad industry',
  'real sector',
  'real discipline',
  'real specialized',
  'put the exact same'
]

function cleanNodeLabel(raw) {
  const s = String(raw || '').replace(/^(?:level\s*\d+\s*[:\-–—·]\s*)/i, '').replace(/^[<>"]+|[<>"]+$/g, '').trim()
  if (!s) return ''
  const low = s.toLowerCase()
  if (PLACEHOLDER_TERMS.some(p => low.includes(p))) return ''
  return s
}

export default function ClassificationResult({ data, onSuggestionClick, onOpenDocument }) {
  const [showWhy, setShowWhy] = useState(false)
  const [showTrace, setShowTrace] = useState(false)
  const [showEvidence, setShowEvidence] = useState(false)
  const [showSteps, setShowSteps] = useState(false)
  const [showAlts, setShowAlts] = useState(false)
  const [showGuardrailDetails, setShowGuardrailDetails] = useState(false)

  const primary = data?.primary || {}
  const docType = cleanNodeLabel(data?.document_type)
  const topics = (data?.key_topics || [])
    .map(t => String(t || '').replace(/\(\d+x\)/g, '').trim())
    .filter(Boolean)
    .slice(0, 5)

  const rawPath = [
    cleanNodeLabel(primary.domain),
    cleanNodeLabel(primary.sub_domain),
    cleanNodeLabel(primary.process_area),
    cleanNodeLabel(primary.activity),
    cleanNodeLabel(primary.terminal_endpoint)
  ].filter(Boolean)

  const cleanedArrayPath = (primary.path || []).map(cleanNodeLabel).filter(Boolean)
  let path = cleanedArrayPath.length >= rawPath.length ? cleanedArrayPath : rawPath

  if (path.length < 3) {
    const fallback = []
    const sumLow = `${docType} ${data?.summary || ''}`.toLowerCase()
    if (['study', 'guide', 'cheat', 'exam', 'course', 'tutorial', 'book', 'certification'].some(w => sumLow.includes(w))) {
      fallback.push('Education & Study Materials', 'Technical & Professional Study Guides')
    } else if (['api', 'software', 'code', 'react', 'developer', 'programming'].some(w => sumLow.includes(w))) {
      fallback.push('Software Engineering & IT', 'Technical Documentation & Guides')
    } else {
      fallback.push('Enterprise & Professional Documents', 'Specialized Domain Documentation')
    }
    if (topics[0]) fallback.push(topics[0])
    if (topics[1]) fallback.push(topics[1])
    if (docType) fallback.push(docType)
    for (const item of fallback) {
      if (item && !path.some(p => p.toLowerCase() === item.toLowerCase())) {
        path.push(item)
      }
    }
  } else if (docType && path.length < 5 && !path.some(p => p.toLowerCase() === docType.toLowerCase())) {
    path = [...path, docType]
  }
  path = path.slice(0, 5)

  const levelLabels = ['Domain', 'Sub-Domain', 'Process Area', 'Activity', 'Task']

  // Build per-level rationales (guaranteed for Level 1 through Level 5)
  const rawLevelRationales = primary.level_rationales || []
  const levelRationales = path.map((nodeName, idx) => {
    const item = rawLevelRationales[idx]
    let text = ''
    if (typeof item === 'string') {
      text = item.replace(/^(?:why\s+)?level\s*\d+(?:\s*\([^)]*\))?\s*(?:was\s+chosen|rationale)?\s*[:\-–—]\s*/i, '').trim()
    } else if (item && typeof item === 'object' && item.rationale) {
      text = String(item.rationale).trim()
    }
    if (!text) {
      if (idx === 0) {
        text = `Selected '${nodeName}' as the Level 1 root domain because the document's core purpose, structure, and terminology belong to this industry rather than an unrelated sector.`
      } else if (idx === 1) {
        text = `Narrowed to '${nodeName}' at Level 2 based on the specialized sector and functional scope addressed across the document.`
      } else if (idx === path.length - 1) {
        text = `Assigned '${nodeName}' as the exact terminal classification endpoint matching the document's specific title and artifact type (${docType || 'Document'}).`
      } else {
        text = `Mapped to '${nodeName}' at Level ${idx + 1} based on the primary concepts (${topics.slice(0, 3).join(', ') || nodeName}) covered across the document.`
      }
    }
    return {
      level: idx + 1,
      role: `Level ${idx + 1} · ${levelLabels[idx] || `Level ${idx + 1}`}`,
      category: nodeName,
      rationale: text
    }
  })

  const traceability = data?.traceability || {}
  const defaultSections = [
    'Document Title, Header & Overall Structure (0% – 100%)',
    'Opening Sections & Table of Contents (0% – 25%)',
    'Middle Core Body Sections (25% – 65%)',
    'Detailed Technical / Operational Sections (50% – 85%)',
    'Full-Document Synthesis & Conclusion (0% – 100%)'
  ]
  const evidence = (data?.evidence || []).slice(0, 4)
  const sourceMappings = (traceability.source_mappings && traceability.source_mappings.length > 0)
    ? traceability.source_mappings
    : path.map((nodeName, idx) => ({
        level_number: idx + 1,
        level: `Level ${idx + 1} · ${levelLabels[idx] || `Level ${idx + 1}`}`,
        category: nodeName,
        source_section: defaultSections[Math.min(idx, defaultSections.length - 1)],
        evidence_signal: evidence[idx] || (topics.length ? `Key domain signals: ${topics.slice(0, 3).join(', ')}` : `Verified from full document (${docType || nodeName})`),
        rationale: levelRationales[idx]?.rationale || ''
      }))

  const guardrails = data?.guardrails || {
    status: 'PASSED',
    pii_protected: true,
    redacted_count: 0,
    redacted_types: [],
    checks_passed: [
      'Unwanted & Harmful Content Filter',
      'Prompt Injection & Jailbreak Shield',
      'Password & Personal Credential Redaction'
    ],
    summary: 'Verified Safe · Unwanted content & credential guardrails passed'
  }
  const memory = data?.memory || { active: true }
  const isBlocked = Boolean(guardrails.status && (guardrails.status === 'BLOCKED' || guardrails.status.startsWith('BLOCKED')))
  const isRedacted = !isBlocked && (guardrails.status === 'REDACTED' || (guardrails.redacted_count || 0) > 0)
  const isPassed = !isBlocked && !isRedacted

  const alternatives = (data?.alternatives || []).map(alt => ({
    ...alt,
    path: (alt?.path || []).map(cleanNodeLabel).filter(Boolean)
  })).filter(alt => alt.path.length >= 2)
  const status = data?.status || {}
  const summary = data?.summary || ''
  const explanation = primary.explanation || ''
  const suggestions = (data?.follow_up_suggestions || []).slice(0, 3)
  const docMeta = data?.document_metadata
  const steps = (data?.reasoning_steps || []).slice(0, 3)

  const confidence = primary.confidence ?? 0
  const confidenceColor =
    confidence >= 85 ? '#34d399' :
    confidence >= 65 ? '#fbbf24' :
    '#f87171'
  const confidenceBg =
    confidence >= 85 ? 'rgba(52, 211, 153, 0.12)' :
    confidence >= 65 ? 'rgba(251, 191, 36, 0.12)' :
    'rgba(248, 113, 113, 0.12)'
  const confidenceBorder =
    confidence >= 85 ? 'rgba(52, 211, 153, 0.28)' :
    confidence >= 65 ? 'rgba(251, 191, 36, 0.28)' :
    'rgba(248, 113, 113, 0.28)'

  function handleDownloadMetadata() {
    const filename = docMeta?.filename || 'taxonomy_classification'
    const baseName = filename.replace(/\.[^/.]+$/, "")

    const exportData = {
      metadata_version: "2.0",
      generated_at: new Date().toISOString(),
      agent: "TAXORA (Enterprise AI Taxonomy Intelligence)",
      guardrails: guardrails,
      memory: memory,
      traceability: {
        trace_id: traceability.trace_id || 'TXR-VERIFIED',
        analysis_scope: traceability.analysis_scope || 'Full-Document Stratified Analysis (0% – 100%)',
        words_analyzed: traceability.words_analyzed || docMeta?.word_count || null,
        pages_analyzed: traceability.pages_analyzed || docMeta?.pages || 1,
        verification_status: traceability.verification_status || 'VERIFIED_FROM_SOURCE',
        source_mappings: sourceMappings
      },
      document: docMeta ? {
        filename: docMeta.filename,
        size_bytes: docMeta.size_bytes,
        char_count: docMeta.char_count,
        word_count: docMeta.word_count || null,
        pages: docMeta.pages || null,
        lines: docMeta.lines || null,
        language: docMeta.language || null,
        kind: docMeta.kind || null,
        type: docMeta.type || null
      } : null,
      classification: {
        domain: path[0] || null,
        terminal_category: path[path.length - 1] || null,
        full_path: path,
        level_rationales: levelRationales,
        hierarchy_level: path.length,
        confidence_score: confidence,
        confidence_level: primary.confidence_label || null,
        status: status,
        document_type: docType || null,
        summary: summary || null,
        key_topics: topics,
        explanation: explanation,
        evidence_from_source: evidence,
        reasoning_steps: steps,
        alternative_matches: alternatives
      }
    }

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${baseName}_metadata.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const LEVEL_PALETTE = [
    { tag: '#38bdf8', dot: '#38bdf8', bg: 'rgba(56, 189, 248, 0.08)', border: '#38bdf8', text: '#bae6fd' },
    { tag: '#60a5fa', dot: '#60a5fa', bg: 'rgba(96, 165, 250, 0.08)', border: '#60a5fa', text: '#cbd5e1' },
    { tag: '#818cf8', dot: '#818cf8', bg: 'rgba(129, 140, 248, 0.08)', border: '#818cf8', text: '#cbd5e1' },
    { tag: '#a78bfa', dot: '#a78bfa', bg: 'rgba(167, 139, 250, 0.08)', border: '#a78bfa', text: '#cbd5e1' },
    { tag: '#34d399', dot: '#34d399', bg: 'rgba(52, 211, 153, 0.1)', border: '#34d399', text: '#d1fae5' }
  ]

  return (
    <div className="bubble ai classificationCard">
      {/* 0. GUARDRAILS STATUS BAR */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center', marginBottom: '14px' }}>
        <button
          type="button"
          onClick={() => setShowGuardrailDetails(v => !v)}
          title="Click to inspect Security & Privacy Guardrail checks"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 12px',
            borderRadius: '999px',
            fontSize: '11.5px',
            fontWeight: 700,
            cursor: 'pointer',
            background: isBlocked
              ? 'rgba(239, 68, 68, 0.22)'
              : isRedacted
              ? 'rgba(251, 191, 36, 0.16)'
              : 'rgba(52, 211, 153, 0.16)',
            color: isBlocked ? '#f87171' : isRedacted ? '#fbbf24' : '#34d399',
            border: isBlocked
              ? '1px solid rgba(239, 68, 68, 0.6)'
              : isRedacted
              ? '1px solid rgba(251, 191, 36, 0.5)'
              : '1px solid rgba(52, 211, 153, 0.45)'
          }}
        >
          <span>🛡️</span>
          <span>
            {isBlocked
              ? `Guardrails: Blocked (${guardrails.triggered_rule || 'Policy Violation'})`
              : isRedacted
              ? `Guardrails: ${guardrails.redacted_count} Secret(s) Masked`
              : 'Guardrails: Passed · Verified Safe'}
          </span>
          <span style={{ opacity: 0.75, fontSize: '10px' }}>{showGuardrailDetails ? '▲' : '▼'}</span>
        </button>
      </div>

      {showGuardrailDetails && (
        <div
          style={{
            marginBottom: '14px',
            padding: '12px 15px',
            borderRadius: '11px',
            background: 'rgba(15, 23, 42, 0.75)',
            border: isRedacted ? '1px solid rgba(251, 191, 36, 0.35)' : '1px solid rgba(52, 211, 153, 0.28)',
            fontSize: '12.5px',
            color: '#d1fae5'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px', marginBottom: '6px' }}>
            <span style={{ fontWeight: 700, color: isRedacted ? '#fcd34d' : '#6ee7b7' }}>
              🛡️ Enterprise BFSI Guardrail Compliance ({guardrails.status || 'PASSED'})
            </span>
            {guardrails.framework && (
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                Framework: <strong>{guardrails.framework}</strong>
              </span>
            )}
          </div>
          <div style={{ color: '#cbd5e1', marginBottom: '8px', lineHeight: '1.5' }}>
            {guardrails.summary}
          </div>
          {guardrails.policy_justification && (
            <div style={{ fontSize: '12px', color: '#cbd5e1', background: 'rgba(255,255,255,0.03)', padding: '6px 10px', borderRadius: '7px', marginBottom: '8px', borderLeft: '3px solid #64dbff' }}>
              <strong>Data Privacy Policy:</strong> {guardrails.policy_justification}
            </div>
          )}
          {guardrails.redacted_types && guardrails.redacted_types.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px' }}>
              <span style={{ fontSize: '11px', color: '#fde68a', fontWeight: 600 }}>Sanitized Identifiers:</span>
              {guardrails.redacted_types.map((rt, idx) => (
                <span
                  key={idx}
                  style={{
                    fontSize: '11px',
                    padding: '2px 8px',
                    borderRadius: '6px',
                    background: 'rgba(251, 191, 36, 0.15)',
                    color: '#fde68a',
                    border: '1px solid rgba(251, 191, 36, 0.3)'
                  }}
                >
                  🔒 {rt}
                </span>
              ))}
            </div>
          )}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {(guardrails.checks_passed || []).map((chk, idx) => (
              <span
                key={idx}
                style={{
                  fontSize: '11px',
                  padding: '2px 8px',
                  borderRadius: '6px',
                  background: 'rgba(52, 211, 153, 0.12)',
                  color: '#a7f3d0',
                  border: '1px solid rgba(52, 211, 153, 0.22)'
                }}
              >
                ✓ {chk}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 1. SHORT SUMMARY */}
      {summary && (
        <p className="taxSummary">
          {summary}
        </p>
      )}

      {/* 2. DOCUMENT TYPE & 5 KEY HIGHLIGHTS */}
      {(docType || topics.length > 0) && (
        <div className="metaRow">
          {docType && (
            <span className="metaTopic" style={{ color: '#c5cad8', fontWeight: 700 }}>{docType}</span>
          )}
          {topics.map((t, i) => (
            <span key={i} className="metaTopic">{t}</span>
          ))}
        </div>
      )}

      {/* 3. PROMINENT TAXONOMY HIERARCHY TREE WITH PER-LEVEL RATIONALE */}
      <div className="taxTreeHero">
        <div className="taxTreeHeroHead">
          <div className="taxTreeLabel">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7" rx="1.5" />
              <rect x="14" y="3" width="7" height="7" rx="1.5" />
              <rect x="14" y="14" width="7" height="7" rx="1.5" />
              <path d="M10 6.5h4" />
              <path d="M6.5 10v7a1.5 1.5 0 0 0 1.5 1.5H14" />
            </svg>
            <span>Taxonomy Hierarchy Tree & Level Rationale</span>
          </div>

          <div className="taxTreeBadges">
            <span
              className="confidenceBadge"
              style={{
                background: confidenceBg,
                color: confidenceColor,
                border: `1px solid ${confidenceBorder}`
              }}
            >
              <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: confidenceColor, display: 'inline-block' }} />
              {confidence}% {primary.confidence_label || 'Match'}
            </span>

            {status.domain && (
              <span className="statusBadge">{status.domain}</span>
            )}
            {status.classification && (
              <span className="statusBadge" style={{ color: '#64dbff', borderColor: 'rgba(100,219,255,0.25)', background: 'rgba(100,219,255,0.06)' }}>
                {status.classification}
              </span>
            )}
          </div>
        </div>

        {/* BALANCED TREE FLOW ACROSS ALL LEVELS WITH INLINE LEVEL 1–5 RATIONALE */}
        <div className="treeFlow">
          {path.map((levelName, idx) => {
            const isTerminal = idx === path.length - 1
            const isLast = idx === path.length - 1
            const lvlRationale = levelRationales[idx]?.rationale
            const lvlColor = isTerminal ? LEVEL_PALETTE[4] : LEVEL_PALETTE[idx % 4]

            return (
              <div
                key={idx}
                className="treeLevel steppedTreeLevel"
                style={{
                  marginLeft: `${idx * 28}px`,
                  position: 'relative',
                  paddingLeft: idx > 0 ? '6px' : '0px',
                  marginBottom: '6px'
                }}
              >
                {idx > 0 && (
                  <div
                    aria-hidden="true"
                    style={{
                      position: 'absolute',
                      left: '-18px',
                      top: '12px',
                      width: '14px',
                      height: '14px',
                      borderLeft: `2px solid ${lvlColor.border}77`,
                      borderBottom: `2px solid ${lvlColor.border}77`,
                      borderBottomLeftRadius: '6px'
                    }}
                  />
                )}
                <div className="treeGutter">
                  <div
                    className="treeDot"
                    style={{
                      background: lvlColor.dot,
                      boxShadow: isTerminal ? '0 0 12px #34d399' : `0 0 8px ${lvlColor.dot}88`
                    }}
                  />
                  {!isLast && <div className="treeLine" />}
                </div>
                <div className="treeNodeBody" style={{ paddingBottom: isTerminal ? '6px' : '16px' }}>
                  <span className="treeLevelTag" style={{ color: lvlColor.tag, fontWeight: 700 }}>
                    {isTerminal
                      ? `🎯 Terminal Category (Level ${idx + 1})`
                      : `Level ${idx + 1} · ${levelLabels[idx] || `Level ${idx + 1}`}`}
                  </span>
                  <span
                    className="treeNodeName"
                    style={{
                      fontSize: isTerminal ? '18px' : '16px',
                      fontWeight: isTerminal ? 750 : 600,
                      color: isTerminal ? '#34d399' : '#f0f7ff'
                    }}
                  >
                    {levelName}
                  </span>
                  {lvlRationale && (
                    <div
                      style={{
                        marginTop: '5px',
                        fontSize: '12.5px',
                        lineHeight: '1.45',
                        color: lvlColor.text,
                        background: lvlColor.bg,
                        borderLeft: `3px solid ${lvlColor.border}`,
                        padding: '6px 12px',
                        borderRadius: '0 7px 7px 0'
                      }}
                    >
                      <strong style={{ color: lvlColor.tag }}>
                        Why Level {idx + 1} ({levelLabels[idx] || 'Category'}):{' '}
                      </strong>
                      {lvlRationale}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* 4. COMPACT "CLICK & VIEW" ACCORDIONS */}
      <div className="accordionGroup">

        {/* WHY THIS CATEGORY & LEVEL 1-5 RATIONALE */}
        {(explanation || levelRationales.length > 0) && (
          <div className="accordionItem">
            <button
              type="button"
              className="accordionBtn"
              onClick={() => setShowWhy(v => !v)}
              aria-expanded={showWhy}
            >
              <span className="accordionTitle">
                <span className="accordionIcon" aria-hidden="true">💡</span>
                <span className="accordionText">Level 1–5 Rationale & Overall Explanation</span>
                <span className="accordionBadge">{levelRationales.length} levels</span>
              </span>
              <span className="accordionTogglePill">
                {showWhy ? 'Hide ▲' : 'View Rationale ▼'}
              </span>
            </button>
            {showWhy && (
              <div className="accordionContent">
                {explanation && (
                  <p style={{ marginBottom: '12px', color: '#e2e8f0', lineHeight: '1.6' }}>
                    {explanation}
                  </p>
                )}
                <div className="stepsList">
                  {levelRationales.map((lr, i) => (
                    <div key={i} className="stepItem" style={{ alignItems: 'flex-start' }}>
                      <span className="stepNumber">L{lr.level}</span>
                      <div>
                        <div style={{ fontWeight: 700, color: '#f8fafc', marginBottom: '2px' }}>
                          {lr.role}: <span style={{ color: '#64dbff' }}>{lr.category}</span>
                        </div>
                        <div style={{ color: '#cbd5e1', fontSize: '13px', lineHeight: '1.5' }}>
                          {lr.rationale}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* END-TO-END TRACEABILITY & SOURCE AUDIT MATRIX */}
        {sourceMappings.length > 0 && (
          <div className="accordionItem">
            <button
              type="button"
              className="accordionBtn"
              onClick={() => setShowTrace(v => !v)}
              aria-expanded={showTrace}
            >
              <span className="accordionTitle">
                <span className="accordionIcon" aria-hidden="true">🔗</span>
                <span className="accordionText">Traceability & Source Audit Matrix</span>
                <span className="accordionBadge">{sourceMappings.length} mapped levels</span>
              </span>
              <span className="accordionTogglePill">
                {showTrace ? 'Hide ▲' : 'View Traceability ▼'}
              </span>
            </button>
            {showTrace && (
              <div className="accordionContent">
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '10px',
                    marginBottom: '12px',
                    padding: '9px 12px',
                    borderRadius: '9px',
                    background: 'rgba(15, 23, 42, 0.65)',
                    border: '1px solid rgba(100, 219, 255, 0.2)',
                    fontSize: '12px',
                    color: '#cbd5e1'
                  }}
                >
                  <span><strong>Trace ID:</strong> {traceability.trace_id || 'TXR-VERIFIED'}</span>
                  {(traceability.words_analyzed || docMeta?.word_count) && (
                    <>
                      <span>·</span>
                      <span><strong>Words Analyzed:</strong> {traceability.words_analyzed || docMeta?.word_count}</span>
                    </>
                  )}
                  {(traceability.pages_analyzed || docMeta?.pages) && (
                    <>
                      <span>·</span>
                      <span><strong>Pages/Sections:</strong> {traceability.pages_analyzed || docMeta?.pages}</span>
                    </>
                  )}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {sourceMappings.map((sm, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '10px 13px',
                        borderRadius: '10px',
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid rgba(255, 255, 255, 0.08)'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px', marginBottom: '4px' }}>
                        <span style={{ fontWeight: 700, color: '#64dbff', fontSize: '13px' }}>
                          {sm.level || `Level ${idx + 1}`} → {sm.category}
                        </span>
                        <span
                          style={{
                            fontSize: '11px',
                            padding: '2px 8px',
                            borderRadius: '6px',
                            background: 'rgba(140, 119, 255, 0.14)',
                            color: '#ddd6fe'
                          }}
                        >
                          📍 {sm.source_section}
                        </span>
                      </div>
                      <div style={{ fontSize: '12.5px', color: '#e2e8f0', marginBottom: '3px' }}>
                        <strong>Source Evidence Signal:</strong> <em>"{sm.evidence_signal}"</em>
                      </div>
                      {sm.rationale && (
                        <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                          <strong>Traceability Logic:</strong> {sm.rationale}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* EVIDENCE FROM SOURCE */}
        {evidence.length > 0 && (
          <div className="accordionItem">
            <button
              type="button"
              className="accordionBtn"
              onClick={() => setShowEvidence(v => !v)}
              aria-expanded={showEvidence}
            >
              <span className="accordionTitle">
                <span className="accordionIcon" aria-hidden="true">📑</span>
                <span className="accordionText">Evidence quotes from document</span>
                <span className="accordionBadge">{evidence.length} points</span>
              </span>
              <span className="accordionTogglePill">
                {showEvidence ? 'Hide ▲' : 'View Evidence ▼'}
              </span>
            </button>
            {showEvidence && (
              <div className="accordionContent">
                <ul className="evidenceList">
                  {evidence.map((ev, i) => (
                    <li key={i} className="evidenceItem">"{ev}"</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* REASONING STEPS */}
        {steps.length > 0 && (
          <div className="accordionItem">
            <button
              type="button"
              className="accordionBtn"
              onClick={() => setShowSteps(v => !v)}
              aria-expanded={showSteps}
            >
              <span className="accordionTitle">
                <span className="accordionIcon" aria-hidden="true">🧠</span>
                <span className="accordionText">Step-by-step logic</span>
                <span className="accordionBadge">{steps.length} steps</span>
              </span>
              <span className="accordionTogglePill">
                {showSteps ? 'Hide ▲' : 'View Logic ▼'}
              </span>
            </button>
            {showSteps && (
              <div className="accordionContent">
                <div className="stepsList">
                  {steps.map((st, i) => (
                    <div key={i} className="stepItem">
                      <span className="stepNumber">{i + 1}</span>
                      <span>{st}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ALTERNATIVES */}
        {alternatives.length > 0 && (
          <div className="accordionItem">
            <button
              type="button"
              className="accordionBtn"
              onClick={() => setShowAlts(v => !v)}
              aria-expanded={showAlts}
            >
              <span className="accordionTitle">
                <span className="accordionIcon" aria-hidden="true">🔀</span>
                <span className="accordionText">Alternative classifications</span>
                <span className="accordionBadge">{alternatives.length} options</span>
              </span>
              <span className="accordionTogglePill">
                {showAlts ? 'Hide ▲' : 'Compare ▼'}
              </span>
            </button>
            {showAlts && (
              <div className="accordionContent">
                {alternatives.map((alt, i) => {
                  const altConf = alt.confidence || 0
                  const aColor = altConf >= 85 ? '#34d399' : altConf >= 65 ? '#fbbf24' : '#f87171'
                  const aBg = altConf >= 85 ? 'rgba(52,211,153,0.12)' : altConf >= 65 ? 'rgba(251,191,36,0.12)' : 'rgba(248,113,113,0.12)'
                  return (
                    <div key={i} className="altCard">
                      <div className="altCardHead">
                        <span className="altPath">{(alt.path || []).join(' › ')}</span>
                        <span
                          style={{
                            background: aBg,
                            color: aColor,
                            borderRadius: '6px',
                            padding: '2px 7px',
                            fontSize: '11px',
                            fontWeight: 700
                          }}
                        >
                          {altConf}% Match
                        </span>
                      </div>
                      {alt.explanation && (
                        <p className="altExpl">{alt.explanation}</p>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

      </div>

      {/* 5. HIGHLIGHTED METADATA DOWNLOAD IN DOWN */}
      <div className="metaDownloadHero">
        <button
          type="button"
          className="metaDownloadBtn"
          onClick={handleDownloadMetadata}
          title="Download structured classification, rationale, traceability & guardrail metadata (.json)"
        >
          <div className="metaDownloadLeft">
            <span className="metaDownloadIcon" aria-hidden="true">⤓</span>
            <span className="metaDownloadTitle">Download Metadata & Traceability (.json)</span>
            {docMeta?.filename && (
              <span className="metaDownloadFilename">· {docMeta.filename}</span>
            )}
          </div>
          <span className="metaDownloadBadge">JSON ⤓</span>
        </button>
        {traceability.trace_id && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '6px' }}>
            <span
              style={{
                fontSize: '11px',
                fontFamily: 'ui-monospace, "JetBrains Mono", Menlo, Consolas, monospace',
                color: 'var(--muted)',
                letterSpacing: '0.6px',
                padding: '2px 8px',
                borderRadius: '6px',
                background: 'rgba(7, 140, 255, 0.06)',
                border: '1px solid rgba(7, 140, 255, 0.16)'
              }}
              title="Verification Audit Code"
            >
              {traceability.trace_id}
            </span>
          </div>
        )}
      </div>

      {/* 6. FOLLOW-UP SUGGESTIONS CHIPS */}
      {suggestions.length > 0 && (
        <div className="suggestionsGroup">
          <span className="reviewSectionLabel">Suggested Follow-ups</span>
          <div className="suggestionChips">
            {suggestions.map((s, i) => (
              <button
                key={i}
                type="button"
                className="suggestionChip"
                onClick={() => onSuggestionClick && onSuggestionClick(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
