/**
 * The marks the assignment asks for: where the interface has to say that a
 * person decides, not the tool.
 *
 * They sit ABOVE the drafts rather than beside them. A warning placed next to
 * the thing it warns about is read after the thing, which for a draft means
 * after it has already been copied.
 */
export default function Banners({ result }) {
  const marks = []
  const flags = result.boundaries?.flags || []

  if (flags.includes('minor')) {
    marks.push({
      kind: 'stop',
      title: 'Схоже на неповнолітнього',
      body: 'У тексті є ознаки того, що підписку оформила дитина або пише ' +
        'неповнолітній. Жодних фінансових обіцянок у відповіді — це окремий ' +
        'маршрут, і рішення ухвалює людина.',
    })
  }

  if (flags.includes('legal')) {
    marks.push({
      kind: 'stop',
      title: 'Справа вже має юридичний бік',
      body: 'У зверненні названо держорган, юриста, суд або вже поданий ' +
        'банківський спір. Відповідь читатиме не лише клієнт — узгодьте ' +
        'формулювання, перш ніж надсилати.',
    })
  }

  if (result.needs_human) {
    marks.push({
      kind: 'stop',
      title: 'Не надсилайте, не прочитавши',
      body: (result.needs_human_reason ||
        'У зверненні є обставини, рішення щодо яких ухвалює людина.') +
        (flags.length
          ? ` Перевірка тексту також позначила: ${flags.join(', ')}.`
          : ''),
    })
  }

  if (!result.grounded) {
    marks.push({
      kind: 'warn',
      title: 'База знань цього не покриває',
      body: 'Жоден документ не відповідає на це звернення, тому чернетки нижче ' +
        'нічого не стверджують по суті — вони уточнюють і передають далі. ' +
        'Факти доведеться взяти деінде.',
    })
  }

  if (result.banned?.length) {
    marks.push({
      kind: 'warn',
      title: 'Спрацював запобіжник',
      body: 'У чернетці є твердження, яке суперечить політиці: ' +
        result.banned.join('; ') + '. Перевірте цей рядок перед надсиланням.',
    })
  }

  if (!result.citation?.verified && result.grounded) {
    marks.push({
      kind: 'warn',
      title: 'Цитату не знайдено в документі',
      body: 'Речення нижче не вдалося знайти дослівно в названому документі. ' +
        'Відкрийте джерело й перевірте, перш ніж посилатись на нього.',
    })
  }

  if (!marks.length) return null

  return (
    <div className="banners">
      {marks.map(m => (
        <div key={m.title} className={`banner ${m.kind}`}>
          <strong>{m.title}</strong>
          <span>{m.body}</span>
        </div>
      ))}
    </div>
  )
}
