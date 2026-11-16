import { useState, useEffect } from 'react'

const THINKING_STEPS = [
  'Inspecting document semantics & structure...',
  'Verifying security & BFSI privacy guardrails...',
  'Evaluating 5-level taxonomy hierarchy (Level 1 → 5)...',
  'Synthesizing per-level rationales & audit traceability...'
]

export default function ThinkingBubble() {
  const [stepIdx, setStepIdx] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setStepIdx(i => (i + 1) % THINKING_STEPS.length)
    }, 700)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="thinking thinkingBubbleCard" aria-live="polite">
      <div className="thinkNameWrap">
        <span className="thinkName">TAXORA</span>
        <span className="bars">
          <i /><i /><i /><i /><i />
        </span>
      </div>
      <div className="thinkingStatusPill">
        <span className="thinkingPulseDot" aria-hidden="true" />
        <span className="thinkingStatusText">{THINKING_STEPS[stepIdx]}</span>
      </div>
    </div>
  )
}
