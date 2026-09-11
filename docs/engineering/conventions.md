# Engineering Conventions

> Owner: docs/engineering/conventions.md

## File Naming
일반 파일은 lowercase-kebab-case를 사용한다. 필수 진입점 AGENTS.md, CLAUDE.md,
ARCHITECTURE.md, README.md 및 도구가 요구하는 고정 파일명은 예외다.

## Branch Naming
`gate-{n}/{short-description}`.

## Commit Messages
Conventional commits: feat, fix, docs, refactor, test, chore.

## Documentation
Canonical Source는 [Index ownership](../index.md)의 정해진 위치에만 작성한다.
다른 문서는 요약과 상대 링크로 참조하며 상세 규칙을 복제하지 않는다.

## Scripts
실행 script는 scripts/ 아래 둔다. Agent는 [AGENTS.md 명령 interface](../../AGENTS.md)를 사용한다.
Stack 미확정 명령은 STUB을 명시한다. STUB의 exit 0은 제품 테스트 통과를 뜻하지 않는다.
Shell은 bash와 set -euo pipefail을 사용하고 실행 권한을 부여한다.

## ExecPlan
복잡 작업은 [계획 규칙](../exec-plans/README.md)에 따라 active/에 계획 작성 후 시작한다.

언어·프레임워크·패키지 매니저 규약은 Gate 2에서 stack 확정 후 추가한다.

## Gate 2 Python stack

Execution 1에서 Python 3.12+, Pydantic 2, uv를 선택했다. 기존 구현 스택은 없었다.
Python의 Unicode code-point 문자열 처리, HF Python 생태계와의 향후 연결,
Pydantic strict schema/JSON Schema 지원을 이유로 선택했다. Provider SDK는 추가하지 않는다.

- Dependencies와 tools는 [pyproject.toml](../../pyproject.toml), 해석된 버전은
  [uv.lock](../../uv.lock)에 고정한다. 설치는 `uv sync --locked`.
- `./scripts/verify`는 doctor → Ruff lint/format check → mypy strict(src) → pytest 순이다.
  `uv run --locked`가 로컬 환경을 맞추며 최초 실행에는 dependency 다운로드가 필요할 수 있다.
- 실행 테스트는 synthetic fixture만 사용하고 network/dataset/inference를 호출하지 않는다.
- Source는 `src/nonsulfit`, tests는 `tests`에 둔다. Python module/import 규칙에 따라
  `__init__.py` 및 `test_contracts.py` 같은 snake_case 파일명은 naming 예외다.
- `./scripts/dev`는 아직 STUB이다. 제품 서버나 inference 구현을 뜻하지 않는다.
- 설치된 package는 `from nonsulfit.contracts import CanonicalDatasetSample`로 접근한다.
  serialization/validation 의미는 [Canonical contracts](../contracts/canonical-contracts.md)가 소유한다.

## Hugging Face adapter

`datasets`와 `huggingface-hub`는 `nonsulfit.providers.huggingface` 내부에서만, `pyarrow`는
`nonsulfit.providers.parquet` 내부에서만 import한다.
Canonical 계약과 향후 Evaluation Engine은 HF row/feature/SDK type을 import하지 않는다.
HF 기본 cache를 사용한다. `HF_HOME`을 명시적으로 설정하는 운영 환경은 repository 밖의
cache directory를 사용해야 하며, 프로젝트 로컬 `.cache/`와 `hf-cache/`는 Git-ignore한다.
원본 이미지 및 access token은 Git에 넣지 않는다.

Private/gated dataset token은 process environment의 `HF_TOKEN`만 사용한다. 예시 파일과
CLI 출력은 token을 포함하거나 echo하지 않는다. 공개 dataset은 token 없이 동작한다.
