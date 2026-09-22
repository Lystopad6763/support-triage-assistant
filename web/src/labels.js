/**
 * Ukrainian wording for the label vocabulary, and nothing else.
 *
 * The RULES live in app/taxonomy.py and arrive over /taxonomy - this file only
 * says how each code is read aloud to a Ukrainian-speaking agent. Keeping the
 * two apart is deliberate: a translated rule would be a second definition to
 * keep in step with the first, and the sheet exists precisely so the reader can
 * check an answer against what the model was actually told.
 */
export const CATEGORY_UA = {
  charge_not_recognised: 'списання не впізнане',
  price_not_expected: 'ціна не та, на яку погоджувались',
  cancel_not_possible: 'скасування не працює',
  nothing_delivered: 'оплачене не надійшло',
  app_defect: 'технічна несправність',
  other: 'інше',
}

export const STEP_UA = {
  refund_and_cancel: 'повернути кошти і скасувати',
  cancel_only: 'лише скасувати',
  explain_charge: 'пояснити списання',
  bug_report: 'завести баг',
  redeliver: 'надіслати повторно',
  escalate_to_authority_case: 'ескалація: справа в органі',
  route_to_human_review: 'на розгляд людини',
}

export const FACT_UA = {
  escalated_out: 'справа вже поза компанією',
  hardship: 'скрутне становище',
  still_bleeding: 'гроші продовжують списуватись',
  deadline: 'годинник цокає',
  large_amount: 'велика сума',
  card_exposed: 'картка досі доступна',
}

export const PRIORITY_NOTE = {
  P1: 'людина дивиться першою',
  P2: 'у межах доби',
  P3: 'звичайна черга',
}

export const PRIORITY_RULE_UA = [
  ['P1', 'у переліку є твердий факт: справа поза компанією або скрутне становище'],
  ['P2', 'перелік не порожній, але твердих фактів немає'],
  ['P3', 'перелік порожній — і це нормальна відповідь для 58% звернень'],
]
