/**
 * The vocabulary in Ukrainian: what each code is called, and the one line that
 * says when it is assigned.
 *
 * The full rules live in app/taxonomy.py and arrive over /taxonomy - the exact
 * English the model is given. These lines are the short read of them, and the
 * sheet keeps the English on hover so the two can be compared without leaving
 * the page. What must never drift is the STRUCTURE - which codes exist, their
 * share, which steps a category allows, which facts are hard - and none of that
 * is written here: it all comes from the server.
 */
export const CATEGORY_UA = {
  charge_not_recognised: 'платіж не розпізнано',
  price_not_expected: 'сума більша за очікувану',
  cancel_not_possible: 'не вдається скасувати',
  nothing_delivered: 'оплачене не надійшло',
  app_defect: 'технічна несправність',
  other: 'інше',
}

export const CATEGORY_WHEN = {
  charge_not_recognised:
    'Заперечує будь-яку підписку, або скасував ще до списання, або видалив акаунт — а гроші зняли.',
  price_not_expected:
    'Називає меншу суму, на яку погоджувався — $1, пробний період — а зняли більшу.',
  cancel_not_possible:
    'Скасування не спрацьовує або підписки не видно в App Store чи Google Play.',
  nothing_delivered:
    'Заплатив, але розбір, звіт, кредити чи доступ не надійшли — або надійшли непридатними.',
  app_defect:
    'Технічна поломка: краш, не заходить, не зберігається місце народження, хибний знак.',
  other:
    'Жодна з п’яти причин не описує звернення. Сюди ж — порожній текст і відгук без прохання.',
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

export const STEP_WHEN = {
  refund_and_cancel: 'Гроші вже пішли: повернути і закрити підписку.',
  cancel_only: 'Гроші ще не пішли, або клієнт прямо не просить повернення.',
  explain_charge: 'Хоче зрозуміти, за що платить, і грошей назад не просить.',
  bug_report: 'Дефект для інженерів. Повертати нічого.',
  redeliver: 'Просить сам продукт, а не гроші.',
  escalate_to_authority_case:
    'Справа вже поза підтримкою: чарджбек подано, скарга в органі, спір банку з платформою. Дозволено з будь-якої категорії і завжди P1.',
  route_to_human_review: 'Вирішує людина. Лише разом із категорією «інше».',
}

export const FACT_UA = {
  escalated_out: 'справа вже поза компанією',
  hardship: 'скрутне становище',
  still_bleeding: 'списання тривають',
  deadline: 'час спливає',
  large_amount: 'велика сума',
  card_exposed: 'картка досі прив’язана',
}

export const FACT_WHEN = {
  escalated_out:
    'Названо банк, чарджбек, Apple, Google, поліцію, суд, юриста чи держорган. Погроза без названого органу не рахується.',
  hardship:
    'Втрата дошкуляє матеріально: немає на їжу чи ліки, пенсія, хвороба, безробіття.',
  still_bleeding:
    'Гроші рухаються далі: два окремі списання, «щомісяця», «досі знімають».',
  deadline:
    'Годинник іде: пробний ще триває, списання в дорозі, названо дату наступного платежу.',
  large_amount:
    'Сума велика проти звичних $40–50 — після переведення в долари, а не за кількістю цифр.',
  card_exposed:
    'Картка досі прив’язана і клієнт боїться подальшого доступу, або мусив її блокувати.',
}

export const PRIORITY_NOTE = {
  P1: 'людина дивиться першою',
  P2: 'у межах доби',
  P3: 'звичайна черга',
}

export const PRIORITY_WHEN = {
  P1: 'У переліку є твердий факт: справа поза компанією або скрутне становище.',
  P2: 'Перелік не порожній, але твердих фактів у ньому немає.',
  P3: 'Перелік порожній. Це нормальна відповідь для 58% звернень, не запасний варіант.',
}
