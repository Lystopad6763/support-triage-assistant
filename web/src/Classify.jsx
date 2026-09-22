import { useEffect, useRef, useState } from 'react'
import { MAX_CHARS } from './examples.js'
import { CLASSIFY_EXAMPLES, VISIBLE_EXAMPLES } from './classifyExamples.js'
import { CATEGORY_UA, STEP_UA, FACT_UA, PRIORITY_NOTE } from './labels.js'

/**
 * Task 1 on the same page as Task 2: one ticket in, three labels out.
 *
 * The three labels are the product, so they are the first thing rendered and
 * the largest thing on the screen. Everything below them is the reason they
 * can be trusted - the words the model quoted, the facts it enumerated before
 * it chose a priority, and whether either of those contradicts the answer.
 *
 * The vocabulary is NOT on this page. It was, in a column on the right, and it
 * made the answer harder to read rather than easier: twenty-two definitions
 * beside three labels is a reference competing with the thing it explains.
 * app/taxonomy.py holds it, with the share, the test and the allowed steps for
 * every value.
 *
 * The review strip is NOT a confidence threshold. `confidence` averaged 0.86
 * when the answer was right and 0.87 when it was wrong, so it is printed as a
 * number and never used to decide anything; the strip is fed by the five
 * deterministic rules in app/taxonomy.py, each of which can be pointed at.
 */
export default function Classify() {
  const [ticket, setTicket] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [allExamples, setAllExamples] = useState(false)
  const box = useRef(null)

  useEffect(() => { box.current?.focus() }, [])

  async function submit(event) {
    event?.preventDefault()
    const text = ticket.trim()
    if (!text || busy || text.length > MAX_CHARS) return
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const response = await fetch('/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticket: text }),
      })
      const data = await response.json().catch(() => null)
      if (!response.ok) {
        // `message` is ours - budget, rate limit, model failure. Anything else
        // came from the framework, and saying which is the difference between
        // "restart the server" and "wait a minute": a 404 here means the
        // process is older than this page, which is served from disk and so
        // updates without it.
        setError(data?.message || (
          response.status === 404
            ? 'Сервер не знає маршруту /classify — процес запущено до того, '
              + 'як його додали. Перезапустіть uvicorn.'
            : `Помилка ${response.status}: ${data?.detail || 'без пояснення'}`))
      } else setResult(data)
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
      <header>
        <h1>Звернення на вході, три мітки на виході</h1>
        <p className="lede">
          Категорія, пріоритет і наступний крок. Нічого не надсилається клієнту:
          це маршрутизація, а рішення лишається за людиною. Поруч із мітками —
          підстава, за якою їх поставлено, і перевірка, чи модель не суперечить
          сама собі.
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
              {busy ? 'Класифікую…' : 'Класифікувати'}
            </button>
          </div>
        </div>
      </form>

      {!result && !busy && (
        <div className="examples">
          <span className="examples-label">Тікети з відгуків у сторах:</span>
          {(allExamples
            ? CLASSIFY_EXAMPLES
            : CLASSIFY_EXAMPLES.slice(0, VISIBLE_EXAMPLES)).map(e => (
            <button key={e.id} className="chip" title={e.text}
                    onClick={() => useExample(e.text)}>
              {e.label}
            </button>
          ))}
          {!allExamples && CLASSIFY_EXAMPLES.length > VISIBLE_EXAMPLES && (
            <button className="chip more" onClick={() => setAllExamples(true)}>
              Більше ({CLASSIFY_EXAMPLES.length - VISIBLE_EXAMPLES})
            </button>
          )}
        </div>
      )}

      {busy && (
        <div className="working"><span className="spinner" /> Класифікую…</div>
      )}

      {error && <div className="banner error"><strong>{error}</strong></div>}

      {result && (
        <main className="result">
          {result.review?.needed && (
            <div className="banner warn">
              <strong>На розгляд людини</strong>
              <ul className="flags">
                {result.review.flags.map(f => (
                  <li key={f.code}><code>{f.code}</code> — {f.why}</li>
                ))}
              </ul>
            </div>
          )}

          <section className="labels">
            <div className="label">
              <span className="label-key">категорія</span>
              <span className="label-value">
                {CATEGORY_UA[result.category] || result.category}
              </span>
              <code>{result.category}</code>
            </div>
            <div className={`label pri ${result.priority}`}>
              <span className="label-key">пріоритет</span>
              <span className="label-value">{result.priority}</span>
              <code>{PRIORITY_NOTE[result.priority]}</code>
            </div>
            <div className="label">
              <span className="label-key">наступний крок</span>
              <span className="label-value">
                {STEP_UA[result.next_step] || result.next_step}
              </span>
              <code>{result.next_step}</code>
            </div>
          </section>

          <section className="card">
            <h2>Чому такий пріоритет</h2>
            {result.priority_facts.length === 0 ? (
              <p className="note">
                Жодного факту терміновості не названо — а це нормальна відповідь
                для 58% звернень, не збій. Порожній перелік означає P3.
              </p>
            ) : (
              <ul className="facts">
                {result.priority_facts.map(f => (
                  <li key={f}><code>{f}</code> {FACT_UA[f] || ''}</li>
                ))}
              </ul>
            )}
            {result.secondary_categories.length > 0 && (
              <p className="note">
                Звернення торкається також:{' '}
                {result.secondary_categories
                  .map(c => CATEGORY_UA[c] || c).join(', ')}.
                Це підказка людині, а не друга відповідь.
              </p>
            )}
          </section>

          <section className="card">
            <h2>
              Підстава
              {result.evidence_verbatim === false && (
                <span className="lang-note">цитати немає в тексті</span>
              )}
            </h2>
            {result.evidence
              ? <blockquote className={result.evidence_verbatim === false ? 'bad' : ''}>
                  {result.evidence}
                </blockquote>
              : <p className="note">Модель не навела цитати.</p>}
            <p className="note">{result.rationale}</p>
          </section>

          <div className="meta">
            <span>модель {result.meta.model}</span>
            <span className="dim">промпт {result.meta.prompt}</span>
            <span className="dim">{result.meta.latency_ms} мс</span>
            <span className="dim">${result.meta.cost_usd.toFixed(6)}</span>
            <span className="dim">впевненість {result.confidence}</span>
            {result.meta.repaired && <span className="dim">JSON полагоджено</span>}
            {result.meta.attempts > 1 && (
              <span className="dim">спроб {result.meta.attempts}</span>
            )}
          </div>
          <p className="note">
            Впевненість показана, але ні на що не впливає: на нашому наборі вона
            дорівнювала 0,86 коли модель мала рацію і 0,87 коли помилялась.
            Маршрутизацію вирішують п'ять перевірок, а не це число —
            <code>taxonomy.REVIEW_RULES</code>.
          </p>
        </main>
      )}
    </div>
  )
}
