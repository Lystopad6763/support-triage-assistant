import { useState } from 'react'

/**
 * What the search actually returned, and how long it took.
 *
 * Collapsed, but the label alone answers the question the page otherwise
 * leaves open: were these drafts written from the knowledge base or from the
 * model's memory. Five documents and a number of milliseconds say the first.
 */
export default function Sources({ sources, ms }) {
  const [open, setOpen] = useState(false)
  if (!sources?.length) return null

  return (
    <section className="card sources">
      <button className="disclosure" onClick={() => setOpen(!open)}>
        {open ? '▾' : '▸'} Пошук у базі знань · знайдено{' '}
        {sources.length} з 73 документів за {(ms / 1000).toFixed(2)} с
      </button>
      {open && (
        <>
          <p className="note sources-note">
            Чернетки спираються лише на ці документи. Усе, чого тут немає,
            асистент стверджувати не має права.
          </p>
          <ol>
            {sources.map(s => (
              <li key={s.doc_id}>
                <a href={s.url} target="_blank" rel="noreferrer">{s.title}</a>
                <code>{s.doc_id}</code>
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  )
}
