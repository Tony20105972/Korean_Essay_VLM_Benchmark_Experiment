# NonsulFit — Dataset Policy

> Canonical Source: Dataset tiers, usage roles, Golden integrity and leakage policy
> Owner: docs/ai/datasets/dataset-policy.md

## Terms: tier, role and Golden status

Tier는 측정 목적, role은 사용 권한, Golden은 검수된 이미지/GT와 versioned manifest를 가진 품질 관리 속성이다.
서로 다른 축이며 Golden을 final holdout과 동의어로 사용하지 않는다. 모든 manifest는 tier, role, golden status를 명시한다.

- Training Set: model weights를 학습·fine-tuning하는 데이터. Golden sample은 포함할 수 없다.
- Development / Tuning Set: prompt/model/threshold/routing 선택을 반복하는 데이터. 여기서 tuning은 weights 학습이 아니다.
- Benchmark Set: 고정된 평가 비교용 데이터. 반복 결과를 보고 후보를 선택하면 development 사용 이력이 생기며 final holdout으로 쓸 수 없다.
- Final Holdout: 후보와 평가 정책을 동결한 뒤 독립적인 최종 보고에만 사용하는 데이터. 모든 반복 최적화와 선택에 사용 금지다.
- Golden Set: 원문 충실성 검수, source/GT revision, lineage를 갖춘 데이터. Development Golden과 Golden Final Holdout은 별도 partition이다. Golden은 어느 role에서도 weights 학습에 쓰지 않는다.
- Challenge Set: 특정 failure mode를 겨냥하는 tier/slice다. development와 holdout partition을 별도로 선언하며 이름만으로 사용 권한을 부여하지 않는다.
- Domain Golden: NonsulFit 운영 분포를 평가하는 Golden이다. development와 writer-disjoint final holdout을 분리한다.

`training/fine-tuning`은 weights 변경을 뜻한다. `selection tuning`은 prompt/model/threshold/routing 선택을 뜻한다.
규칙과 보고서에서 단독으로 “모델 튜닝”이라고 쓰지 않고 어느 의미인지 명시한다.

## Dataset tiers (long-term targets, not implemented datasets)

| Tier | Purpose | Coverage / target |
|---|---|---|
| G0 Smoke | 빠른 pipeline/schema/API regression 탐지 | 초기 목표 100–200 samples. 품질/일반화의 최종 증거로 사용하지 않음 |
| G1 General Korean Golden | 범용 한국어 handwriting recognition 품질 측정 | 초기 목표 1,000–2,000 samples. 외부 데이터도 검수/lineage 기준 충족 시 Golden으로 등록 |
| G2 Challenge / Anti-Correction | 자동교정·문맥 추측·누락·환각 취약점 측정 | 희귀어, mixed-script, 비정상 표현, 장문과 correction-opportunity annotations |
| G3 NonsulFit Domain Golden | Production validity 측정 | 실제 또는 실제 운영에 매우 가까운 학생 논술 답안. final holdout은 writer-disjoint 필수 |

External General Benchmark는 외부 공개/허가 데이터를 사용하며 범용 한국어 손글씨 성능을 측정한다.
NonsulFit 실제 운영 분포를 대표한다고 주장하지 않는다. Domain Golden은 이 운영 유효성을 별도로 측정하므로 External과 분리한다.
G1이 항상 외부 데이터라는 뜻은 아니다. source_origin과 license/permission reference를 manifest에 기록한다.

## Usage matrix

YES는 해당 role의 권한이며 다른 integrity 규칙도 함께 충족해야 한다.
Final Reporting은 독립적인 최종 성능 주장이다. Development 결과를 진단용으로 공개할 수는 있지만 holdout 성능이라고 표현하지 않는다.

| Dataset role / partition | Training / fine-tuning | Prompt tuning | Model selection | Threshold / routing tuning | Final reporting |
|---|---|---|---|---|---|
| Training (non-Golden) | YES | YES | NO | NO | NO |
| Development / Tuning (non-Golden or Golden) | NO | YES | YES | YES | NO |
| Reusable Benchmark | NO | YES | YES | YES | NO |
| Challenge Development (Golden) | NO | YES | YES | YES | NO |
| Final Holdout (including External/Challenge Golden Holdout) | NO | NO | NO | NO | YES |
| Domain Golden Final Holdout | NO | NO | NO | NO | YES |

