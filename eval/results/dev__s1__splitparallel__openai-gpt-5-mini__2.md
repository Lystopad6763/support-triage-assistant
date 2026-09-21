# dev / prompt s1-split-parallel / openai/gpt-5-mini

| metric | value |
|---|---|
| tickets | 50 |
| scored (returned valid output) | 50 |
| hard failures | 0 |
| category accuracy | **86%** |
| macro F1 over categories | **0.88** |
| macro precision / recall over categories | 0.95 / 0.87 |
| macro precision / recall over classes with 3+ rows | 0.92 / 0.79 |
| macro F1 over classes with 3+ rows | **0.80** (5 classes) |
| priority accuracy | 62% |
| next_step accuracy | 76% |
| all three correct | 42% |
| secondary categories (Jaccard) | 52% |
| evidence verbatim | 96% |
| repaired after invalid JSON | 0 |
| confidence when right / wrong | 0.78 / 0.81 |
| cost | $0.09609 = $0.00192/ticket = $19.22/10k |

| escalation precision / recall | 82% / 93% (missed 2, spurious 6) |

## Per category

| category | in set | predicted | precision | recall | F1 |
|---|---|---|---|---|---|
| cancellation_failed | 21 | 20 | 100% | 95% | 0.98 |
| trial_converted | 13 | 11 | 91% | 77% | 0.83 |
| unauthorized_charge | 6 | 9 | 67% | 100% | 0.80 |
| refund_request | 4 | 1 | 100% | 25% | 0.40 |
| service_not_delivered | 3 | 3 | 100% | 100% | 1.00 |
| app_technical | 1 (too few rows to read) | 1 | 100% | 100% | 1.00 |
| content_quality | 1 (too few rows to read) | 1 | 100% | 100% | 1.00 |
| other | 1 (too few rows to read) | 1 | 100% | 100% | 1.00 |
| pricing_unclear | 0 | 3 | 0% | 0% | 0.00 |

## By slice

An average over 50 rows can sit at 80% while a whole language is wrong.

| cut | slice | n | category | all three |
|---|---|---|---|---|
| language | english | 38 | 92% | 42% |
| language | non-english latin | 8 | 62% | 38% |
| language | non-latin script | 4 | 75% | 50% |
| tone | aggressive | 16 | 81% | 25% |
| tone | plain | 34 | 88% | 50% |
| topics | multi-topic | 21 | 95% | 33% |
| topics | single topic | 29 | 79% | 48% |
| kb | kb has an answer | 44 | 84% | 43% |
| kb | not in the kb | 6 | 100% | 33% |

## Category errors

| expected | actual | n |
|---|---|---|
| trial_converted | unauthorized_charge | 3 |
| refund_request | pricing_unclear | 2 |
| refund_request | trial_converted | 1 |
| cancellation_failed | pricing_unclear | 1 |

## Every ticket

