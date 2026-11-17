import { useState, useRef } from 'react'

export default function Composer({ onSend }) {
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const fileRef = useRef(null)

  function handleSubmit(e) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed && !file) return
    onSend(trimmed, file)
    setText('')
    setFile(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  function handleFileChange(e) {
    const f = e.target.files && e.target.files[0]
    if (f) setFile(f)
  }

  return (
    <div className="composerArea">
      {file && (
        <div style={{ display: 'flex', justifyContent: 'center', width: '100%', margin: '0 auto 10px' }}>
          <div className="attachedRow composerAttached">
            <span className="attachChip">
              <span className="attachName">{file.name}</span>
              <button
                type="button"
                className="attachRemove"
                aria-label={`Remove ${file.name}`}
                onClick={() => { setFile(null); if (fileRef.current) fileRef.current.value = '' }}
              >
                ×
              </button>
            </span>
          </div>
        </div>
      )}
      <div className="composer">
        <input autoComplete="off"
          ref={fileRef}
          type="file"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        <form onSubmit={handleSubmit}>
          <button
            className="plus"
            type="button"
            aria-label="Add file"
            title="Add file"
            onClick={() => fileRef.current?.click()}
          >
            <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="m21.4 11.6-8.9 8.9a6 6 0 0 1-8.5-8.5l9.3-9.3a4 4 0 0 1 5.7 5.7l-9.3 9.3a2 2 0 0 1-2.8-2.8l8.6-8.6"/>
            </svg>
          </button>
          <input
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="Message TAXORA..."
            maxLength={1000}
            autoComplete="off"
            aria-label="Message"
          />
          <button className="chatSend" aria-label="Send">
            <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M5 12h13"/>
              <path d="m13 7 5 5-5 5"/>
            </svg>
          </button>
        </form>
      </div>
      <div className="fine">TAXORA · AI TAXONOMY EXPERT</div>
    </div>
  )
}
