# Model consensus against our labels: dev, next_step

12 runs, 2 distinct models: openai/gpt-4.1-mini (v8), openai/gpt-5-mini (s1-split-parallel), openai/gpt-5-mini (s1-split-staged), openai/gpt-5-mini (v8)

## UNANIMOUS: 2 tickets

### as:12339183335 - labelled `acknowledge_and_close`, models say `escalate_to_human` (12/12)
> The app had a technical glitch and just to be on the safe side I checked my account. I messaged straightaway stating that the extra attempts were not showing, and it was not to purchase any credits in that amount. Instead of refunding, they added the credits, whilst admitting there was a technical glitch and now the support agent is awol. Total scam and need to get the money back, now conveniently they’re not replying. Total joke and scam. Update: they are saying they will not refund. Despite the fact I followed the info online - submitted the evidence and they admitted a technical error. I want my refund - I do not want the credits. Last Update: After stating it was theft, and stating it wa...
our rationale: Credits were charged during an admitted technical glitch and, after the writer cited consumer law and bank routes, Nebula confirmed it will refund, so the money question is already settled.
their reason (openai/gpt-5-mini): The user repeatedly insists they want the money back and states support refused or delayed the refund despite admitting a technical error, so this is a refund request for a withheld refund. | A payment was made and the user is requesting a refund for funds wrongly applied (money is at stake but not 

### gp:764df98a-261 - labelled `acknowledge_and_close`, models say `escalate_to_human` (12/12)
> DON'T HAVE A CANCELLATION OPTION! Do not subscribe. Out of curiosity I tried the e days free trial then I had no option to cancel. They set up a daily payment of £0.94. After all my attempts to cancel I contacted my bank and explained everything so they blocked the future payments and refund me for what already been paid meanwhile till I was trying to cancel.
our rationale: No cancellation option after the free trial and a daily GBP 0.94 debit, but the bank has already blocked future payments and refunded what was taken, so nothing is moving and nothing is asked of Nebula.
their reason (openai/gpt-5-mini): The user says they could not find or complete a cancellation after starting a free trial and were billed daily despite attempts to cancel, indicating a cancellation flow failure. | User reports an unauthorized daily payment and involvement of their bank to block payments and refund past charges, so 

## MAJORITY: 2 tickets

### gp:d531010e-e31 - labelled `ask_purchase_rail`, models say `escalate_to_human` (10/12)
votes: escalate_to_human x10, ask_purchase_rail x2
> 1달러 결재하면 스케치된 그림을 메일로 보내주는줄 알고 결재했더니 앱다운시 29.99달러 가 같이 결재되었어. 스케치그림은 찾아볼수도 없고 메일을 여니 또 스케치를 위한 초기질문 루트만 나오네요. 취소하려고 몇시간을 찾아헤메도 자기네들이 말하는 루트대로의 취소활불 탭은 어디에도 없어요. 이건 사기라고 밖에 생각 안들어요 도대체 어디로 들어가야 취소 환불을 받을수 있을까요?
our rationale: $1 for a soulmate sketch came with a simultaneous $29.99 charge, the sketch never arrived, and hours of searching found no cancel/refund tab - the explicit question is where to cancel and be refunded, and no store is named.
their reason (openai/gpt-5-mini): User reports they were charged after a $1 purchase and cannot find or complete the app's cancellation/refund flow despite searching for hours. | The user reports an unexpected $29.99 charge that they cannot cancel or find a refund/cancellation option for, which is a single charge that needs reversal

### gp:ea35c182-8ba - labelled `guide_cancellation`, models say `escalate_to_human` (8/12)
votes: escalate_to_human x8, ask_purchase_rail x3, guide_cancellation x1
> Predetory 'Free Trial' no way to cancel! hunt ed thru this entire app and cannot find ANYWHERE to cancel, so being charged for a subscription i do NOT want!! you guys need to make it very clear and eady for people to cancel their subscription etc, because at present, its extremely dodgy to not have this option anywhere and almost constitutes THEFT plain and simple!
our rationale: Being billed for a subscription following a free trial with no cancel control found anywhere in the app, so the charge is recurring and unstoppable; they have searched only the app and not the purchase rail, so the route still needs to be given.
their reason (openai/gpt-4.1-mini): The user cannot find or complete cancellation and is being charged for a subscription they do not want, indicating a cancellation failure and ongoing charges, which requires urgent escalation.

## SPLIT: 0 tickets

4 of 50 tickets flagged on next_step: 2 unanimous, 2 majority, 0 split. A flag is a question, not a verdict - adjudicate against the label dictionary.
