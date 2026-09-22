import { useState } from 'react'

const LABELS = {
  formal: { name: 'Формальний', hint: 'привітання, посилання на правило, підпис' },
  empathetic: { name: 'Емпатичний', hint: 'починається з того, що сталося з людиною' },
  concise: { name: 'Стислий', hint: 'до трьох речень, одразу дія' },
}

/**
 * One draft, in two languages when the customer did not write in English.
 *
 * The customer's language is shown first and selected by default, because it
 * is the text that gets sent. The English is kept one click away rather than
 * hidden: it is what the policy checks actually read, so an agent who wants to
 * know what was verified has to be able to see it.
 */
export default function Reply({ reply, language }) {
  const hasLocal = Boolean(reply.localised)
  const [showEnglish, setShowEnglish] = useState(!hasLocal)
  const [copied, setCopied] = useState(false)

  const text = showEnglish ? reply.english : reply.localised
  const label = LABELS[reply.tone] || { name: reply.tone, hint: '' }

  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      setCopied(false)
    }
  }

  return (
    <article className={`card reply ${reply.tone}`}>
      <header>
        <div>
          <h3>{label.name}</h3>
          <span className="hint">{label.hint}</span>
        </div>
        <div className="reply-actions">
          {hasLocal && (
            <div className="toggle">
              <button
                className={!showEnglish ? 'on' : ''}
                onClick={() => setShowEnglish(false)}
              >
                {language}
              </button>
              <button
                className={showEnglish ? 'on' : ''}
                onClick={() => setShowEnglish(true)}
              >
                English
              </button>
            </div>
          )}
          <button className={copied ? 'copy done' : 'copy'} onClick={copy}>
            {copied ? '✓ Скопійовано' : 'Копіювати'}
          </button>
        </div>
      </header>
      <p className="reply-text">{text}</p>
      {hasLocal && showEnglish && (
        <p className="note">
          Це версія, яку читають перевірки політик. Клієнтові піде текст
          мовою {language}.
        </p>
      )}
    </article>
  )
}
