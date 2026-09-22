import { useEffect, useState } from 'react'
import {
  CATEGORY_UA, CATEGORY_WHEN, STEP_UA, STEP_WHEN,
  FACT_UA, FACT_WHEN, PRIORITY_NOTE, PRIORITY_WHEN,
} from '../labels.js'

/**
 * The vocabulary, beside the answer: what each label is, and when it is given.
 *
 * Two lines per entry and no more. An earlier version printed the full English
 * rule for every code and became a wall nobody would read while looking for one
 * word - so the rule now lives on hover, in the `title`, exactly as the model
 * receives it, and the visible line is the short Ukrainian read of it.
 *
 * The STRUCTURE comes from GET /taxonomy, which renders app/taxonomy.py: which
 * codes exist, their share of the corpus, which steps each category allows,
 * which facts are hard. None of that is written in the page, so the sheet
 * cannot drift from the file the prompt is built out of. Only the wording is
 * local, in labels.js.
 *
 * With a result on screen the matching entries are marked, which is the whole
 * reason it sits next to the answer rather than on a help page: the test that
 * fired, the fact that set the priority, the row of the table that allowed the
 * step. The label can be checked instead of believed.
 */
export default function Sheet({ result }) {
  const [tax, setTax] = useState(null)

  useEffect(() => {
    fetch('/taxonomy').then(r => r.json()).then(setTax).catch(() => {})
  }, [])

  if (!tax) return null

  const hit = {
    category: result?.category,
    step: result?.next_step,
    priority: result?.priority,
    facts: new Set(result?.priority_facts || []),
  }

  return (
    <aside className="sheet">
      <div className="sheet-head">
        <h2>Словник</h2>
      </div>

      <section>
        <h3>Категорії <span>перша, що підходить</span></h3>
        {tax.categories.map(c => (
          <div key={c.code}
               className={hit.category === c.code ? 'item hit' : 'item'}
               title={`${c.test}\n\n${c.not}`}>
            <div className="item-top">
              <strong>{CATEGORY_UA[c.code] || c.code}</strong>
              <em>{c.share}</em>
            </div>
            <p>{CATEGORY_WHEN[c.code]}</p>
            <div className="pills">
              {c.steps.map(s => (
                <span key={s}
                      className={hit.category === c.code && hit.step === s
                        ? 'pill hit' : 'pill'}>
                  {STEP_UA[s] || s}
                </span>
              ))}
            </div>
          </div>
        ))}
      </section>

      <section>
        <h3>Пріоритет <span>з переліку фактів, не з категорії</span></h3>
        {['P1', 'P2', 'P3'].map(level => (
          <div key={level} className={hit.priority === level ? 'item hit' : 'item'}>
            <div className="item-top">
              <strong className={`lvl ${level}`}>{level}</strong>
              <em>{PRIORITY_NOTE[level]}</em>
            </div>
            <p>{PRIORITY_WHEN[level]}</p>
          </div>
        ))}
      </section>

      <section>
        <h3>Факти терміновості <span>шість, і жодного понад</span></h3>
        {tax.facts.map(f => (
          <div key={f.code}
               className={hit.facts.has(f.code) ? 'item hit' : 'item'}
               title={f.definition}>
            <div className="item-top">
              <strong>{FACT_UA[f.code] || f.code}</strong>
              <em className={f.hard ? 'hard' : ''}>
                {f.hard ? 'твердий → P1' : 'м’який → P2'}
              </em>
            </div>
            <p>{FACT_WHEN[f.code]}</p>
          </div>
        ))}
      </section>

      <section>
        <h3>Наступні кроки <span>обмежені таблицею категорії</span></h3>
        {tax.steps.map(s => (
          <div key={s.code}
               className={hit.step === s.code ? 'item hit' : 'item'}
               title={s.guide}>
            <div className="item-top">
              <strong>{STEP_UA[s.code] || s.code}</strong>
              <em>{s.guide.split('.')[0]}</em>
            </div>
            <p>{STEP_WHEN[s.code]}</p>
          </div>
        ))}
      </section>

      <section>
        <h3>До людини <span>правила, не поріг впевненості</span></h3>
        {tax.review_rules.map(r => {
          const fired = (result?.review?.flags || []).some(f => f.code === r.code)
          return (
            <div key={r.code} className={fired ? 'item hit' : 'item'}>
              <div className="item-top"><strong>{r.code}</strong></div>
              <p>{r.why}</p>
            </div>
          )
        })}
      </section>
    </aside>
  )
}
