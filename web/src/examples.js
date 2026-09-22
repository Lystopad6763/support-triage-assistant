// Real tickets from benchmark/tickets.csv, not written for the demo.
//
// Five, chosen to break in different places: a language the knowledge base is
// not written in, a cancellation whose correct answer depends on the store, a
// trial that converted, a delivery complaint mixed with a crash, and a pure
// technical fault with no money in it at all. A demo whose examples all work
// is a demo that has been arranged.
export const MAX_CHARS = 12000

export const EXAMPLES = [
  {
    label: 'Іспанська · списання без підписки',
    text: 'Necesito que me ayuden, la aplicación acaba de hacer un cobro a mi cuenta. Y yo no tengo ninguna suscripción, hice una compra hace unos días, pero suscripción no tengo.',
  },
  {
    label: 'Німецька · пастка з пробним',
    text: 'Dies ist ein Betrug. Ich habe lediglich 1 € bezahlt, dennoch wurden mir gestern 43 € von meiner Kreditkarte abgebucht. Ich fordere eine vollständige Rückerstattung. Ich habe die App unmittelbar nach der Zahlung von 1 € gelöscht.',
  },
  {
    label: 'Англійська · де скасувати',
    text: 'Where do I cancel? How can you can charge per minute if you are sending an offline message? Same rate as if they\'re online? Rip off? Not to mention the the expensive package',
  },
  {
    label: 'Португальська · не отримав послугу',
    text: 'Ele não entregou o serviço que eu paguei, quero o dinheiro de volta! O aplicativo trava o tempo todo, nao tem nenhum conteúdo relevante.',
  },
  {
    label: 'Англійська · застосунок не відкривається',
    text: 'I haven\'t used this app in a while and I tried going into the app. It would exit without loading. It just started doing this issue for me and it still won\'t load. Please help to fix this issue for me so I can use this app without it doing this same issue',
  },
]
