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
export const MAX_CHARS = 12000
export const VISIBLE = 4

export const EXAMPLES = [
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
    id: "as:7839095010",
    label: "Акаунт заблоковано за віком",
    // межі: не спрацювали · бази знань на це немає - правильна відповідь grounded: false
    text: "Pelase take off the age restriction thing. I absolutely loved this app untill you suspended my account for being “too young” i dont understand why this app has an age restriction, Its an astrology app, could you pelase get rid of it, i really want to use it but i cant because i was born in [BirthDate] and you need to be born in [BirthDate] to use it but i cant because if i change my birth year to that, then my readings wont be right. :(",
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
    id: "gp:7e8f319c-459",
    label: "Психік замовк, кредити згоріли",
    // межі: не спрацювали · еталонний документ на позиції 2
    text: "every time the psychic would go to answer me it would go busy and I never got an answer and the time would run out I even bought some extra credits and it never got transferred in very disappointed and I want my money back",
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
