/**
 * Eight tickets for the classifier tab, and they are not a random sample.
 *
 * Every one is a real ticket from data/sets/dev_v1.json on which the shipped
 * pair - prompt v4, gemini-3.1-flash-lite - already produced all three labels
 * correctly, with a quote that really is in the text. They were chosen that way
 * on purpose: a demo button that fails is a demo button nobody presses twice.
 *
 * So do NOT read the hit rate here as the system's. That number is in
 * data/runs/, measured on 157 rows nobody picked: macro-F1 0.803 on the core
 * classes, and 54 of those 157 rows are wrong in at least one field.
 *
 * Between them they cover all six categories, five of the seven steps, all
 * three priorities and five languages - so the sheet on the right lights up in
 * a different place each time.
 */
export const CLASSIFY_EXAMPLES = [
  {
    id: "gp:00ba66b2-f3e",
    label: "Італійська · раптове списання",
    // charge_not_recognised / P3 / refund_and_cancel
    text: "MI SONO RITROVATA CON 49 EURO IN MENO SUL CONTO ... SENZA SAPERE PERCHE. NON È SPECIFICATO CHE SI ATTIVA L'ABBONAMENTO ORA CHIEDO IL RIMBORSO. COME FACCIO?",
  },
  {
    id: "as:14252277944",
    label: "Китайська · пробний став річною",
    // price_not_expected / P1 / refund_and_cancel
    text: "骗子软件 上面显示是三天免费试用，结果一下载就扣了363，退款也被拒绝了 ，I was misled by the interface into an accidental subscription, losing 363 RMB. Apple refused a refund, and your response was just \"we'll look into it\" with no real action. If you can collect the payment, why not refund it? Please stop the runaround and solve this issue.",
  },
  {
    id: "as:5579173328",
    label: "Не вдається відписатись",
    // cancel_not_possible / P2 / cancel_only
    text: "Please Help Hi, I just downloaded the app but didn’t know it had a fee. Can’t figure out how to unsubscribe and not be charged. Please let me know how to cancel subscription before getting charged as I don’t need this app. There are no Settings in the app which is un fortunate. Please help asap.",
  },
  {
    id: "as:7473868563",
    label: "Оплачене не відкривається",
    // nothing_delivered / P3 / redeliver
    text: "Bug in app The app is overall amazing. However, in the past 2 weeks, I am not able to open my conversations I’ve had with astrologers. I just got an alert that I had an answer to my question but the app gave me an error message saying “data couldn’t be read because it is missing”. I did not see any way to contact in the app. I paid for the question, but I cannot see the response. I thought about deleting and reinstalling the app, but I’m not sure if my info and past activities will transfer. Please help....",
  },
  {
    id: "as:13607579600",
    label: "Застосунок не вантажиться",
    // app_defect / P3 / bug_report
    text: "App Having Trouble Loading I haven't used this app in a while and I tried going into the app. It would exit without loading. It just started doing this issue for me and it still won't load. Please help to fix this issue for me so I can use this app without it doing this same issue",
  },
  {
    id: "gp:8b9dc776-d5f",
    label: "Не про гроші зовсім",
    // other / P3 / route_to_human_review
    text: "I love how I got to put \"non-binary\" as my gender cause I can't tell if I want to be a girl, or boy. Now on to the main topic It gives me random stuff that I have to \"buy\" and it wants to know where I live? What's up with that??",
  },
  {
    id: "as:13425069663",
    label: "Португальська · послугу не надано",
    // nothing_delivered / P3 / refund_and_cancel
    text: "O pior aplicativo que já usei na minha vida Ele não entregou o serviço que eu paguei, quero o dinheiro de volta! O aplicativo trava o tempo todo, nao tem nenhum conteúdo relevante.",
  },
  {
    id: "as:12669241957",
    label: "Іспанська · підписки не видно",
    // charge_not_recognised / P3 / refund_and_cancel
    text: "Cobros excesivos Desde que revisé la app el día que la descargue comprobé que no estaba la suscripción activada, es más no aparece en mis suscripciones activas, aún así me han cobrado 39,90 por una semana. Nunca la usé por que está todo en inglés. Quiero que me devuelvan el dinero!!!",
  },
]

export const VISIBLE_EXAMPLES = 4
