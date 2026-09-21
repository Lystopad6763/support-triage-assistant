# Model consensus against our labels: dev, priority

12 runs, 2 distinct models: openai/gpt-4.1-mini (v8), openai/gpt-5-mini (s1-split-parallel), openai/gpt-5-mini (s1-split-staged), openai/gpt-5-mini (v8)

## UNANIMOUS: 0 tickets

## MAJORITY: 4 tickets

### as:14133480377 - labelled `3`, models say `2` (8/12)
votes: 2 x8, 3 x4
> トライアルから自動的にサブスク課金に移行されて引き落としされました。 サブスク解除はアプリ内でしかできないようです。 英語を訳しながらやっと解除できました。解除後はメールがきましたが、信用できなかったので、いろいろ調べたらPayPalでの自動決済のキャンセルをすれば引き落としされないようだったので、PayPalの方でも解除しました。 他に困っている方の参考になればと思います🙏
our rationale: The trial auto-converted and was debited, but the writer found the in-app cancellation by translating the English, then also stopped the PayPal auto-payment - the case is closed by their own hand and the post is advice for others.
their reason (openai/gpt-5-mini): User reports a trial automatically converted into a paid subscription and a charge occurred, which matches trial_converted. | The user reports a charge occurred when their trial automatically converted to a subscription (a billing event already landed), which makes this a priority 2 billing issue. |

### as:14161665940 - labelled `3`, models say `2` (9/12)
votes: 2 x9, 3 x2, 1 x1
> Achtung Abzocke! Bitte aufpassen, wenn man bei dieser unseriösen Firma etwas bezahlt! Es wird mit der ersten Zahlung ungewollt / ungefragt ein Abo mit einer Einzugsermächtigung eingerichtet! So kann die Firma mindestens einen Jahresbeitrag rechtssicher abbuchen. Achtet darauf, dass keine Verknüpfung mit eurer Zahlungsquelle ausgelöst wird!!!! Zudem ist die Art der „Dienstleistung“ mehr als fraglich, unseriös und maximal beliebig interpretierbar.
our rationale: A warning to other readers that the first payment silently sets up a subscription with a direct-debit mandate - a transparency complaint with no amount, no date and no request, so no money is moving.
their reason (openai/gpt-5-mini): The user states a subscription was set up without consent ('ungewollt / ungefragt'), indicating an unauthorized charge. | User reports an unwanted subscription and direct-debit authorization (money at stake/recurring charge risk) but does not state an active charge that cannot be stopped or a vulner

### as:14252277944 - labelled `2`, models say `1` (9/12)
votes: 1 x9, 2 x3
> 上面显示是三天免费试用，结果一下载就扣了363，退款也被拒绝了 ，I was misled by the interface into an accidental subscription, losing 363 RMB. Apple refused a refund, and your response was just "we'll look into it" with no real action. If you can collect the payment, why not refund it? Please stop the runaround and solve this issue.
our rationale: AUDIT 2026-09-21: was pricing_unclear, which requires that the terms were not visible - but the ticket says the three-day free trial WAS displayed, so that exclusion does not fit. Apple refused the refund and support answered 'we'll look into it' with no action: that is the second situation in which
their reason (openai/gpt-5-mini): User states a three-day free trial turned into an immediate 363 RMB charge, indicating a trial converted into a paid subscription. | A payment of 363 RMB was taken and Apple (a third party) has already refused a refund, indicating money has been lost and a third party is involved which requires urge

### gp:d4eafab3-834 - labelled `1`, models say `2` (11/12)
votes: 2 x11, 1 x1
> got charged twice in 3 days for $43 and $71 without my consent. absolutely unacceptable conduct. i expect a refund as thjs is a total violatiom of the original agreement.
our rationale: Two different amounts, $43 and $71, taken three days apart is not the renewal cycle of anything agreed to, and nothing indicates the billing has stopped.
their reason (openai/gpt-5-mini): The user states they were charged without their consent, indicating an unauthorized charge rather than a billing process error or trial conversion. | The user reports unauthorized charges (two specific amounts) and requests a refund, which is a billing issue where money is at stake but not ongoing l

## SPLIT: 2 tickets

### gp:764df98a-261 - labelled `3`, models say `1` (7/12)
votes: 1 x7, 2 x5
> DON'T HAVE A CANCELLATION OPTION! Do not subscribe. Out of curiosity I tried the e days free trial then I had no option to cancel. They set up a daily payment of £0.94. After all my attempts to cancel I contacted my bank and explained everything so they blocked the future payments and refund me for what already been paid meanwhile till I was trying to cancel.
our rationale: No cancellation option after the free trial and a daily GBP 0.94 debit, but the bank has already blocked future payments and refunded what was taken, so nothing is moving and nothing is asked of Nebula.
their reason (openai/gpt-5-mini): The user says they were unable to cancel the trial/subscription and were charged despite attempts to cancel, so the root cause is a failed cancellation. | The user states they involved their bank which blocked future payments and refunded charges, indicating third-party intervention for billing issu

### gp:c0c4abb2-9cc - labelled `2`, models say `1` (7/12)
votes: 1 x7, 2 x5
> ich habe da im Netz zu nichts zugestimmt und jetzt finde ich keinen Weg die App zu kündigen! ich möchte nicht, dass die für die App bei mir abbuchen!
our rationale: No charge has landed yet - the writer wants to stop a future debit and cannot find any way to cancel, so the cancellation route is the answer they are missing.
their reason (openai/gpt-5-mini): User reports they cannot find a way to cancel the app and want to prevent future charges, indicating a failure or inability to cancel. | User reports they cannot find a way to cancel and explicitly says they do not want charges to be taken, indicating an ongoing or imminent recurring charge they can

6 of 50 tickets flagged on priority: 0 unanimous, 4 majority, 2 split. A flag is a question, not a verdict - adjudicate against the label dictionary.
