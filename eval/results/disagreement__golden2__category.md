# Model consensus against our labels: golden2, category

20 runs, 10 distinct models: anthropic/claude-haiku-4.5 (v8), anthropic/claude-sonnet-5 (v8), google/gemini-2.5-flash-lite (v8), google/gemini-3.1-flash-lite (v8), openai/gpt-4.1-mini (v8), openai/gpt-4.1-nano (v8), openai/gpt-4o-mini-2024-07-18 (v8), openai/gpt-5-mini (v8), openai/gpt-5-nano (v8), qwen/qwen3-max (v8)

## UNANIMOUS: 1 tickets

### gp:0cc6d44e-da3 - labelled `data_privacy`, models say `cancellation_failed` (20/20)
> i have canceled my subscription to this and am still being charged for it. my subscription ends in May. Delete my account with you. Thank you.
our secondary: ['cancellation_failed']
our rationale: An explicit request to delete the account, which the definition's NOT clause makes decisive: anger about data handling WITHOUT a deletion request goes elsewhere, and this one has the request. Priority 1 because the charges continue after a cancellation, stated in the text.
their reason (anthropic/claude-haiku-4.5): The writer states they cancelled but are still being charged, which is the core of cancellation_failed; they also request account deletion, but the blocking issue is the recurring charge that cancellation did not stop.

## MAJORITY: 11 tickets

### as:12481846751 - labelled `data_privacy`, models say `app_technical` (17/20)
votes: app_technical x17, content_quality x2, data_privacy x1
> The reason I give this 2 stars is because I believe just for an app it is asking very personal questions about me that I don’t believe I need to share. Nevertheless, I did it anyway. When I was trying to put my boyfriend’s birth date to the compatibility thing it wasn’t letting me but his month? If I put it as the right month the day would be wrong. The only thing that isn’t messing up would be the year he was born. I restarted the app 4 times thinking it was an error but I was wrong. I feel like if this actually worked I would leave a way better review because I’m not understanding what’s wrong, Thank you.
our secondary: ['app_technical']
our rationale: The stated reason for the two stars is that the app asks for personal information the writer does not believe it needs - a question about how data is handled, which the definition covers even without a deletion request. The date-picker fault is carried alongside. No money moves and nothing is blocke
their reason (anthropic/claude-haiku-4.5): The primary issue is a technical malfunction in the date input field for the compatibility feature; the data privacy concern about personal questions is secondary and does not block the app's function.

### as:13315148261 - labelled `pricing_unclear`, models say `trial_converted` (18/20)
votes: trial_converted x18, refund_request x2
> I selected a “🔥 3-day FREE TRIAL” deal that was shown as normally £5.99, but I was charged £48.99 for an annual plan within seconds — before the app even finished downloading. No warning, no genuine trial period, and no chance to cancel first. Apple and Nebula have both refused to refund me. The app also offers cheaper weekly and monthly options, so there’s no reason I’d ever have chosen the annual plan. This experience feels very misleading. Please be cautious before downloading.
our secondary: ['trial_converted', 'refund_request']
our rationale: A three-day free trial shown at 5.99 became a 48.99 annual charge within seconds, before the download finished, so nothing renewed - it was mis-presented. Apple and Nebula have both already refused.
their reason (anthropic/claude-haiku-4.5): A trial was presented and accepted but immediately converted to a paid annual subscription without warning or opportunity to cancel; both the store and support have already refused refund, triggering escalation.

### as:13540954035 - labelled `pricing_unclear`, models say `trial_converted` (15/20)
votes: trial_converted x15, unauthorized_charge x3, refund_request x2
> I would like to report an issue with the website "Ask Nebula." I accessed their service through an Facebook ad offering a quiz to discover my astrological card. The initial offer was to complete the quiz and pay $1 through Apple Pay, which I accepted. After paying the $1, I was directed to another page that advertised subscription services. I wanted to navigate away and simply view my quiz results without signing up for any subscription. However, without my permission and without the usual Face ID verification that Apple Pay normally requires, an $77.3 charge was processed through my Apple Pay account. I was not informed clearly that an $77.3 charge would be made, nor did I authorize it. The...
our secondary: ['trial_converted', 'refund_request']
our rationale: AUDIT 2026-09-21: was unauthorized_charge, which the rules reserve for 'a charge with no prior purchase at all' - an accepted $1 quiz charge is a prior purchase. The models say trial_converted and that is not right either: the writer's complaint is 'I was not informed clearly that an $77.3 charge wo
their reason (anthropic/claude-haiku-4.5): A $1 trial converted to a $77.3 charge without clear disclosure or authorization, support already refused a full refund, and the writer states money needed for essential purposes at a vulnerable time, triggering priority 1 and escalation.

### as:6986478942 - labelled `other`, models say `content_quality` (18/20)
votes: content_quality x18, other x1, data_privacy x1
> I cant get ur email but Prishtina is not a serbian city is a Kosova city please fix that other wise i will no be using ur app
our rationale: A factual correction to the app's city data with a political edge - Prishtina listed under Serbia. It is not the reading, chart or sign, so not content_quality; the application is not malfunctioning, so not app_technical; no money is involved. No knowledge base article covers it and the subject is s
their reason (anthropic/claude-haiku-4.5): The writer is reporting inaccurate content in the app's astrology or location data, not a billing or technical issue.

