# Model consensus against our labels: golden2, priority

20 runs, 10 distinct models: anthropic/claude-haiku-4.5 (v8), anthropic/claude-sonnet-5 (v8), google/gemini-2.5-flash-lite (v8), google/gemini-3.1-flash-lite (v8), openai/gpt-4.1-mini (v8), openai/gpt-4.1-nano (v8), openai/gpt-4o-mini-2024-07-18 (v8), openai/gpt-5-mini (v8), openai/gpt-5-nano (v8), qwen/qwen3-max (v8)

## UNANIMOUS: 0 tickets

## MAJORITY: 6 tickets

### as:11791457752 - labelled `2`, models say `1` (14/20)
votes: 1 x14, 2 x6
> This app is a scam ,they cut took off money from my account without me even knowing . When I complained ,they said they will refund me ,and never refunded me . They keep on telling me that they refunded me ,but when I look at their receipt they sent the money to another account that’s not mine . When I keep on pointing out that they refunded to someone else account to mine ,they start acting dumb . They don’t wanna give my money back . 58 Australian $ was taken off my account and I never got to see it nor the half of it . A scam and scandal . I’ll make a campaign on TikTok and YouTube ,denouncing those practices from your company ,such a shame . The videos are coming . I don’t care about the...
our rationale: The refund was issued to an account that is not the writer's and support keeps asserting it was paid, so a human has to trace one payment. A TikTok campaign is a threat of publicity, not a bank, a regulator or a lawyer, so it is not the third-party trigger.
their reason (anthropic/claude-haiku-4.5): A refund was already requested and refused by support, with funds allegedly sent to the wrong account; this is a bounded charge but with documented support failure and escalation threat, requiring human intervention.

### as:13315148261 - labelled `2`, models say `1` (15/20)
votes: 1 x15, 2 x5
> I selected a “🔥 3-day FREE TRIAL” deal that was shown as normally £5.99, but I was charged £48.99 for an annual plan within seconds — before the app even finished downloading. No warning, no genuine trial period, and no chance to cancel first. Apple and Nebula have both refused to refund me. The app also offers cheaper weekly and monthly options, so there’s no reason I’d ever have chosen the annual plan. This experience feels very misleading. Please be cautious before downloading.
our rationale: A three-day free trial shown at 5.99 became a 48.99 annual charge within seconds, before the download finished, so nothing renewed - it was mis-presented. Apple and Nebula have both already refused.
their reason (anthropic/claude-haiku-4.5): A trial was presented and accepted but immediately converted to a paid annual subscription without warning or opportunity to cancel; both the store and support have already refused refund, triggering escalation.

### as:14369349630 - labelled `1`, models say `2` (17/20)
votes: 2 x17, 1 x3
> I saw an advertisement for NEBULA and decided to try the free trial. Immediately, my account was charged $1.00 and $29.99 (equivalent to 26,328 VND and 789,577 VND) without any confirmation or authorization from me. Today, after 7 days, my account was automatically charged $49.99 (equivalent to 1,315,437 VND) without any prior notification or email. During those 7 days, I barely used any of your services. I believe this billing practice is misleading and feels like a scam. I request that you cancel this transaction immediately and issue a full refund for the amount charged.
our rationale: AUDIT 2026-09-21: was unauthorized_charge. The writer 'decided to try the free trial' and was auto-charged $49.99 seven days later - the canonical conversion, and R1 applies verbatim: a charge that followed a small starting payment is trial_converted even when the writer calls it a scam. Priority st
their reason (anthropic/claude-haiku-4.5): A trial converted to paid subscription with multiple charges ($1, $29.99, then $49.99) and the charges are still recurring; the writer states no confirmation or authorization and no prior notification, indicating a transparency failure at trial entry and ongoing automatic billing that has not been s

### as:7839095010 - labelled `1`, models say `3` (12/20)
votes: 3 x12, 1 x6, 2 x2
> I absolutely loved this app untill you suspended my account for being “too young” i dont understand why this app has an age restriction, Its an astrology app, could you pelase get rid of it, i really want to use it but i cant because i was born in [BirthDate] and you need to be born in [BirthDate] to use it but i cant because if i change my birth year to that, then my readings wont be right. :(
our rationale: An account suspended over an age restriction, with the writer stating their own birth year. account_access is not a category, and nothing else fits. Priority 1 on a stated vulnerability: the writer says they are below the age limit, which is the one fact here that the priority rule names.
their reason (google/gemini-2.5-flash-lite): The user's account was suspended due to an age restriction, which they believe is arbitrary for an astrology app. They are requesting the removal of this restriction to continue using the app, indicating a potential issue with the app's age gating mechanism or data handling related to age.

### gp:797c2e50-e37 - labelled `1`, models say `2` (13/20)
votes: 2 x13, 1 x7
> Eu fiz uma pequena compra, e agora estão me cobrando 133,60 sem eu ter feito nenhum tipo.de plano! Eu estou muito chateada com essa situação, com essas cobranças indevidas, eu não fiz nenhum plano pra virem me cobrar todo mês. Quero cancelar isso!
our rationale: A small purchase turned into 133.60 billed monthly with no plan taken out; the charges recur and the writer asks for them to stop.
their reason (anthropic/claude-haiku-4.5): A writer made a small purchase and is now being charged a much larger amount (133.60) without agreeing to a subscription plan, indicating a trial or introductory offer that converted to a paid subscription; the charge has already occurred and the writer cannot complete cancellation, requiring human 

### gp:89206aed-567 - labelled `3`, models say `2` (15/20)
votes: 2 x15, 3 x5
> I was not impressed. Answers were very generic, I went on there hoping for some clarification.. that didn't happen. So if you want to waste ur money, go right ahead. I canceled my subscription and wish I could get my money back!!
our rationale: The complaint is that the answers were generic - a quality complaint, with no billing fault anywhere in it. The writer cancelled successfully, so no money is moving and nothing is blocked; the wish for a refund is a wish, not a charge to reverse.
their reason (google/gemini-2.5-flash-lite): The user is unhappy with the quality of the service received and is requesting a refund. They also state they canceled their subscription, implying a cancellation_failed secondary category.

## SPLIT: 0 tickets

6 of 82 tickets flagged on priority: 0 unanimous, 6 majority, 0 split. A flag is a question, not a verdict - adjudicate against the label dictionary.
