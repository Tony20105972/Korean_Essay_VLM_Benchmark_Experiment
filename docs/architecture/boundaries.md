# NonsulFit — Architecture Boundaries

> Canonical Source: Domain dependencies, handoffs, Provider boundary and artifact provenance
> Owner: docs/architecture/boundaries.md

## Scope and public contracts

이 문서는 논리적 책임과 의존 규칙을 고정한다. 디렉터리, DB, SDK, schema 구현은 후속 Gate에서 정한다.
Public Contract는 versioned provider-neutral artifact/schema이며 다른 Domain의 실행 구현을 뜻하지 않는다.
모든 handoff artifact는 자신의 ID/version과 upstream artifact references를 갖는다. 후속 Domain은 upstream artifact를 변경하지 않고 새 artifact를 생성한다.
Canonical Schemas는 공통 ID, source location, uncertainty, provenance 참조를 정의하는 계약이다. 특정 Provider나 제품 Domain 구현에 의존하지 않는다.

## Capture quality and recognition difficulty

두 위험은 별도 축이다. 하나의 image quality 점수로 인식 신뢰도를 대신하지 않는다.

| Risk | Meaning | Examples |
|---|---|---|
| Capture Quality Risk | 촬영/이미지 품질로 인해 시각 정보가 손실되거나 왜곡됨 | blur, perspective, shadow, glare, crop loss, low resolution, lighting problem |
| Recognition Difficulty Risk | 사진이 깨끗해도 손글씨 형태 자체의 난이도로 판독이 어려움 | severe handwriting variation, collapsed glyph shapes, overwriting, faint strokes, unusual character formation, writer-specific ambiguity, visually ambiguous characters |

**Good image quality does not imply reliable handwriting recognition.** Capture Quality ≠ Recognition Confidence.
Capture Quality와 Handwriting/Recognition Difficulty도 서로 다른 개념이다. Faint strokes 등은 원인이 겹칠 수 있으며 단일 원인으로 강제 분류하지 않는다.
Risk의 관찰 근거와 해당 source region을 보존하고, 원인을 모르면 unknown으로 남긴다. 선명한 이미지라는 이유로 전사를 confirmed로 승격하지 않는다.
이는 책임 분류이며 Image Quality Gate, difficulty classifier, Risk Engine 구현이나 threshold 요구가 아니다.

## Domain handoff contracts

### Perception

| Field | Contract |
|---|---|
| Question | 학생이 실제로 무엇을 썼는가? |
| Owns | 이미지 기반 인식과 Canonical Perception Result 생성. 전사 행동의 유일한 owner는 [Verbatim Contract](../ai/perception/verbatim-contract.md)다. |
| Receives | Original student image와 선택적 derived image/preprocessing artifact 및 source references |
| Produces | Canonical Perception Result: raw transcription, source reference, line/region IDs와 locations, reading-order 관계, uncertain/conflicting spans, unreadable regions, perception status, provenance references |
| Must Preserve | 의미를 담은 시각 증거, 학생 오류, 확인된 읽기 순서, 원본까지의 추적성. 상세 행동은 Verbatim Contract 적용 |
| Must Not Do | scoring, rubric judgment, evidence interpretation, spelling/grammar correction, rewriting, intent reconstruction. Evidence·Decision 판단을 선행하지 않음 |
| Allowed Dependencies | Canonical Schemas, source artifact public contract, Model Gateway Interface |
| Forbidden Dependencies | Evidence/Decision/Generation 구현과 판정 artifact, Provider Adapter/SDK |

Canonical result의 raw transcription은 Provider raw response와 다르다. 전자는 인식된 원문 텍스트, 후자는 Provider가 반환한 원시 응답이다.
Region은 사용한 이미지의 좌표계와 artifact ID를 명시하며 derived image 좌표는 source로의 변환 참조를 갖는다.

### Perception → Evidence: outcome preservation

