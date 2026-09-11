# NonsulFit — AI Evaluation Metrics

> Canonical Source: Metric calculations, evaluation normalization and candidate acceptance
> Owner: docs/ai/evaluation/metrics.md

## Evaluation principle and scope

**No candidate is accepted based on CER improvement alone.** P0 전체와 slice regression을 함께 판단한다.
CER가 개선되어도 Auto-Correction 등 핵심 품질이 악화되면 reject 대상이다.
이 문서는 `evaluation/metrics-v1` 계산 계약이다. 아래 결과를 바꾸는 정의 변경은 새 policy version을 만든다.
Dataset의 사용 권한·holdout 격리는 [Dataset Policy](../datasets/dataset-policy.md)가 소유한다.

## Shared calculation contract

- 평가 단위 sample은 한 source page다. 문서 여러 페이지는 page별 sample로 나눈다. 각 frozen benchmark execution은 sample마다 하나의 page run과 terminal outcome을 갖는다. benchmark_execution_id는 page run_id들을 묶는 평가 실행 ID이며 inference run_id와 구분한다.
- GT는 이미지와 대조하여 검수한 verbatim 문자열이다. Unicode code point 순서로 비교한다. 눈으로도 미확정인 GT, 읽기 순서 미확정 GT는 text/auto-correction 평가 eligible=false와 이유를 manifest에 사전 기록하고 별도 slice로 보고한다. Candidate 결과를 보고 제외하지 않는다.
- Prediction은 저장된 canonical raw transcription이다. Provider raw response, feedback, human correction을 prediction으로 사용하지 않는다. 출력 문자열의 trim/교정/암묵적 정규화는 금지한다.
- 유효한 terminal canonical result가 없으면 text metric의 prediction은 빈 문자열로 둔다. 실패를 text 평균에서 조용히 제외하지 않는다. eligible count, failed count, GT 제외 count를 함께 보고한다.
- Levenshtein 비용은 match=0, substitution/insertion/deletion=1이다. Prefix dynamic programming의 traceback은 문자열 끝에서 시작하며 동점이면 match, substitution, deletion, insertion 순으로 고른다. 이 하나의 deterministic alignment에서 S/D/I를 얻는다.
- 기본 비율은 corpus micro aggregation: sample별 numerator 합 / denominator 합이다. per-sample counts와 rates도 보존한다. sample rate의 단순 평균을 corpus 값으로 쓰지 않는다.
- 모든 text rate는 fraction으로 저장하며 표시 시 100을 곱해 %로 표현할 수 있다. 삽입 때문에 CER/WER/Hallucination은 1을 넘을 수 있으며 clamp하지 않는다.
- GT 길이 0이면 각 metric의 numerator가 0일 때 rate=0, 양수이면 null(undefined)이다. 따라서 empty GT에 삽입이 있으면 CER/WER/Hallucination은 null, Omission은 0이다. Corpus는 빈 GT sample의 해당 edit count도 numerator에 포함한다. corpus denominator가 0이면 같은 규칙을 적용하고 nonempty-on-empty count를 병기한다. Sample 자체가 0개인 평가는 모든 official metric을 null로 보고한다.

## Strict CER

| Field | Definition |
|---|---|
| Purpose | Verbatim 문자 충실도 측정 |
| Unit | Unicode code-point edit / GT code point |
| Inputs | 검수 GT, canonical raw transcription |
| Calculation | (S + I + D) / N_GT, 위 deterministic Levenshtein 사용 |
| Aggregation | sum(S+I+D) / sum(N_GT), sample counts/rates 병기 |
| Edge Cases | 공백/tab/CR/LF 등 모든 문자를 포함한다. 줄바꿈 포함, Unicode normalization 없음. Empty GT와 terminal failure는 shared contract 적용 |
| Interpretation | 낮을수록 원문과 일치. 언어적으로 올바른 문장인지 평가하지 않음 |

GT serialization의 줄바꿈은 LF(U+000A), 눈에 보이는 단어 간 공백은 U+0020으로 저장하고 GT revision을 고정한다.
문자 인코딩은 UTF-8이며 파일 byte 수로 CER를 계산하지 않는다. Prediction CRLF나 분해 자모는 Strict에서 그대로 비교한다.

## Normalized CER

| Field | Definition |
|---|---|
| Purpose | 허용된 formatting/Unicode 표현 차이를 분리해서 비교 |
| Unit | Normalized code-point edit / normalized GT code point |
| Inputs | 원본 GT/prediction의 평가용 복사본, normalization policy version |
| Calculation | 양쪽에 아래 v1 transform을 동일하게 적용한 뒤 Levenshtein (S+I+D)/N |
| Aggregation | normalized edit 합 / normalized GT 길이 합 |
| Edge Cases | transform 후 empty인 경우 shared empty 규칙 적용. policy 불일치 결과는 같은 비교로 합치지 않음 |
| Interpretation | Strict CER와 함께 보고. 낮아져도 자동교정 허용의 근거가 아님 |