Golden development의 prompt tuning은 평가 결과로 instruction을 수정하는 것을 뜻한다. Golden GT를 few-shot 예시나 다른 inference prompt 내용으로 옮기는 것은 DATA005로 금지한다.
Prompt/출력/GT를 보며 반복 수정한 Dataset, model 선택·threshold/routing 조정에 사용한 Dataset은 final holdout이 아니다.
Final holdout 실행 전 candidate, dataset, metric/normalization/acceptance policy를 동결한다.
Holdout 결과를 이후 개선에 활용하면 그 partition은 노출된 것으로 기록하고 독립 최종 보고를 위해 새 untouched holdout을 확보한다.
이를 이름 변경이나 manifest version 증가만으로 다시 untouched 상태로 만들 수 없다.
운영상 실패의 재실행은 동일한 동결 설정과 이유를 기록하며 실패 기록을 삭제하거나 좋은 실행만 골라 보고하지 않는다.

## Dataset invariants

| ID | Rule |
|---|---|
| DATA001 | 모든 Golden sample은 training/fine-tuning에 사용하지 않는다. 평가 독립성과 이미지/GT 무결성을 보호하며 human correction도 우회 수단이 아니다. |
| DATA002 | Golden manifest는 immutable version이다. source/GT/annotation/role 변경은 새 version과 change reason을 기록하고 기존 version을 보존한다. |
| DATA003 | Benchmark run은 dataset/manifest version, source revision, GT revision, sample ID를 기록한다. |
| DATA004 | Evaluation run은 sample-level prediction, metric counts/denominators, status, annotation labels, provenance references를 보존한다. |
| DATA005 | Golden GT를 inference prompt에 노출하지 않는다. 평가자는 inference 완료 후 별도 평가 경계에서 GT를 사용한다. |
| DATA006 | Final holdout은 weights 학습 및 모든 반복 selection tuning에서 격리한다. 개발 사용 이력이 있는 sample을 final holdout으로 승격하지 않는다. |
| DATA007 | Domain Golden final holdout은 writer-disjoint다. 아래 writer/duplicate 정책을 반드시 충족한다. |

Manifest의 최소 정보는 sample/page ID, source image ID/digest, source dataset/revision, GT/annotation revision,
tier, role, golden status, writer identity 또는 unavailable 상태, split/lineage, usage/exposure history, permission reference다.
Artifact/run/evaluation 연결의 상세 owner는 [Architecture Provenance](../../architecture/boundaries.md)다.

## Writer and duplicate leakage

Writer identity가 있으면 동일 writer의 sample이 training/development/selection benchmark와 final holdout을 가로지를 수 없다.
여러 source에서 동일 writer임이 확인되면 하나의 writer group으로 묶는다. Domain Golden final holdout은 writer identity와 이 검증 증거 없이는 승인하지 않는다.
Writer를 확인할 수 없는 Domain data는 development/general benchmark로만 사용하고 writer-generalization holdout 주장을 하지 않는다.

Writer 정보가 없는 External Dataset은 provenance에 `writer-disjoint guarantee unavailable`을 기록한다.
General Benchmark로 사용할 수 있고, usage-disjoint final reporting을 하더라도 writer-generalization claim은 금지한다.
이 제한을 Domain Golden의 writer-disjoint 요구를 면제하는 데 사용하지 않는다.

Split 공개/동결 전 source lineage와 exact image digest를 검사하고, crop/resize/재촬영 등 near-duplicate handwriting/image 후보를 검사한다.
Near-duplicate 검사는 선택한 방법/version, 범위, 결과, 미검사 범위·한계를 기록한다. 의심 쌍은 사람 검토로 해결하기 전 holdout에서 격리한다.
External과 Domain 사이에도 같은 검사와 lineage 관리를 적용하며 중복 source sample을 양쪽 독립 집계에 넣지 않는다.
동일 원본의 파생 이미지는 새 독립 sample로 취급하지 않으며 같은 split에 속한다.

## Human corrections and evaluation

Perception correction은 새 GT revision 후보이며 검수 후에만 Golden GT로 채택한다. Decision override를 전사 GT로 사용하지 않는다.
Golden 수정 시 기존 benchmark 결과를 소급 변경하지 않고 새 dataset/GT revision으로 평가한다.
Golden sample에서 파생된 correction도 DATA001/006의 사용 이력을 상속한다.
지표/annotation 계산은 [Evaluation Metrics](../evaluation/metrics.md), 교정 artifact 관계는 [Architecture](../../architecture/boundaries.md)가 소유한다.
