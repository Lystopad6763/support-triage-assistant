/**
 * The quote and where it came from.
 *
 * `is_page` matters and is not cosmetic: ten policy documents share one /terms
 * address, so a link can open the page that contains the passage rather than
 * the passage. Saying "here" when it means "somewhere on this page" wastes the
 * agent's time silently, which is the worst way to waste it.
 */
export default function Citation({ citation }) {
  if (!citation?.quote) return null

  return (
    <section className="card citation">
      <h2>
        Цитата з бази знань
        {citation.verified
          ? <span className="badge ok">знайдено в документі</span>
          : <span className="badge warn">не знайдено дослівно</span>}
      </h2>
      <blockquote>{citation.quote}</blockquote>
      <div className="citation-source">
        <code>{citation.doc_id}</code>
        {citation.url && (
          <a href={citation.url} target="_blank" rel="noreferrer">
            відкрити джерело ↗
          </a>
        )}
        {citation.is_page && (
          <span className="note">
            посилання веде на сторінку з кількома документами — шукайте абзац
          </span>
        )}
      </div>
    </section>
  )
}
