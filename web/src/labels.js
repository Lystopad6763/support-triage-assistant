/**
 * How each code is read aloud in Ukrainian, and nothing else.
 *
 * The rules - what each label means, when it is assigned, which steps a
 * category allows - live in app/taxonomy.py, with the share of the corpus and
 * the deciding test beside each value. This file only names things on screen,
 * so that the answer does not read as machine identifiers.
 */
export const CATEGORY_UA = {
  charge_not_recognised: 'платіж не розпізнано',
  price_not_expected: 'сума більша за очікувану',
  cancel_not_possible: 'не вдається скасувати',
  nothing_delivered: 'заплатив, але не отримав',
  app_defect: 'технічна несправність',
  other: 'інше',
}

export const STEP_UA = {
  refund_and_cancel: 'повернути кошти і скасувати',
  cancel_only: 'лише скасувати',
  explain_charge: 'пояснити списання',
  bug_report: 'завести баг',
  redeliver: 'надіслати повторно',
  escalate_to_authority_case: 'ескалація: офіційна справа',
  route_to_human_review: 'на розгляд людини',
}

export const FACT_UA = {
  escalated_out: 'справа вже поза компанією',
  hardship: 'скрутне становище',
  still_bleeding: 'списання тривають',
  deadline: 'час спливає',
  large_amount: 'велика сума',
  card_exposed: 'картка досі прив’язана',
}

export const PRIORITY_NOTE = {
  P1: 'людина дивиться першою',
  P2: 'у межах доби',
  P3: 'звичайна черга',
}