Uncertainty / unreadable은 자유 서술 경고가 아니라 **first-class perception outcome**이다.
Transcription, source reference, uncertain spans, unreadable regions, perception status, provenance를 반드시 함께 표현할 수 있어야 한다.
텍스트가 전혀 없는 unreadable region도 source location으로 참조할 수 있어야 한다. Schema/enum은 Gate 1/2에서 확정한다.
페이지 전체 상태로 개별 span의 불확실성을 지우지 않는다. Confirmed는 현재 증거에 근거한 상태이지 오류가 없다는 보증이 아니다.

| Perception outcome | Evidence handoff rule |
|---|---|
| Confirmed text | 출처와 상태를 유지하면서 normal evidence processing 허용 |
| Uncertain / conflicting text | 불확실성·충돌·시각 근거 후보를 보존하고 confirmed evidence와 구분. Evidence가 임의로 uncertainty를 제거하거나 확정 상태로 승격하지 않음 |
| Unreadable region | 내용이 미확정인 영역 참조를 전달. Semantic guessing으로 내용을 복원하거나 근거가 없다는 확정 판정으로 바꾸지 않음 |

시각 근거를 확인한 새 Perception 결과 또는 이미지 검토에 근거한 human correction revision으로 해소되기 전에는 downstream이 확정 전사로 취급할 수 없다.
영향받지 않은 confirmed 영역은 처리할 수 있으나 미해결 영역에 의존하는 Decision은 review-needed로 유지하며 점수/판정을 확정하지 않는다.
모든 uncertain 후보를 버리고 남은 문장만 확정 답안 전체처럼 제시하는 것도 금지한다.

### Evidence

| Field | Contract |
|---|---|
| Question | 평가 판단의 근거가 답안 어디에 있는가? |
| Owns | 답안 내 근거 위치 식별, claim-evidence 연결, 루브릭 관련 근거 후보 추출 |
| Receives | Canonical Perception Result. 루브릭 관련 후보 생성 시 versioned rubric criteria의 공개 정의를 받음 |
| Produces | Evidence references, source spans/locations, claim-evidence mappings, rubric-relevant evidence candidates |
| Must Preserve | Perception result ID/version, 원문 인용과 source 위치, 관련 uncertainty 및 원본 이미지까지의 링크 |
| Must Not Do | final score calculation, final rubric verdict, feedback wording, Provider-specific parsing, 원문 수정 |
| Allowed Dependencies | Canonical Schemas, Perception Public Contract, Rubric Domain의 공개 criteria, Model Gateway Interface |
| Forbidden Dependencies | Perception internals, Decision/Generation 구현·결과에 대한 역의존, Provider Adapter/SDK |

Source span은 참조하는 raw transcription의 Unicode code-point 기준 반개방 구간 [start, end)과 line/region 참조를 갖는다.
관찰된 인용과 해석된 claim을 구분한다. 불확실한 전사를 확정된 근거로 숨기지 않는다.

### Decision

| Field | Contract |
|---|---|
| Question | Evidence를 루브릭 기준으로 어떻게 판단하는가? |
| Owns | 루브릭/업무 규칙에 따른 판정과 점수 |
| Receives | Evidence artifacts, versioned rubric/business rules |
| Produces | Rubric decisions, scores, applicable confidence/uncertainty, rationale의 Evidence references, finalized/review-needed 상태 |
| Must Preserve | Evidence linkage, rubric/business-rule version, upstream uncertainty. 미해결 판단은 finalized로 표시하지 않음 |
| Must Not Do | direct image transcription, Provider SDK access, Provider-specific response parsing, 피드백 재작성으로 판정 변경 |
| Allowed Dependencies | Canonical Schemas, Evidence Public Contract, Rubric Domain, Model Gateway Interface |
| Forbidden Dependencies | Perception internals, Generation 구현, Provider Adapter/SDK |

### Generation

