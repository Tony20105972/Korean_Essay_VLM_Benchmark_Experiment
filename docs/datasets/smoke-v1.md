# smoke-v1 — External Smoke Dataset

> Owner: docs/datasets/smoke-v1.md — smoke-v1 freeze의 source, identity, selection과 한계

`smoke-v1`은 평가 시스템이 동작하는지 확인하기 위한 G0 Smoke subset이다. Tier/role/Golden의
의미는 [Dataset Policy](../ai/datasets/dataset-policy.md)가 소유하고, 변환 동작과 CLI는
[HF Adapter](huggingface-adapter.md)가 소유한다. 이 문서는 이 특정 freeze의 결정만 기록한다.

## Source

```text
dataset:   hyokwan/ocr_dataset
revision:  7257b1a377b98e06e85ac2aba040263083aa9185
split:     train (유일한 split)
rows:      85,549
layout:    86 parquet shards, 약 42.7 GB
columns:   modality, image, instruction, input, output, source, label
license:   Apache 2.0 (upstream 표기; 별도 permission review는 수행하지 않았다)
```

Upstream dataset 전체는 Golden이 아니다. `smoke-v1`은 tier `G0`, role `benchmark`,
`golden: false`로 동결한다. 품질이나 일반화의 최종 증거로 사용하지 않는다.

## Mapping

```yaml
image:         image
transcription: output
sample_id:     null      # ID column 없음 → content-digest identity
writer_id:     null      # 필기자 구분 불가
```

`instruction`, `input`, `source`, `modality`는 상수에 가까운 값이고 canonical sample에 넣지
않는다. `label`(`P.Paper` / `T.Tablet`)은 매체 유형이며 selection stratification에 쓰고 report에
기록한다. Canonical `Metadata.capture_quality`와 `handwriting_difficulty`에는 넣지 않는다.
그 둘은 촬영 품질과 판독 난이도를 뜻하고 upstream은 어느 쪽도 제공하지 않기 때문이다.

## Sample identity

Dataset에 고유 식별자 column이 없으므로 content-digest identity를 쓴다. Row index는 장기
식별자가 아니다. Revision이 바뀌면 row 순서가 바뀔 수 있고, 그때 같은 ID가 다른 sample을
가리키면 벤치마크 비교가 조용히 무의미해진다. 계산식과 canonical 기록은
[HF Adapter의 Sample identity](huggingface-adapter.md#sample-identity)가 소유한다.

Manifest의 `selected_rows`는 어느 shard의 몇 번째 row였는지를 기록하지만 이는 다운로드 범위를
줄이기 위한 hint이며 materialize 시 content digest로 재검증한다. Row가 이동했거나 내용이
바뀌면 조용히 다른 sample로 대체되지 않고 실패한다.

## Selection

```text
scan window:    86 shard 중 균등 간격 6개 shard의 text column
selection pool: 각 shard의 앞 2개 row group
target size:    150
```

선택은 결정론적이고 seed가 없다. 먼저 transcription 길이 band(`short` < 50자,
`medium` 50–199자, `long` 200자 이상)로 배분하되 각 band에 floor를 두고, band 안에서 label 비율에
비례해 배분한 뒤 각 bucket에서 균등 간격으로 고른다. Band floor는 이 source가 `medium`에
크게 치우쳐 있어 비례 배분만 하면 짧은 전사가 통째로 빠지기 때문이다. Label은 반대로
비례 배분한다. `P.Paper` / `T.Tablet` 비율 자체가 재현할 가치가 있는 성질이다.

Pool을 row group 단위로 제한하는 이유는 fetch 비용이다. Parquet은 row 단위로 읽을 수 없고
row group이 약 100 MB이므로 pool을 넓히면 선택한 150개를 얻기 위해 읽어야 하는 양이 커진다.
전체 42.7 GB를 내려받지 않는다는 제약을 지키기 위한 의도적 절충이다.

실제 분포, GT 검증 결과와 freeze 시점은 `./scripts/dataset select`가 생성하는
[smoke-v1.report.md](../../datasets/manifests/smoke-v1.report.md)에 있다.

## Ground truth

GT는 `output` column을 **verbatim** 보존한다. Trim, Unicode normalization, 맞춤법 교정,
CRLF 변환을 하지 않는다([Verbatim Contract](../ai/perception/verbatim-contract.md)).
검증은 source를 서술할 뿐 고치지 않는다. 빈 전사, 중복 전사, UTF-8 인코딩 불가, control
character, NFC 불일치, 자모, 한자/영문/이모티콘/숫자 포함 여부를 세어 report에 남긴다.

자모는 두 종류를 나눠 센다. Conjoining jamo(U+1100–U+11FF 등)는 분해되었거나 깨진 음절을
뜻하므로 이상 징후로 다루고, compatibility jamo(U+3130–U+318F)는 손글씨에 정상적으로 나타나는
독립 글자이므로 성질로만 기록한다. 둘을 한 지표로 합치면 정상 원문을 손상으로 오독하게 된다.
한자·영문·이모티콘·숫자도 마찬가지로 결함이 아니라 mixed-script 커버리지 근거다.
Manifest는 image digest가 중복된 sample을 허용하지 않으므로 freeze 시 제외하고 report에 기록한다.

## Limitations

```text
writer identity:        제공 안 됨. writer-disjoint 및 writer-generalization 주장 금지
handwriting difficulty: 제공 안 됨. 값을 만들어내지 않는다
capture quality:        제공 안 됨
near-duplicate review:  exact image digest 중복만 검사했다. crop/resize/재촬영 등
                        near-duplicate 검수는 수행하지 않았다
permission review:      license 표기를 옮겨 적었을 뿐 별도 승인 검토가 아니다
sampling:               문서화된 shard/row group subset이며 전체 split의 무작위 표본이 아니다
```

이 한계 때문에 `smoke-v1`은 final holdout이 될 수 없고 Golden으로 승격하지 않는다.

## Reproducing

```bash
./scripts/dataset validate smoke-v1
```

Pinned revision을 해석하고 `selected_rows`의 row group만 읽어 각 sample의 content ID와 image
digest를 다시 계산한 뒤 frozen manifest의 pin과 대조한다. Manual review artifact(전사 텍스트와
thumbnail 포함)는 `./scripts/dataset select`의 `--review-dir`에 쓰며 Git에 넣지 않는다.
