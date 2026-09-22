import { useEffect, useRef, useState } from 'react'
import Banners from './components/Banners.jsx'
import Crisis from './components/Crisis.jsx'
import Reply from './components/Reply.jsx'
import Citation from './components/Citation.jsx'
import Sources from './components/Sources.jsx'
import Meta from './components/Meta.jsx'
import { EXAMPLES, MAX_CHARS, VISIBLE } from './examples.js'

/**
 * The agent pastes a ticket and reads three drafts. That is the whole product,
 * so the page is one column and the drafts start where the eye lands.
 *
 * What does NOT happen here: nothing is sent to a customer, and no draft is
 * chosen for the agent. The banners above the drafts exist because the
 * assignment asks the interface to mark where a person has to decide, and a
 * mark that has to be looked for is not a mark.
 *
 * Ergonomics are two keystrokes and a click, because this is a tool somebody
 * uses forty times a day: the box is focused on load, Ctrl+Enter sends without
 * reaching for the mouse, and every draft has its own copy button rather than
 * one selection the agent has to make by hand.
 */
export default function App() {
  const [ticket, setTicket] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [health, setHealth] = useState(null)
  const [allExamples, setAllExamples] = useState(false)
  const box = useRef(null)

  useEffect(() => {
    fetch('/health').then(r => r.json()).then(setHealth).catch(() => {})
    box.current?.focus()
  }, [])

  async function submit(event) {
    event?.preventDefault()
    const text = ticket.trim()
    if (!text || busy || text.length > MAX_CHARS) return
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const response = await fetch('/draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticket: text }),
      })
      const data = await response.json()
      if (!response.ok) setError(data.message || 'Не вдалося отримати відповідь.')
      else setResult(data)
    } catch {
      setError('Сервер не відповідає. Спробуйте ще раз за хвилину.')
    } finally {
      setBusy(false)
    }
  }

  function onKeyDown(event) {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') submit(event)
  }

  function useExample(text) {
    setTicket(text)
    setResult(null)
    setError(null)
    box.current?.focus()
  }

  function clear() {
    setTicket('')
    setResult(null)
    setError(null)
    box.current?.focus()
  }

  const over = ticket.length > MAX_CHARS

  return (
    <div className="page">
      <div className="brand">
        <i className="brand-dot" />
        nebula <span>· помічник агента підтримки</span>
      </div>

      <header>
        <h1>Звернення на вході, три чернетки на виході</h1>
        <p className="lede">
          Вставте текст звернення будь-якою мовою. Отримаєте стисле резюме,
          три варіанти відповіді різного тону та цитату з бази знань із
          посиланням на джерело. Клієнту нічого не надсилається — вирішуєте ви.
        </p>
      </header>

      <form onSubmit={submit}>
        <div className="composer">
          <textarea
            ref={box}
            value={ticket}
            onChange={e => setTicket(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Вставте сюди звернення клієнта…"
            spellCheck={false}
          />
          <div className="row">
            <div className="row-left">
              <span className={over ? 'count over' : 'count'}>
                {ticket.length.toLocaleString('uk')} / {MAX_CHARS.toLocaleString('uk')}
              </span>
              <span className="kbd-hint"><kbd>Ctrl</kbd> + <kbd>Enter</kbd></span>
              {ticket && (
                <button type="button" className="ghost" onClick={clear}>
                  Очистити
                </button>
              )}
            </div>
            <button type="submit" className="primary"
                    disabled={busy || !ticket.trim() || over}>
              {busy ? 'Обробляю…' : 'Підготувати відповіді'}
            </button>
          </div>
        </div>
      </form>

      {!result && !busy && (
        <div className="examples">
          <span className="examples-label">Тікети з відгуків у сторах:</span>
          {(allExamples ? EXAMPLES : EXAMPLES.slice(0, VISIBLE)).map(e => (
            <button key={e.id} className="chip" title={e.text}
                    onClick={() => useExample(e.text)}>
              {e.label}
            </button>
          ))}
          {!allExamples && EXAMPLES.length > VISIBLE && (
            <button className="chip more" onClick={() => setAllExamples(true)}>
              Більше ({EXAMPLES.length - VISIBLE})
            </button>
          )}
          {allExamples && (
            <button className="chip more" onClick={() => setAllExamples(false)}>
              Згорнути
            </button>
          )}
        </div>
      )}

      {busy && (
        <div className="working">
          <span className="spinner" /> Шукаю в базі знань і готую чернетки…
        </div>
      )}

      {error && <div className="banner error"><strong>{error}</strong></div>}

      {result?.halted === 'crisis' && <Crisis data={result} />}

      {result && !result.halted && (
        <main className="result">
          <Banners result={result} />

          <section className="card summary">
            <h2>Резюме для агента</h2>
            <p>{result.summary}</p>
          </section>

          <Citation citation={result.citation} />

          <section className="replies">
            <h2>
              Варіанти відповіді
              {result.language && result.language.toLowerCase() !== 'english' && (
                <span className="lang-note">
                  {result.detected_language &&
                   result.detected_language !== result.language
                    ? `клієнт пише: ${result.detected_language} · відповідь: ${result.language}`
                    : `мова клієнта: ${result.language}`}
                </span>
              )}
            </h2>
            {result.replies.map(r => (
              <Reply key={r.tone} reply={r} language={result.language} />
            ))}
          </section>

          <Sources sources={result.sources} ms={result.meta.retrieval_ms} />
          <Meta meta={result.meta} similarity={result.similarity} />
        </main>
      )}

      <footer>
        {health?.ok && (
          <span>
            {health.chunks} документів у базі · відбиток {health.fingerprint} ·
            {' '}модель {health.model} · промпт {health.prompt}
          </span>
        )}
      </footer>
    </div>
  )
}
