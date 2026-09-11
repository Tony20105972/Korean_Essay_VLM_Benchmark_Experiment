"""Executable contract v1; behavioral policy owners are linked in docs/index.md."""

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

ID = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Count = Annotated[int, Field(ge=0)]
Number = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class Contract(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class ArtifactReference(Contract):
    artifact_id: ID
    version: ID


class Provenance(Contract):
    producer: ID
    producer_version: ID
    upstream: tuple[ArtifactReference, ...]
    notes: tuple[ID, ...] = ()


class ImageReference(Contract):
    artifact_id: ID
    uri: ID
    sha256: Digest
    page_id: ID


class Source(Contract):
    provider: ID
    source_type: Literal["external", "domain", "synthetic"]
    dataset_identifier: ID
    revision: ID | None
    split: ID | None
    original_sample_id: ID | None
    identity_method: Literal["upstream-id", "content-digest"]

    @model_validator(mode="after")
    def identity(self) -> Self:
        if self.identity_method == "upstream-id" and self.original_sample_id is None:
            raise ValueError("upstream-id requires original_sample_id; row offsets are not IDs")
        return self


class Span(Contract):
    start: Count
    end: Count

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("span must be nonempty [start,end) in Unicode code points")
        return self


class Region(Contract):
    region_id: ID
    image_artifact_id: ID
    # Normalized coordinates permit images without known pixel dimensions.
    x: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    y: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    width: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]
    height: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]
    coordinate_system: Literal["normalized-top-left"]

    @model_validator(mode="after")
    def bounds(self) -> Self:
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("region extends beyond image")
        return self


class UncertainSpan(Contract):
    span: Span | None
    region: Region
    kind: Literal["character", "layout", "order"]
    status: Literal["uncertain", "conflicting"]
    candidates: tuple[ID, ...] | None
    visual_evidence: ID | None

    @model_validator(mode="after")
    def evidence(self) -> Self:
        if self.candidates is not None and (not self.candidates or not self.visual_evidence):
            raise ValueError("candidates require visual evidence; unknown candidates use null")
        if self.status == "conflicting" and (
            self.candidates is None or len(set(self.candidates)) < 2
        ):
            raise ValueError("conflict requires at least two distinct supported candidates")
        return self


class UnreadableRegion(Contract):
    region: Region
    reason: ID


class Metadata(Contract):
    writer_id: ID | None = None
    capture_quality: Literal["good", "degraded", "unknown"] = "unknown"
    handwriting_difficulty: Literal["easy", "medium", "hard", "extreme", "unknown"] = "unknown"
    script_properties: tuple[ID, ...] | None = None
    content_properties: tuple[ID, ...] | None = None


class Eligibility(Contract):
    text_eligible: bool
    reason: ID | None

    @model_validator(mode="after")
    def exclusion(self) -> Self:
        if self.text_eligible == (self.reason is not None):
            raise ValueError("eligible requires null reason; ineligible requires reason")
        return self


class GroundTruth(Contract):
    transcription: str | None
    revision: ID
    eligibility: Eligibility

    @model_validator(mode="after")
    def text(self) -> Self:
        if self.eligibility.text_eligible and self.transcription is None:
            raise ValueError("eligible GT requires text; empty string is valid")
        if self.transcription is not None and "\r" in self.transcription:
            raise ValueError("GT serialization requires LF; adapter must version conversion")
        return self


class NonStandardText(Contract):
    opportunity_id: ID
    span: Span
    region: Region
    observed_text: ID
    error_type: ID
    standardized_candidates: tuple[ID, ...]
    correction_reason: ID


class Annotations(Contract):
    revision: ID
    uncertain_regions: tuple[UncertainSpan, ...] = ()
    unreadable_regions: tuple[UnreadableRegion, ...] = ()
    intentionally_non_standard_text: tuple[NonStandardText, ...] = ()


def check_span(span: Span | None, text: str) -> None:
    if span is not None and span.end > len(text):
        raise ValueError("span exceeds unnormalized Unicode code-point length")


