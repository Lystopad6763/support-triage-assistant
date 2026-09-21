# 10 models on golden, 2 runs per cell

settings mode: **off** - no reasoning parameter is sent, because "low" means a small budget on gpt-5 and full extended thinking on Claude, which would compare modes rather than models

Mean over runs; +- is the spread across runs of the same cell, which is the floor below which two models are not distinguishable.

**What macro F1 averages over.** 8 of 10 categories appear in `golden`: `trial_converted` x21, `cancellation_failed` x12, `unauthorized_charge` x7, `pricing_unclear` x6, `service_not_delivered` x1, `app_technical` x1, `content_quality` x1, `refund_request` x1.

- 4 classes carry 3+ rows and are readable: `cancellation_failed`, `pricing_unclear`, `trial_converted`, `unauthorized_charge`.
- 4 classes carry two rows or fewer: `app_technical`, `content_quality`, `refund_request`, `service_not_delivered`. F1 on those is 0 or 1 with nothing between, and macro F1 weights each of them the same as a class with forty rows. The **macro F1** column therefore moves several points on a single ticket. Read it beside the accuracy column, not instead of it.
- 2 categories never appear at all: `data_privacy`, `other`. Nothing in this table measures them.

## Prompt v1

| model | served by | category | macro F1 | macro P/R | non-latin | all three | esc P/R | evidence | hard fails | tokens in/out | thinking | cached in | p50 | p95 | $/10k |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropic/claude-sonnet-5 | Anthropic x72, (unknown) x28 | 75% +-4% **n=72/100** | 0.64 | 0.71/0.67 | 79% | 35% | 100%/35% | 99% | 28 | 1,545/412 | 301 | 0 | 4304ms | 14171ms | $72.17 |
| qwen/qwen3-max | Alibaba x100 | 69% +-1% | 0.65 | 0.68/0.76 | 100% | 9% | 0%/0% | 96% | 0 | 950/147 | 0 | 730 | 4515ms | 6311ms | $8.61 |
| anthropic/claude-haiku-4.5 | Anthropic x100 | 62% +-0% | 0.55 | 0.60/0.65 | 67% | 24% | 67%/96% | 96% | 0 | 1,620/147 | 0 | 0 | 2781ms | 3484ms | $23.58 |
| google/gemini-2.5-flash-lite | Google AI Studio x100 | 62% +-0% | 0.65 | 0.71/0.80 | 50% | 10% | 67%/7% | 100% | 0 | 967/141 | 0 | 623 | 1632ms | 3117ms | $0.97 |
| google/gemini-3.1-flash-lite | Google AI Studio x100 | 56% +-0% | 0.49 | 0.57/0.62 | 33% | 10% | 0%/0% | 100% | 0 | 967/127 | 0 | 0 | 1671ms | 2492ms | $4.33 |
| openai/gpt-4o-mini-2024-07-18 | OpenAI x100 | 54% +-0% | 0.56 | 0.65/0.65 | 33% | 8% | 0%/0% | 98% | 0 | 1,164/87 | 0 | 986 | 2007ms | 2702ms | $1.53 |
| openai/gpt-4.1-mini | OpenAI x100 | 50% +-0% | 0.48 | 0.57/0.64 | 33% | 16% | 85%/43% | 92% | 0 | 1,160/118 | 0 | 137 | 2398ms | 3601ms | $6.13 |
| openai/gpt-5-mini | OpenAI x100 | 42% +-3% | 0.49 | 0.60/0.48 | 42% | 6% | 67%/7% | 100% | 0 | 1,158/879 | 733 | 435 | 12179ms | 16140ms | $19.50 |
| openai/gpt-5-nano | OpenAI x100 | 36% +-6% | 0.47 | 0.64/0.52 | 42% | 5% | 50%/17% | 100% | 0 | 1,158/2,398 | 2,266 | 88 | 17404ms | 28187ms | $10.13 |
| openai/gpt-4.1-nano | OpenAI x100 | 24% +-0% | 0.36 | 0.43/0.53 | 17% | 5% | 0%/0% | 97% | 0 | 1,160/95 | 0 | 52 | 2656ms | 3983ms | $1.50 |

## Prompt v8

