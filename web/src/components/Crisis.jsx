/**
 * What the page shows instead of drafts.
 *
 * Not a banner above three replies - the replies are gone. A tool that offers
 * a choice of tone to somebody who has just said they want to die is worse
 * than a tool that says nothing, and this is the one place where saying less
 * is the whole feature.
 *
 * The numbers are Nebula's own, published on their safety page for 55
 * countries. Nothing here was written by a model and nothing was retrieved.
 */
export default function Crisis({ data }) {
  return (
    <main className="result">
      <section className="card crisis">
        <h2>Чернеток немає — і це навмисно</h2>
        <p>
          У зверненні є ознаки кризового стану. Асистент не пропонує варіантів
          відповіді в таких випадках: тут потрібна людина, а не чернетка.
        </p>
        <p className="note">
          Передайте звернення за протоколом безпеки. Нижче — ресурси, які
          публікує сама компанія.
        </p>

        <ul className="hotlines">
          {data.resources.map(r => (
            <li key={r}>{r}</li>
          ))}
        </ul>

        {data.resources_url && (
          <a href={data.resources_url} target="_blank" rel="noreferrer">
            Сторінка безпеки Nebula ↗
          </a>
        )}
      </section>
    </main>
  )
}
