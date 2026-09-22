// Twelve real tickets from data/sets/golden_v1.json, hand-labelled by a person
// and then measured once: the comment above each one is what the labeller wrote
// down, and each is a row the shipped pair got right in all three fields on the
// golden run (data/runs/20260922-092600_*).
//
// Chosen for the stories rather than for the categories. A bank-versus-platform
// dispute already running, an antivirus reporting malware in the app, an account
// suspended for age, a sketch that never arrived, a woman who expected a photo
// and was handed to a psychic, a Turkish charge of 1,161.29 that is an ordinary
// $35 once converted - the trap our own labelling fell into first. Six
// languages, all six categories, and the two rarest steps in the taxonomy.
//
// Not a sample, and not a hit rate. They were picked BECAUSE the model gets them
// right, so a demo button does not fail in front of someone; the honest number
// is 151 of 235 golden rows correct in all three fields.
//
// The first four show by default; the rest are behind "Більше".
//
// The first eight opened this tab; the twelve after them were added later
// from golden. The order is deliberate - the plain shapes first, the
// awkward stories after.


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
id: "gp:83ce12d3-9f5",
    label: "Французька · доступу так і не дали",
    // nothing_delivered / P3 / refund_and_cancel
    text: "Arnaque complète, je demande d'ailleurs le remboursement de la, somme dépenser puisque je n'ai eu accès à rien de ce que j'ai demandé.... Tout est en anglais et rien ne ressemblait à ma, demande très mauvaise expérience",
  },
  {
id: "as:12669241957",
    label: "Іспанська · підписки не видно",
    // charge_not_recognised / P3 / refund_and_cancel
    text: "Cobros excesivos Desde que revisé la app el día que la descargue comprobé que no estaba la suscripción activada, es más no aparece en mis suscripciones activas, aún así me han cobrado 39,90 por una semana. Nunca la usé por que está todo en inglés. Quiero que me devuelvan el dinero!!!",
  },
  {
id: "as:14139572007",
    label: "Іспанська · спір банку з платформою триває",
    // charge_not_recognised / P1 / escalate_to_authority_case · триває спір між її банком і платформою
    text: "Auto conocimiento Engancha y es buena la informacion. Problema: te das de baja de la suscripcion o sin suscribirte haces una compra… y yo llevo meses intentando que me devuelvan cada cargo inventado por ellos ( hasta 3 seguidos en minutos) y muchos días… para no tener que bloquear mi tarjeta de crédito. Con litigios entre mi banco u la plataforma sigo.",
  },
  {
id: "gp:714879d6-762",
    label: "Антивірус повідомляє про malware",
    // other / P3 / route_to_human_review · звіт про безпеку: антивірус користувача повідомляє про шкідливий код
    text: "Hey I just wanted you to know I just use this anti-spyware app and it says you have malware on this app please check with your anti virus software or team to make sure to remove it so it doesn't harm your customers!",
  },
  {
id: "as:7839095010",
    label: "Акаунт заблоковано за віком",
    // other / P3 / route_to_human_review · політика акаунта: блокування за віком, заявник неповнолітній і просить
    text: "Pelase take off the age restriction thing. I absolutely loved this app untill you suspended my account for being “too young” i dont understand why this app has an age restriction, Its an astrology app, could you pelase get rid of it, i really want to use it but i cant because i was born in [BirthDate] and you need to be born in [BirthDate] to use it but i cant because if i change my birth year to that, then my readings wont be right. :(",
  },
  {
id: "as:12432196856",
    label: "Оголосив, що подає чарджбек",
    // charge_not_recognised / P1 / refund_and_cancel · заявив про чарджбек
    text: "Refund I will start a chargeback, I have unsubscribed 7 months ago and you guys have just charged me. Please refund me immediattely",
  },
  {
id: "gp:00a73c05-36d",
    label: "Скетч не надійшов, просить саме його",
    // nothing_delivered / P3 / redeliver · скетч не прийшов
    text: "where's my sketch? instead I'm lured into some psychic stuff, I want nothing to do with it. I should be able to unsubscribe and I cannot do that easily like when I signed up.",
  },
  {
id: "gp:ab4ec96c-f56",
    label: "Чекала фото, відправили до екстрасенса",
    // nothing_delivered / P3 / refund_and_cancel · чекала фото, відправили до екстрасенса
    text: "still can't figure out what's going on, I thought you were gonna send me a photo, got sent to a so called psychic instead. jst another gimmick to get you to give them money, and download there app, still haven't got my pic, I want my money back. all I wanted was the pic, Im not allowed to be talking to a psychic, part of my religion, the only psychic I believe in is the Holy King, one and only, he says not to entertain these things, it's a gimmick, I was doing this for the fun and boredom, feelI",
  },
  {
id: "as:13564172721",
    label: "Корейська · оплатив у вебі, результат лише в застосунку",
    // nothing_delivered / P3 / refund_and_cancel · ВІДГУК: заголовок 시간낭비랑 상술 오짐
    text: "시간낭비랑 상술 오짐 웹에서 결제해놓고 무조건 앱 다운로드해야 결과 볼 수 있고... 귀찮고 어디까지 가나 싶어서 깔아봤는데 결과 나오려면 10분 걸린다길래 각 보여서 그냥 지웁니다. 환불이나 해주든가. 결과도 내놓고 돈이나 받아먹든가.",
  },
  {
id: "gp:846a3603-136",
    label: "Французька · після оплати все англійською",
    // nothing_delivered / P3 / refund_and_cancel · опитування французькою, після оплати все англійською - куплене неприда
    text: "promotion offerte à 1 euro pour essaie présente en français pour tout ce qui est du questionnaire de préambule et une fois payé pour accéder à l appli... tout passe en anglais !! je demande un remboursement pour non conformité et la on me demande mes infos banquaires soit disant nécessaire pour me rembourser alors que j ai payé avec PAYPAL.... Ca pue l arnaque!!",
  },
  {
id: "gp:b8abd509-487",
    label: "Італійська · не може скасувати через мову",
    // cancel_not_possible / P3 / cancel_only · не може скасувати, бо не знає англійської
    text: "l'ho scaricato per sbaglio e ora mi ritrova abbonata ... no n so come fare ad annullare abbonamento perché non parlo inglese...",
  },
  {
id: "as:12734468144",
    label: "Турецька · погоджувався на 19,99, знято 1 161,29",
    // price_not_expected / P3 / refund_and_cancel · погодився на 19,99 TL, знято 1161,29
    text: "you fooled I was charged 1,161,29 TL without permission. I only agreed to pay 19.99 TL. I want to cancel and get a refund. Please help.",
  },
  {
id: "as:13585202841",
    label: "Акаунт видалено, гроші ще намагаються зняти",
    // charge_not_recognised / P3 / cancel_only · гроші ще не зняті, застосунок лише намагається
    text: "? I deleted my account about a week ago, this app still wants to withdraw money from my card even though I didn't buy a subscription, how do I understand this? How can I fix this? Contact me urgently!",
  },
  {
id: "gp:d6e6182c-c69",
    label: "Іспанська · просить іспанську мову",
    // app_defect / P3 / bug_report · ВІДГУК: Esta buena la app pero
    text: "Esta buena la app pero necesito que este en español porque si no tengo que usar mucho el traductor y no entiendo lo que dice",
  },
]

export const VISIBLE_EXAMPLES = 4
