// Real tickets, straight out of benchmark/tickets.csv - the same 430 the
// retrieval grid was scored on. Nothing here was written for the demo, which is
// the point: a demo whose examples were composed for it proves only that they
// were composed for it.
//
// Twelve, chosen to break in different places. Nine languages against a
// knowledge base that exists only in English. Both stores, including one whose
// text names the other - the case where the store prefix would send retrieval
// to the wrong cancellation rail. A trial that converted, a charge with no
// subscription behind it, a service never delivered, and one complaint that is
// really about the price of a free app.
//
// The first four show by default; the rest are behind "Більше", because a wall
// of twelve chips is a wall, not a choice.
export const MAX_CHARS = 12000
export const VISIBLE = 4

export const EXAMPLES = [
  {
    id: "gp:953b362d-75b",
    label: "Англійська · двічі списали",
    text: "charged, my card 2 times and I didn't do anything with your site. 48 on April 30 and 58 on April 1st. I want my money back",
  },
  {
    id: "as:7628936087",
    label: "Іспанська · випадкова підписка",
    text: "apreté sin querer para hacer una suscripción y ahora no la puedo cancelar me cobraron $49.49 dólares quiero mi dinero de vuelta",
  },
  {
    id: "gp:6915993b-f13",
    label: "Німецька · не вдалося скасувати пробний",
    text: "Ich bin äußerst unzufrieden mit der App, alles hängt und ich konnte mein Test-Abo nicht kündigen... Ich möchte ein refund",
  },
  {
    id: "as:13425069663",
    label: "Португальська · не отримав послугу",
    text: "Ele não entregou o serviço que eu paguei, quero o dinheiro de volta! O aplicativo trava o tempo todo, nao tem nenhum conteúdo relevante.",
  },
  {
    id: "gp:ec01520a-736",
    label: "Іспанська · $1 обернулись на $40",
    text: "Pague por la prueba 1$ y NUNCA autorize a que me cobren 40$ pasado unos días, hasta había desinstalado la app DEVUELVAN MI DINERO",
  },
  {
    id: "as:11690424562",
    label: "Турецька · 25 ₺ обернулись на 1054 ₺",
    text: "25 türk lirası yazıyordu ama benden 1054,64 çekilmiş geri iade istiyorum. Türkçe dil desteği olmadığı için anlaşamıyoruz bir türlü.",
  },
  {
    id: "gp:933d17fa-9b3",
    label: "Португальська · магазин один, текст про інший",
    text: "Me roubaram 207 reais! Eu não utilizei nenhum serviço. Apenas cheguei no Nebula por curiosidade. Quero meu dinheiro de volta",
  },
  {
    id: "as:9410499825",
    label: "Французька · не вдається скасувати",
    text: "Une bonne appli cependant impossible d’annuler mon abonnement j’ai été prélevé 59€ c’est beaucoup trop . Je veux annuler",
  },
  {
    id: "gp:a85982ee-f2b",
    label: "Арабська · списання без підписки",
    text: "لقد تم سحب مبلغ من البطاقة لدي ولا اعرف لماذا لم اشترك الا مرة واحدة الرجاء إرجاع المبلغ كان المبلغ ٤٥ دينار أردني لا أعرف لماذا",
  },
  {
    id: "as:13564172721",
    label: "Корейська · просить повернення",
    text: "웹에서 결제해놓고 무조건 앱 다운로드해야 결과 볼 수 있고... 귀찮고 어디까지 가나 싶어서 깔아봤는데 결과 나오려면 10분 걸린다길래 각 보여서 그냥 지웁니다. 환불이나 해주든가. 결과도 내놓고 돈이나 받아먹든가.",
  },
  {
    id: "gp:5ad4f47a-8c6",
    label: "Тайська · автосписання без попередження",
    text: "ยังไม่ทราบว่าทำไมถึงมีการตัดเงินไปแบบอัตโนมัติ แบบไม่แจ้งล่วงหน้าทั้งที่ยังไม่สมัครใช้บริการอะไร เสียเวลาไปทำบัตรเดบิตใหม่อีกแล้ว",
  },
  {
    id: "gp:0d3c530a-79a",
    label: "Англійська · «безкоштовний» застосунок",
    text: "I cant see anything I want without paying and it was so called a free app I just wanna see the results like is it so hard to ask",
  },
]
