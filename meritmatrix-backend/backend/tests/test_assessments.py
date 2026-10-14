"""Assessment authorization and input validation regression tests."""
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.assessment import AssessmentCreate, MarkEntry, MarkBatch


def test_assessments_require_authentication(client):
    response = client.get(f"/api/v1/assessments?school_id={uuid4()}")
    assert response.status_code == 401


def test_assessment_creation_requires_assessment_permission(client, make_user, auth_headers, seeded_rbac):
    make_user(email="student-assessments@example.com", password="StrongPass123", role_name="STUDENT")
    headers = auth_headers("student-assessments@example.com", "StrongPass123")
    response = client.post(
        f"/api/v1/assessments?school_id={uuid4()}",
        headers=headers,
        json={
            "class_subject_id": str(uuid4()),
            "term_id": str(uuid4()),
            "title": "Test",
            "max_score": 100,
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_assessment_schema_rejects_non_positive_max_score():
    with pytest.raises(ValidationError):
        AssessmentCreate(
            class_subject_id=uuid4(),
            term_id=uuid4(),
            title="Unit test",
            max_score=0,
        )


def test_mark_schema_rejects_negative_scores():
    with pytest.raises(ValidationError):
        MarkEntry(enrollment_id=uuid4(), score=-1)


def test_marks_batch_rejects_empty_submissions():
    with pytest.raises(ValidationError):
        MarkBatch(marks=[])
