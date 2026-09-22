// Eight real tickets from data/sets/golden_v1.json, hand-labelled, and every one
// of them a case where a draft is the wrong output. A decision has already been
// taken by someone who is not us: a report filed, a dispute opened, an account
// blocked, a promise made - or the knowledge base simply has no answer, which
// the retrieval gold says outright for most of these.
//
// The comment above each names what the deterministic boundary layer returned
// and where the retriever put the right document. Only one of the eight trips
// the word list; the rest are caught by the knowledge base having nothing to
// ground on, which is why the assistant has two independent layers and not one.
//
// The first four show by default; the rest are behind "Більше".
//
// The first twelve opened this tab; the ones after them are cases where a
// draft is the wrong output at all. Two tickets appeared in both groups and
// are kept once, so the count is not twelve plus eight.


export const MAX_CHARS = 12000
export const VISIBLE = 4

export const EXAMPLES = [
  {
    id: "gp:7e8f319c-459",
    label: "Психік не відповів, кредити згоріли",
    // en_or_unknown / nothing_delivered · еталонний документ на позиції 2
    text: "every time the psychic would go to answer me it would go busy and I never got an answer and the time would run out I even bought some extra credits and it never got transferred in very disappointed and I want my money back",
  },
  {
    id: "as:7469353964",
    label: "Перехід до астролога глючить",
    // en_or_unknown / app_defect · еталонний документ на позиції 1
    text: "Astrologers Error I really love the app and the design. I also love how you can learn more about yourself and your signs. The only I problem is that when I try to go to a “astrologer” it glitches out. It keep saying “something went wrong, try again.” And I have to end up force closing the app because it get stuck there. Please fix this.",
  },
  {
    id: "gp:82d224b2-190",
    label: "Прогноз суперечить реальному транзиту",
    // en_or_unknown / app_defect · еталонний документ на позиції 1
    text: "The app and daily predictions are somewhat good, but the weekly and monthly ones are extremely wrong, they say a planet is transiting x house, when the reality it's the complete opposite! I'm an astrologer, I know! Please fix these errors, as it changes the whole prediction",
  },
  {
    id: "as:7839095010",
    label: "Акаунт заблоковано за віком",
    // en_or_unknown / other · еталонний документ на позиції 2
    text: "Pelase take off the age restriction thing. I absolutely loved this app untill you suspended my account for being “too young” i dont understand why this app has an age restriction, Its an astrology app, could you pelase get rid of it, i really want to use it but i cant because i was born in [BirthDate] and you need to be born in [BirthDate] to use it but i cant because if i change my birth year to that, then my readings wont be right. :(",
  },
  {
    id: "gp:49399c13-8f7",
    label: "Іспанська · прибрати дані картки",
    // es / other · еталонний документ на позиції 1
    text: "por favor !! quiten mis datos de tarjeta !! no me hagan ningun rebajo más !!! por favor, quiten la suscripción !!! pague, y nada fue lo que esperaba, ya desinstale esa app... porfavor gracias",
  },
  {
    id: "gp:b3528ce5-5cc",
    label: "Іспанська · не зберігається дата народження",
    // es / app_defect · еталонний документ на позиції 1
    text: "quiero decir que arreglen el tema de la fecha de nacimiento porque yo quiero entrar pero no aparece mi fecha y estaría bueno que lo arreglen..",
  },
  {
    id: "gp:d6e6182c-c69",
    label: "Іспанська · застосунок лише англійською",
    // es / app_defect · еталонний документ на позиції 1
    text: "Esta buena la app pero necesito que este en español porque si no tengo que usar mucho el traductor y no entiendo lo que dice",
  },
  {
    id: "gp:530e156f-6dc",
    label: "Французька · не вдається відписатись",
    // fr / cancel_not_possible · еталонний документ на позиції 1
    text: "je veux me désabonner et c'est impossible on me prend 39€ depuis juin c'est abusé Comment peut-on faire pour être remboursé",
  },
  {
    id: "gp:9888b65c-3d2",
    label: "Турецька · 1200 TL після скасування",
    // tr / charge_not_recognised · еталонний документ на позиції 1
    text: "Deneme süresi bitmeden üyelik iptali yapmama rağmen 1200 TL hesabımdan para çekilmiş.Bu kabul edilemez.Acil olarak para çekmeyi sonlandırın ve paramı iade edin.Yoksa hukuki haklarımı kullanacağım.",
  },
  {
    id: "gp:4c3c5636-634",
    label: "Корейська · $1 обернувся підпискою",
    // hangul / price_not_expected · еталонний документ на позиції 1
    text: "아니, 재미삼아 1달러 결제하고 나갔는데 그날 바로 구독료나가고 1주일 뒤에는 배로 결제되었네요. 어떻게 이럴수 있습니까? 구독취소는 왜 안되게 해놓은겁니까? 구독동의도 하지않았는데 구독되게 해놓고 자동결제하는건 사기 아닌가요? 플레이스토어에서 구독 왜 취소 안되나요? 구독목록은 왜 안뜨게 해놓으신거죠? 그래놓고 영어설명에는 구독되어있으니 취소방법 올려놓으셨던데 사기 아닌가요? 저 해외불법청구로 카드사에 신고해놨습니다. 저 정말로 화가나네요. 법적대응 찾을것이니 후속조치 바랍니다. 그리고 답변 한국말로 적으세요. 왜 영어로 답변 답니까? 팔아먹을때는 한국어고, 고지내용, 환급정책은 다 영어네요? 것도 한국어로 다 다세요. 그리고 답변 이거 AI죠? 메일 주소도 통일되어있지 않던데요? 이거 파봐야겠네. 대응이 성의없어서 신고하겠습니다.",
  },
  {
    id: "gp:627a8093-bdb",
    label: "Італійська · підписка, якої не замовляли",
    // it / charge_not_recognised · еталонний документ на позиції 1
    text: "mi e appena apparso un abbonamento di 49,90 non richiesto da me e non so come posso annullarlo....già provato fare la segnalazione....comunque i soldi non ci sono e non ci saranno in quella carta quindi avrei bisogno cortesemente di ritirare la richiesta di pagamento si questo abbonamento che non l'ho richiesto",
  },
  {
    id: "as:5355417868",
    label: "Довічна покупка не відновлюється",
    // en_or_unknown / nothing_delivered · еталонний документ на позиції 1
    text: "Cannot restore purchase The app seems to be error then I reinstalled it and cannot restore the life-time purchase $119.99 (it said “try again later”). I already paid on Dec 10, 2019 and the bill was sent to my email. Please check immediately!!!",
  },
  {
    id: "gp:9dd03aa6-f28",
    label: "Погрожує позовом",
    // legal · еталонний документ на позиції 2
    text: "I have never subscribed to anything I even deleted my account and I was charged 42 dollars for what.I even contacted them to stop trying to deduct money from me as I do not have any subscription with them.Please refund my money or im going to sue you you are complete fraudstars",
  },
  {
    id: "gp:758d89da-c44",
    label: "Португальська · поліція і заява на YouTube",
    // межі: не спрацювали · бази знань на це немає - правильна відповідь grounded: false
    text: "ISSO É UM GOLPE, QUERO SABER SE ESSES GOLPISTAS VÃO TER ACESSO AO MEUS CARTÃO, JÁ DENUNCIEI VOCÊS NO YOUTUBE, COMPREI UM VALOR DE 13 REAIS E RASPARAM MINHA CONTA DE CRÉDITO SE EU TIVESSE UM VALOR ALTO TINHAM PEGADO, EU QUERO MEU DINHEIRO, E AINDA FICAM PEDINDO PRA MANDAR MENSAGEM PARA RESOLVER DEVOLVAM MEU DINHEIRO SIMPLES, NAO VEIO EMAIL DE COMPROVANTE DE PAGAMENTO. E AINDA FICAM MANDANDO MENSAGEM QUE O MEU PROBLEMA ESTÁ RESOLVIDO, NÃO NÃO ESTÁ RESOLVIDO,CASO DE POLÍCIA.",
  },
  {
    id: "gp:714879d6-762",
    label: "Антивірус повідомляє про malware",
    // межі: не спрацювали · бази знань на це немає - правильна відповідь grounded: false
    text: "Hey I just wanted you to know I just use this anti-spyware app and it says you have malware on this app please check with your anti virus software or team to make sure to remove it so it doesn't harm your customers!",
  },
  {
    id: "gp:cd1b6ada-e47",
    label: "Обіцяне повернення не виплачене понад місяць",
    // межі: не спрацювали · еталонний документ на позиції 1
    text: "I had downloaded the app and subscribed because it said I would get my money back if I unsubscribe within 3 days .. I unsubscribe that same night and I haven't received my money it's been over a month now 32.46 is wat it charged me... i need that money back",
  },
  {
    id: "as:12957254026",
    label: "Російська · астролог вийшов із чату",
    // межі: не спрацювали · еталонний документ на позиції 5
    text: "Проблема. Деньги вычитывают из баланса, а вместо ответа астролог покидает чат. И потом требуют чтобы я снова пополнила баланс чтобы увидеть ответ, так как время и кредиты утекли! Будьте добры компенсируйте это!",
  },
  {
    id: "gp:846a3603-136",
    label: "Французька · після оплати все англійською",
    // межі: не спрацювали · еталонний документ на позиції 1
    text: "promotion offerte à 1 euro pour essaie présente en français pour tout ce qui est du questionnaire de préambule et une fois payé pour accéder à l appli... tout passe en anglais !! je demande un remboursement pour non conformité et la on me demande mes infos banquaires soit disant nécessaire pour me rembourser alors que j ai payé avec PAYPAL.... Ca pue l arnaque!!",
  },
]
