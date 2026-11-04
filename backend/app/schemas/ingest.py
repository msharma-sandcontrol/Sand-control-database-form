"""Pydantic models for the record-submission payload.

The shape is inherently Category -> Subcategory -> Parameter -> value --
exactly what the form's own "Export as JSON" button produces -- so it's
modeled as generic nested dicts rather than ~150 named fields.
db/mapping.py's field_registry-driven flatten_bucket() is what actually
knows what a valid bucket looks like (see schemas/validation.py).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from backend.app.schemas.validation import validate_bucket
from db.mapping import LEVEL_LIMITS, parent_answers
from dictionary import CURRENT_SCHEMA_VERSION
from dictionary.structure import LEVELS, MULTILATERAL_PARAMETER

Bucket = dict[str, dict[str, dict[str, Any]]]
CommentBucket = dict[str, dict[str, dict[str, str]]]
LIMITS = LEVEL_LIMITS


class CompletionIntervalComments(BaseModel):
    fields: CommentBucket = Field(default_factory=dict)
    sand_bodies: list[CommentBucket] = Field(default_factory=list)


class LateralComments(BaseModel):
    fields: CommentBucket = Field(default_factory=dict)
    completion_intervals: list[CompletionIntervalComments] = Field(default_factory=list)


class RecordComments(BaseModel):
    well: CommentBucket = Field(default_factory=dict)
    laterals: list[LateralComments] = Field(default_factory=list)


class CompletionIntervalIngest(BaseModel):
    fields: Bucket = Field(default_factory=dict)
    sand_bodies: list[Bucket] = Field(min_length=1, max_length=LIMITS["sand_body"])

    @field_validator("fields")
    @classmethod
    def _validate_fields(cls, v: Bucket) -> Bucket:
        return validate_bucket(v, scope="completion_interval")


class LateralIngest(BaseModel):
    fields: Bucket = Field(default_factory=dict)
    completion_intervals: list[CompletionIntervalIngest] = Field(
        min_length=1, max_length=LIMITS["completion_interval"])

    @field_validator("fields")
    @classmethod
    def _validate_fields(cls, v: Bucket) -> Bucket:
        return validate_bucket(v, scope="lateral")


def _count(bucket: Bucket, scope: str, parameter: str) -> int | None:
    """A counter's visible answer as an int (already validated as a whole
    number by its own bucket), or None if it is hidden or blank."""
    value = parent_answers(bucket, scope).get(parameter)
    try:
        return None if value in (None, "") else int(str(value))
    except ValueError:
        return None


class RecordIngest(BaseModel):
    schema_version: int = Field(strict=True)
    generated_at: datetime | None = None
    record_status: Literal["draft", "complete"] | None = None
    well: Bucket = Field(default_factory=dict)
    laterals: list[LateralIngest] = Field(min_length=1, max_length=LIMITS["lateral"])
    comments: RecordComments | None = None

    @field_validator("schema_version")
    @classmethod
    def _supported_schema_version(cls, value: int) -> int:
        if value != CURRENT_SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema version {value}; expected {CURRENT_SCHEMA_VERSION}")
        return value

    @field_validator("well")
    @classmethod
    def _validate_well(cls, v: Bucket) -> Bucket:
        return validate_bucket(v, scope="well")

    @field_validator("laterals")
    @classmethod
    def _validate_sand_bodies(cls, v: list[LateralIngest], info: ValidationInfo) -> list[LateralIngest]:
        # Sand Bodies are validated here rather than on CompletionIntervalIngest
        # because a blank Fluid Type falls back to the well's Well type for
        # liquid/gas units, and only this level can see the well. `well` is
        # declared first, so info.data holds it once it has validated; if it
        # failed, the request fails anyway and no fallback is applied.
        well = info.data.get("well")
        inherited = parent_answers(well, "well") if well is not None else {}
        errors = []
        for i, lateral in enumerate(v, start=1):
            for j, interval in enumerate(lateral.completion_intervals, start=1):
                for k, sand_body in enumerate(interval.sand_bodies, start=1):
                    try:
                        validate_bucket(sand_body, scope="sand_body", inherited=inherited)
                    except ValueError as exc:
                        errors.append(f"Lateral {i}, Completion Interval {j}, Sand Body {k}: {exc}")
        if errors:
            raise ValueError("; ".join(errors))
        return v

    @model_validator(mode="after")
    def _validate_counts(self) -> "RecordIngest":
        # The form's Apply buttons keep every counter equal to its number of
        # blocks, so a disagreement means a hand-edited or partial record.
        # Reject it rather than guess which side is right.
        errors = []
        if parent_answers(self.well, "well").get(MULTILATERAL_PARAMETER) == "Yes":
            stated = _count(self.well, "well", LEVELS[0].counter)
            if stated is not None and stated != len(self.laterals):
                errors.append(f"{LEVELS[0].counter} is {stated} but {len(self.laterals)} laterals were sent")
        elif len(self.laterals) != 1:
            errors.append(f"A well that is not multilateral has exactly one lateral, not {len(self.laterals)}")
        for i, lateral in enumerate(self.laterals, start=1):
            stated = _count(lateral.fields, "lateral", LEVELS[1].counter)
            if stated is not None and stated != len(lateral.completion_intervals):
                errors.append(f"Lateral {i}: {LEVELS[1].counter} is {stated} but "
                              f"{len(lateral.completion_intervals)} were sent")
            for j, interval in enumerate(lateral.completion_intervals, start=1):
                stated = _count(interval.fields, "completion_interval", LEVELS[2].counter)
                if stated is not None and stated != len(interval.sand_bodies):
                    errors.append(f"Lateral {i}, Completion Interval {j}: {LEVELS[2].counter} is {stated} "
                                  f"but {len(interval.sand_bodies)} were sent")
        if errors:
            raise ValueError("; ".join(errors))
        return self

    @model_validator(mode="after")
    def _validate_comment_layout(self) -> "RecordIngest":
        # The static form saves incomplete files locally, but this endpoint
        # creates submitted records. An explicit draft marker is therefore a
        # useful final guard even when a particular draft happens to contain
        # enough required values to pass field validation.
        if self.record_status == "draft":
            raise ValueError("Draft files cannot be submitted as completed records")
        if self.comments is None:
            return self
        if len(self.comments.laterals) != len(self.laterals):
            raise ValueError("Comment groups must match laterals")
        for lateral, lateral_notes in zip(self.laterals, self.comments.laterals):
            if len(lateral_notes.completion_intervals) != len(lateral.completion_intervals):
                raise ValueError("Comment groups must match completion intervals")
            for interval, notes in zip(lateral.completion_intervals, lateral_notes.completion_intervals):
                if len(notes.sand_bodies) != len(interval.sand_bodies):
                    raise ValueError("Comment groups must match sand bodies")
        return self


class RecordCreated(BaseModel):
    id: int