`evaluation/normalization-policy-v1`은 다음 순서만 허용한다.

1. Unicode NFC (canonical composition만; NFKC 사용 금지).
2. CRLF를 LF로, 남은 CR을 LF로 변경.
3. U+0009 TAB과 LF를 U+0020 SPACE로 변경.
4. 연속 U+0020을 하나로 압축하고 양 끝 U+0020만 제거.

다른 공백 문자, punctuation, 대소문자, 글자, 단어 순서는 그대로 둔다. 맞춤법 교정, 단어 치환, 문법 수정, 의미 보정은 금지한다.
Normalization은 **evaluation-time comparison transform**이다. Inference output과 저장된 raw transcription 및 GT를 변경하지 않는다.
향후 formatting category를 추가하더라도 version을 바꾸고 baseline/candidate 모두 재평가한다.

## WER

| Field | Definition |
|---|---|
| Purpose | 한국어 surface 단어 단위 오류 측정 |
| Unit | Surface-token edit / GT token |
| Inputs | Raw GT/prediction |
| Calculation | U+0020 SPACE, TAB, CR, LF의 연속 구간으로 split하고 빈 token을 제거. Unicode normalization 없이 token sequence Levenshtein (S+I+D)/N_GT_tokens |
| Aggregation | token edit 합 / GT token 수 합 |
| Edge Cases | punctuation은 token 일부다. 다른 Unicode whitespace로 split하지 않는다. Empty token sequence는 shared empty 규칙 적용 |
| Interpretation | 낮을수록 좋음. 형태소 기반 WER가 아니며 morphology-aware 평가는 별도 metric/version |

## Omission Rate

| Field | Definition |
|---|---|
| Purpose | GT에 있으나 prediction에서 빠진 문자 측정 |
| Unit | Deleted GT code point / GT code point |
| Inputs | Strict CER와 동일한 GT/prediction alignment |
| Calculation | D / N_GT. Substitution을 deletion으로 중복 계산하지 않음 |
| Aggregation | sum(D) / sum(N_GT) |
| Edge Cases | 공백/줄바꿈 포함. 실패 prediction은 빈 문자열이므로 nonempty GT는 전부 deletion. Empty 규칙 공통 |
| Interpretation | 낮을수록 누락이 적음 |

## Hallucination Rate

| Field | Definition |
|---|---|
| Purpose | GT에 없는 prediction insertion을 측정하는 operational proxy |
| Unit | Inserted prediction code point / GT code point |
| Inputs | Strict CER/Omission과 동일한 alignment |
| Calculation | I / N_GT. Substitution은 별도이며 전부 hallucination으로 분류하지 않음 |
| Aggregation | sum(I) / sum(N_GT) |
| Edge Cases | 공백/줄바꿈 포함, 1 초과 가능. Empty GT에서 삽입 count와 undefined rate를 보존 |
| Interpretation | 낮을수록 삽입이 적음. 모든 의미적 환각을 포착하는 metric이라는 주장은 금지 |

## Auto-Correction Rate (annotation-assisted)

| Field | Definition |
|---|---|
| Purpose | 학생의 실제 비표준/오류 표현을 더 자연스럽거나 표준적인 표현으로 바꾸는 실패 측정 |
| Unit | Auto-corrected annotated opportunity / eligible annotated opportunity |
| Inputs | 이미지 검수 GT, raw prediction, frozen opportunity annotations, candidate별 adjudicated labels |
| Calculation | auto-corrected로 확정된 opportunity 수 / 평가 eligible opportunity 수 |
| Aggregation | 전체 opportunity numerator/denominator를 합산. Sample별 counts와 annotated coverage 병기 |
| Edge Cases | opportunity 0이면 N/A(null), 0으로 대체하지 않음. 미판정 opportunity가 있으면 provisional count만 보고 official rate는 null. Terminal failure는 auto-corrected=false로 기록하고 omission/structure 실패와 함께 해석 |
| Interpretation | 낮을수록 좋음. 단순 substitution 전체나 일반 CER와 같지 않음. 누락/실패가 많아 낮아진 값을 품질 개선으로 채택하지 않음 |

최소 annotation contract:

