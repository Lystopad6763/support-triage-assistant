# Model consensus against our labels: golden, priority

23 runs, 10 distinct models: anthropic/claude-haiku-4.5 (v8), anthropic/claude-sonnet-5 (v8), google/gemini-2.5-flash-lite (v8), google/gemini-3.1-flash-lite (v8), openai/gpt-4.1-mini (v8), openai/gpt-4.1-nano (v8), openai/gpt-4o-mini-2024-07-18 (v8), openai/gpt-5-mini (v8), openai/gpt-5-nano (v8), qwen/qwen3-max (v8)

## UNANIMOUS: 0 tickets

## MAJORITY: 2 tickets

### as:14369349630 - labelled `1`, models say `2` (17/21)
votes: 2 x17, 1 x4
> I saw an advertisement for NEBULA and decided to try the free trial. Immediately, my account was charged $1.00 and $29.99 (equivalent to 26,328 VND and 789,577 VND) without any confirmation or authorization from me. Today, after 7 days, my account was automatically charged $49.99 (equivalent to 1,315,437 VND) without any prior notification or email. During those 7 days, I barely used any of your services. I believe this billing practice is misleading and feels like a scam. I request that you cancel this transaction immediately and issue a full refund for the amount charged.
our rationale: AUDIT 2026-09-21: was unauthorized_charge. The writer 'decided to try the free trial' and was auto-charged $49.99 seven days later - the canonical conversion, and R1 applies verbatim: a charge that followed a small starting payment is trial_converted even when the writer calls it a scam. Priority st
their reason (anthropic/claude-haiku-4.5): A small trial charge ($1.00) converted to paid subscriptions ($29.99 then $49.99) without the user's awareness, and the charges are still recurring; this requires human review to verify the trial terms and stop ongoing charges.

### gp:797c2e50-e37 - labelled `1`, models say `2` (16/21)
votes: 2 x16, 1 x5
> Eu fiz uma pequena compra, e agora estão me cobrando 133,60 sem eu ter feito nenhum tipo.de plano! Eu estou muito chateada com essa situação, com essas cobranças indevidas, eu não fiz nenhum plano pra virem me cobrar todo mês. Quero cancelar isso!
our rationale: A small purchase turned into 133.60 billed monthly with no plan taken out; the charges recur and the writer asks for them to stop.
their reason (anthropic/claude-haiku-4.5): A writer made a small purchase and is now being charged a much larger amount (133.60) without agreeing to a subscription plan, indicating a trial or introductory offer that converted to a paid subscription; the writer cannot complete cancellation and support escalation is needed to stop recurring ch

## SPLIT: 7 tickets

### as:13315148261 - labelled `2`, models say `1` (11/21)
votes: 1 x11, 2 x10
> I selected a “🔥 3-day FREE TRIAL” deal that was shown as normally £5.99, but I was charged £48.99 for an annual plan within seconds — before the app even finished downloading. No warning, no genuine trial period, and no chance to cancel first. Apple and Nebula have both refused to refund me. The app also offers cheaper weekly and monthly options, so there’s no reason I’d ever have chosen the annual plan. This experience feels very misleading. Please be cautious before downloading.
our rationale: A three-day free trial shown at 5.99 became a 48.99 annual charge within seconds, before the download finished, so nothing renewed - it was mis-presented. Apple and Nebula have both already refused.
their reason (anthropic/claude-haiku-4.5): A trial offer converted to a paid annual subscription without adequate disclosure or opportunity to cancel, with both the store and support already refusing refund, triggering escalation.

### as:13607579600 - labelled `3`, models say `2` (11/21)
votes: 2 x11, 3 x10
> I haven't used this app in a while and I tried going into the app. It would exit without loading. It just started doing this issue for me and it still won't load. Please help to fix this issue for me so I can use this app without it doing this same issue
our rationale: The app exits without loading and the writer asks for help fixing it; no money is involved and a documented answer exists.
their reason (anthropic/claude-haiku-4.5): The app crashes on launch and will not load, blocking the user from accessing the service they may have paid for; this requires technical investigation beyond standard troubleshooting.

### as:13766345904 - labelled `2`, models say `1` (11/21)
votes: 1 x11, 2 x10
> Ich wollte diese App testen und habe daher 1€ bewusst dafür ausgegeben. Danach wurden mir jedoch noch 150€ abgebucht, ohne dass ich die App weiter benutzt hätte. Der Support reagiert überhaupt nicht auf Mails. Lasst euch bitte nicht verarschen!
our rationale: 1 euro spent deliberately to test, then 150 debited without further use, and support does not answer email at all - so repeating an instruction would go nowhere.
their reason (anthropic/claude-haiku-4.5): A €1 trial converted to a €150 charge without further use, support is unresponsive, and the charges have already occurred - this meets escalation criteria for both unresponsive support and ongoing financial harm.

