# Model consensus against our labels: golden, category

23 runs, 10 distinct models: anthropic/claude-haiku-4.5 (v8), anthropic/claude-sonnet-5 (v8), google/gemini-2.5-flash-lite (v8), google/gemini-3.1-flash-lite (v8), openai/gpt-4.1-mini (v8), openai/gpt-4.1-nano (v8), openai/gpt-4o-mini-2024-07-18 (v8), openai/gpt-5-mini (v8), openai/gpt-5-nano (v8), qwen/qwen3-max (v8)

## UNANIMOUS: 0 tickets

## MAJORITY: 6 tickets

### as:13315148261 - labelled `pricing_unclear`, models say `trial_converted` (18/21)
votes: trial_converted x18, refund_request x3
> I selected a “🔥 3-day FREE TRIAL” deal that was shown as normally £5.99, but I was charged £48.99 for an annual plan within seconds — before the app even finished downloading. No warning, no genuine trial period, and no chance to cancel first. Apple and Nebula have both refused to refund me. The app also offers cheaper weekly and monthly options, so there’s no reason I’d ever have chosen the annual plan. This experience feels very misleading. Please be cautious before downloading.
our secondary: ['trial_converted', 'refund_request']
our rationale: A three-day free trial shown at 5.99 became a 48.99 annual charge within seconds, before the download finished, so nothing renewed - it was mis-presented. Apple and Nebula have both already refused.
their reason (anthropic/claude-haiku-4.5): A trial offer converted to a paid annual subscription without adequate disclosure or opportunity to cancel, with both the store and support already refusing refund, triggering escalation.

### as:13540954035 - labelled `pricing_unclear`, models say `trial_converted` (18/21)
votes: trial_converted x18, refund_request x2, unauthorized_charge x1
> I would like to report an issue with the website "Ask Nebula." I accessed their service through an Facebook ad offering a quiz to discover my astrological card. The initial offer was to complete the quiz and pay $1 through Apple Pay, which I accepted. After paying the $1, I was directed to another page that advertised subscription services. I wanted to navigate away and simply view my quiz results without signing up for any subscription. However, without my permission and without the usual Face ID verification that Apple Pay normally requires, an $77.3 charge was processed through my Apple Pay account. I was not informed clearly that an $77.3 charge would be made, nor did I authorize it. The...
our secondary: ['trial_converted', 'refund_request']
our rationale: AUDIT 2026-09-21: was unauthorized_charge, which the rules reserve for 'a charge with no prior purchase at all' - an accepted $1 quiz charge is a prior purchase. The models say trial_converted and that is not right either: the writer's complaint is 'I was not informed clearly that an $77.3 charge wo
their reason (anthropic/claude-haiku-4.5): A $1 trial converted to a $77.3 charge without clear disclosure or authorization, support already refused a full refund offering only partial credits instead, and the writer names Consumer Affairs as the next step, triggering escalation.

### gp:55cfe709-0af - labelled `trial_converted`, models say `refund_request` (13/21)
votes: refund_request x13, trial_converted x8
> hello, my credit card was automatically charged just now - I want a refund as I do not wish to use the app. can you please help me? I don't find the trial version of the app useful. Edit: I wrote to the email you asked me to, but so far no response has been received. please help.
our secondary: ['refund_request', 'cancellation_failed']
our rationale: AUDIT 2026-09-20: was refund_request. The card was charged automatically after a trial the writer did not find useful - that is the converted-trial pattern, and the refund is the demand, not the cause. Support has not answered the address they were sent to.
their reason (anthropic/claude-haiku-4.5): The writer demands a refund for a charge that has landed, but does not state which store (Apple, Google Play, or website) processed the payment, so the purchase rail must be identified before the refund can be routed.

### gp:bd3f0d61-144 - labelled `pricing_unclear`, models say `trial_converted` (15/22)
votes: trial_converted x15, pricing_unclear x3, refund_request x2, cancellation_failed x2
> تم خصم مبلغ 1 دولار مني، ثم تم خصم 14.99 دولار إضافية ولم يكن واضحًا لي عند الدفع أن هذا المبلغ الإضافي سيُخصم. كما واجهت صعوبة في إلغاء الاشتراك. تواصلت مع خدمة العملاء وطلبت استرداد مبلغ 14.99 دولار وإلغاء اشتراكي نهائيًا. بس الحلو فيهم انهم يجاوبون على الايميل بس بشوف يردون فلوسي الي خصمت من غير علمي أو لا!!
our secondary: ['refund_request', 'cancellation_failed']
our rationale: A further 14.99 followed the 1-dollar payment with no indication at checkout that it would be taken; support has been asked for that sum back and for a permanent cancellation, and the outcome is pending.
their reason (anthropic/claude-haiku-4.5): A trial charge of $1 converted to a $14.99 subscription without clear disclosure, the user cannot cancel, support has been contacted but only responds via email without resolving the refund, and charges are ongoing—this meets escalation criteria.