| model | served by | category | macro F1 | macro P/R | non-latin | all three | esc P/R | evidence | hard fails | tokens in/out | thinking | cached in | p50 | p95 | $/10k |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen/qwen3-max | Alibaba x100 | 86% +-3% | 0.73 | 0.72/0.77 | 92% | 48% | 90%/67% | 89% | 0 | 1,862/150 | 0 | 1,628 | 4390ms | 5601ms | $10.25 |
| openai/gpt-5-nano | OpenAI x100 | 82% +-3% | 0.68 | 0.69/0.71 | 83% | 29% | 84%/57% | 99% | 0 | 2,073/2,873 | 2,728 | 1,812 | 19687ms | 28156ms | $11.71 |
| openai/gpt-5-mini | OpenAI x100 | 81% +-4% | 0.73 | 0.77/0.74 | 83% | 51% | 85%/74% | 97% | 0 | 2,073/1,073 | 920 | 1,882 | 14827ms | 21476ms | $22.42 |
| google/gemini-3.1-flash-lite | Google AI Studio x100 | 76% +-0% | 0.62 | 0.69/0.69 | 83% | 54% | 90%/100% | 100% | 0 | 1,915/134 | 0 | 0 | 1804ms | 2093ms | $6.80 |
| openai/gpt-4o-mini-2024-07-18 | OpenAI x100 | 75% +-1% | 0.69 | 0.72/0.73 | 92% | 28% | 90%/67% | 91% | 0 | 2,079/92 | 0 | 1,873 | 2296ms | 2984ms | $2.27 |
| anthropic/claude-haiku-4.5 | Anthropic x100 | 74% +-0% | 0.68 | 0.71/0.80 | 67% | 42% | 71%/96% | 93% | 0 | 2,607/142 | 0 | 0 | 2881ms | 3741ms | $33.21 |
| openai/gpt-4.1-mini | OpenAI x100 | 73% +-1% | 0.73 | 0.76/0.82 | 83% | 41% | 79%/89% | 97% | 0 | 2,075/129 | 0 | 1,412 | 2546ms | 3882ms | $6.13 |
| google/gemini-2.5-flash-lite | Google AI Studio x100 | 72% +-0% | 0.65 | 0.68/0.70 | 67% | 36% | 89%/59% | 96% | 0 | 1,915/181 | 0 | 1,530 | 1836ms | 2312ms | $1.26 |
| anthropic/claude-sonnet-5 | (unknown) x94, Anthropic x6 | 62% +-18% **n=6/100** | 0.58 | 0.58/0.58 | 83% | 38% | 50%/25% | 100% | 94 | 211/46 | 37 | 0 | 742ms | 4780ms | $8.92 |
| openai/gpt-4.1-nano | OpenAI x100 | 25% +-1% | 0.41 | 0.40/0.63 | 17% | 9% | 100%/26% | 95% | 0 | 2,075/92 | 0 | 1,413 | 2538ms | 3804ms | $1.38 |

## Did the prompt choose the winner?

- **v1**: qwen/qwen3-max (69%) > anthropic/claude-haiku-4.5 (62%) > google/gemini-2.5-flash-lite (62%) > google/gemini-3.1-flash-lite (56%) > openai/gpt-4o-mini-2024-07-18 (54%) > openai/gpt-4.1-mini (50%) > openai/gpt-5-mini (42%) > openai/gpt-5-nano (36%) > openai/gpt-4.1-nano (24%)
- **v8**: qwen/qwen3-max (86%) > openai/gpt-5-nano (82%) > openai/gpt-5-mini (81%) > google/gemini-3.1-flash-lite (76%) > openai/gpt-4o-mini-2024-07-18 (75%) > anthropic/claude-haiku-4.5 (74%) > openai/gpt-4.1-mini (73%) > google/gemini-2.5-flash-lite (72%) > openai/gpt-4.1-nano (25%)

Same order under both prompts means the prompt is not deciding the ranking. A model that only leads under the tuned prompt is evidence of the bias, and the gap is its size. A model that answered fewer than 90% of its tickets is left out of these two orderings and carries **n=answered/attempted** in the table above: its accuracy is measured on whatever survived, which is not the same test the others took.

## These rows were measured under a different prompt

`prompt_sha256` on the saved run does not match what v1, v8 renders to now. The taxonomy, the rules or the wording has moved since, so the models that produced these answers were shown a different question. Rescoring them is honest about the LABELS and silent about the PROMPT, which is why this block exists.

| cell | saved hash |
|---|---|
| v1 anthropic/claude-haiku-4.5 | not recorded - the run predates the fix that writes it |
| v1 anthropic/claude-sonnet-5 | not recorded - the run predates the fix that writes it |
| v1 google/gemini-2.5-flash-lite | not recorded - the run predates the fix that writes it |
| v1 google/gemini-3.1-flash-lite | not recorded - the run predates the fix that writes it |
| v1 openai/gpt-4.1-mini | not recorded - the run predates the fix that writes it |
| v1 openai/gpt-4.1-nano | not recorded - the run predates the fix that writes it |
| v1 openai/gpt-4o-mini-2024-07-18 | not recorded - the run predates the fix that writes it |
| v1 openai/gpt-5-mini | not recorded - the run predates the fix that writes it |
| v1 openai/gpt-5-nano | not recorded - the run predates the fix that writes it |
| v1 qwen/qwen3-max | not recorded - the run predates the fix that writes it |
| v8 anthropic/claude-haiku-4.5 | not recorded - the run predates the fix that writes it |
| v8 anthropic/claude-sonnet-5 | not recorded - the run predates the fix that writes it |
| v8 google/gemini-2.5-flash-lite | not recorded - the run predates the fix that writes it |
| v8 google/gemini-3.1-flash-lite | not recorded - the run predates the fix that writes it |
| v8 openai/gpt-4.1-mini | not recorded - the run predates the fix that writes it |
| v8 openai/gpt-4.1-nano | not recorded - the run predates the fix that writes it |
| v8 openai/gpt-4o-mini-2024-07-18 | not recorded - the run predates the fix that writes it |
| v8 openai/gpt-5-mini | not recorded - the run predates the fix that writes it |
| v8 openai/gpt-5-nano | not recorded - the run predates the fix that writes it |
| v8 qwen/qwen3-max | not recorded - the run predates the fix that writes it |
