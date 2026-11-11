import { useRef, useState } from 'react'

function formatTimestamp(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const diffDays = Math.floor((now - d) / 86400000)
  if (diffDays === 0) {
    return `TODAY · ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  } else if (diffDays === 1) {
    return 'YESTERDAY'
  } else {
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }).toUpperCase()
  }
}

function getPreview(messages) {
  if (!messages || messages.length === 0) return ''
  const first = messages.find(m => m.role === 'user')
  return first?.content?.slice(0, 80) || ''
}

export default function HomePage({ sessions, onOpenChat, onSeeMore }) {
  const [inputText, setInputText] = useState('')
  const [file, setFile] = useState(null)
  const [showSeeMore, setShowSeeMore] = useState(false)
  const fileRef = useRef(null)

  const visibleSessions = sessions.slice(0, 3)
  const hasMore = sessions.length > 3

  function handleStart() {
    if (!inputText.trim() && !file) return
    onOpenChat(null, inputText.trim(), file)
    setInputText('')
    setFile(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleStart()
    }
  }

  function handleFileChange(e) {
    const f = e.target.files && e.target.files[0]
    if (f) setFile(f)
  }

  function handleSeeMore() {
    setShowSeeMore(true)
    onSeeMore && onSeeMore()
  }

  return (
    <section id="home">
      <header>
        <div className="word">TAXORA</div>
      </header>

      <main className="home">
        <div className="heroGroup">
          <div className="eyebrow">INTELLIGENCE · REFINED</div>
          <h1>Think clearly.<br /><span>Explore deeply.</span></h1>
          <p className="sub">
            Tell me where it belongs.
          </p>

          <div className="promptGlow">
            <div className="prompt">
              <input autoComplete="off"
                ref={fileRef}
                className="fileInput"
                id="startFile"
                type="file"
                onChange={handleFileChange}
              />
              <button
                className="startAttach"
                id="startAttach"
                type="button"
                aria-label="Add file"
                title="Add file"
                onClick={() => fileRef.current?.click()}
              >
                <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="m21.4 11.6-8.9 8.9a6 6 0 0 1-8.5-8.5l9.3-9.3a4 4 0 0 1 5.7 5.7l-9.3 9.3a2 2 0 0 1-2.8-2.8l8.6-8.6"/>
                </svg>
              </button>
              <input autoComplete="off"
                id="startInput"
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Start with a thought, question, or idea..."
                aria-label="Start conversation"
              />
              <button className="send" id="startBtn" aria-label="Send" onClick={handleStart}>
                <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M5 12h13"/>
                  <path d="m13 7 5 5-5 5"/>
                </svg>
              </button>
            </div>
          </div>

          {file && (
            <div className="filePill show">
              Attached · {file.name}
            </div>
          )}
        </div>

        <div className="recentGroup">
          <div className={`recentHead recentOnly${sessions.length === 0 ? ' recentEmpty' : ''}`}>
            <span>RECENT CONVERSATIONS</span>
          </div>

          <div className="cards">
            {visibleSessions.map(session => (
              <button
                key={session.id}
                className="card"
                onClick={() => onOpenChat(session.id, null, null)}
              >
                <small>{formatTimestamp(session.timestamp)}</small>
                <b>{session.title}</b>
                <p>{getPreview(session.messages)}</p>
              </button>
            ))}
            {visibleSessions.length === 0 && (
              <div className="card emptyCard">
                <small>NOTHING YET</small>
                <b>No conversations yet</b>
                <p>Type a message or attach a file above to begin.</p>
              </div>
            )}
            {hasMore && (
              <button
                type="button"
                className="seeMoreOnly"
                onClick={handleSeeMore}
                disabled={showSeeMore}
              >
                {showSeeMore ? 'NO MORE RECENT CHATS' : <>SEE MORE <span>+</span></>}
              </button>
            )}
          </div>
        </div>
      </main>
    </section>
  )
}