| Field | Contract |
|---|---|
| Question | 확정된 판단을 학생과 강사에게 어떻게 설명하는가? |
| Owns | 확정 판정의 설명과 학습 제안 표현 |
| Receives | Finalized Decision artifacts, relevant Evidence references |
| Produces | Student-facing feedback, teacher-facing explanation, learning suggestions |
| Must Preserve | Decision meaning, score, rubric verdict, Evidence linkage 및 명시된 uncertainty |
| Must Not Do | finalized score 변경, rubric decision 반전, evidence 발명, original transcription 수정 |
| Allowed Dependencies | Canonical Schemas, Decision Public Contract, Evidence References, Model Gateway Interface |
| Forbidden Dependencies | Perception internals, upstream Domain 구현, Provider Adapter/SDK |

Finalized artifact가 없으면 Generation은 최종 평가 피드백을 만들지 않고 review-needed 상태를 반환한다.

## Dependency direction

다음 화살표는 코드/계약 의존 방향이다. 데이터 흐름 또는 실행 호출 순서와 구분한다.

```text
Perception -> Canonical Schemas + Source Artifact Contract
Evidence -> Canonical Schemas + Perception Public Contract + Rubric Criteria
Decision -> Canonical Schemas + Evidence Public Contract + Rubric Domain
Generation -> Canonical Schemas + Decision Public Contract + Evidence References

Product Domains -> Model Gateway Interface
Provider Adapters -> Model Gateway Interface (implements) + Provider SDKs
```

런타임 요청은 Product Domain → Model Gateway Interface → 주입된 Provider Adapter → Provider SDK 순서다.
Gateway Interface는 Adapter/SDK를 import하지 않는다. 조립 계층만 interface에 adapter를 연결하며 업무 판단을 하지 않는다.
공개 artifact를 전달받는 것은 upstream 구현 호출 권한이 아니다. 위 목록 이외의 Domain 내부 의존 및 역방향/순환 의존은 금지한다.
특히 Decision → Provider SDK, Generation → Provider SDK, Perception → Decision, Generation → Perception internals는 금지한다.

## Model Gateway boundary

Gateway는 Provider authentication/configuration, request translation, response parsing, error mapping,
provider-specific model identifier resolution, canonical response conversion을 담당한다.
Provider SDK import는 Gateway 내부 Provider Adapter layer에만 허용한다. Perception을 포함한 모든 제품 Domain과 Gateway Interface는 SDK를 알지 않는다.
예시 위치는 `model-gateway/providers/{openrouter,openai,anthropic,google}`이며 실제 코드 구조는 Gate 1/2에서 확정한다.
Gateway는 canonical success/error, neutral model identity, usage/cost metadata와 opaque raw-response reference를 반환한다.
Provider-specific type/response object는 밖으로 전달하지 않는다. Provider identity 문자열은 provenance이며 SDK type 의존이 아니다.
Raw response는 Gateway가 보존하고 제품 Domain은 opaque reference만 유지한다. 오프라인 감사자가 원시 응답을 열람하는 것은 Domain의 Provider parsing을 허용하지 않는다.
Gateway는 전사 교정·근거 해석·루브릭 판정을 소유하지 않는다.

## Architecture invariants

| ID | Rule |
|---|---|
| ARCH001 | Perception은 Decision package를 직접 참조할 수 없다. |
| ARCH002 | Decision은 OpenRouter/OpenAI/Anthropic/Google 등 Provider SDK 또는 response type을 직접 참조할 수 없다. |
| ARCH003 | Provider-specific response/type은 Model Gateway 밖에 노출하지 않는다. SDK import는 Provider Adapter에만 허용한다. |
| ARCH004 | 모든 AI inference attempt는 run_id, provider, model identity, model version 또는 resolved model identifier, prompt_version, preprocessing_version, pipeline_version을 기록한다. 아래 linkage contract를 따른다. |
| ARCH005 | Golden의 training/fine-tuning 금지와 final holdout 격리는 [Dataset Policy](../ai/datasets/dataset-policy.md)의 DATA001/006을 따른다. |
| ARCH006 | Original student image는 immutable source artifact다. 전처리 결과로 대체할 수 없다. |
| ARCH007 | Perception은 scoring/rubric judgment/교정/재작성을 하지 않는다. 행동 상세는 [Verbatim Contract](../ai/perception/verbatim-contract.md)가 소유한다. |
| ARCH008 — Explicit Uncertainty | Perception result must explicitly represent uncertainty and unreadable visual regions. 시각적 증거가 충분하지 않으면 확정 텍스트를 만들어서는 안 된다. 행동 상세는 Verbatim Contract를 따른다. |
| ARCH009 — Unsafe Propagation Prevention | Uncertain, conflicting, or unreadable perception output must not propagate to Evidence or Decision as confirmed student text. 불확실한 결과를 확정된 학생 원문으로 자동 전달하지 않는다. 위 outcome preservation 계약을 따른다. |

