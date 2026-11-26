import { useState, useEffect, useRef } from 'react'
import AuroraBackground from './components/AuroraBackground.jsx'
import HomePage from './components/HomePage.jsx'
import ChatPage from './components/ChatPage.jsx'
import { classifyContent, getTaxonomy, submitFeedback } from './services/api.js'

const SESSIONS_KEY = 'taxora_sessions'

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2)
}

// Only conversations that actually have messages are ever kept in history.
function loadSessions() {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY)
    const list = raw ? JSON.parse(raw) : []
    return list
      .map(s => {
        const messages = (s.messages || [])
          .filter(m => m.role !== 'thinking')
          .map(m => ({ ...m, isNew: false }))

        let title = s.title || 'Taxonomy Consultation'
        let hasTopicTitle = Boolean(s.hasTopicTitle)

        // Upgrade unlocked sessions: prefer AI taxonomy classification topic, or smart-stripped prompt/filename
        if (!s.titleLocked) {
          const lastClassMsg = [...messages].reverse().find(m => m.role === 'ai' && m.resultData?.primary?.path)
          const classTitle = lastClassMsg ? titleFromResult(lastClassMsg.resultData) : null
          if (classTitle) {
            title = classTitle
            hasTopicTitle = true
          } else {
            const topicUserMsg = messages.find(m => m.role === 'user' && ((m.content && !isGenericGreeting(m.content)) || m.file?.name))
            if (topicUserMsg) {
              title = formatSmartTitle(topicUserMsg.content, topicUserMsg.file?.name)
              hasTopicTitle = true
            } else if (isGenericGreeting(title)) {
              title = 'Taxonomy Consultation'
            }
          }
        }

        return {
          ...s,
          title,
          hasTopicTitle,
          messages
        }
      })
      .filter(s => s.messages.length > 0)
      .sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0))
  } catch {
    return []
  }
}

function saveSessions(sessions) {
  try {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
  } catch {
    // ignore storage errors
  }
}

function shorten(text, max) {
  return text.length > max ? text.slice(0, max) + '\u2026' : text
}

const GENERIC_CHAT_INPUTS = new Set([
  'hi', 'hello', 'hey', 'hola', 'hii', 'hiii', 'heyy', 'yo', 'sup',
  'how are you', 'how are u', 'how r u', 'how r you', 'how are you doing',
  'how are u doing', 'hows it going', 'how is it going', 'whats up',
  'good morning', 'good afternoon', 'good evening', 'greetings',
  'hi there', 'hello there', 'hey there', 'ok', 'okay', 'thanks', 'thank you'
])

function isGenericGreeting(text) {
  if (!text) return true
  const cleaned = text.trim().toLowerCase().replace(/[^\w\s]/g, '').replace(/\s+/g, ' ')
  return GENERIC_CHAT_INPUTS.has(cleaned) || cleaned.length <= 2
}

function formatSmartTitle(text, fileName) {
  // 1. If user attached a file, clean file name
  if (fileName) {
    const base = fileName.replace(/\.[^/.]+$/, '').replace(/[-_]+/g, ' ').trim()
    if (base) {
      const formatted = base.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ')
      return shorten(formatted, 42)
    }
  }

  // 2. If user supplied text prompt, strip filler prefixes
  if (text && !isGenericGreeting(text)) {
    let clean = text.trim().replace(/\s+/g, ' ')
    clean = clean.replace(/^(?:can you|please|kindly|could you|would you|i want to|i need to|help me|can u|plz)\s+/i, '')
    clean = clean.replace(/^(?:classify|categorize|identify|find taxonomy|taxonomy for|tag|analyze|review)\s+(?:this|the|my|our)?\s*/i, '')
    clean = clean.replace(/^(?:document|contract|file|record|content|text|clause)\s+(?:for|on|about|regarding)?\s*/i, '')
    clean = clean.replace(/^[?:!.,-\s]+/, '')
    if (clean.length > 2) {
      const capitalized = clean.charAt(0).toUpperCase() + clean.slice(1)
      return shorten(capitalized, 42)
    }
  }

  return 'Taxonomy Consultation'
}

