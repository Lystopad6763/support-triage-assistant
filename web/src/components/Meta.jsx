/**
 * Latency, cost and how different the three drafts actually are.
 *
 * The similarity number is here rather than in a report because it is the one
 * that says whether the agent was given a choice or three paraphrases, and an
 * agent who sees it once learns to distrust the day it climbs.
 */
export default function Meta({ meta, similarity }) {
  const worst = similarity
    ? Math.max(...Object.values(similarity))
    : null

  return (
    <section className="meta">
      <span>{(meta.total_ms / 1000).toFixed(1)} с</span>
      <span className="dim">
        пошук {meta.retrieval_ms} · генерація {meta.generation_ms}
        {meta.localise_ms > 0 && ` · переклад ${meta.localise_ms}`}
      </span>
      <span>${meta.cost_usd.toFixed(5)}</span>
      {worst !== null && (
        <span className={worst > 0.5 ? 'warn-text' : ''}>
          схожість тонів ≤ {worst.toFixed(2)}
        </span>
      )}
      <span className="dim">{meta.model} · {meta.prompt}</span>
    </section>
  )
}