### as:6990946809 - labelled `content_quality`, models say `app_technical` (18/20)
votes: app_technical x18, content_quality x2
> Right so when I first downloaded the app it said I was a Leo which is correct, I’m born on the [BirthDate] and when I’m on the page it says that tabard correct but when I redownloaded the app it said I was cancer! This is ovs a glitch, can you get it sorted because I love your app and I would hate to not be able to use it
our secondary: ['app_technical']
our rationale: The rising sign changed from Leo to Cancer between two installs of the same app with the same birth data. The definition names a sign being wrong; the writer calls it a glitch, and the wording does not decide the category. No money, nothing blocked.
their reason (anthropic/claude-haiku-4.5): The app is displaying an incorrect zodiac sign after reinstall, a technical malfunction; the writer has not reported billing issues, charges, or service delivery failures, and no escalation triggers are present beyond the need for a technical fix.

### as:9923170783 - labelled `data_privacy`, models say `cancellation_failed` (16/20)
votes: cancellation_failed x16, data_privacy x4
> Horrible user account and data privacy management. GDPR problem I never received any of my credentials or confirmation of subscription for premium services/auto renewal of monthly subscription payment and cannot therefore access my account to cancel it! Basically, after I deleted the app, it deleted my account but not the attached payment ! Now when I login with my previously registered email address, it just made a new signup and no history of premium subscription! Never seen that with any app before, the app has to be taken down by App Store and Google.
our secondary: ['cancellation_failed']
our rationale: The ticket opens by naming data privacy management and GDPR, and the stated fact is that deleting the account left the payment attached and running with no way back in to stop it. Priority 1 because the charges are still repeating and the writer cannot reach the control. Contested with cancellation_
their reason (anthropic/claude-haiku-4.5): The user deleted the app expecting it to stop charges, but was billed anyway and cannot now access the account to cancel the subscription because login creates a new account with no history; this is a documented failure of the cancellation mechanism combined with ongoing charges and data handling co

### gp:bd3f0d61-144 - labelled `pricing_unclear`, models say `trial_converted` (12/20)
votes: trial_converted x12, pricing_unclear x5, cancellation_failed x2, refund_request x1
> تم خصم مبلغ 1 دولار مني، ثم تم خصم 14.99 دولار إضافية ولم يكن واضحًا لي عند الدفع أن هذا المبلغ الإضافي سيُخصم. كما واجهت صعوبة في إلغاء الاشتراك. تواصلت مع خدمة العملاء وطلبت استرداد مبلغ 14.99 دولار وإلغاء اشتراكي نهائيًا. بس الحلو فيهم انهم يجاوبون على الايميل بس بشوف يردون فلوسي الي خصمت من غير علمي أو لا!!
our secondary: ['refund_request', 'cancellation_failed']
our rationale: A further 14.99 followed the 1-dollar payment with no indication at checkout that it would be taken; support has been asked for that sum back and for a permanent cancellation, and the outcome is pending.
their reason (anthropic/claude-haiku-4.5): A $1 trial converted to a $14.99 charge without clear disclosure, combined with difficulty cancelling and support contact already made without resolution, requires human escalation.

### gp:c1030e67-355 - labelled `refund_request`, models say `unauthorized_charge` (16/20)
votes: unauthorized_charge x16, cancellation_failed x2, refund_request x2
> this app stole my money just for downloading. after being refused they sent the charge time after time at least 15 time until the caught my last $50 I need my money back they keep closing my case tho I provided what they asked for terrible
our secondary: ['unauthorized_charge']
our rationale: The case is reopened and closed again after the evidence support asked for was supplied, so the refund itself is the dispute. Priority 1 twice over on stated facts: the charge was retried about fifteen times, so it is still repeating, and 'my last $50' states a sum that cannot be afforded.
their reason (anthropic/claude-haiku-4.5): Recurring charges that have not stopped, a refund already refused by support, and a stated inability to afford the loss ($50 is the last money available) are all escalation triggers; the primary cause is unauthorized charges with no prior purchase.

### gp:cec7603a-31c - labelled `other`, models say `pricing_unclear` (14/20)
votes: pricing_unclear x14, content_quality x4, service_not_delivered x2
> I like all the added pieces and parts that are on here, but 3 minutes can you talk with a psychic when they charge you for the wait, is no way to find out any answers or if you like the psychic.
our secondary: ['pricing_unclear']
our rationale: The free three minutes are consumed by waiting for the psychic to respond. Not pricing_unclear: the writer does not say the terms were hidden, they say the offer as designed cannot work. No request is made and no charge is disputed.
their reason (anthropic/claude-haiku-4.5): The writer is complaining that the cost and terms of paid psychic consultations are not transparent before purchase—specifically, that a 3-minute session charges for wait time and offers no preview or satisfaction mechanism—which is a pricing and transparency issue rather than a billing error or fai

