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
9. 읽을 수 없는 영역은 명시적인 unreadable 상태와 source region metadata로 남기고 보이지 않는 글자를 raw transcription에 채우지 않는다. 읽을 수 있는 부분만 보존한다. 이로 인한 평가상 누락을 숨기지 않는다.
10. Model/Provider가 바뀌어도 같은 계약을 적용한다. 원본과 전사의 연결은 [Architecture](../../architecture/boundaries.md)의 handoff/provenance 계약을 따른다.

## Safe Failure Principle

**When visual evidence is insufficient, explicit uncertainty is preferred over plausible transcription.**
Unreadable ≠ Guess. 문맥으로 추측하지 않고, 읽히지 않는 글자를 조용히 채우거나 모호한 텍스트를 언어적으로 그럴듯한 구절로 바꾸지 않는다.
인식 불확실성을 숨기거나 formatting 문제로 취급하지 않는다. 텍스트 일부가 읽혀도 불확실한 나머지를 확정된 원문에 섞지 않는다.

- **Auto-Correction:** 보이는 학생 원문을 더 자연스럽거나 표준적으로 고치는 오류.
- **Unsupported Guessing:** 보이지 않거나 시각 정보가 불충분한 내용을 문맥으로 확정하는 오류. 우연히 정답 문자열과 같아도 시각적 근거 없이 확정하면 안전한 인식이 아니다.

Uncertainty는 판독에 확신이 부족함을, unreadable은 해당 입력의 영역에서 지지할 수 있는 전사를 얻지 못했음을 명시한다.
Retry 또는 human review 필요성을 결과로 표현할 수 있어야 하며, 충분한 시각 근거 확인 없이 성공한 전사처럼 표시하지 않는다.
선명한 사진도 판독이 어려울 수 있다. 위험 분류와 first-class outcome 인계 의무는 [Architecture](../../architecture/boundaries.md)가 소유한다.

## Example

학생 이미지가 `세계화의 문재점은`이면 허용 전사는 `세계화의 문재점은`이다.
`세계화의 문제점은`은 Auto-Correction Error다. 사람이 전사 GT를 검토할 때도 학생의 오류를 보존한다.

## Evaluation boundary

[Normalized CER](../evaluation/metrics.md)는 평가 시 비교 복사본에만 formatting transform을 적용한다.
Inference output, 저장된 raw transcription, 원본 이미지를 변경하는 권한을 주지 않는다.
Domain 의존과 artifact 인계는 [Architecture Boundaries](../../architecture/boundaries.md)가 소유한다.
