"""Base.metadata reflects the expected 5 tables with sane column counts and
correctly-wired foreign keys/cascades. Pure Python-object inspection --
does not need a live database.
"""
from __future__ import annotations

import db.models  # noqa: F401  (populates Base.metadata as a side effect)
from db.base import Base


def test_expected_tables_present():
    assert set(Base.metadata.tables.keys()) == {
        "organizations",
        "well",
        "well_lateral",
        "completion_interval",
        "sand_body",
    }


def test_well_has_structural_plus_dictionary_columns():
    well = Base.metadata.tables["well"]
    structural = {"id", "organization_id", "created_at", "updated_at", "submitted_at", "raw_payload"}
    assert structural.issubset(set(well.columns.keys()))
    assert len(well.columns) > len(structural) + 50


def test_foreign_keys_wired_correctly():
    well = Base.metadata.tables["well"]
    completion_interval = Base.metadata.tables["completion_interval"]
    sand_body = Base.metadata.tables["sand_body"]

    assert {fk.target_fullname for fk in well.foreign_keys} == {"organizations.id"}
    lateral = Base.metadata.tables["well_lateral"]
    assert {fk.target_fullname for fk in lateral.foreign_keys} == {"well.id"}
    assert {fk.target_fullname for fk in completion_interval.foreign_keys} == {"well_lateral.id"}
    assert {fk.target_fullname for fk in sand_body.foreign_keys} == {"completion_interval.id"}


def test_cascade_delete_on_child_foreign_keys():
    completion_interval = Base.metadata.tables["completion_interval"]
    sand_body = Base.metadata.tables["sand_body"]
    (well_fk,) = Base.metadata.tables["well_lateral"].foreign_keys
    (lateral_fk,) = completion_interval.foreign_keys
    (ci_fk,) = sand_body.foreign_keys
    assert well_fk.constraint.ondelete == "CASCADE"
    assert lateral_fk.constraint.ondelete == "CASCADE"
    assert ci_fk.constraint.ondelete == "CASCADE"


def test_ordinal_unique_constraints_present():
    completion_interval = Base.metadata.tables["completion_interval"]
    sand_body = Base.metadata.tables["sand_body"]
    assert any(
        {c.name for c in uc.columns} == {"lateral_id", "ordinal"} for uc in completion_interval.constraints
    )
    assert any(
        {c.name for c in uc.columns} == {"well_id", "ordinal"}
        for uc in Base.metadata.tables["well_lateral"].constraints
    )
    assert any(
        {c.name for c in uc.columns} == {"completion_interval_id", "ordinal"} for uc in sand_body.constraints
    )


def test_relationships_configure_without_error():
    from sqlalchemy.orm import configure_mappers

    configure_mappers()