- 평가 전 `opportunity_id`, sample/GT revision, raw GT code-point span [start,end), source region, 실제 비표준 표현, 오류 유형, 표준화된 표현 후보와 correction reason을 고정한다.
- 하나의 학생 오류에 하나의 opportunity를 부여하며 중복/겹치는 span은 동결 전에 병합·판정한다. Opportunities는 eligible GT sample에만 둔다.
- Candidate별 annotation은 run_id, opportunity_id, prediction span 또는 absent, label(`auto-corrected`, `preserved`, `other-error`, `absent`, `unresolved`), reason, reviewer 및 annotation version을 기록한다.
- 이미지상 실제 표현이 확인되고 prediction의 대응 표현이 그 오류를 표준화/자연화한 경우만 auto-corrected다. 다른 오인식·누락은 다른 label이다. 미리 열거하지 않은 표준화 표현도 이 조건으로 판정하고 근거를 남긴다.
- Alignment는 후보 위치 탐색에 쓰되 자동 문자열 치환만으로 label을 확정하지 않는다. 판단 불일치는 별도 adjudication으로 해결하고 미해결을 분모에서 제거하지 않는다.
- Annotation coverage는 opportunity가 있는 sample 수 / text-eligible sample 수와 opportunity 수를 보고한다. G2 slice를 별도 보고한다. Annotation 없는 전체 데이터에 대해 auto-correction 0이라고 주장하지 않는다.
- Baseline/candidate는 같은 frozen opportunity set과 annotation rubric으로 평가한다. Annotation revision 변경 시 둘 다 재평가한다.

## Structured Output Failure Rate

| Field | Definition |
|---|---|
| Purpose | 소비 가능한 canonical output을 제공하지 못한 요청 비율 |
| Unit | Failed page request / accepted page request |
| Inputs | Frozen schema/parser version, 모든 page request의 terminal outcome |
| Calculation | terminal valid canonical result가 없는 request 수 / accepted request 수 |
| Aggregation | 모든 accepted page request에서 failures / total. Retry attempt를 새 request로 세지 않음 |
| Edge Cases | invalid JSON, required field missing, schema validation failure, parser failure, unrecoverable output, timeout/provider error로 output 부재 모두 failure. Retry 후 성공은 terminal success이며 attempt failures는 별도 counts로 보존. Request 0이면 null |
| Interpretation | 낮을수록 좋음. terminal success가 중간 실패·비용·지연을 지우지 않음 |

Text schema의 구체 필드 구현은 후속 Gate에서 정하되 benchmark 전에 schema/parser version과 retry/repair policy를 동결한다.
문법적 parsing 외에 전사 교정으로 repair하면 Verbatim 위반이다. Schema만 맞고 전사가 틀리면 text metric 실패이지 structure 실패로 재분류하지 않는다.

## Cost / Page

| Field | Definition |
|---|---|
| Purpose | 한 페이지 요청에 귀속되는 전체 inference 비용 |
| Unit | USD / accepted source page request |
| Inputs | Primary/retry/secondary/verifier 등 run의 모든 inference attempt usage, 실제 청구 또는 versioned 가격표, currency conversion reference |
| Calculation | 모든 귀속 inference 비용 합 / accepted page requests 수 |
| Aggregation | run 총 비용 / run 총 페이지 요청 수. sample별 비용·실패 비용도 보존 |
| Edge Cases | 실패·재시도·cache 관련 청구도 포함. 청구 없는 호출은 근거와 함께 0. 비용 미상은 0이 아니라 unknown이며 공식 총값은 null, known subtotal과 coverage 병기. 다중 page 공동 호출 비용은 포함 page에 균등 배분, 실패 page 포함. Request 0이면 null |
| Interpretation | 낮을수록 비용 효율적. 품질 계약 위반과 교환하지 않음 |

기본값은 total inference cost attributable to one processed page다. 로컬 preprocessing CPU/storage 비용은 제외하고 필요 시 별도 metric으로 보고한다.
실제 비용과 가격표 추정은 cost_basis로 구분하고 같은 비교에서 동일 기준을 사용한다. Verifier 등은 비용 범위 정의일 뿐 Gate 0 구현 요구가 아니다.

## End-to-End Perception Latency P50 / P95

두 P0 metric은 아래 동일한 분포에서 q=0.50, q=0.95만 다르게 계산한다. Model-call-only latency와 혼합하지 않는다.

| Field | Definition |
|---|---|
| Purpose | P50: 일반 요청 대기시간; P95: 느린 요청의 tail latency |
| Unit | milliseconds / accepted page request |
| Inputs | monotonic request-accepted timestamp, terminal result-ready 또는 terminal-failure timestamp |
| Calculation | duration=end-start. duration을 오름차순 정렬한 x에서 Pq=x[ceil(q*n)] (1-based nearest-rank) |
| Aggregation | 모든 accepted request의 terminal duration 분포에서 각각 P50/P95. Batch percentile의 평균을 쓰지 않음 |
| Edge Cases | queue/preprocessing/primary/retry/secondary/verifier/parsing 포함. 실패는 failure 시점, timeout은 동결 timeout 종료 시점까지 포함. 실행 중 request가 남으면 결과 provisional. n=0 또는 missing/invalid timestamps가 있으면 공식 percentile null, coverage/이유 병기 |
| Interpretation | 낮을수록 빠름. failure가 빨리 종료해 개선된 값은 실패율과 함께 해석 |

