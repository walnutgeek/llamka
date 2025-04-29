import pytest

from llamka.llore.state_db import Source, TypeInfo, VectorizationAttempt, create_ddl_from_model


@pytest.mark.debug
def test_type_info():
    assert TypeInfo.from_field_info(VectorizationAttempt.model_fields["timestamp"]) == (
        False,
        TypeInfo.get("datetime"),
    )


@pytest.mark.debug
def test_dll():
    assert (
        create_ddl_from_model(VectorizationAttempt)
        == "CREATE TABLE VectorizationAttempt (attempt_id INTEGER, source_id INTEGER, timestamp TEXT, n_chunks INTEGER, error TEXT NULL, sha256 TEXT)"
    )
    assert (
        create_ddl_from_model(Source)
        == "CREATE TABLE Source (source_id INTEGER, absolute_path TEXT)"
    )
