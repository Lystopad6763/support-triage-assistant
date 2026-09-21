# 9 models on golden, 1 runs per cell

settings mode: **off** - no reasoning parameter is sent, because "low" means a small budget on gpt-5 and full extended thinking on Claude, which would compare modes rather than models

Mean over runs; +- is the spread across runs of the same cell, which is the floor below which two models are not distinguishable.

## Prompt v8

| model | served by | category | macro F1 | non-latin | all three | esc P/R | evidence | hard fails | tokens in/out | p50 | p95 | $/10k |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen/qwen3-max | Alibaba x4 | 100% +-0% | 1.00 | 100% | 50% | 100%/67% | 75% | 0 | 1,888/158 | 11297ms | 11297ms | $13.11 |
| openai/gpt-5-mini | OpenAI x4 | 75% +-0% | 0.67 | 75% | 25% | 100%/33% | 100% | 0 | 2,103/1,030 | 17281ms | 17281ms | $21.41 |
| openai/gpt-4.1-mini | OpenAI x4 | 75% +-0% | 0.67 | 75% | 25% | 100%/67% | 100% | 0 | 2,105/135 | 8375ms | 8375ms | $9.25 |
| anthropic/claude-sonnet-5 | Claude Platform on AWS x4 | 75% +-0% | 0.67 | 75% | 25% | 100%/33% | 100% | 0 | 3,536/635 | 16391ms | 16391ms | $134.31 |
| google/gemini-3.1-flash-lite | Google x4 | 75% +-0% | 0.67 | 75% | 50% | 100%/67% | 100% | 0 | 2,358/132 | 8000ms | 8000ms | $7.89 |
| anthropic/claude-haiku-4.5 | Amazon Bedrock x4 | 50% +-0% | 0.38 | 50% | 0% | 75%/100% | 75% | 0 | 2,680/180 | 8891ms | 8891ms | $35.84 |
| google/gemini-2.5-flash-lite | Google x4 | 50% +-0% | 0.38 | 50% | 25% | 100%/67% | 100% | 0 | 1,928/175 | 7140ms | 7140ms | $2.63 |
| openai/gpt-5-nano | OpenAI x4 | 25% +-0% | 0.25 | 25% | 0% | 0%/0% | 100% | 0 | 2,103/3,242 | 28859ms | 28859ms | $13.59 |
| openai/gpt-4.1-nano | OpenAI x4 | 25% +-0% | 0.25 | 25% | 0% | 100%/33% | 100% | 0 | 2,105/94 | 8438ms | 8438ms | $1.47 |
