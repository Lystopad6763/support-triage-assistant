# dev / prompt v1 / openai/gpt-5-mini

| metric | value |
|---|---|
| tickets | 5 |
| scored (returned valid output) | 5 |
| hard failures | 0 |
| category accuracy | **60%** |
| macro F1 over categories | **0.61** |
| macro F1 over classes with 3+ rows | **0.00** (0 classes) |
| priority accuracy | 60% |
| next_step accuracy | 20% |
| all three correct | 0% |
| secondary categories (Jaccard) | 67% |
| evidence verbatim | 100% |
| repaired after invalid JSON | 0 |
| confidence when right / wrong | 0.83 / 0.88 |
| cost | $0.00551 = $0.00110/ticket = $11.01/10k |

| escalation precision / recall | 0% / 0% (missed 2, spurious 0) |

## Per category

| category | in set | predicted | precision | recall | F1 |
|---|---|---|---|---|---|
| cancellation_failed | 2 (too few rows to read) | 1 | 100% | 50% | 0.67 |
| refund_request | 2 (too few rows to read) | 1 | 100% | 50% | 0.67 |
| trial_converted | 1 (too few rows to read) | 3 | 33% | 100% | 0.50 |

## By slice

An average over 50 rows can sit at 80% while a whole language is wrong.

| cut | slice | n | category | all three |
|---|---|---|---|---|
| language | non-english latin | 1 | 100% | 0% |
| language | non-latin script | 4 | 50% | 0% |
| tone | aggressive | 1 | 100% | 0% |
| tone | plain | 4 | 50% | 0% |
| topics | single topic | 5 | 60% | 0% |
| kb | kb has an answer | 5 | 60% | 0% |

## Category errors

| expected | actual | n |
|---|---|---|
| refund_request | trial_converted | 1 |
| cancellation_failed | trial_converted | 1 |

## Every ticket

| ticket | input (trimmed) | expected | actual | pass |
|---|---|---|---|---|
| as:14252277944 | 上面显示是三天免费试用，结果一下载就扣了363，退款也被拒绝了 ，I was misled by the interface into an accidental subscription, losing 363 RMB | refund_request P2 escalate_to_human | trial_converted P2 ask_purchase_rail | fail (cPs) |
| as:14133480377 | トライアルから自動的にサブスク課金に移行されて引き落としされました。 サブスク解除はアプリ内でしかできないようです。 英語を訳しながらやっと解除できました。解除後はメールがきましたが、信用できなかったので、いろいろ調べた | trial_converted P3 acknowledge_and_close | trial_converted P2 send_kb_article | fail (Cps) |
| as:14312098923 | برنامج سيء يقوم بالخصم من حسابي ولم اطلب الاشتراك ،قمت بحذف البرنامج ومازال يخصم ،حاولت إلغاءه بكل الطرق ومازا | cancellation_failed P1 escalate_to_human | cancellation_failed P1 ask_purchase_rail | fail (CPs) |
| gp:d531010e-e31 | 1달러 결재하면 스케치된 그림을 메일로 보내주는줄 알고 결재했더니 앱다운시 29.99달러 가 같이 결재되었어. 스케치그림은 찾아볼수도 없고 메일을 여니 또 스케치를 위한 초기질문 루트만 나오네요.  | cancellation_failed P1 ask_purchase_rail | trial_converted P2 ask_purchase_rail | fail (cpS) |
| gp:fc04bcca-56d | lo resumiré...Son unos ladrones, te roban. Te dicen "Es gratis" para luego quitarte el dinero, son un asco. NO | refund_request P2 ask_purchase_rail | refund_request P2 process_refund | fail (CPs) |

Upper case = that field matched: C category, P priority, S next_step.
