import { useEffect, useRef } from 'react'
import ThinkingBubble from './ThinkingBubble.jsx'
import ClassificationResult from './ClassificationResult.jsx'

function formatBytes(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  const kb = bytes / 1024
  if (kb < 1024) return kb.toFixed(1) + ' KB'
  return (kb / 1024).toFixed(1) + ' MB'
}

function UserBubble({ msg, onOpenDocument }) {
  // Support both new msg.file object and legacy "[File: name.ext]" text
  let file = msg.file
  let content = msg.content || ''
  if (!file && content.startsWith('[File: ')) {
    const endIdx = content.indexOf(']')
    if (endIdx !== -1) {
      file = { name: content.slice(7, endIdx).trim() }
      content = content.slice(endIdx + 1).trim()
    }
  }

  const hasFile = Boolean(file && (file.name || file.filename))
  const fileName = file?.filename || file?.name || 'Attached file'
  const fileExt = fileName.split('.').pop()?.toUpperCase() || 'FILE'
  const sizeText = file?.size_bytes ? formatBytes(file.size_bytes) : (file?.size ? formatBytes(file.size) : fileExt)

  return (
    <div className={`bubble user${hasFile ? ' userBubbleWithFile' : ''}`}>
      {hasFile && (
        <button
          type="button"
          className="userFileCard userFileClickable"
          onClick={() => onOpenDocument && onOpenDocument(file)}
          title="Open document"
        >
          <div className="userFileHeader">
            <div className="userFileLeft">
              <span className="userFileIcon" aria-hidden="true">📄</span>
              <div className="userFileInfo">
                <span className="userFileName" title={fileName}>{fileName}</span>
                <span className="userFileMeta">
                  {sizeText}
                  {file?.pages ? ` · ${file.pages} page${file.pages > 1 ? 's' : ''}` : ''}
                </span>
              </div>
            </div>
            <span className="userFileViewBtn">Open ↗</span>
          </div>
        </button>
      )}
      {content && <div className="userMessageText">{content}</div>}
    </div>
  )
}

function AiChatBubble({ msg, onOpenDocument }) {
  const docMeta = msg.document_metadata
  const guardrails = msg.guardrails
  const memory = msg.memory
  const isFraudBlocked = guardrails?.status === 'BLOCKED_FRAUD_ANOMALY'
  const isBlocked = guardrails?.status === 'BLOCKED' || isFraudBlocked
  const isRedacted = guardrails?.status === 'REDACTED' || (guardrails?.redacted_count || 0) > 0

  function handleDownloadMeta() {
    const filename = docMeta?.filename || 'document'
    const baseName = filename.replace(/\.[^/.]+$/, "")
    const metaObj = {
      message: msg.content,
      document_metadata: docMeta,
      guardrails: guardrails || null,
      memory: memory || null,
      exported_at: new Date().toISOString()
    }
    const blob = new Blob([JSON.stringify(metaObj, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${baseName}_metadata.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div
      className="bubble ai"
      style={{
        maxWidth: 'min(88%, 720px)',
        padding: '16px 18px',
        lineHeight: '1.6',
        border: isBlocked ? '1px solid rgba(248, 113, 113, 0.45)' : undefined,
        background: isBlocked ? 'rgba(127, 29, 29, 0.22)' : undefined
      }}
    >
      {(isBlocked || isRedacted || (memory?.conversation_turns > 0)) && (
        <div style={{ marginBottom: '10px', display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
          {isBlocked && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '11.5px',
                fontWeight: 700,
                padding: '4px 10px',
                borderRadius: '999px',
                background: isFraudBlocked ? 'rgba(239, 68, 68, 0.22)' : 'rgba(248, 113, 113, 0.16)',
                color: isFraudBlocked ? '#fca5a5' : '#fca5a5',
                border: isFraudBlocked ? '1px solid rgba(239, 68, 68, 0.6)' : '1px solid rgba(248, 113, 113, 0.4)'
              }}
            >
              {isFraudBlocked ? '🛡️ BFSI FRAUD & ANOMALY REJECTION · ' : '🛡️ GUARDRAIL BLOCK · '}
              {guardrails?.anomaly_details?.rule || guardrails?.triggered_rule || 'Security & Privacy Policy'}
            </span>
          )}
          {isRedacted && !isBlocked && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '11.5px',
                fontWeight: 700,
                padding: '4px 10px',
                borderRadius: '999px',
                background: 'rgba(251, 191, 36, 0.15)',
                color: '#fde68a',
                border: '1px solid rgba(251, 191, 36, 0.35)'
              }}
            >
              🛡️ BFSI PRIVACY SHIELD · {guardrails?.redacted_count || 1} Sensitive Identifier(s) Sanitized
            </span>
          )}
          {memory?.conversation_turns > 0 && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                fontSize: '11px',
                fontWeight: 600,
                padding: '3px 9px',
                borderRadius: '999px',
                background: 'rgba(140, 119, 255, 0.12)',
                color: '#c4b5fd',
                border: '1px solid rgba(140, 119, 255, 0.28)'
              }}
            >
              🧠 Memory Active ({memory.remembered_documents_count || 0} doc{memory.remembered_documents_count === 1 ? '' : 's'} · {memory.conversation_turns} turns)
            </span>
          )}
        </div>
      )}
      {docMeta && (
        <div style={{ marginBottom: '10px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="metaDocPill"
            onClick={() => onOpenDocument && onOpenDocument(docMeta)}
            style={{ cursor: 'pointer' }}
            title="Open document"
          >
            <span style={{ color: '#8c77ff' }}>📄</span>
            <span style={{ fontWeight: 600, color: '#e2e4ee' }}>{docMeta.filename}</span>
            <span style={{ color: '#8c77ff', marginLeft: '3px', fontWeight: 600 }}>Open ↗</span>
          </button>
          <button
            type="button"
            className="metaDocPill"
            onClick={handleDownloadMeta}
            style={{ cursor: 'pointer' }}
            title="Download metadata as JSON"
          >
            <span style={{ color: '#64dbff' }}>⤓</span>
            <span style={{ fontWeight: 600, color: '#e2e4ee' }}>Metadata (.json)</span>
          </button>
        </div>
      )}
      <div style={{ fontSize: '15.5px', color: '#f7f7fb', whiteSpace: 'pre-wrap' }}>
        {msg.content}
      </div>
    </div>
  )
}