function titleFromResult(result) {
  if (!result || result.type === 'chat') return null
  const rawPath = (result.primary?.path || [])
    .map(p => String(p || '').replace(/^(?:level\s*\d+\s*[:\-–—·]\s*)/i, '').trim())
    .filter(p => p && !/industry \/ broad domain|sub-domain|process area|specialized category|exact document type|specific subject/i.test(p))
  if (result.document_type) {
    return shorten(result.document_type, 52)
  }
  let t = rawPath.length > 1 ? rawPath.slice(-2).join(' \u203A ') : (rawPath[0] || '')
  if (!t) t = (result.summary || '').slice(0, 42)
  return t ? shorten(t, 52) : null
}

// Automatically keeps the chat title relevant to what the conversation is about,
// unless the user manually renamed the chat.
function autoTitle(session, result, latestUserText = '', latestFileName = '') {
  if (session.titleLocked) return {}

  // 1. If we got a classification result, always title the chat after the classified taxonomy topic
  const classTitle = titleFromResult(result)
  if (classTitle) {
    return { title: classTitle, hasTopicTitle: true }
  }

  // 2. If it's a chat response and the session doesn't have a specific topic title yet,
  //    upgrade the title when the user asks a meaningful question or uploads a file
  if (!session.hasTopicTitle) {
    if (latestUserText && !isGenericGreeting(latestUserText)) {
      return { title: formatSmartTitle(latestUserText, latestFileName), hasTopicTitle: true }
    }
    if (latestFileName) {
      return { title: formatSmartTitle('', latestFileName), hasTopicTitle: true }
    }
  }

  return {}
}

// Build conversation history & structured document memory for the API
function buildHistory(messages) {
  const result = []
  for (const msg of messages) {
    if (msg.role === 'user') {
      const textContent = msg.content || ''
      const filePrefix = msg.file ? `[Attached File: ${msg.file.name}] ` : ''
      const full = `${filePrefix}${textContent}`.trim()
      if (full) result.push({ role: 'user', content: full })
    } else if (msg.role === 'ai' && (msg.content || msg.resultData)) {
      const rd = msg.resultData
      if (rd?.primary?.path) {
        const p = rd.primary.path.join(' > ')
        const docType = rd.document_type ? ` | Document Type: ${rd.document_type}` : ''
        const topics = (rd.key_topics || []).slice(0, 5).join(', ')
        const topicsPart = topics ? ` | Key Topics: ${topics}` : ''
        const ratList = (rd.primary.level_rationales || [])
          .map(r => (typeof r === 'string' ? r : `Level ${r.level} (${r.category}): ${r.rationale}`))
          .join(' ; ')
        const ratPart = ratList ? ` | Level Rationales: ${ratList}` : ''
        const explPart = rd.primary.explanation ? ` | Overall Rationale: ${rd.primary.explanation}` : ''
        const evPart = (rd.evidence || []).length ? ` | Source Evidence: ${(rd.evidence || []).join(' | ')}` : ''
        const content = `[Classified as: ${p}]${docType}${topicsPart}${ratPart}${explPart}${evPart} Summary: ${rd.summary || msg.content}`
        result.push({ role: 'assistant', content })
      } else {
        result.push({ role: 'assistant', content: msg.content })
      }
    }
  }
  return result
}

