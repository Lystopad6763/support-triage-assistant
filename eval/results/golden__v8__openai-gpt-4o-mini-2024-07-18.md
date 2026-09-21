# golden / prompt v8 / openai/gpt-4o-mini-2024-07-18

| metric | value |
|---|---|
| tickets | 50 |
| scored (returned valid output) | 50 |
| hard failures | 0 |
| category accuracy | **74%** |
| macro F1 over categories | **0.68** |
| macro F1 over classes with 3+ rows | **0.70** (4 classes) |
| priority accuracy | 78% |
| next_step accuracy | 46% |
| all three correct | 28% |
| secondary categories (Jaccard) | 48% |
| evidence verbatim | 92% |
| repaired after invalid JSON | 0 |
| confidence when right / wrong | 0.92 / 0.91 |
| cost | $0.01133 = $0.00023/ticket = $2.27/10k |

| escalation precision / recall | 90% / 67% (missed 9, spurious 2) |

## Per category

| category | in set | predicted | precision | recall | F1 |
|---|---|---|---|---|---|
| trial_converted | 21 | 21 | 76% | 76% | 0.76 |
| cancellation_failed | 12 | 11 | 91% | 83% | 0.87 |
| unauthorized_charge | 7 | 11 | 55% | 86% | 0.67 |
| pricing_unclear | 6 | 2 | 100% | 33% | 0.50 |
| app_technical | 1 (too few rows to read) | 1 | 100% | 100% | 1.00 |
| content_quality | 1 (too few rows to read) | 1 | 100% | 100% | 1.00 |
| refund_request | 1 (too few rows to read) | 1 | 0% | 0% | 0.00 |
| service_not_delivered | 1 (too few rows to read) | 2 | 50% | 100% | 0.67 |

## By slice

An average over 50 rows can sit at 80% while a whole language is wrong.

| cut | slice | n | category | all three |
|---|---|---|---|---|
| language | english | 35 | 66% | 26% |
| language | non-english latin | 9 | 100% | 44% |
| language | non-latin script | 6 | 83% | 17% |
| tone | aggressive | 10 | 60% | 20% |
| tone | plain | 40 | 78% | 30% |
| topics | multi-topic | 24 | 58% | 21% |
| topics | single topic | 26 | 88% | 35% |
| kb | kb has an answer | 42 | 74% | 26% |
| kb | not in the kb | 8 | 75% | 38% |

## Category errors

| expected | actual | n |
|---|---|---|
| pricing_unclear | trial_converted | 4 |
| trial_converted | unauthorized_charge | 3 |
| trial_converted | cancellation_failed | 1 |
| unauthorized_charge | service_not_delivered | 1 |
| trial_converted | refund_request | 1 |
| cancellation_failed | trial_converted | 1 |
| cancellation_failed | unauthorized_charge | 1 |
| refund_request | unauthorized_charge | 1 |

## Every ticket

