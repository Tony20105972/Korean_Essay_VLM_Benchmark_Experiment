# NonsulFit — Perception Verbatim Contract

> Canonical Source: Perception behavior (이 문서만 전사 행동의 Source of Truth다)
> Owner: docs/ai/perception/verbatim-contract.md

## Primary objective

최우선 목적은 **Visual / Verbatim Fidelity**다. 자연스럽거나 교정된 한국어 생성이 아니다.
Handwriting recognition, layout recognition, reading order, uncertainty detection, raw transcription preservation을 수행한다.

## Behavior contract

1. 이미지에 보이는 내용을 전사하고 학생의 맞춤법 오류, 비문, 반복 표현을 그대로 보존한다.
2. spelling correction, grammar correction, rewriting, language polishing, student intent reconstruction을 하지 않는다.
3. scoring, essay grading/quality evaluation, rubric judgment, evidence interpretation을 하지 않는다. 후속 Domain의 판단을 선행하지 않는다.
4. 불분명한 글자를 문맥만으로 확정하거나 이미지에 없는 내용을 생성하지 않는다.
5. 문서의 reading order가 확인되면 그대로 유지한다. 모호한 layout을 자연스러운 문장 순서로 재구성하지 않는다.
6. 순서를 확정할 수 없으면 region별 텍스트와 확인된 order 관계를 보존하고 `ambiguous ordering` uncertainty를 기록한다. 전송용 안정적 region 순서는 확인된 읽기 순서로 주장하지 않는다.
7. 인식 불확실성은 source region/span과 유형(character/layout/order), 상태, 시각 근거가 있는 후보를 별도 metadata로 전달한다. 후보가 없으면 unknown으로 둔다.
8. uncertainty는 unknown을 자연어 추측으로 숨기는 수단이 아니다. 후속 Domain이 확인된 전사와 후보를 구별할 수 있어야 한다.
9. 읽을 수 없는 영역은 unknown metadata로 남기고 보이지 않는 글자를 raw transcription에 채우지 않는다. 읽을 수 있는 부분만 보존한다. 이로 인한 평가상 누락을 숨기지 않는다.
10. Model/Provider가 바뀌어도 같은 계약을 적용한다. 원본과 전사의 연결은 [Architecture](../../architecture/boundaries.md)의 handoff/provenance 계약을 따른다.

## Example

학생 이미지가 `세계화의 문재점은`이면 허용 전사는 `세계화의 문재점은`이다.
`세계화의 문제점은`은 Auto-Correction Error다. 사람이 전사 GT를 검토할 때도 학생의 오류를 보존한다.

## Evaluation boundary

[Normalized CER](../evaluation/metrics.md)는 평가 시 비교 복사본에만 formatting transform을 적용한다.
Inference output, 저장된 raw transcription, 원본 이미지를 변경하는 권한을 주지 않는다.
Domain 의존과 artifact 인계는 [Architecture Boundaries](../../architecture/boundaries.md)가 소유한다.