export default function App() {
  const [page, setPage] = useState('home') // 'home' | 'chat'
  const [sessions, setSessions] = useState(() => loadSessions())
  // null while on the chat page = a blank draft conversation (not stored yet)
  const [currentSessionId, setCurrentSessionId] = useState(null)
  const [, setTaxonomy] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    if (typeof window !== 'undefined' && window.self !== window.top) {
      document.documentElement.classList.add('in-iframe')
    }
  }, [])

  useEffect(() => {
    getTaxonomy()
      .then(data => setTaxonomy(data))
      .catch(() => setTaxonomy(null))
  }, [])

  useEffect(() => {
    saveSessions(sessions)
  }, [sessions])

  // Always keep the latest list available for instant saves (delete / page close)
  const sessionsRef = useRef(sessions)
  useEffect(() => {
    sessionsRef.current = sessions
  }, [sessions])

  useEffect(() => {
    const flush = () => saveSessions(sessionsRef.current)
    window.addEventListener('pagehide', flush)
    window.addEventListener('beforeunload', flush)
    // Another tab changed the history: follow it so a stale tab never brings deleted chats back
    const onStorage = e => {
      if (e.key === SESSIONS_KEY) setSessions(loadSessions())
    }
    window.addEventListener('storage', onStorage)
    return () => {
      window.removeEventListener('pagehide', flush)
      window.removeEventListener('beforeunload', flush)
      window.removeEventListener('storage', onStorage)
    }
  }, [])

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') setSidebarOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const currentSession = sessions.find(s => s.id === currentSessionId) || null

  function updateSession(id, updater) {
    setSessions(prev => prev.map(s => (s.id === id ? updater(s) : s)))
  }

  function applyResult(sessionId, result) {
    setSessions(prev => {
      const s = prev.find(item => item.id === sessionId)
      if (!s) return prev
      let msgs = s.messages.filter(m => m.role !== 'thinking')
      if (result.document_metadata) {
        for (let i = msgs.length - 1; i >= 0; i--) {
          if (msgs[i].role === 'user' && msgs[i].file) {
            msgs[i] = {
              ...msgs[i],
              file: {
                ...msgs[i].file,
                ...result.document_metadata
              }
            }
            break
          }
        }
      }
      const lastUserMsg = [...msgs].reverse().find(m => m.role === 'user')
      const aiMsg = result.type === 'chat'
        ? { role: 'ai', content: result.message || '', document_metadata: result.document_metadata, guardrails: result.guardrails, memory: result.memory, isNew: true }
        : { role: 'ai', content: result.summary || '', resultData: result, document_metadata: result.document_metadata, guardrails: result.guardrails, memory: result.memory, isNew: true }
      const updated = {
        ...s,
        ...autoTitle(s, result, lastUserMsg?.content || '', lastUserMsg?.file?.name || ''),
        updatedAt: Date.now(),
        messages: [...msgs, aiMsg]
      }
      return [updated, ...prev.filter(item => item.id !== sessionId)]
    })
  }

  function applyError(sessionId, err) {
    let errText =
      err?.response?.data?.detail ||
      err?.message ||
      'Could not process your request. Please try again.'
    if (errText.toLowerCase().includes('unreadable') || errText.includes('502')) {
      errText = 'I am ready to assist. Please try rephrasing your question or uploading your file.'
    }
    setSessions(prev => prev.map(s => {
      if (s.id !== sessionId) return s
      const msgs = s.messages.filter(m => m.role !== 'thinking')
      return { ...s, messages: [...msgs, { role: 'ai', content: errText, isNew: true }] }
    }))
  }

  // Creates a stored conversation from the first message and asks the AI.
  function startNewConversation(text, file) {
    if (!text && !file) return
    const sessionId = generateId()
    const fileMeta = file ? {
      name: file.name,
      size: file.size,
      type: file.name.split('.').pop()?.toUpperCase() || 'FILE'
    } : null

    const hasTopic = Boolean((text && !isGenericGreeting(text)) || file?.name)
    const created = {
      id: sessionId,
      title: formatSmartTitle(text, file?.name),
      hasTopicTitle: hasTopic,
      messages: [
        { role: 'user', content: text || '', file: fileMeta },
        { role: 'thinking', content: '' }
      ],
      timestamp: Date.now()
    }
    setSessions(prev => [created, ...prev])
    setCurrentSessionId(sessionId)
    Promise.all([
      classifyContent(file, text, []),
      new Promise(res => setTimeout(res, 850))
    ])
      .then(([result]) => applyResult(sessionId, result))
      .catch(err => applyError(sessionId, err))
  }

  // Sends a message. A blank draft is only stored once the first message is sent.
  function sendMessage(text, file) {
    if (!text && !file) return

    const existing = sessions.find(s => s.id === currentSessionId)
    if (!existing) {
      startNewConversation(text, file)
      return
    }

    const fileMeta = file ? {
      name: file.name,
      size: file.size,
      type: file.name.split('.').pop()?.toUpperCase() || 'FILE'
    } : null

    const history = buildHistory(existing.messages)
    const userMsg = { role: 'user', content: text || '', file: fileMeta }
    const thinkingMsg = { role: 'thinking', content: '' }
    const sessionId = existing.id

    setSessions(prev => prev.map(s => {
      if (s.id !== sessionId) return s
      let nextTitle = s.title
      let nextHasTopic = s.hasTopicTitle
      if (!s.titleLocked && !s.hasTopicTitle && ((text && !isGenericGreeting(text)) || file?.name)) {
        nextTitle = formatSmartTitle(text, file?.name)
        nextHasTopic = true
      }
      return { ...s, title: nextTitle, hasTopicTitle: nextHasTopic, messages: [...s.messages, userMsg, thinkingMsg] }
    }))

    Promise.all([
      classifyContent(file, text, history),
      new Promise(res => setTimeout(res, 850))
    ])
      .then(([result]) => applyResult(sessionId, result))
      .catch(err => applyError(sessionId, err))
  }

  // Open an existing conversation (id) or a blank draft (id = null).
  function openChat(id, initialText, initialFile) {
    setSidebarOpen(false)
    setPage('chat')
    if (id) {
      setCurrentSessionId(id)
    } else if (initialText || initialFile) {
      startNewConversation(initialText, initialFile)
    } else {
      setCurrentSessionId(null)
    }
  }

  function newSession() {
    setCurrentSessionId(null) // blank draft, nothing stored until the user types
    setPage('chat')
    setSidebarOpen(false)
  }

  function loadSession(id) {
    setCurrentSessionId(id)
    setPage('chat')
  }

  function renameSession(id, title) {
    updateSession(id, s => ({ ...s, title, titleLocked: true }))
  }

  // Delete, then land on a blank new conversation (not the front page).
  function deleteSession(id) {
    const idx = sessionsRef.current.findIndex(s => s.id === id)
    const next = sessionsRef.current.filter(s => s.id !== id)
    sessionsRef.current = next
    saveSessions(next) // write to storage right away, don't wait for the next render
    setSessions(next)
    if (id === currentSessionId) {
      if (next.length > 0) {
        const nextSess = next[idx >= 0 && idx < next.length ? idx : next.length - 1]
        setCurrentSessionId(nextSess.id)
        setPage('chat')
        setSidebarOpen(false)
      } else {
        setCurrentSessionId(null)
        setPage('chat')
        setSidebarOpen(false)
      }
    }
  }

  function goHome() {
    setSidebarOpen(false)
    setPage('home')
  }

  function handleFeedback(action, editedPath) {
    submitFeedback(action, editedPath).catch(() => {})
  }

  function handleSuggestionClick(text) {
    sendMessage(text, null)
  }

  return (
    <div className="app">
      <AuroraBackground />

      {page === 'home' && (
        <HomePage
          sessions={sessions}
          onOpenChat={(id, text, file) => openChat(id, text, file)}
          onSeeMore={() => {}}
        />
      )}

      {page === 'chat' && (
        <ChatPage
          session={currentSession}
          sessions={sessions}
          sidebarOpen={sidebarOpen}
          onOpenSidebar={() => setSidebarOpen(true)}
          onCloseSidebar={() => setSidebarOpen(false)}
          onBack={goHome}
          onNew={newSession}
          onLoadSession={loadSession}
          onSend={sendMessage}
          onFeedback={handleFeedback}
          onSuggestionClick={handleSuggestionClick}
          onRename={renameSession}
          onDelete={deleteSession}
        />
      )}
    </div>
  )
}