def unique(values: tuple[str, ...], name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {name}")


class CanonicalDatasetSample(Contract):
    schema_version: Literal["dataset-sample/v1"]
    sample_id: ID
    source: Source
    input: ImageReference
    ground_truth: GroundTruth
    metadata: Metadata | None = None
    annotations: Annotations | None = None
    provenance: Provenance

    @model_validator(mode="after")
    def linkage(self) -> Self:
        if not self.provenance.upstream:
            raise ValueError("dataset provenance requires upstream reference")
        if (
            self.source.source_type == "external"
            and (self.metadata is None or self.metadata.writer_id is None)
            and "writer-disjoint guarantee unavailable" not in self.provenance.notes
        ):
            raise ValueError("unknown external writer requires explicit provenance limitation")
        if self.annotations:
            text = self.ground_truth.transcription or ""
            regions = [u.region for u in self.annotations.uncertain_regions]
            regions += [u.region for u in self.annotations.unreadable_regions]
            regions += [u.region for u in self.annotations.intentionally_non_standard_text]
            if any(r.image_artifact_id != self.input.artifact_id for r in regions):
                raise ValueError("annotation region must refer to input source image")
            for uncertainty in self.annotations.uncertain_regions:
                check_span(uncertainty.span, text)
            opportunities = self.annotations.intentionally_non_standard_text
            unique(tuple(o.opportunity_id for o in opportunities), "opportunity ID")
            previous_end = 0
            for opportunity in sorted(opportunities, key=lambda o: o.span.start):
                check_span(opportunity.span, text)
                if not self.ground_truth.eligibility.text_eligible:
                    raise ValueError("correction opportunities require eligible GT")
                if opportunity.span.start < previous_end:
                    raise ValueError("correction opportunities overlap")
                if text[opportunity.span.start : opportunity.span.end] != opportunity.observed_text:
                    raise ValueError("opportunity must preserve exact GT text")
                previous_end = opportunity.span.end
        return self


class ManifestSample(Contract):
    sample_id: ID
    image: ImageReference
    gt_revision: ID
    annotation_revision: ID | None
    writer_id: ID | None
    eligibility: Eligibility
    sample_reference: ArtifactReference


class SelectionMetadata(Contract):
    method: ID
    seed: int | None
    rationale: ID
    selected_at: ID
    change_reason: ID
    lineage: tuple[ArtifactReference, ...]
    exposure_history: tuple[ID, ...] | None
    permission_reference: ID | None
    integrity_review_reference: ID | None
    writer_disjoint: Literal["verified", "unavailable", "not-checked"]

    @model_validator(mode="after")
    def timestamp(self) -> Self:
        timestamp = datetime.fromisoformat(self.selected_at)
        if timestamp.utcoffset() is None:
            raise ValueError("selection timestamp requires timezone")
        return self


class DatasetManifest(Contract):
    schema_version: Literal["dataset-manifest/v1"]
    manifest_id: ID
    manifest_version: ID
    dataset_identifier: ID
    dataset_revision: ID
    split: ID
    source_origin: Literal["external", "domain", "synthetic"]
    tier: Literal["G0", "G1", "G2", "G3"]
    role: Literal["training", "development", "benchmark", "final-holdout"]
    golden: bool
    selected_samples: tuple[ManifestSample, ...]
    selection_metadata: SelectionMetadata
    provenance: Provenance

    @model_validator(mode="after")
    def frozen_selection(self) -> Self:
        if self.dataset_revision.lower() in {"unknown", "main", "master", "latest"}:
            raise ValueError("manifest requires immutable upstream revision")
        unique(tuple(s.sample_id for s in self.selected_samples), "sample ID")
        unique(tuple(s.image.sha256 for s in self.selected_samples), "image digest")
        unique(tuple(s.image.artifact_id for s in self.selected_samples), "image artifact ID")
        if self.golden and self.role == "training":
            raise ValueError("Golden cannot train weights")
        selection = self.selection_metadata
        if self.role == "final-holdout":
            if selection.exposure_history != ():
                raise ValueError("holdout requires known empty development exposure history")
            if not selection.permission_reference or not selection.integrity_review_reference:
                raise ValueError("holdout requires permission and integrity review evidence")
            if self.source_origin == "domain" and (
                selection.writer_disjoint != "verified"
                or any(s.writer_id is None for s in self.selected_samples)
            ):
                raise ValueError("domain holdout requires verified writer identities")
        if selection.writer_disjoint == "verified" and (
            any(s.writer_id is None for s in self.selected_samples)
            or not selection.integrity_review_reference
        ):
            raise ValueError("writer-disjoint claim requires identities and evidence")
        if not self.provenance.upstream:
            raise ValueError("manifest requires upstream provenance")
        return self

    def validate_samples(self, samples: tuple[CanonicalDatasetSample, ...]) -> None:
        """Validate a materialized subset against frozen pins, without downloading it."""
        unique(tuple(s.sample_id for s in samples), "materialized sample ID")
        actual = {s.sample_id: s for s in samples}
        if set(actual) != {s.sample_id for s in self.selected_samples}:
            raise ValueError("materialized subset differs from manifest")
        for pin in self.selected_samples:
            sample = actual[pin.sample_id]
            if (
                sample.source.dataset_identifier != self.dataset_identifier
                or sample.source.revision != self.dataset_revision
                or sample.source.split != self.split
                or sample.source.source_type != self.source_origin
                or sample.input != pin.image
                or sample.ground_truth.revision != pin.gt_revision
                or sample.ground_truth.eligibility != pin.eligibility
                or (sample.annotations.revision if sample.annotations else None)
                != pin.annotation_revision
                or (sample.metadata.writer_id if sample.metadata else None) != pin.writer_id
            ):
                raise ValueError("sample does not match frozen manifest pins")


class SourceReference(Contract):
    original: ImageReference
    input_artifact_id: ID
    derived_reference: ArtifactReference | None
    coordinate_mapping_reference: ArtifactReference | None

    @model_validator(mode="after")
    def derived(self) -> Self:
        is_derived = self.input_artifact_id != self.original.artifact_id
        if is_derived:
            if (
                self.derived_reference is None
                or self.coordinate_mapping_reference is None
                or self.derived_reference.artifact_id != self.input_artifact_id
            ):
                raise ValueError("derived input requires artifact and original coordinate mapping")
        elif self.derived_reference is not None or self.coordinate_mapping_reference is not None:
            raise ValueError("original input cannot claim derived mapping")
        return self


class TextRegion(Contract):
    region: Region
    span: Span


class OrderRelation(Contract):
    before: ID
    after: ID


class PerceptionProvenance(Provenance):
    run_id: ID
    parser_version: ID
    attempt_records_reference: ArtifactReference
    raw_response_ref: ArtifactReference | None
    raw_response_absence_reason: ID | None

    @model_validator(mode="after")
    def raw_response(self) -> Self:
        if (self.raw_response_ref is None) != (self.raw_response_absence_reason is not None):
            raise ValueError("absent raw response requires reason, present response forbids reason")
        if not self.upstream:
            raise ValueError("perception requires upstream run/input provenance")
        return self


class CanonicalPerceptionResult(Contract):
    schema_version: Literal["perception-result/v1"]
    result_id: ID
    result_version: ID
    sample_id: ID
    transcription: str
    text_regions: tuple[TextRegion, ...]
    reading_order: tuple[OrderRelation, ...]
    uncertain_spans: tuple[UncertainSpan, ...]
    unreadable_regions: tuple[UnreadableRegion, ...]
    perception_status: Literal["confirmed", "uncertain", "unreadable"]
    source_reference: SourceReference
    provenance: PerceptionProvenance

    @model_validator(mode="after")
    def outcomes(self) -> Self:
        expected = "uncertain" if self.uncertain_spans or self.unreadable_regions else "confirmed"
        if self.unreadable_regions and not self.transcription and not self.uncertain_spans:
            expected = "unreadable"
        if self.perception_status != expected:
            raise ValueError("page status must preserve local uncertainty/unreadable outcomes")
        regions = [t.region for t in self.text_regions]
        regions += [u.region for u in self.uncertain_spans]
        regions += [u.region for u in self.unreadable_regions]
        if any(r.image_artifact_id != self.source_reference.input_artifact_id for r in regions):
            raise ValueError("region must reference actual input coordinate system")
        definitions: dict[str, Region] = {}
        for region in regions:
            if region.region_id in definitions and definitions[region.region_id] != region:
                raise ValueError("same region ID has conflicting coordinates")
            definitions[region.region_id] = region
        covered: set[int] = set()
        for text_region in self.text_regions:
            check_span(text_region.span, self.transcription)
            covered.update(range(text_region.span.start, text_region.span.end))
        if covered != set(range(len(self.transcription))):
            raise ValueError("every transcription code point requires a source text region")
        for uncertainty in self.uncertain_spans:
            check_span(uncertainty.span, self.transcription)
        edges: dict[str, set[str]] = {r: set() for r in definitions}
        for relation in self.reading_order:
            if relation.before not in edges or relation.after not in edges:
                raise ValueError("reading order contains unknown region")
            edges[relation.before].add(relation.after)
        # A unique topological order exists only when every removal has one choice.
        ambiguous_order = False
        reverse_order: list[str] = []
        pending = set(edges)
        while pending:
            leaves = {r for r in pending if not (edges[r] & pending)}
            if not leaves:
                raise ValueError("reading order must be acyclic")
            ambiguous_order |= len(leaves) > 1
            reverse_order.extend(sorted(leaves))
            pending -= leaves
        if ambiguous_order and not any(u.kind == "order" for u in self.uncertain_spans):
            raise ValueError("partial reading order requires explicit order uncertainty")
        if not ambiguous_order:
            positions = {region_id: i for i, region_id in enumerate(reversed(reverse_order))}
            text_order = [
                positions[t.region.region_id]
                for t in sorted(self.text_regions, key=lambda t: t.span.start)
            ]
            if text_order != sorted(text_order):
                raise ValueError("transcription contradicts confirmed reading order")
        return self


class PolicyVersions(Contract):
    metric: ID
    normalization: ID
    annotation: ID
    result_schema_version: Literal["perception-result/v1"]
    parser: ID


class BenchmarkRun(Contract):
    schema_version: Literal["benchmark-run/v1"]
    benchmark_execution_id: ID
    manifest_reference: ArtifactReference
    candidate_reference: ArtifactReference
    execution_configuration_reference: ArtifactReference
    policies: PolicyVersions
    sample_ids: tuple[ID, ...]
    provenance: Provenance

    @model_validator(mode="after")
    def sample_identity(self) -> Self:
        unique(self.sample_ids, "benchmark sample ID")
        return self


class MetricObservation(Contract):
    numerator: Number | None
    denominator: Number | None
    value: Number | None
    status: Literal["measured", "undefined", "not-measured", "provisional"]
    reason: ID | None

    @model_validator(mode="after")
    def missing(self) -> Self:
        if self.status == "measured":
            if self.value is None:
                raise ValueError("measured metric requires value")
        elif self.value is not None or self.reason is None:
            raise ValueError("unmeasured official value must be null with reason")
        return self


class BenchmarkSampleResult(Contract):
    schema_version: Literal["benchmark-sample-result/v1"]
    evaluation_id: ID
    benchmark_execution_id: ID
    sample_id: ID
    run_id: ID
    manifest_reference: ArtifactReference
    source: Source
    image: ImageReference
    gt_revision: ID
    annotation_revision: ID | None
    policies: PolicyVersions
    eligibility: Eligibility
    terminal_status: Literal["success", "failure"]
    prediction: CanonicalPerceptionResult | None
    failure_reason: ID | None
    metrics: dict[ID, MetricObservation]
    annotation_labels_reference: ArtifactReference | None
    provenance: Provenance

    @model_validator(mode="after")
    def terminal(self) -> Self:
        if self.terminal_status == "success":
            if self.prediction is None or self.failure_reason is not None:
                raise ValueError("success requires canonical prediction and no failure")
        elif self.prediction is not None or self.failure_reason is None:
            raise ValueError("failure requires absent prediction and reason")
        if self.prediction is not None and (
            self.prediction.sample_id != self.sample_id
            or self.prediction.provenance.run_id != self.run_id
            or self.prediction.source_reference.original != self.image
            or self.prediction.provenance.parser_version != self.policies.parser
        ):
            raise ValueError("prediction/sample/run/source/parser linkage mismatch")
        return self

    @property
    def metric_prediction(self) -> str:
        return self.prediction.transcription if self.prediction is not None else ""

    def validate_context(self, run: BenchmarkRun, manifest: DatasetManifest) -> None:
        """Check joined artifacts before evaluation/reporting; no metric calculation."""
        reference = ArtifactReference(
            artifact_id=manifest.manifest_id, version=manifest.manifest_version
        )
        if (
            run.manifest_reference != reference
            or self.manifest_reference != reference
            or self.benchmark_execution_id != run.benchmark_execution_id
            or self.policies != run.policies
            or run.sample_ids != tuple(s.sample_id for s in manifest.selected_samples)
        ):
            raise ValueError("benchmark context mismatch")
        pin = next((s for s in manifest.selected_samples if s.sample_id == self.sample_id), None)
        if pin is None or (
            self.image != pin.image
            or self.gt_revision != pin.gt_revision
            or self.annotation_revision != pin.annotation_revision
            or self.eligibility != pin.eligibility
            or self.source.dataset_identifier != manifest.dataset_identifier
            or self.source.revision != manifest.dataset_revision
            or self.source.split != manifest.split
            or self.source.source_type != manifest.source_origin
        ):
            raise ValueError("evaluation does not match frozen sample")
