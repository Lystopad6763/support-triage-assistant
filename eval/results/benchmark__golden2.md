# 10 models on golden2, 2 runs per cell

settings mode: **off** - no reasoning parameter is sent, because "low" means a small budget on gpt-5 and full extended thinking on Claude, which would compare modes rather than models

Mean over runs; +- is the spread across runs of the same cell, which is the floor below which two models are not distinguishable.

**What macro F1 averages over.** 10 of 10 categories appear in `golden2`: `trial_converted` x21, `cancellation_failed` x12, `unauthorized_charge` x7, `service_not_delivered` x7, `content_quality` x7, `pricing_unclear` x6, `app_technical` x6, `refund_request` x6, `other` x6, `data_privacy` x4.

- 10 classes carry 3+ rows and are readable: `app_technical`, `cancellation_failed`, `content_quality`, `data_privacy`, `other`, `pricing_unclear`, `refund_request`, `service_not_delivered`, `trial_converted`, `unauthorized_charge`.
- 0 classes carry two rows or fewer: none. F1 on those is 0 or 1 with nothing between, and macro F1 weights each of them the same as a class with forty rows. The **macro F1** column therefore moves several points on a single ticket. Read it beside the accuracy column, not instead of it.
- 0 categories never appear at all: none. Nothing in this table measures them.

## Prompt v8

| model | served by | category | macro F1 | macro P/R | non-latin | all three | esc P/R | evidence | hard fails | tokens in/out | thinking | cached in | p50 | p95 | $/10k |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| openai/gpt-5-mini | OpenAI x164 | 77% +-1% | 0.72 | 0.80/0.71 | 83% | 42% | 83%/70% | 99% | 0 | 2,043/1,026 | 878 | 1,830 | 14640ms | 24421ms | $21.52 |
| qwen/qwen3-max | Alibaba x164 | 77% +-0% | 0.66 | 0.76/0.68 | 100% | 46% | 93%/61% | 91% | 0 | 1,840/149 | 0 | 1,567 | 4414ms | 6016ms | $10.41 |
| google/gemini-3.1-flash-lite | Google AI Studio x164 | 77% +-0% | 0.68 | 0.72/0.69 | 67% | 35% | 83%/81% | 98% | 0 | 1,897/130 | 0 | 0 | 2000ms | 2421ms | $6.71 |
| anthropic/claude-sonnet-5 | Anthropic x164 | 76% +-3% | 0.68 | 0.78/0.68 | 83% | 49% | 95%/64% | 98% | 0 | 3,436/546 | 399 | 0 | 7773ms | 15022ms | $123.36 |
| openai/gpt-4o-mini-2024-07-18 | OpenAI x164 | 71% +-1% | 0.63 | 0.66/0.65 | 100% | 16% | 67%/57% | 96% | 0 | 2,049/88 | 0 | 1,818 | 2515ms | 4226ms | $2.24 |
| openai/gpt-4.1-mini | OpenAI x164 | 71% +-0% | 0.62 | 0.63/0.65 | 83% | 38% | 77%/79% | 93% | 0 | 2,045/127 | 0 | 1,524 | 2617ms | 3664ms | $5.66 |
| google/gemini-2.5-flash-lite | Google AI Studio x164 | 70% +-0% | 0.64 | 0.68/0.65 | 67% | 37% | 84%/62% | 99% | 0 | 1,897/180 | 0 | 1,533 | 2030ms | 2773ms | $1.24 |
| anthropic/claude-haiku-4.5 | Anthropic x164 | 69% +-1% | 0.62 | 0.66/0.62 | 50% | 39% | 68%/90% | 96% | 0 | 2,565/139 | 0 | 0 | 2820ms | 4320ms | $32.64 |
| openai/gpt-5-nano | OpenAI x164 | 65% +-2% | 0.60 | 0.68/0.61 | 75% | 21% | 77%/40% | 97% | 0 | 2,043/2,741 | 2,606 | 1,630 | 22500ms | 37242ms | $11.25 |
| openai/gpt-4.1-nano | OpenAI x164 | 41% +-2% | 0.45 | 0.54/0.51 | 25% | 13% | 96%/27% | 98% | 0 | 2,045/92 | 0 | 1,442 | 2327ms | 5928ms | $1.34 |
