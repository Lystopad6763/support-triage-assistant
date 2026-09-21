# Model consensus against our labels: golden2, next_step

20 runs, 10 distinct models: anthropic/claude-haiku-4.5 (v8), anthropic/claude-sonnet-5 (v8), google/gemini-2.5-flash-lite (v8), google/gemini-3.1-flash-lite (v8), openai/gpt-4.1-mini (v8), openai/gpt-4.1-nano (v8), openai/gpt-4o-mini-2024-07-18 (v8), openai/gpt-5-mini (v8), openai/gpt-5-nano (v8), qwen/qwen3-max (v8)

## UNANIMOUS: 0 tickets

## MAJORITY: 4 tickets

### as:13385806227 - labelled `acknowledge_and_close`, models say `send_kb_article` (12/20)
votes: send_kb_article x12, acknowledge_and_close x8
> Please can you app creators just charge to download the app. Making the app free makes it seem like there is a lite/free version upon download. As soon as you put in all your information you can’t continue without paying. Silly and kind of false advertisement.
our rationale: Product feedback addressed to the developers about a free download that cannot be used without paying; no charge is disputed and nothing is asked to be reversed.
their reason (google/gemini-2.5-flash-lite): The user was unclear about the pricing before proceeding with the app, which falls under pricing_unclear. The next step is to send a knowledge base article.

### gp:9b389617-7d9 - labelled `escalate_to_human`, models say `process_refund` (13/20)
votes: process_refund x13, ask_purchase_rail x4, escalate_to_human x2, request_evidence x1
> J'ai commandé une prediction sur 3 mois et la somme a été prélevée (37,99€) mais j'ai reçu un mail m'informant que ma commande a été annulée et que j'allais être remboursée... Je n'ai jamais reçu ni le remboursement ni ma prédiction, je suis très en colère, rendez-moi mon argent !!!
our rationale: A three-month prediction was paid for at 37.99 EUR; the order was cancelled by email with a refund promised, and neither the prediction nor the refund arrived. A promise made in writing and not kept is the documented route failing.
their reason (anthropic/claude-sonnet-5): The company already promised a refund by email but never delivered it, making the stuck refund itself the core issue, with one bounded charge at stake.

### gp:b186f161-98c - labelled `ask_purchase_rail`, models say `escalate_to_human` (12/20)
votes: escalate_to_human x12, process_refund x4, ask_purchase_rail x3, guide_cancellation x1
> bonjour je viens de me rendre compte qu'on m'a prélevé 39 euros mais j'ai déjà désabonner je comprends pas pourquoi ??? je veux de remboursement je regarde même pas
our rationale: Already unsubscribed and was still taken 39 euro; one charge to reverse and no store is named.
their reason (anthropic/claude-haiku-4.5): The writer cancelled the subscription but was charged anyway, which is the documented failure mode of cancellation_failed; the charge has already landed and the cancellation was already attempted, triggering escalation.

### gp:cec7603a-31c - labelled `acknowledge_and_close`, models say `send_kb_article` (16/20)
votes: send_kb_article x16, acknowledge_and_close x2, ask_purchase_rail x1, process_refund x1
> I like all the added pieces and parts that are on here, but 3 minutes can you talk with a psychic when they charge you for the wait, is no way to find out any answers or if you like the psychic.
our rationale: The free three minutes are consumed by waiting for the psychic to respond. Not pricing_unclear: the writer does not say the terms were hidden, they say the offer as designed cannot work. No request is made and no charge is disputed.
their reason (anthropic/claude-haiku-4.5): The writer is complaining that the cost and terms of paid psychic consultations are not transparent before purchase—specifically, that a 3-minute session charges for wait time and offers no preview or satisfaction mechanism—which is a pricing and transparency issue rather than a billing error or fai

## SPLIT: 5 tickets