| ticket | input (trimmed) | expected | actual | pass |
|---|---|---|---|---|
| as:14338757395 | 我在網路上看到一則廣告並下載了這個 App。 我本來不打算在 App 裡購買任何 300 點或類似的東西，但我無緣無故被扣了 45 美元，對此我感到非常不滿。 我已經取消訂閱了，但我不確定能否獲得退款。 我剛在週二晚上收 | trial_converted P2 ask_purchase_rail | trial_converted P2 process_refund | fail (CPs) |
| as:14273196771 | 1ドルで試してみるも広告と違って意味の無いものだったためにサブスク解約して退会した。カードの締め日前に詳細見たら勝手に課金されてる。すぐにサポートに返金求めるメールを英語と日本語で送信し、AIと思われるところから返信きた | cancellation_failed P1 escalate_to_human | cancellation_failed P1 escalate_to_human | PASS |
| gp:bf31982c-d4d | мне списали средства без моего согласия...я жду возврата иначе я буду действовать дальше пока не добьюсь справ | unauthorized_charge P2 escalate_to_human | unauthorized_charge P1 escalate_to_human | fail (CpS) |
| gp:bd3f0d61-144 | تم خصم مبلغ 1 دولار مني، ثم تم خصم 14.99 دولار إضافية ولم يكن واضحًا لي عند الدفع أن هذا المبلغ الإضافي سيُخصم | pricing_unclear P2 escalate_to_human | trial_converted P2 process_refund | fail (cPs) |
| gp:ef85c1c4-989 | Cero, muy bien las preguntas antes de pagar y descargar la app, ya que pagué me solicitó descargar la app y so | service_not_delivered P2 request_evidence | service_not_delivered P2 process_refund | fail (CPs) |
| gp:797c2e50-e37 | Eu fiz uma pequena compra, e agora estão me cobrando 133,60 sem eu ter feito nenhum tipo.de plano! Eu estou mu | trial_converted P1 ask_purchase_rail | trial_converted P2 guide_cancellation | fail (Cps) |
| gp:b186f161-98c | bonjour je viens de me rendre compte qu'on m'a prélevé 39 euros mais j'ai déjà désabonner je comprends pas pou | cancellation_failed P2 ask_purchase_rail | cancellation_failed P2 process_refund | fail (CPs) |
| as:14537367690 | Richiesto pagamento di 1€ e poi mi trovo 40€ in meno per un addebito successivo mai autorizzato, tra l’altro n | trial_converted P2 ask_purchase_rail | trial_converted P2 process_refund | fail (CPs) |
| as:13766345904 | Ich wollte diese App testen und habe daher 1€ bewusst dafür ausgegeben. Danach wurden mir jedoch noch 150€ abg | trial_converted P2 escalate_to_human | trial_converted P2 process_refund | fail (CPs) |
| gp:23f05069-025 | bir kaç gün önce işlem yaptım paramı ödedim daha sonrasında aboneliğimi iptal edip uygulamayı sildim ama bugün | cancellation_failed P1 escalate_to_human | cancellation_failed P1 escalate_to_human | PASS |
| gp:d8ae97b0-7a9 | I never approved any subscription charges for this app. I would like for this to end, I've tried once, now I'm | unauthorized_charge P2 ask_purchase_rail | unauthorized_charge P2 escalate_to_human | fail (CPs) |
| gp:d16e1bc8-19b | I wish I had read the reviews before installing the app,esp the negative feedback,which turns out to be true.  | trial_converted P2 process_refund | cancellation_failed P2 guide_cancellation | fail (cPs) |
| as:13385806227 | Please can you app creators just charge to download the app. Making the app free makes it seem like there is a | pricing_unclear P3 acknowledge_and_close | pricing_unclear P3 send_kb_article | fail (CPs) |
| gp:104349bb-267 | has a free trial, but when you register charges a subscription fee. also doesn't give you a reading and wants  | trial_converted P1 escalate_to_human | trial_converted P2 process_refund | fail (Cps) |
| gp:82f84670-2b9 | Me debitaron un dinero sin mi consentimiento. No hay manera de desuscribirme, ni de eliminar mis datos de tarj | unauthorized_charge P1 escalate_to_human | unauthorized_charge P1 escalate_to_human | PASS |
| as:13730278321 | Nebula recently debited $42.99 USD from my card. I did not authorise this purchase nor did I sign up for a sub | trial_converted P1 escalate_to_human | unauthorized_charge P1 escalate_to_human | fail (cPS) |
| as:13315148261 | I selected a “🔥 3-day FREE TRIAL” deal that was shown as normally £5.99, but I was charged £48.99 for an annua | pricing_unclear P2 escalate_to_human | trial_converted P2 process_refund | fail (cPs) |
| gp:89bdbbb4-ff3 | please stop withdrawing money from my account, why are you charging me for nothing I never received or had any | unauthorized_charge P1 escalate_to_human | unauthorized_charge P1 escalate_to_human | PASS |
| gp:afc80fcc-7be | très mauvaise expérience. j'ai payé 1€ pour avoir des renseignements le 21.12.25 que je n'ai jamais reçu. depu | cancellation_failed P1 escalate_to_human | cancellation_failed P1 escalate_to_human | PASS |
| gp:90556d05-623 | I took a quiz online then paid $1.00 for some info. I had to get the app so, I did. the info was not even wort | trial_converted P3 guide_cancellation | trial_converted P2 process_refund | fail (Cps) |
| as:14220433116 | 1. they will show u 1 dollar charge. after that without your concern will deduct 49 dollar 2. after contacting | trial_converted P2 escalate_to_human | trial_converted P2 process_refund | fail (CPs) |
| as:13597633287 | saw an ad online, just out of curiosity filled out my info and chose the $1 package to just read what i was in | trial_converted P2 process_refund | trial_converted P2 process_refund | PASS |
| as:13607579600 | I haven't used this app in a while and I tried going into the app. It would exit without loading. It just star | app_technical P3 send_kb_article | app_technical P2 escalate_to_human | fail (Cps) |
| as:14463152512 | Absolute scam! I was charged 20,000 VND for a reading service, but the app crashed right after payment and gav | unauthorized_charge P1 escalate_to_human | service_not_delivered P1 escalate_to_human | fail (cPS) |
| as:10775738782 | So basically I was signing in to use the app and it said my sun sign is Sagittarius that’s correct it said my  | content_quality P3 send_kb_article | content_quality P3 acknowledge_and_close | fail (CPs) |
| gp:55cfe709-0af | hello, my credit card was automatically charged just now - I want a refund as I do not wish to use the app. ca | trial_converted P2 escalate_to_human | refund_request P2 escalate_to_human | fail (cPS) |
| gp:bf7ca7c9-f1e | i downloaded the app but never had any consultation with anyone... i got debited even without using my 3mins f | trial_converted P2 ask_purchase_rail | trial_converted P2 process_refund | fail (CPs) |
| as:13540954035 | I would like to report an issue with the website "Ask Nebula." I accessed their service through an Facebook ad | pricing_unclear P1 escalate_to_human | trial_converted P1 escalate_to_human | fail (cPS) |
| gp:1fd14cb2-984 | Don't even try the free trial cuz it's a nightmare trying to figure out how to cancel it and it's not worth an | cancellation_failed P2 guide_cancellation | cancellation_failed P1 guide_cancellation | fail (CpS) |
| as:14369349630 | I saw an advertisement for NEBULA and decided to try the free trial. Immediately, my account was charged $1.00 | trial_converted P1 escalate_to_human | trial_converted P2 process_refund | fail (Cps) |
| as:14450344254 | 本來我只是出於好奇付一美元試用這個應用程式，怎料他們直接獲取了我的信用卡資料，在未經我授權的情況下私自不斷扣款。我前後被連續扣款了三個月，發現後隨即聯絡客服，他們回覆非常迅速並安排了退款。但這令人十分懷疑，這似乎是他們慣 | trial_converted P3 acknowledge_and_close | trial_converted P2 process_refund | fail (Cps) |
| as:14000315965 | I purchased a sketch for €1 and have not used the application since. I did not agree to any future payments or | trial_converted P2 ask_purchase_rail | unauthorized_charge P2 process_refund | fail (cPs) |
| as:14056071581 | I saw an ad on instagram and took the quiz and then payed £1 for the results which I didn’t even get, and with | trial_converted P1 escalate_to_human | trial_converted P1 escalate_to_human | PASS |
| gp:2835ec28-9d3 | hello, I cancelled and unsuscribed from your app even go as far as to delete the app... yet I am being charged | cancellation_failed P1 escalate_to_human | cancellation_failed P1 escalate_to_human | PASS |
| as:14550479655 | An unauthorized automatic charge was made to my account; I was charged $1 for an advertisement, and then, seve | trial_converted P2 ask_purchase_rail | unauthorized_charge P2 process_refund | fail (cPs) |
| gp:3e7e2275-b5e | I would put a zero if I could. It tricks you into subscribing with no clear way to unsubscribe from their serv | cancellation_failed P1 escalate_to_human | trial_converted P2 process_refund | fail (cps) |
| gp:e18e8473-db4 | I want to cancel now. I misunderstood the nature of the app. I can't find out how to cancel it. Get me out!! I | cancellation_failed P2 guide_cancellation | cancellation_failed P1 guide_cancellation | fail (CpS) |
| gp:1e7e13aa-1c9 | This app is a scam. I stopped using this app after paying $1 and asking for only 1 question, i also closed the | trial_converted P1 escalate_to_human | trial_converted P1 route_to_safety_report | fail (CPs) |
| gp:acae8516-ecf | why deducted from my debit card again without my consent?? it's SGD 63.50 ??? can you stop made payment?? this | cancellation_failed P1 escalate_to_human | unauthorized_charge P1 escalate_to_human | fail (cPS) |
| as:13277034138 | They will take $45 from you even after saying you canceled. I canceled the same day on the app and the webpage | cancellation_failed P1 escalate_to_human | cancellation_failed P1 escalate_to_human | PASS |
| gp:8e3810f3-e94 | I had paid just 1$ for the support 17/10/ 2025 and today on 30/10/2025 I was charged 43.99$ when I had not eve | trial_converted P2 ask_purchase_rail | trial_converted P2 process_refund | fail (CPs) |
| as:14322764387 | Hi, I was only trying to start the free trial to test the app, and I don’t know how I ended up being charged f | trial_converted P2 process_refund | trial_converted P2 process_refund | PASS |
| gp:a9836e23-588 | I have been charged £49.99 two months in a row as I cannot find anywhere how to cancel. It is no where to be f | cancellation_failed P1 escalate_to_human | cancellation_failed P1 guide_cancellation | fail (CPs) |
| as:14518204004 | 我是在看到「靈魂伴侶（Soulmate）」的廣告後開始使用這項服務。當時網頁引導我支付 US$1 取得結果，我原本以為自己只是購買這一次性的 US$1 服務。 但是幾天後，我的信用卡卻被 NEBULA_WEB ACCES | trial_converted P3 acknowledge_and_close | trial_converted P2 process_refund | fail (Cps) |
| as:13254291446 | About a week ago my 73 year old husband who has Alzheimer’s got hold of my phone and apparently paid for a sub | refund_request P1 escalate_to_human | unauthorized_charge P1 escalate_to_human | fail (cPS) |
| gp:eede1f7d-7fe | I'm upset with this app as I canceled my subscription and never use it and it keeps trying to charge me. I wan | cancellation_failed P1 escalate_to_human | cancellation_failed P1 escalate_to_human | PASS |
| gp:44d651fb-41a | Experiência horrível. App em inglês, cobraram 13,67 reais e depois convertido em dólares foi debitado quase 80 | pricing_unclear P2 ask_purchase_rail | trial_converted P2 process_refund | fail (cPs) |
| gp:267d293f-a16 | It seems good for all intents and purposes, however they try to upsell constantly. You have to pay extra for t | pricing_unclear P3 send_kb_article | pricing_unclear P3 send_kb_article | PASS |
| gp:d8080fd8-fc2 | necesito que me desvinculen la cuenta porque jamás pude usar ese servicio pero ahora me llega un mensaje que n | unauthorized_charge P1 escalate_to_human | unauthorized_charge P1 escalate_to_human | PASS |
| as:13611286141 | They are charging me every month and I do NOT have any active subscriptions nor have I used the app in MONTHS. | unauthorized_charge P1 escalate_to_human | unauthorized_charge P1 escalate_to_human | PASS |

Upper case = that field matched: C category, P priority, S next_step.