| ticket | input (trimmed) | expected | actual | pass |
|---|---|---|---|---|
| as:14252277944 | 上面显示是三天免费试用，结果一下载就扣了363，退款也被拒绝了 ，I was misled by the interface into an accidental subscription, losing 363 RMB | refund_request P2 escalate_to_human | trial_converted P1 escalate_to_human | fail (cpS) |
| as:14133480377 | トライアルから自動的にサブスク課金に移行されて引き落としされました。 サブスク解除はアプリ内でしかできないようです。 英語を訳しながらやっと解除できました。解除後はメールがきましたが、信用できなかったので、いろいろ調べた | trial_converted P3 acknowledge_and_close | trial_converted P3 acknowledge_and_close | PASS |
| as:14312098923 | برنامج سيء يقوم بالخصم من حسابي ولم اطلب الاشتراك ،قمت بحذف البرنامج ومازال يخصم ،حاولت إلغاءه بكل الطرق ومازا | cancellation_failed P1 escalate_to_human | cancellation_failed P1 escalate_to_human | PASS |
| gp:d531010e-e31 | 1달러 결재하면 스케치된 그림을 메일로 보내주는줄 알고 결재했더니 앱다운시 29.99달러 가 같이 결재되었어. 스케치그림은 찾아볼수도 없고 메일을 여니 또 스케치를 위한 초기질문 루트만 나오네요.  | cancellation_failed P1 ask_purchase_rail | cancellation_failed P2 escalate_to_human | fail (Cps) |
| gp:fc04bcca-56d | lo resumiré...Son unos ladrones, te roban. Te dicen "Es gratis" para luego quitarte el dinero, son un asco. NO | refund_request P2 ask_purchase_rail | pricing_unclear P2 ask_purchase_rail | fail (cPS) |
| gp:f21ba9eb-0b2 | sou mais uma que caiu nesta propaganda enganosa...vendo a reposta deles aqui e n estao se importando este app  | refund_request P2 ask_purchase_rail | pricing_unclear P2 ask_purchase_rail | fail (cPS) |
| as:14011743614 | Surtout n essayez pas la période d essai ces voleurs vous débite alors même que vous vous êtes désabonnés! J a | cancellation_failed P2 escalate_to_human | cancellation_failed P2 escalate_to_human | PASS |
| gp:72e76b58-33a | Attenzione a questa app, si nasconde dietro un pagamento di 1€ un abbonamento, che nessuno ha autorizzato, dop | trial_converted P1 escalate_to_human | trial_converted P1 escalate_to_human | PASS |
| gp:1cf837ac-86a | Mir wurde andauernd Geld abgebucht. Hab jedoch nur das kostenlose Abo bestellt. Und sofort gekündigt als ich g | cancellation_failed P1 escalate_to_human | cancellation_failed P1 escalate_to_human | PASS |
| gp:8f7008e4-4ca | dolandırıcıdir Bir yerde reklamını görüp girdim 0.50 dolar karsilihinda ad soyad doğum tarihi gibi bilgileri g | unauthorized_charge P1 escalate_to_human | unauthorized_charge P2 escalate_to_human | fail (CpS) |
| gp:f509687c-69e | Not as described originally. Not for me and everything is an extra charge. I should have just paid the minimum | service_not_delivered P2 request_evidence | service_not_delivered P2 ask_purchase_rail | fail (CPs) |
| gp:1a5f3a36-2e5 | This app appears to be ok, however I only authorized a trial charge of 7.99 I've been charge 2x 35.99 in the p | cancellation_failed P1 escalate_to_human | cancellation_failed P2 escalate_to_human | fail (CpS) |
| gp:b04894fd-bff | This app is truly incredible. So far everythit that I have read has been spot on. I love that when I want to s | other P3 acknowledge_and_close | other P3 acknowledge_and_close | PASS |
| as:12136193056 | Cus honey they WILL scam you! I’m not stupid nor am I blind! They offered a three day free trial in which at t | trial_converted P1 escalate_to_human | trial_converted P2 escalate_to_human | fail (CpS) |
| as:11918006893 | Hello I would like this to be fixed since I didn’t buy anything from the app and I had to delete my account to | unauthorized_charge P1 escalate_to_human | unauthorized_charge P2 escalate_to_human | fail (CpS) |
| gp:14528ce0-b72 | Dear Nebula Support Team, I am requesting an immediate refund of the unexpected $29.99 charge made to my credi | trial_converted P2 ask_purchase_rail | trial_converted P2 ask_purchase_rail | PASS |
| gp:08385e3d-45b | i was charged for 14$ when i agreed for 1$ only as part of an advertisment. ​I believe this application uses d | trial_converted P2 ask_purchase_rail | trial_converted P2 escalate_to_human | fail (CPs) |
| gp:329c4dbd-da9 | I am finding it too hard for me to cancel my subscription. I'm 70 years old and not very good with technology. | cancellation_failed P1 escalate_to_human | cancellation_failed P1 escalate_to_human | PASS |
| gp:fa462cf6-83a | Paid $5 or whatever for palmistry. Which was ok..cool. But then I chose to buy 80 credits for the 9.99. Never  | service_not_delivered P2 escalate_to_human | service_not_delivered P2 escalate_to_human | PASS |
| gp:9ffcf41c-33c | on part of 1 of reading my star sign was correct the 2 pages star sign reading was INCORRECT star sign a joke  | content_quality P3 guide_cancellation | content_quality P3 guide_cancellation | PASS |
| gp:5dcf0661-216 | I was interested in palmistry for $1 as advertised on their some ad. The links they sent me in the email with  | trial_converted P1 escalate_to_human | trial_converted P2 escalate_to_human | fail (CpS) |
| as:12190236921 | Nebula auto renewed after deleting account. Check on IPhone if I was subscribed before deleting app to cancel  | cancellation_failed P1 escalate_to_human | cancellation_failed P2 escalate_to_human | fail (CpS) |
| as:7100042476 | I just updated the app and I’m quite disappointed. Not sure if they’re trying to force new users to upgrade to | app_technical P3 send_kb_article | app_technical P3 escalate_to_human | fail (CPs) |
| as:12339183335 | The app had a technical glitch and just to be on the safe side I checked my account. I messaged straightaway s | refund_request P3 acknowledge_and_close | refund_request P2 escalate_to_human | fail (Cps) |
| gp:1ab36f69-034 | It's a trap. It's impossible to cancel the subscription. The link on the website is broken, the app freezes wh | cancellation_failed P1 escalate_to_human | cancellation_failed P1 escalate_to_human | PASS |
| gp:fc7472ac-1c1 | This is the waste of time paying $1 for the trial for not getting a free skitch and it turned out to be a scam | service_not_delivered P2 guide_cancellation | service_not_delivered P2 ask_purchase_rail | fail (CPs) |
| as:13354574554 | I am writing a review as a charge of $65 AUD that was deducted from my account without my authorisation or con | trial_converted P2 ask_purchase_rail | trial_converted P2 ask_purchase_rail | PASS |
| gp:955a8abf-f27 | I haven't interacted with this app except to pay $1:00 for a one time 3mins reading after which I deleted the  | trial_converted P2 ask_purchase_rail | trial_converted P2 escalate_to_human | fail (CPs) |
| gp:11b675dc-7bc | Customer service is a joke. DO NOT spend the 1 dollar to try the app because when you go to cancel your subscr | cancellation_failed P2 escalate_to_human | cancellation_failed P2 escalate_to_human | PASS |
| as:14551516138 | I initially signed up for Nebula through an advertisement for approximately $1. However, I was later charged a | trial_converted P1 escalate_to_human | trial_converted P1 escalate_to_human | PASS |
| as:13613859375 | I got this app from Instagram i hadn't even downloaded it and it was just interesting to me at the time. Still | cancellation_failed P1 escalate_to_human | pricing_unclear P1 guide_cancellation | fail (cPs) |
| gp:d4eafab3-834 | got charged twice in 3 days for $43 and $71 without my consent. absolutely unacceptable conduct. i expect a re | unauthorized_charge P1 escalate_to_human | unauthorized_charge P2 ask_purchase_rail | fail (Cps) |
| gp:6b654831-ab0 | This apps is totally scam, charge my card for amount of USD. 20,99. I already check for many times that i don' | unauthorized_charge P1 escalate_to_human | unauthorized_charge P2 escalate_to_human | fail (CpS) |
| gp:d42a2c2c-c6d | They stole my money. I only paid $5 the first time, and it was fine, just to read some survey results they wer | trial_converted P1 escalate_to_human | unauthorized_charge P2 escalate_to_human | fail (cpS) |
| as:14492078493 | Hello, I would like to formally request a refund for the charges made to my bank account. I was charged withou | unauthorized_charge P1 escalate_to_human | unauthorized_charge P2 escalate_to_human | fail (CpS) |
| gp:5bcde7fc-cf4 | disgusting. No complete anything of what I originally signed up for. And I can't find how to cancel subscripti | cancellation_failed P2 guide_cancellation | cancellation_failed P2 guide_cancellation | PASS |
| gp:597f7476-722 | orbio.. Maybe reread this. I did cancel. One of your support people said it was canceled. And I wasn't charged | cancellation_failed P1 escalate_to_human | cancellation_failed P2 escalate_to_human | fail (CpS) |
| gp:ea35c182-8ba | Predetory 'Free Trial' no way to cancel! hunt ed thru this entire app and cannot find ANYWHERE to cancel, so b | cancellation_failed P1 guide_cancellation | cancellation_failed P1 ask_purchase_rail | fail (CPs) |
| gp:773442e1-d66 | Nebula, I made a one time purchase to see what my soulmate would look like and instead you guys are billing me | cancellation_failed P1 escalate_to_human | cancellation_failed P1 escalate_to_human | PASS |
| gp:1f2146f8-5fb | I want to cancel subscription not interested in the ocult not even for entertainment I can't cancel why is it  | cancellation_failed P2 guide_cancellation | cancellation_failed P2 guide_cancellation | PASS |
| gp:af7bdde4-21a | I actually wrote a very nice positive review. I was fair, detailed and sincere. I would not to take that back! | cancellation_failed P1 escalate_to_human | cancellation_failed P1 escalate_to_human | PASS |
| gp:76d080ff-04f | I followed their so called subscription cancellation instructions only to be charged $61.00 give me my money b | cancellation_failed P2 escalate_to_human | cancellation_failed P2 escalate_to_human | PASS |
| as:14543848514 | The app just paid my credit card 49.99 usd without authorization. I didnt register the auto credit. How did yo | unauthorized_charge P2 ask_purchase_rail | unauthorized_charge P2 ask_purchase_rail | PASS |
| gp:764df98a-261 | DON'T HAVE A CANCELLATION OPTION! Do not subscribe. Out of curiosity I tried the e days free trial then I had  | cancellation_failed P3 acknowledge_and_close | cancellation_failed P1 escalate_to_human | fail (Cps) |
| as:14304708630 | I was charged for something I didn’t subscribe to and when I wrote an email to get refunded, no one got back t | trial_converted P2 escalate_to_human | unauthorized_charge P2 escalate_to_human | fail (cPS) |
| gp:dcce2851-e69 | need a refund I never wanted to keep this app. I canceled it on the last day of trial and was still charged $5 | cancellation_failed P2 escalate_to_human | cancellation_failed P2 escalate_to_human | PASS |
| as:14161665940 | Achtung Abzocke! Bitte aufpassen, wenn man bei dieser unseriösen Firma etwas bezahlt! Es wird mit der ersten Z | trial_converted P3 send_kb_article | unauthorized_charge P1 acknowledge_and_close | fail (cps) |
| gp:c0c4abb2-9cc | ich habe da im Netz zu nichts zugestimmt und jetzt finde ich keinen Weg die App zu kündigen! ich möchte nicht, | cancellation_failed P2 guide_cancellation | cancellation_failed P1 guide_cancellation | fail (CpS) |
| gp:7983368e-950 | I would give zero stars if I could. Like so many others have said, it is nearly impossible to cancel!! It does | cancellation_failed P1 escalate_to_human | cancellation_failed P2 escalate_to_human | fail (CpS) |
| as:13635950628 | I bought a birth chart reading for USD 0.50 and have been charged twice for a monthly subscription despite inf | trial_converted P1 escalate_to_human | trial_converted P2 escalate_to_human | fail (CpS) |

Upper case = that field matched: C category, P priority, S next_step.
