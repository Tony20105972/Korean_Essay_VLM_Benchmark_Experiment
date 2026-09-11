# NonsulFit — Product Vision

> Canonical Source: Product purpose and scope
> Owner: docs/product/vision.md

---

## What is NonsulFit?

NonsulFit은 학생의 서면 논술 답안을 처리하는 **Humanities Essay AI System**이다.

Student Answer Image
→ Perception
→ Evidence Extraction
→ Decision
→ Feedback Generation


## Core Purpose

| # | 목적 |
|---|------|
| 1 | 학생 손글씨를 안정적으로 디지털화한다 |
| 2 | 평가 근거를 추적 가능하게 만든다 |
| 3 | 루브릭 기반 판단을 일관되게 만든다 |
| 4 | 피드백 생성과 평가 결정을 분리한다 |
| 5 | 강사의 반복 작업과 수정 시간을 감소시킨다 |
| 6 | AI 오류와 Human Correction을 장기 데이터 자산으로 축적한다 |

## Users

- **Primary User**: 논술 답안을 평가·첨삭하는 강사 및 운영자
- **Beneficiary**: 학생 (최종 결과의 주요 수혜자)

## Domain Pipeline

네 Domain은 명시적으로 분리된다. 각 Domain의 상세 책임은 [Architecture Boundaries](../architecture/boundaries.md)를 참조한다.

| Domain | Core Question |
|--------|---------------|
| Perception | 학생이 실제로 무엇을 썼는가? |
| Evidence | 평가 판단에 필요한 근거가 답안 어디에 존재하는가? |
| Decision | 해당 Evidence를 루브릭 기준으로 어떻게 판단할 것인가? |
| Generation | 확정된 판단을 학생과 강사에게 어떻게 설명할 것인가? |

## Current focus and Human Review

현재 가장 중요한 기술 Domain은 Perception이다. 원문 인식이 틀리면 이후 근거·판정·설명의 신뢰성이 흔들린다.
AI Native Harness는 문서 계약, 재현 가능한 평가, 데이터 격리와 provenance를 통해 모델/Prompt 변경에도 이 기준을 유지한다.
이는 OCR/VLM 호출을 넘어 평가 근거와 판단을 추적하는 제품을 위한 기반이다.

강사/운영자는 이미지와 전사를 검토해 인식 오류를 바로잡고, 별도로 루브릭 판단을 검토·override한다.
Perception correction은 전사 Ground Truth 수정이며 Decision review는 평가 판단 수정이다. 두 데이터를 섞지 않는다.
이미지·모델 전사·사람이 수정한 전사·오류 유형·provenance를 연결한 기록은 장기 Dataset 자산이다.
구체 인계·revision 책임은 [Human Review Boundary](../architecture/boundaries.md), 편입/사용 제한은 [Dataset Policy](../ai/datasets/dataset-policy.md)가 소유한다.
화면·업무 UI 구현은 현재 범위 밖이다.

## Initial Non-Goals

Gate 0 단계에서 다음은 구현하지 않는다:

- Product UI / Production API
- Model Gateway implementation
- Provider adapters (OpenRouter, OpenAI, Claude, Gemini)
- Image preprocessing implementation
- Verifier / Risk Engine / Selective Re-Perception
- Fine-tuning / LoRA / QLoRA / Writer Adaptation
- Model Router / Multi-Agent orchestrator
- Vector Context Retrieval / Agent Eval platform
- Production observability stack