### as:14322764387 - labelled `process_refund`, models say `escalate_to_human` (10/20)
votes: escalate_to_human x10, process_refund x7, route_to_apple x3
> Hi, I was only trying to start the free trial to test the app, and I don’t know how I ended up being charged for an annual subscription. I never intended to purchase the yearly plan. I don't need it. Could you please help me understand what happened and assist me with a refund? I contacted apple but the request was diclined as it went through third party. I would really appreciate your help. Thank you.
our rationale: A free trial ended as an annual plan that was never intended; Apple declined the request because it went through a third party, which names the rail Nebula can refund itself.
their reason (anthropic/claude-haiku-4.5): A free trial became a paid annual subscription without the user's intent, and Apple declined the refund citing a third-party processor, requiring human investigation of the conversion mechanism and refund eligibility.

### as:14369349630 - labelled `escalate_to_human`, models say `ask_purchase_rail` (9/20)
votes: ask_purchase_rail x9, process_refund x6, escalate_to_human x5
> I saw an advertisement for NEBULA and decided to try the free trial. Immediately, my account was charged $1.00 and $29.99 (equivalent to 26,328 VND and 789,577 VND) without any confirmation or authorization from me. Today, after 7 days, my account was automatically charged $49.99 (equivalent to 1,315,437 VND) without any prior notification or email. During those 7 days, I barely used any of your services. I believe this billing practice is misleading and feels like a scam. I request that you cancel this transaction immediately and issue a full refund for the amount charged.
our rationale: AUDIT 2026-09-21: was unauthorized_charge. The writer 'decided to try the free trial' and was auto-charged $49.99 seven days later - the canonical conversion, and R1 applies verbatim: a charge that followed a small starting payment is trial_converted even when the writer calls it a scam. Priority st
their reason (anthropic/claude-sonnet-5): A trial charge of $1 followed by automatic renewal charges of $29.99 and $49.99 without notice is a trial silently converting to a paid subscription, and the purchase platform is not stated.

### as:7123738621 - labelled `request_evidence`, models say `ask_purchase_rail` (11/20)
votes: ask_purchase_rail x11, process_refund x7, request_evidence x2
> This app is a fraud guys. I paid money for an astrologer consulting. They deducted the money but i never got any reply. Please refund my money you thieves
our rationale: Paid for an astrologer consultation and never got a reply - receiving nothing, not receiving something poor. The ticket names no date, no amount and no consultation, so the first action is to get enough to find the order.
their reason (anthropic/claude-sonnet-5): The user paid for a consultation that was never delivered, and wants a refund, but the ticket does not state where the purchase was made.

### as:7469353964 - labelled `send_kb_article`, models say `escalate_to_human` (11/20)
votes: escalate_to_human x11, send_kb_article x5, acknowledge_and_close x2, request_evidence x2
> I really love the app and the design. I also love how you can learn more about yourself and your signs. The only I problem is that when I try to go to a “astrologer” it glitches out. It keep saying “something went wrong, try again.” And I have to end up force closing the app because it get stuck there. Please fix this.
our rationale: Opening the astrologer screen produces 'something went wrong' and the app has to be force-closed. The application misbehaving, with no billing anywhere in the ticket.
their reason (anthropic/claude-haiku-4.5): The ticket describes a crash or hang when accessing the astrologer feature, which is an app technical issue. Priority 3 because no money is moving and nothing is blocked; escalate to human because the specific error state and device/OS context needed to reproduce the bug are not documented, and a te

### gp:d8ae97b0-7a9 - labelled `ask_purchase_rail`, models say `escalate_to_human` (11/20)
votes: escalate_to_human x11, guide_cancellation x4, ask_purchase_rail x3, route_to_safety_report x2
> I never approved any subscription charges for this app. I would like for this to end, I've tried once, now I'm pretty pissed. Cancel this!!
our rationale: Denies ever approving any subscription charge and has already tried once to stop it; no amount and no store are named, so the rail has to be established first.
their reason (anthropic/claude-haiku-4.5): The writer attempted cancellation but it failed, and charges are continuing; they have tried the documented route and it did not work, triggering escalation.

9 of 82 tickets flagged on next_step: 0 unanimous, 4 majority, 5 split. A flag is a question, not a verdict - adjudicate against the label dictionary.
