# Model consensus against our labels: golden, next_step

23 runs, 10 distinct models: anthropic/claude-haiku-4.5 (v8), anthropic/claude-sonnet-5 (v8), google/gemini-2.5-flash-lite (v8), google/gemini-3.1-flash-lite (v8), openai/gpt-4.1-mini (v8), openai/gpt-4.1-nano (v8), openai/gpt-4o-mini-2024-07-18 (v8), openai/gpt-5-mini (v8), openai/gpt-5-nano (v8), qwen/qwen3-max (v8)

## UNANIMOUS: 0 tickets

## MAJORITY: 2 tickets

### as:13385806227 - labelled `acknowledge_and_close`, models say `send_kb_article` (17/21)
votes: send_kb_article x17, acknowledge_and_close x4
> Please can you app creators just charge to download the app. Making the app free makes it seem like there is a lite/free version upon download. As soon as you put in all your information you can’t continue without paying. Silly and kind of false advertisement.
our rationale: Product feedback addressed to the developers about a free download that cannot be used without paying; no charge is disputed and nothing is asked to be reversed.
their reason (google/gemini-2.5-flash-lite): The user states the cost was not clear before they entered their information and proceeded to payment, which is a pricing transparency issue.

### gp:d8ae97b0-7a9 - labelled `ask_purchase_rail`, models say `escalate_to_human` (14/21)
votes: escalate_to_human x14, ask_purchase_rail x3, route_to_safety_report x2, guide_cancellation x2
> I never approved any subscription charges for this app. I would like for this to end, I've tried once, now I'm pretty pissed. Cancel this!!
our rationale: Denies ever approving any subscription charge and has already tried once to stop it; no amount and no store are named, so the rail has to be established first.
their reason (anthropic/claude-haiku-4.5): The writer states they tried to cancel once and it failed; they are now demanding cancellation again, which is a cancellation_failed case requiring human intervention since the documented route was already attempted.

## SPLIT: 9 tickets

### as:10775738782 - labelled `send_kb_article`, models say `acknowledge_and_close` (9/21)
votes: acknowledge_and_close x9, send_kb_article x8, escalate_to_human x4
> So basically I was signing in to use the app and it said my sun sign is Sagittarius that’s correct it said my rising sign was cancer correct but then it said my moon sign was cancer too that’s incorrect im a Gemini moon and I am for sure of it in the reviews everyone talks about how accurate this app is but honestly I’m not so sure because it got my zodiac chart wrong can you please fix this glitch that you have in the game ?
our rationale: The moon sign in the generated chart is wrong while the sun and rising are right, and the writer asks for the calculation to be fixed. No money is involved.
their reason (anthropic/claude-haiku-4.5): The writer received a reading with content they believe is inaccurate; no money is at stake, nothing was blocked, and no service failed to arrive.

### as:14000315965 - labelled `ask_purchase_rail`, models say `process_refund` (10/21)
votes: process_refund x10, ask_purchase_rail x7, escalate_to_human x2, request_evidence x2
> I purchased a sketch for €1 and have not used the application since. I did not agree to any future payments or subscriptions. However, €42.99 was charged to my card without my authorization by the Nebula application. I kindly request that this unauthorized charge be reviewed and that my money be refunded as soon as possible.
our rationale: 1 euro for a sketch, then 42.99 on the card with no further use of the app - the converted-trial pattern - and a refund is requested. No store is named.
their reason (openai/gpt-4.1-nano): The user states that the charge was unauthorized and they did not agree to any future payments.

### as:14322764387 - labelled `process_refund`, models say `escalate_to_human` (9/21)
votes: escalate_to_human x9, process_refund x9, route_to_apple x3
> Hi, I was only trying to start the free trial to test the app, and I don’t know how I ended up being charged for an annual subscription. I never intended to purchase the yearly plan. I don't need it. Could you please help me understand what happened and assist me with a refund? I contacted apple but the request was diclined as it went through third party. I would really appreciate your help. Thank you.
our rationale: A free trial ended as an annual plan that was never intended; Apple declined the request because it went through a third party, which names the rail Nebula can refund itself.
their reason (anthropic/claude-haiku-4.5): A free trial became a paid annual subscription without the user's intent, and Apple declined the refund citing a third-party processor, requiring human investigation of the conversion mechanism and refund eligibility.

### as:14369349630 - labelled `escalate_to_human`, models say `process_refund` (10/21)
votes: process_refund x10, escalate_to_human x6, ask_purchase_rail x5
> I saw an advertisement for NEBULA and decided to try the free trial. Immediately, my account was charged $1.00 and $29.99 (equivalent to 26,328 VND and 789,577 VND) without any confirmation or authorization from me. Today, after 7 days, my account was automatically charged $49.99 (equivalent to 1,315,437 VND) without any prior notification or email. During those 7 days, I barely used any of your services. I believe this billing practice is misleading and feels like a scam. I request that you cancel this transaction immediately and issue a full refund for the amount charged.
our rationale: AUDIT 2026-09-21: was unauthorized_charge. The writer 'decided to try the free trial' and was auto-charged $49.99 seven days later - the canonical conversion, and R1 applies verbatim: a charge that followed a small starting payment is trial_converted even when the writer calls it a scam. Priority st
their reason (openai/gpt-4.1-nano): The user requests a refund for charges made without prior notification or authorization, which is a billing issue.

