import { useState } from 'react'

/** The five documents retrieval returned, so the agent can see what was read. */
export default function Sources({ sources }) {
  const [open, setOpen] = useState(false)
  if (!sources?.length) return null

  return (
    <section className="card sources">
      <button className="disclosure" onClick={() => setOpen(!open)}>
        {open ? '▾' : '▸'} Документи, які знайшов пошук ({sources.length})
      </button>
      {open && (
        <ol>
          {sources.map(s => (
            <li key={s.doc_id}>
              <a href={s.url} target="_blank" rel="noreferrer">{s.title}</a>
              <code>{s.doc_id}</code>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