### gp:d16e1bc8-19b - labelled `trial_converted`, models say `cancellation_failed` (13/21)
votes: cancellation_failed x13, trial_converted x6, refund_request x2
> I wish I had read the reviews before installing the app,esp the negative feedback,which turns out to be true. Stated that it would send an email 24 hours to remind you of your trial. However I didnt get an email and next thing I know,my cc was charged for a monthly subscription and now Im frantically trying to find the cancel button, but they dont have it on their app 🙄 You would have to look for it in your google account,apparently.how very inconvenient. App wasnt very useful,I want a refund
our secondary: ['cancellation_failed', 'refund_request', 'pricing_unclear']
our rationale: The promised 24-hour trial reminder never arrived and the card was charged for a monthly plan; the writer names the Google account as where the subscription lives, so the rail is known.
their reason (anthropic/claude-haiku-4.5): The writer received no trial reminder email, was charged after the trial, and cannot locate the cancellation control in the app itself—a documented failure of the cancellation mechanism combined with a trial-to-paid conversion, requiring human investigation of both the missing email and the app's ca

### gp:d8080fd8-fc2 - labelled `unauthorized_charge`, models say `cancellation_failed` (13/21)
votes: cancellation_failed x13, unauthorized_charge x8
> necesito que me desvinculen la cuenta porque jamás pude usar ese servicio pero ahora me llega un mensaje que no pudieron hacer el cobro de 148 mil pesos cuando eso jamás se usó me van a descontar por favor necesito que hagan la desvinculación ya que por ningún lado me sale ni por la play store ni por mi cuenta pésima app
our secondary: ['cancellation_failed']
our rationale: AUDIT 2026-09-21: was cancellation_failed. The subscription appears neither in the Play Store nor in the account and no starting payment is named, so there is nothing to cancel - the same conditional clause that sent gp:90556d05-623 the other way, because there a dollar WAS named and here none is.
their reason (anthropic/claude-haiku-4.5): The writer cannot find or complete cancellation through normal channels (Play Store, account settings) and reports a charge attempt for a service never used, with the account now inaccessible for self-service cancellation.

## SPLIT: 4 tickets

### as:13254291446 - labelled `refund_request`, models say `unauthorized_charge` (12/21)
votes: unauthorized_charge x12, refund_request x9
> About a week ago my 73 year old husband who has Alzheimer’s got hold of my phone and apparently paid for a subscription for this service! I was unaware until the charge showed up in my account. Unaware he’d done this at h we time I contacted nebula and pay pal as this was the way he paid. I asked nebula to cancel and please refund. Pay pal also opened an investigation that they closed same day when I explained I found out it was my husband that made the charge. Pay pal just said to contact nebula for refund. To say that this has been a huge ordeal with more than 60 emails exchanged!! Nebula continues to say that pay pal is investigating! I have sent nebula proof that pay pal has closed claim...
our secondary: ['unauthorized_charge']
our rationale: The purchase was made by a 73-year-old with Alzheimer's, PayPal closed its claim over a week ago, and the refund is still being withheld from someone on a fixed low income who cannot buy medication.
their reason (google/gemini-2.5-flash-lite): The user states her husband with Alzheimer's made the charge, and she has been unable to get a refund from Nebula despite PayPal closing their investigation. The user also mentions being on a fixed low income and needing money for medication, which elevates the priority to 1.

### as:14000315965 - labelled `trial_converted`, models say `unauthorized_charge` (12/21)
votes: unauthorized_charge x12, trial_converted x9
> I purchased a sketch for €1 and have not used the application since. I did not agree to any future payments or subscriptions. However, €42.99 was charged to my card without my authorization by the Nebula application. I kindly request that this unauthorized charge be reviewed and that my money be refunded as soon as possible.
our secondary: ['refund_request', 'unauthorized_charge']
our rationale: 1 euro for a sketch, then 42.99 on the card with no further use of the app - the converted-trial pattern - and a refund is requested. No store is named.
their reason (google/gemini-2.5-flash-lite): The user states that a charge of €42.99 was made without their authorization, fitting the unauthorized_charge category. The priority is 2 as it is a single charge to reverse.

### as:14463152512 - labelled `unauthorized_charge`, models say `service_not_delivered` (12/21)
votes: service_not_delivered x12, unauthorized_charge x6, refund_request x2, cancellation_failed x1
> Absolute scam! I was charged 20,000 VND for a reading service, but the app crashed right after payment and gave me ZERO results or content. On top of that, it automatically deducted an extra 425,000 VND from my Visa card without my consent. Their support form on the website doesn't work and crashes intentionally. I demand an immediate full refund and subscription cancellation!
our secondary: ['service_not_delivered', 'refund_request', 'app_technical']
our rationale: An extra 425,000 VND taken without consent is not a renewal of the 20,000 paid for a reading, which the crash never delivered; a refund and cancellation are demanded today.
their reason (anthropic/claude-haiku-4.5): The primary issue is a paid reading service that never arrived due to an app crash; the secondary unauthorized charge and non-functional support form create compounding failures that require human investigation to establish what was actually charged and why.

### gp:44d651fb-41a - labelled `pricing_unclear`, models say `trial_converted` (7/21)
votes: trial_converted x7, unauthorized_charge x6, pricing_unclear x4, refund_request x4
> Experiência horrível. App em inglês, cobraram 13,67 reais e depois convertido em dólares foi debitado quase 80 conto do meu cartão. Absurdo, quero estorno. Golpe! Não façam isso!
our secondary: ['refund_request', 'unauthorized_charge']
our rationale: Charged 13.67 reais and then nearly 80 after a conversion into dollars, which is not the amount that was presented; a refund is demanded.
their reason (google/gemini-3.1-flash-lite): The user describes a small initial charge followed by a larger subscription charge, which characterizes a trial conversion, and they are requesting a refund.

10 of 50 tickets flagged on category: 0 unanimous, 6 majority, 4 split. A flag is a question, not a verdict - adjudicate against the label dictionary.