Success-only latency와 model-call latency는 보조 metric으로 따로 표시할 수 있다. P0 end-to-end 값을 대신할 수 없다.
전송 전 이미지 업로드 시간과 Feedback Generation 시간은 이 Perception 측정 경계에 포함하지 않는다.

## Baseline comparison and acceptance

변경마다 아래 record를 보존한다.

- Baseline identifier / Candidate identifier (model/provider resolved identity 포함)
- Dataset/manifest/source/GT/annotation versions; 각 후보의 prompt/preprocessing/pipeline/schema/parser versions
- Metric/normalization policy version; execution configuration, retry/timeout, cost basis, concurrency
- P0 metrics before/after, numerator/denominator와 coverage, G0–G3 및 frozen slice regressions
- Cost change, latency change, Decision (`accept`, `reject`, `defer`), Reason, reviewer/time, acceptance policy version

같은 eligible samples, metric 정의와 통제된 실행 조건으로 비교한다. 조건을 바꾸면 변경 이유와 영향도 기록한다.
Slice 목록은 결과 열람 전에 freeze하며 tier 및 G2 failure-mode slice를 포함한다.
Hard threshold는 Golden development baseline 확보 후 **versioned acceptance policy**로 확정한다. Gate 0에서는 임의 숫자를 만들지 않는다.
정책 동결 전 결과는 진단용이며 candidate acceptance는 `defer`다. 이후에는 그 정책의 한계와 tradeoff 규칙으로 결정한다.
필수 P0가 누락/미판정이면 accept하지 않는다. Auto-Correction 기회가 없는 경우 annotation된 G2 evaluation을 추가해야 한다.
CER 개선만으로 accept하지 않으며 핵심 품질 악화는 reject 대상으로 검토하고, 정책 위반은 reject한다.
Contract 위반을 Normalized CER 또는 비용 개선으로 정당화하지 않는다.
비교/선택은 development benchmark에서 한다. Final holdout은 후보/정책 동결 후 최종 보고용이며 그 결과로 후보를 다시 선택하지 않는다.

## Calculation review examples

이 예시는 위 규칙의 검산 자료이며 별도 규칙 owner가 아니다.

| Input / case | Expected result |
|---|---|
| GT=`문재점`, prediction=`문재점` | Strict CER=0/3; annotated opportunity 1개가 preserved면 Auto-Correction=0/1 |
| GT=`문재점`, prediction=`문제점` | S=1,D=0,I=0; Strict/Normalized CER=1/3; correction label 확정 시 Auto-Correction=1/1 |
| GT code points `[가, LF, 나]`, prediction=`가 나` | Strict CER=1/3, Normalized CER=0/3, WER=0/2 |
| GT=`가`(U+AC00), prediction=`가`(U+1100 U+1161) | Strict CER=2/1, Normalized CER=0/1 |
| GT empty, prediction=`가` | I=1; sample CER/Hallucination=null, Omission=0; nonempty-on-empty=1 |
| 두 sample: empty→`가`, `나`→`나` | Corpus Strict CER=(1+0)/(0+1)=1; sample rate 평균 사용 금지 |
| GT=`가나`, terminal failure | Prediction empty, D=2, CER/Omission=1; structure failure=1/1 |
| Opportunity label unresolved | Official Auto-Correction=null, candidate accept 금지 |
| Request duration이 120ms 하나뿐 | P50=P95=120ms |
| Retry 후 성공, primary $0.01 + retry $0.02 | Structure failure=0/1, Cost/Page=$0.03; latency는 두 attempt와 대기 포함 |

## P1 metrics (future; not implemented in Gate 0)

| Metric | Intended question |
|---|---|
| Critical Semantic Error Rate | 의미를 왜곡하는 치명적 오류가 얼마나 있는가? |
| Uncertainty Error Recall | 실제 전사 오류 중 uncertainty 표시가 포착한 비율은 무엇인가? |
| Human Correction Time | 사람이 AI 결과를 수정하는 데 걸리는 시간은? |
| Auto Acceptance Rate | 수정 없이 승인된 결과 비율은? |

P1의 annotation/분모/측정 절차는 도입 전에 별도 versioned 정의로 확정한다. 현재 P0 채택 기준을 대체하지 않는다.
