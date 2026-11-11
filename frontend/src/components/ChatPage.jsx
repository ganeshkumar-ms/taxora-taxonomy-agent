import { useState, useEffect } from 'react'
import Sidebar from './Sidebar.jsx'
import MessageList from './MessageList.jsx'
import Composer from './Composer.jsx'
import DocumentViewer from './DocumentViewer.jsx'
import { toViewerDoc } from '../services/api.js'

export default function ChatPage({
  session,
  sessions,
  sidebarOpen,
  onOpenSidebar,
  onCloseSidebar,
  onBack,
  onNew,
  onLoadSession,
  onSend,
  onFeedback,
  onSuggestionClick,
  onRename,
  onDelete
}) {
  const [editingTitle, setEditingTitle] = useState(false)
  const [titleDraft, setTitleDraft] = useState('')
  const [viewerDoc, setViewerDoc] = useState(null)
  const messages = session?.messages || []
  const title = session?.title || 'New conversation'

  // Close the viewer when switching conversations
  useEffect(() => { setViewerDoc(null) }, [session?.id])

  function openDocument(meta) {
    setViewerDoc(toViewerDoc(meta))
  }

  function commitTitle() {
    const v = titleDraft.trim()
    if (session && v && v !== session.title) onRename && onRename(session.id, v)
    setEditingTitle(false)
  }

  return (
    <section
      className={`chatPage${sidebarOpen ? ' drawerOpen' : ''}`}
      id="chatPage"
      style={{ display: 'block' }}
    >
      <div
        className={`scrim${sidebarOpen ? ' show' : ''}`}
        onClick={onCloseSidebar}
      />
      <div className={`layout${viewerDoc ? ' withViewer' : ''}`}>
        <Sidebar
          sessions={sessions}
          currentSessionId={session?.id}
          onNew={onNew}
          onLoad={onLoadSession}
          onClose={onCloseSidebar}
          isOpen={sidebarOpen}
          onRename={onRename}
          onDelete={onDelete}
        />
        <main className="chat">
          <div className="chatHead">
            <div>
              {editingTitle ? (
                <input autoComplete="off"
                  autoFocus
                  className="titleInput"
                  value={titleDraft}
                  maxLength={60}
                  onChange={e => setTitleDraft(e.target.value)}
                  onBlur={commitTitle}
                  onKeyDown={e => {
                    if (e.key === 'Enter') commitTitle()
                    if (e.key === 'Escape') setEditingTitle(false)
                  }}
                />
              ) : (
                <b
                  className={session ? 'titleEditable' : ''}
                  title={session ? 'Click to rename' : ''}
                  onClick={() => {
                    if (!session) return
                    setTitleDraft(session.title)
                    setEditingTitle(true)
                  }}
                >
                  {title}
                  {session && <span className="titlePencil" aria-hidden="true"> &#9998;</span>}
                </b>
              )}
              <small>CONVERSATION SPACE</small>
            </div>
            <div className="mobileActions">
              <button
                className="mobileMenu"
                type="button"
                aria-label="Open recent conversations"
                title="Recent conversations"
                aria-expanded={sidebarOpen}
                onClick={onOpenSidebar}
              >
                <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M5 7h14M5 12h14M5 17h14"/>
                </svg>
                <span className="recentTxt">RECENT</span>
              </button>
              <button className="ghost" onClick={onBack}>
                <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="m3 10 9-7 9 7"/>
                  <path d="M5 9v11h14V9"/>
                  <path d="M9 20v-6h6v6"/>
                </svg>
                <span style={{ marginLeft: '7px' }}>HOME</span>
              </button>
            </div>
          </div>

          <MessageList
            messages={messages}
            onFeedback={onFeedback}
            onSuggestionClick={onSuggestionClick}
            onOpenDocument={openDocument}
          />

          <Composer onSend={onSend} />
        </main>
        <DocumentViewer doc={viewerDoc} onClose={() => setViewerDoc(null)} />
      </div>
    </section>
  )
}


