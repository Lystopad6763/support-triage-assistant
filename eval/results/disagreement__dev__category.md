# Model consensus against our labels: dev, category

12 runs, 2 distinct models: openai/gpt-4.1-mini (v8), openai/gpt-5-mini (s1-split-parallel), openai/gpt-5-mini (s1-split-staged), openai/gpt-5-mini (v8)

## UNANIMOUS: 1 tickets

### as:14252277944 - labelled `refund_request`, models say `trial_converted` (12/12)
> 上面显示是三天免费试用，结果一下载就扣了363，退款也被拒绝了 ，I was misled by the interface into an accidental subscription, losing 363 RMB. Apple refused a refund, and your response was just "we'll look into it" with no real action. If you can collect the payment, why not refund it? Please stop the runaround and solve this issue.
our secondary: ['trial_converted']
our rationale: AUDIT 2026-09-21: was pricing_unclear, which requires that the terms were not visible - but the ticket says the three-day free trial WAS displayed, so that exclusion does not fit. Apple refused the refund and support answered 'we'll look into it' with no action: that is the second situation in which
their reason (openai/gpt-5-mini): User says a 3-day free trial was shown but was immediately charged 363 RMB after download, indicating a trial converted into a paid subscription. | A payment of 363 RMB was charged and the user states Apple refused a refund, so money is at stake and a third party has been involved, requiring prompt 

## MAJORITY: 3 tickets

### as:14161665940 - labelled `pricing_unclear`, models say `unauthorized_charge` (8/12)
votes: unauthorized_charge x8, trial_converted x3, pricing_unclear x1
> Achtung Abzocke! Bitte aufpassen, wenn man bei dieser unseriösen Firma etwas bezahlt! Es wird mit der ersten Zahlung ungewollt / ungefragt ein Abo mit einer Einzugsermächtigung eingerichtet! So kann die Firma mindestens einen Jahresbeitrag rechtssicher abbuchen. Achtet darauf, dass keine Verknüpfung mit eurer Zahlungsquelle ausgelöst wird!!!! Zudem ist die Art der „Dienstleistung“ mehr als fraglich, unseriös und maximal beliebig interpretierbar.
our secondary: ['trial_converted', 'content_quality']
our rationale: A warning to other readers that the first payment silently sets up a subscription with a direct-debit mandate - a transparency complaint with no amount, no date and no request, so no money is moving.
their reason (openai/gpt-5-mini): The user states a subscription was set up without consent ('ungewollt / ungefragt'), indicating an unauthorized charge. | User reports an unwanted subscription and direct-debit authorization (money at stake/recurring charge risk) but does not state an active charge that cannot be stopped or a vulner

### as:14304708630 - labelled `trial_converted`, models say `unauthorized_charge` (11/12)
votes: unauthorized_charge x11, trial_converted x1
> I was charged for something I didn’t subscribe to and when I wrote an email to get refunded, no one got back to me. I only requested and paid for the sketch. I looked up on FAQs that will I be charged monthly for only requesting a sketch and the answer I got was that I’m not automatically subscribed to anything but I was charged for the subscription. I would like my refund as soon as possible.
our secondary: ['unauthorized_charge', 'refund_request']
our rationale: Paid only for a one-off sketch and was then billed a subscription - the same small-purchase-then-subscription sequence the calibration treats as a converted trial - and the emailed refund request went unanswered.
their reason (openai/gpt-5-mini): The user says they were charged for a subscription they did not subscribe to, indicating an unauthorized charge, and they also request a refund. | The user reports an unauthorized charge and a refund request that has gone unanswered (money is at stake but not described as ongoing/recurring), so this

### gp:fc7472ac-1c1 - labelled `cancellation_failed`, models say `trial_converted` (10/12)
votes: trial_converted x10, service_not_delivered x2
> This is the waste of time paying $1 for the trial for not getting a free skitch and it turned out to be a scam. I am not paying $50 for the subscription. I need to cancel and get my $1 back. Why waste the money while you get charged and have a psychic read your astrology.
our secondary: ['refund_request', 'service_not_delivered']
our rationale: The $50 has not been taken yet and the writer's request is to cancel before it lands plus get the $1 back, so the cancellation route is the action.
their reason (openai/gpt-5-mini): User describes a $1 trial payment and subsequent unwanted subscription outcome and asks for cancellation/refund, indicating a trial converted into a paid subscription. | User reports a charge has been made and requests cancellation and refund, which is a billing issue needing timely response but not

## SPLIT: 0 tickets

4 of 50 tickets flagged on category: 1 unanimous, 3 majority, 0 split. A flag is a question, not a verdict - adjudicate against the label dictionary.
