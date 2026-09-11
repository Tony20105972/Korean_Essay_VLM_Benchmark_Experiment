# NonsulFit — Perception Verbatim Contract

> Canonical Source: Perception Engine의 행동 계약
> Owner: docs/ai/perception/

---

## Primary Objective

Perception Engine의 최우선 목적은 **Natural Language Quality가 아니라 Visual Fidelity / Verbatim Fidelity**다.

이미지에 보이는 것을 있는 그대로 전사하는 것이 목표이며, 더 자연스러운 한국어를 만드는 것이 목표가 아니다.

---

## Contract

| # | Rule |
|---|------|
| 1 | 이미지에 실제로 보이는 글자만 전사한다 |
| 2 | 맞춤법을 임의로 고치지 않는다 |
| 3 | 문법을 고치지 않는다 |
| 4 | 문장을 더 자연스럽게 재작성하지 않는다 |
| 5 | 학생의 비문 또는 반복 표현을 수정하지 않는다 |
| 6 | 불분명한 글자를 문맥만으로 확정하지 않는다 |
| 7 | 이미지에 없는 내용을 생성하지 않는다 |
| 8 | 가능한 한 original reading order를 유지한다 |
| 9 | 불확실한 영역은 uncertainty로 표현할 수 있어야 한다 |
| 10 | Provider가 변경되어도 동일한 Contract를 유지한다 |

---

## Example

Student image에 다음이 쓰여 있는 경우:

세계화의 문재점은


**허용 (Verbatim Fidelity):**

세계화의 문재점은


**실패 (Auto-Correction Error):**

세계화의 문제점은


후자는 언어적으로 자연스럽지만 Perception 관점에서는 **Auto-Correction Error**다.

학생이 실제로 `문재점`이라 썼다면 Perception은 `문재점`을 반환해야 한다. 맞춤법 교정은 Perception의 책임이 아니다.

---

## Boundary Reference

Perception의 허용/금지 책임 상세는 `docs/architecture/boundaries.md`의 Perception 섹션을 참조한다.