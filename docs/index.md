# NonsulFit — Documentation Index

이 문서는 Context Router다. 각 책임의 유일한 Canonical owner는 아래 파일이다. 다른 문서는 요약과 링크만 제공하며 규칙 변경은 owner에서 시작한다.

| Area | Canonical document | 이 문서는 어떤 질문에 답하는가? |
|---|---|---|
| Product | [vision.md](product/vision.md) | 누구를 위해 무엇을 만들며, 현재 초점·Human Review 목적·Non-goal은 무엇인가? |
| Architecture | [boundaries.md](architecture/boundaries.md) | Domain/Provider/provenance 경계는 무엇이며, capture quality와 handwriting difficulty는 어떻게 다르고 불확실한 결과는 downstream으로 어떻게 전달되는가? |
| Perception | [verbatim-contract.md](ai/perception/verbatim-contract.md) | 무엇을 그대로 전사하며, 못 읽었을 때 추측하지 않고 uncertainty/unreadable을 어떻게 드러내는가? |
| AI Evaluation | [metrics.md](ai/evaluation/metrics.md) | P0 metric을 어떻게 계산하며 Safe Failure와 difficult handwriting을 어떻게 평가하고 모델/Prompt 변경을 판단하는가? |
| Dataset | [dataset-policy.md](ai/datasets/dataset-policy.md) | Golden·tuning·holdout 사용 권한과 writer/duplicate leakage 방지는 무엇인가? |
| Quality | [definition-of-done.md](quality/definition-of-done.md) | 실제 Repository 상태가 Gate 0을 통과했는지 어떻게 검증하고 다음 단계는 무엇인가? |

README는 프로젝트 진입점이며 정책 owner가 아니다. Architecture의 invariant 요약은 행동·데이터·metric owner를 대체하지 않는다.
상세 규칙이 서로 다르면 임의로 선택하지 말고 material contradiction으로 기록하여 Gate 종료 전에 해소한다.