### gp:797c2e50-e37 - labelled `ask_purchase_rail`, models say `guide_cancellation` (9/21)
votes: guide_cancellation x9, ask_purchase_rail x6, escalate_to_human x5, process_refund x1
> Eu fiz uma pequena compra, e agora estão me cobrando 133,60 sem eu ter feito nenhum tipo.de plano! Eu estou muito chateada com essa situação, com essas cobranças indevidas, eu não fiz nenhum plano pra virem me cobrar todo mês. Quero cancelar isso!
our rationale: A small purchase turned into 133.60 billed monthly with no plan taken out; the charges recur and the writer asks for them to stop.
their reason (google/gemini-2.5-flash-lite): The user states they made a small purchase and are now being charged a larger monthly fee without signing up for a plan, which indicates a trial period converted to a subscription. They also want to cancel.

### gp:90556d05-623 - labelled `guide_cancellation`, models say `process_refund` (10/21)
votes: process_refund x10, guide_cancellation x5, ask_purchase_rail x5, escalate_to_human x1
> I took a quiz online then paid $1.00 for some info. I had to get the app so, I did. the info was not even worth a dollar. generic...like a fortune cookie. I never made an account so, how can I be sure I won't be charged again? I didn't agree to a subscription. there's no subscription listed in my Google play account. I sent a request to cancel through the website too. for how bad it was and since I'm requesting this within 10 minutes of paying...I hope I don't get scammed!
our rationale: AUDIT 2026-09-21: was cancellation_failed, which the rules make conditional - 'all of that assumes there IS a subscription the writer knows about. Someone who ... has no subscription in the store has nothing to cancel: that is unauthorized_charge, or trial_converted if a small starting payment is na
their reason (anthropic/claude-haiku-4.5): A small introductory payment ($1.00) for a quiz result converted to a paid subscription model; the writer paid and received content but now fears recurring charges and wants the charge reversed.

### gp:b186f161-98c - labelled `ask_purchase_rail`, models say `escalate_to_human` (11/21)
votes: escalate_to_human x11, process_refund x7, ask_purchase_rail x3
> bonjour je viens de me rendre compte qu'on m'a prélevé 39 euros mais j'ai déjà désabonner je comprends pas pourquoi ??? je veux de remboursement je regarde même pas
our rationale: Already unsubscribed and was still taken 39 euro; one charge to reverse and no store is named.
their reason (anthropic/claude-haiku-4.5): The writer cancelled the subscription but was charged anyway, which is the documented trigger for escalation to a human; the charge is bounded and already taken, making this priority 2.

### gp:bd3f0d61-144 - labelled `escalate_to_human`, models say `process_refund` (8/22)
votes: process_refund x8, ask_purchase_rail x7, escalate_to_human x6, send_kb_article x1
> تم خصم مبلغ 1 دولار مني، ثم تم خصم 14.99 دولار إضافية ولم يكن واضحًا لي عند الدفع أن هذا المبلغ الإضافي سيُخصم. كما واجهت صعوبة في إلغاء الاشتراك. تواصلت مع خدمة العملاء وطلبت استرداد مبلغ 14.99 دولار وإلغاء اشتراكي نهائيًا. بس الحلو فيهم انهم يجاوبون على الايميل بس بشوف يردون فلوسي الي خصمت من غير علمي أو لا!!
our rationale: A further 14.99 followed the 1-dollar payment with no indication at checkout that it would be taken; support has been asked for that sum back and for a permanent cancellation, and the outcome is pending.
their reason (openai/gpt-4.1-nano): The user requests a refund for the additional charge and cancellation, indicating a billing issue.

### gp:ef85c1c4-989 - labelled `request_evidence`, models say `ask_purchase_rail` (11/22)
votes: ask_purchase_rail x11, process_refund x9, escalate_to_human x2
> Cero, muy bien las preguntas antes de pagar y descargar la app, ya que pagué me solicitó descargar la app y sorpresa! no funciona sólo aparece el logo muy bonito y no pasa nada, al querer descargar los resultados del test me manda a la app que no funciona!!! exijo un reembolso, por qué pagar por algo que no recibí 😡😡😡😡😡😡😡😡😡😡😡😡😡😡😡😡😡
our rationale: Paid, then the app showed only a logo and never loaded, so the test results were never delivered; the demand is a refund for something not received.
their reason (anthropic/claude-sonnet-5): The core problem is that the app fails to load or function after payment, blocking access to the purchased test results, which is a technical malfunction rather than simple non-delivery or a billing dispute.

11 of 50 tickets flagged on next_step: 0 unanimous, 2 majority, 9 split. A flag is a question, not a verdict - adjudicate against the label dictionary.