export default function MessageList({ messages, onFeedback, onSuggestionClick, onOpenDocument }) {
  const listRef = useRef(null)
  const prevLastRoleRef = useRef(null)

  useEffect(() => {
    const el = listRef.current
    if (!el) return

    const lastMsg = messages[messages.length - 1]
    const currentLastRole = lastMsg?.role
    const isNewAiReply = currentLastRole === 'ai' && (prevLastRoleRef.current === 'thinking' || lastMsg?.isNew)

    if (isNewAiReply) {
      // Scroll directly to the START of the new AI reply so the user can read from the top
      const timer = setTimeout(() => {
        if (!el) return
        const aiBubbles = el.querySelectorAll('.bubble.ai')
        const lastAiBubble = aiBubbles[aiBubbles.length - 1]
        if (lastAiBubble) {
          const elRect = el.getBoundingClientRect()
          const bubbleRect = lastAiBubble.getBoundingClientRect()
          const targetTop = el.scrollTop + (bubbleRect.top - elRect.top) - 18
          el.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' })
        }
      }, 50)
      prevLastRoleRef.current = currentLastRole
      return () => clearTimeout(timer)
    } else {
      // For user messages or thinking bubble, scroll to bottom so the prompt and thinking state are visible
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
    }

    prevLastRoleRef.current = currentLastRole
  }, [messages])

  return (
    <div className="messages" aria-live="polite" ref={listRef}>
      {messages.map((msg, i) => {
        if (msg.role === 'user') {
          return <UserBubble key={i} msg={msg} onOpenDocument={onOpenDocument} />
        }
        if (msg.role === 'thinking') {
          return <ThinkingBubble key={i} />
        }
        if (msg.role === 'ai') {
          if (msg.resultData) {
            return (
              <ClassificationResult
                key={i}
                data={msg.resultData}
                onFeedback={onFeedback}
                onSuggestionClick={onSuggestionClick}
                onOpenDocument={onOpenDocument}
              />
            )
          }
          return <AiChatBubble key={i} msg={msg} onOpenDocument={onOpenDocument} />
        }
        return null
      })}
    </div>
  )
}
