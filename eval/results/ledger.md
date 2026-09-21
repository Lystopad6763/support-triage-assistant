# Run ledger

Rebuilt from eval/results/*.json by eval/ledger.py - never typed, and never appended to, so it cannot outlive the runs it reports.

## Per prompt version (repeats collapsed)

| set | prompt | model | runs | category | macro F1 | priority | next_step | all three | $/10k |
|---|---|---|---|---|---|---|---|---|---|
| dev | s1-split-parallel | openai/gpt-5-mini | 2 | 85% +-4% | 0.78 | 68% | 75% | 46% | $20.36 |
| dev | s1-split-staged | openai/gpt-5-mini | 2 | 81% +-1% | 0.73 | 65% | 75% | 43% | $20.56 |
| dev | v1 | openai/gpt-5-mini | 2 | 58% +-3% | 0.62 | 69% | 22% | 6% | $10.56 |
| dev | v2 | openai/gpt-5-mini | 1 | 76% +-0% | 0.66 | 70% | 32% | 20% | $9.75 |
| dev | v3 | openai/gpt-5-mini | 1 | 76% +-0% | 0.71 | 72% | 78% | 48% | $12.30 |
| dev | v4 | openai/gpt-5-mini | 1 | 74% +-0% | 0.66 | 76% | 82% | 54% | $9.46 |
| dev | v5 | openai/gpt-5-mini | 5 | 82% +-3% | 0.76 | 74% | 76% | 57% | $10.71 |
| dev | v6 | openai/gpt-5-mini | 2 | 79% +-1% | 0.66 | 77% | 71% | 55% | $9.21 |
| dev | v7 | openai/gpt-5-mini | 2 | 80% +-3% | 0.68 | 77% | 70% | 56% | $9.49 |
| dev | v8 | openai/gpt-4.1-mini | 5 | 88% +-0% | 0.82 | 73% | 78% | 58% | $5.56 |
| dev | v8 | openai/gpt-5-mini | 3 | 81% +-8% | 0.75 | 77% | 75% | 55% | $9.84 |

## Every run

| set | prompt | hash | model | seed | category | macro F1 | all three | evidence | fails | $/10k | when |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | s1-split-parallel | `9f79f11aebf67691` | openai/gpt-5-mini | - | 88% | 0.82 | 50% | 98% | 0 | $21.51 | 2026-09-21T07:06:14+00:00 |
| dev | s1-split-parallel | `9f79f11aebf67691` | openai/gpt-5-mini | - | 82% | 0.75 | 42% | 96% | 0 | $19.22 | 2026-09-21T07:15:40+00:00 |
| dev | s1-split-staged | `9f79f11aebf67691` | openai/gpt-5-mini | - | 80% | 0.77 | 44% | 98% | 0 | $20.83 | 2026-09-21T07:18:35+00:00 |
| dev | s1-split-staged | `9f79f11aebf67691` | openai/gpt-5-mini | - | 82% | 0.70 | 42% | 96% | 0 | $20.28 | 2026-09-21T07:22:51+00:00 |
| dev | v1 | `-` | openai/gpt-5-mini | - | 60% | 0.61 | 0% | 100% | 0 | $11.01 | (file 2026-09-21T13:29) |
| dev | v1 | `-` | openai/gpt-5-mini | - | 56% | 0.62 | 12% | 100% | 0 | $10.12 | (file 2026-09-21T13:29) |
| dev | v2 | `-` | openai/gpt-5-mini | - | 76% | 0.66 | 20% | 100% | 0 | $9.75 | (file 2026-09-21T13:29) |
| dev | v3 | `-` | openai/gpt-5-mini | - | 76% | 0.71 | 48% | 100% | 0 | $12.30 | (file 2026-09-21T13:29) |
| dev | v4 | `44ccf44a4ef5a603` | openai/gpt-5-mini | - | 74% | 0.66 | 54% | 98% | 0 | $9.46 | (file 2026-09-21T13:29) |
| dev | v5 | `4b86311dc07a1566` | openai/gpt-5-mini | - | 84% | 0.70 | 62% | 100% | 0 | $11.98 | (file 2026-09-21T13:29) |
| dev | v5 | `4b86311dc07a1566` | openai/gpt-5-mini | - | 82% | 0.80 | 50% | 100% | 0 | $9.26 | (file 2026-09-21T13:29) |
| dev | v5 | `4b86311dc07a1566` | openai/gpt-5-mini | - | 76% | 0.68 | 56% | 100% | 0 | $9.80 | (file 2026-09-21T13:29) |
| dev | v5 | `4b86311dc07a1566` | openai/gpt-5-mini | 7 | 84% | 0.79 | 58% | 100% | 0 | $11.97 | (file 2026-09-21T13:29) |
| dev | v5 | `4b86311dc07a1566` | openai/gpt-5-mini | 7 | 82% | 0.83 | 58% | 98% | 0 | $10.55 | (file 2026-09-21T13:29) |
| dev | v6 | `8375b260f302099c` | openai/gpt-5-mini | - | 80% | 0.67 | 56% | 94% | 0 | $9.21 | 2026-09-20T21:28:37+00:00 |
| dev | v6 | `8375b260f302099c` | openai/gpt-5-mini | - | 78% | 0.66 | 54% | 96% | 0 | $9.21 | 2026-09-20T21:29:48+00:00 |
| dev | v7 | `7be31b747008ffb3` | openai/gpt-5-mini | - | 78% | 0.68 | 52% | 92% | 0 | $9.59 | 2026-09-20T21:34:34+00:00 |
| dev | v7 | `7be31b747008ffb3` | openai/gpt-5-mini | - | 82% | 0.68 | 60% | 98% | 0 | $9.39 | 2026-09-20T21:35:42+00:00 |
| dev | v8 | `7f10e9393f471fce` | openai/gpt-4.1-mini | - | 88% | 0.82 | 56% | 92% | 0 | $5.98 | 2026-09-21T08:41:18+00:00 |
| dev | v8 | `7f10e9393f471fce` | openai/gpt-4.1-mini | - | 88% | 0.82 | 58% | 92% | 0 | $5.22 | 2026-09-21T08:42:00+00:00 |
| dev | v8 | `7f10e9393f471fce` | openai/gpt-4.1-mini | - | 88% | 0.82 | 56% | 92% | 0 | $6.14 | 2026-09-21T08:42:36+00:00 |
| dev | v8 | `7f10e9393f471fce` | openai/gpt-4.1-mini | - | 88% | 0.82 | 60% | 94% | 0 | $5.58 | 2026-09-21T08:43:19+00:00 |
| dev | v8 | `7f10e9393f471fce` | openai/gpt-4.1-mini | - | 88% | 0.82 | 58% | 92% | 0 | $4.87 | 2026-09-21T08:46:14+00:00 |
| dev | v8 | `7f10e9393f471fce` | openai/gpt-5-mini | - | 80% | 0.76 | 48% | 98% | 0 | $10.03 | 2026-09-20T21:54:33+00:00 |
| dev | v8 | `7f10e9393f471fce` | openai/gpt-5-mini | - | 90% | 0.88 | 66% | 96% | 0 | $9.29 | 2026-09-20T21:57:29+00:00 |
| dev | v8 | `7f10e9393f471fce` | openai/gpt-5-mini | - | 74% | 0.62 | 52% | 100% | 0 | $10.19 | 2026-09-21T08:44:04+00:00 |