ARCH009는 잘못된 전사 → 확정 텍스트 → Evidence → Decision → 잘못된 첨삭으로 이어지는 전파를 차단한다.
오류가 탐지되거나 결과가 충돌하면 상태와 참조를 유지하고, 후속 단계의 의미 해석으로 이를 숨기지 않는다.

## Provenance linkage contract

- `source_image_id`: 원본 bytes의 immutable identity 및 content digest. 수정된 원본은 새 artifact다.
- `derived_image_id`: source_image_id, preprocessing_version, 변환 parameters와 좌표 mapping 참조를 가진다. 파생본은 원본을 덮어쓰지 않는다.
- `sample_id`: versioned dataset manifest에서 source_image_id와 page 식별자를 연결한다. 선택한 derived artifact는 run 입력에 기록한다.
- `run_id`와 `inference_run_id`는 동일한 논리 실행 ID의 명칭이다. 한 perception request의 retry/secondary/verifier 호출은 고유 attempt_id와 parent run_id로 연결한다.
- 각 inference attempt는 실제 input artifact IDs, ARCH004 fields, 시작/종료·실패 상태, usage/cost를 기록한다. 이미지 전처리가 없으면 preprocessing_version은 `none`; prompt 등 적용되지 않는 필드는 이유와 함께 `not-applicable`로 기록하고 생략하지 않는다.
- Provider가 model version을 제공하지 않으면 실제 resolved identifier와 resolution timestamp 및 version unavailable 상태를 기록한다. 버전을 추측하지 않는다.
- `raw_response_ref`: Gateway가 보존한 원시 응답 참조다. 응답이 없으면 null과 failure reason을 남긴다.
- Canonical Perception Result는 result ID/version, run_id, source/derived IDs, schema/parser version, raw_response_ref를 연결한다. parse failure도 별도 run outcome으로 보존한다.
- Evaluation result는 sample_id + run_id + dataset/manifest version + source/GT revision + metric/normalization/annotation policy version을 참조한다. parsed result reference와 평가 output을 보존한다.

Source → derived → run inputs, source → sample → run, run → raw response/canonical result → evaluation의 연결을 모두 추적할 수 있어야 한다.
이는 관계 계약이며 DB schema 구현 요구가 아니다. 원시 응답, raw transcription, human correction, evaluation-time 변환본은 서로 구분한다.

## Human review boundary

[Product Vision](../product/vision.md)의 Human Review 목적에 따라 다음 artifact를 구분한다.

- Perception correction은 이미지에 근거한 transcription Ground Truth correction이다. original image, model transcription, human corrected transcription, error type, reviewer/review time, run/result references를 연결한다. 학생의 맞춤법을 교정하는 작업이 아니다.
- Decision review/override는 rubric judgment correction이다. 기존 decision ID, rubric version, 검토된 evidence, 이전/새 판정·점수, 변경 이유, reviewer/time을 연결한다. transcription GT에 합치지 않는다.
- 둘 다 기존 결과를 덮어쓰지 않고 새 revision을 만든다. Perception correction 이후의 Evidence/Decision은 재검토하거나 새 revision으로 재생성하며 이전 판정을 조용히 재사용하지 않는다.
- Decision override 이후 Generation은 새 finalized Decision을 참조한다. Human correction의 Dataset 편입은 [Dataset Policy](../ai/datasets/dataset-policy.md)를 따르며 Golden 격리를 우회하지 않는다.