### as:14220433116 - labelled `2`, models say `1` (12/21)
votes: 1 x12, 2 x9
> 1. they will show u 1 dollar charge. after that without your concern will deduct 49 dollar 2. after contacting CS instead of coarify they straight down cancelled my subscription resulting loosing my money 3. They declined to provide any receipt or invoice of the payment, breaking any country business law of providing oayment receipt minimum upon asking if not automatic. 4. Their so called psychic are all FAKE AI AGENTS replying and eating your money 5. afyer cancellation had 32 dollar balance which was deducted fir a 6. minutes chat. can you inagine almost 5 dollar charge for per minute chat, and it doesnt matter who replies or chat, it kight be you are typing still they will still deduct th...
our rationale: 1 dollar became 49, the remaining 32-dollar balance was burnt by a six-minute chat at roughly 5 per minute, and a receipt was refused outright when asked for. SECONDARY 2026-09-21: advisor_conduct dropped with the category itself - the accusation that the psychics are not real is carried by a billin
their reason (anthropic/claude-haiku-4.5): A small initial charge ($1) followed by a large deduction ($49) without explicit consent is trial_converted; the writer shows acute distress, names multiple systemic complaints including ongoing charges after cancellation, and describes a pattern of financial harm that requires human investigation.

### as:14450344254 - labelled `3`, models say `2` (10/21)
votes: 2 x10, 3 x8, 1 x3
> 本來我只是出於好奇付一美元試用這個應用程式，怎料他們直接獲取了我的信用卡資料，在未經我授權的情況下私自不斷扣款。我前後被連續扣款了三個月，發現後隨即聯絡客服，他們回覆非常迅速並安排了退款。但這令人十分懷疑，這似乎是他們慣常的騙財手法——平時趁用戶不注意時默默扣錢，一旦被人發現並追究，就極速退款了事。這完全是不良商家的做法!! I was curious and signed up for a $1 trial, but this app immediately captured my credit card details and started charging me repeatedly without my authorization. They continued to bill me for three months until I caught them. Although they refunded me very quickly after I contacted support, I suspect this is a deliberate and predatory tactic—they silently take your money and only offer an instant refund once you catch them. This is completely dishonest and predatory behavior!!!
our rationale: Three months of charges followed a 1-dollar trial, but support refunded them quickly once contacted; what remains is an accusation about the pattern, not an open case.
their reason (google/gemini-2.5-flash-lite): The user signed up for a $1 trial which then converted to recurring charges, fitting the trial_converted category. The priority is 2 as one charge has landed and a refund is requested. The next step is to process the refund.

### as:14518204004 - labelled `3`, models say `2` (12/21)
votes: 2 x12, 3 x9
> 我是在看到「靈魂伴侶（Soulmate）」的廣告後開始使用這項服務。當時網頁引導我支付 US$1 取得結果，我原本以為自己只是購買這一次性的 US$1 服務。 但是幾天後，我的信用卡卻被 NEBULA_WEB ACCESS 扣款 US$49.99。直到看到信用卡通知後，我才意識到原來 US$1 的服務後面還連結著自動續訂的訂閱方案。 我認為這項資訊在付款過程中應該以更加醒目、清楚的方式告知消費者，尤其應該讓使用者在付款前非常明確地知道：「支付 US$1 後，幾天後將自動收取 US$49.99。」 我發現扣款後立即取消自動付款並聯絡客服。值得說明的是，客服最後同意將 US$49.99 全額退回，也確認取消後續訂閱，這部分的處理速度值得肯定。 我留下這篇評論不是要說所有人都不要使用，而是提醒其他使用者： 如果你是因為 US$1 的 Soulmate／占星廣告而進來，請在付款之前仔細確認後續的訂閱與自動續費條款，避免像我一樣，在沒有充分注意到的情況下產生 US$49.99 的續訂費用。 I started using this service after seeing a “Soulmate” advertisement. I was guided to pay $1 USD to receive the result, and at the time, I believed I was simply purchasing a one-time $1 service. However, several days later, my credit card was charged $4...
our rationale: A 1-dollar Soulmate offer carried a 49.99 renewal that was not made obvious, but support has already refunded it in full and confirmed the cancellation.
their reason (google/gemini-2.5-flash-lite): The user was charged $49.99 after a $1 trial, which is a trial_converted scenario. The user also requested a refund, but the primary issue is the conversion from trial to subscription. The user also stated that customer support agreed to a full refund and cancelled the subscription, so the next step

### gp:bf31982c-d4d - labelled `2`, models say `1` (12/22)
votes: 1 x12, 2 x10
> мне списали средства без моего согласия...я жду возврата иначе я буду действовать дальше пока не добьюсь справедливости...ведь я даже не пользовался ни раз это приложение, почему не потребовалась подтверждение оплаты, я даже смс не видел что мне списали деньги...это так не пройдет...
our rationale: Says the app was never used once, no payment confirmation was requested and no SMS arrived, so the charge is not a renewal of anything agreed to.
their reason (anthropic/claude-haiku-4.5): The writer denies ever authorizing or using the app, states funds were taken without consent, and explicitly threatens legal action ('буду действовать дальше пока не добьюсь справедливости'), which is a third-party involvement trigger requiring escalation.

9 of 50 tickets flagged on priority: 0 unanimous, 2 majority, 7 split. A flag is a question, not a verdict - adjudicate against the label dictionary.