### gp:d16e1bc8-19b - labelled `trial_converted`, models say `cancellation_failed` (14/20)
votes: cancellation_failed x14, trial_converted x4, refund_request x2
> I wish I had read the reviews before installing the app,esp the negative feedback,which turns out to be true. Stated that it would send an email 24 hours to remind you of your trial. However I didnt get an email and next thing I know,my cc was charged for a monthly subscription and now Im frantically trying to find the cancel button, but they dont have it on their app 🙄 You would have to look for it in your google account,apparently.how very inconvenient. App wasnt very useful,I want a refund
our secondary: ['cancellation_failed', 'refund_request', 'pricing_unclear']
our rationale: The promised 24-hour trial reminder never arrived and the card was charged for a monthly plan; the writer names the Google account as where the subscription lives, so the rail is known.
their reason (anthropic/claude-haiku-4.5): The writer was charged after a trial without receiving the promised reminder email, then could not find the cancellation control in the app itself, making cancellation_failed the primary cause; the charge has already landed and the cancellation mechanism is blocked, requiring human intervention.

### gp:d8080fd8-fc2 - labelled `unauthorized_charge`, models say `cancellation_failed` (14/20)
votes: cancellation_failed x14, unauthorized_charge x3, service_not_delivered x2, data_privacy x1
> necesito que me desvinculen la cuenta porque jamás pude usar ese servicio pero ahora me llega un mensaje que no pudieron hacer el cobro de 148 mil pesos cuando eso jamás se usó me van a descontar por favor necesito que hagan la desvinculación ya que por ningún lado me sale ni por la play store ni por mi cuenta pésima app
our secondary: ['cancellation_failed']
our rationale: AUDIT 2026-09-21: was cancellation_failed. The subscription appears neither in the Play Store nor in the account and no starting payment is named, so there is nothing to cancel - the same conditional clause that sent gp:90556d05-623 the other way, because there a dollar WAS named and here none is.
their reason (anthropic/claude-haiku-4.5): The writer cannot find or complete cancellation through normal channels (Play Store, account settings) and reports a charge attempt on an account they never used, creating a dual problem: a failed cancellation mechanism and a disputed charge.

## SPLIT: 3 tickets

### as:13254291446 - labelled `refund_request`, models say `unauthorized_charge` (11/20)
votes: unauthorized_charge x11, refund_request x9
> About a week ago my 73 year old husband who has Alzheimer’s got hold of my phone and apparently paid for a subscription for this service! I was unaware until the charge showed up in my account. Unaware he’d done this at h we time I contacted nebula and pay pal as this was the way he paid. I asked nebula to cancel and please refund. Pay pal also opened an investigation that they closed same day when I explained I found out it was my husband that made the charge. Pay pal just said to contact nebula for refund. To say that this has been a huge ordeal with more than 60 emails exchanged!! Nebula continues to say that pay pal is investigating! I have sent nebula proof that pay pal has closed claim...
our secondary: ['unauthorized_charge']
our rationale: The purchase was made by a 73-year-old with Alzheimer's, PayPal closed its claim over a week ago, and the refund is still being withheld from someone on a fixed low income who cannot buy medication.
their reason (google/gemini-2.5-flash-lite): The user states her husband with Alzheimer's made an unauthorized charge, and she has been unable to get a refund despite multiple attempts and explanations of her financial vulnerability, indicating a need for human escalation.

### as:14000315965 - labelled `trial_converted`, models say `unauthorized_charge` (11/20)
votes: unauthorized_charge x11, trial_converted x9
> I purchased a sketch for €1 and have not used the application since. I did not agree to any future payments or subscriptions. However, €42.99 was charged to my card without my authorization by the Nebula application. I kindly request that this unauthorized charge be reviewed and that my money be refunded as soon as possible.
our secondary: ['refund_request', 'unauthorized_charge']
our rationale: 1 euro for a sketch, then 42.99 on the card with no further use of the app - the converted-trial pattern - and a refund is requested. No store is named.
their reason (google/gemini-2.5-flash-lite): The user states they did not agree to any future payments or subscriptions and that the charge was unauthorized, indicating an unauthorized charge. Since the purchase rail is not specified, the next step is to ask for it.

### gp:55cfe709-0af - labelled `trial_converted`, models say `refund_request` (11/20)
votes: refund_request x11, trial_converted x9
> hello, my credit card was automatically charged just now - I want a refund as I do not wish to use the app. can you please help me? I don't find the trial version of the app useful. Edit: I wrote to the email you asked me to, but so far no response has been received. please help.
our secondary: ['refund_request', 'cancellation_failed']
our rationale: AUDIT 2026-09-20: was refund_request. The card was charged automatically after a trial the writer did not find useful - that is the converted-trial pattern, and the refund is the demand, not the cause. Support has not answered the address they were sent to.
their reason (anthropic/claude-haiku-4.5): The writer demands a refund for a charge that just occurred and mentions a trial, suggesting trial_converted, but does not state where the purchase was made, so the purchase rail must be identified first.

15 of 82 tickets flagged on category: 1 unanimous, 11 majority, 3 split. A flag is a question, not a verdict - adjudicate against the label dictionary.
