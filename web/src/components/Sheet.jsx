import { useEffect, useState } from 'react'
import {
  CATEGORY_UA, STEP_UA, FACT_UA, PRIORITY_NOTE, PRIORITY_RULE_UA,
} from '../labels.js'

/**
 * The vocabulary, beside the answer, so a label can be checked rather than
 * taken on trust.
 *
 * Everything here comes from GET /taxonomy, which renders app/taxonomy.py -
 * the same text the model is given, in the same order. The order matters and is
 * preserved: categories are tested top to bottom and the FIRST one that fits
 * wins, which is why several tickets that look like two categories are not
 * ambiguous at all.
 *
 * When a result is on screen the matching entries are marked. That turns the
 * sheet from a reference into the justification for the answer just given: here
 * is the test that fired, here is the fact that set the priority, here is the
 * row of the table that allowed the step.
 */
export default function Sheet({ result }) {
  const [tax, setTax] = useState(null)

  useEffect(() => {
    fetch('/taxonomy').then(r => r.json()).then(setTax).catch(() => {})
  }, [])

  if (!tax) return null

  const on = {
    category: result?.category,
    step: result?.next_step,
    priority: result?.priority,
    facts: new Set(result?.priority_facts || []),
  }

  return (
    <aside className="sheet">
      <div className="sheet-head">
        <h2>Шпаргалка</h2>
        <p>
          Дослівно те, що бачить модель — англійською, бо саме такими словами їй
          це й сказано. Українською підписано лише назви.
        </p>
      </div>

      <details open>
        <summary>Категорії <span>{tax.categories.length}</span></summary>
        <p className="sheet-note">
          Перевіряються згори вниз, спрацьовує <strong>перша</strong>, що
          підходить. Тому звернення, схоже на дві категорії, не є неоднозначним.
        </p>
        {tax.categories.map(c => (
          <div key={c.code} className={on.category === c.code ? 'entry hit' : 'entry'}>
            <div className="entry-head">
              <strong>{CATEGORY_UA[c.code] || c.code}</strong>
              <span className="share">{c.share}</span>
            </div>
            <code>{c.code}</code>
            <p>{c.test}</p>
            <p className="caveat">{c.not}</p>
            <div className="steps">
              {c.steps.map(s => (
                <span key={s}
                      className={on.category === c.code && on.step === s
                        ? 'pill hit' : 'pill'}>
                  {STEP_UA[s] || s}
                </span>
              ))}
            </div>
          </div>
        ))}
      </details>

      <details>
        <summary>Пріоритет <span>3</span></summary>
        <p className="sheet-note">
          Пріоритет не виводиться з категорії. Модель спершу перелічує факти
          терміновості, які може процитувати, а тоді механічно перетворює
          перелік:
        </p>
        {PRIORITY_RULE_UA.map(([level, rule]) => (
          <div key={level}
               className={on.priority === level ? 'entry hit' : 'entry'}>
            <div className="entry-head">
              <strong className={`lvl ${level}`}>{level}</strong>
              <span className="share">{PRIORITY_NOTE[level]}</span>
            </div>
            <p>{rule}</p>
          </div>
        ))}
        <p className="sheet-note">Шість фактів, і жодного понад це:</p>
        {tax.facts.map(f => (
          <div key={f.code} className={on.facts.has(f.code) ? 'entry hit' : 'entry'}>
            <div className="entry-head">
              <strong>{FACT_UA[f.code] || f.code}</strong>
              <span className="share">{f.hard ? 'твердий → P1' : 'м’який → P2'}</span>
            </div>
            <code>{f.code}</code>
            <p>{f.definition}</p>
          </div>
        ))}
      </details>

      <details>
        <summary>Наступні кроки <span>{tax.steps.length}</span></summary>
        <p className="sheet-note">
          Крок обмежений таблицею: для кожної категорії дозволені лише свої.
          Виняток один — ескалація дозволена звідусіль і завжди P1.
        </p>
        {tax.steps.map(s => (
          <div key={s.code} className={on.step === s.code ? 'entry hit' : 'entry'}>
            <div className="entry-head">
              <strong>{STEP_UA[s.code] || s.code}</strong>
            </div>
            <code>{s.code}</code>
            <p>{s.guide}</p>
          </div>
        ))}
      </details>

      <details>
        <summary>Коли йде до людини <span>{tax.review_rules.length}</span></summary>
        <p className="sheet-note">
          П'ять правил, і жодного порогу за впевненістю: на нашому наборі вона
          дорівнювала 0,86 коли модель мала рацію і 0,87 коли помилялась.
        </p>
        {tax.review_rules.map(r => {
          const fired = (result?.review?.flags || []).some(f => f.code === r.code)
          return (
            <div key={r.code} className={fired ? 'entry hit' : 'entry'}>
              <div className="entry-head"><code>{r.code}</code></div>
              <p>{r.why}</p>
            </div>
          )
        })}
      </details>
    </aside>
  )
}
