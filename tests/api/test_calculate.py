"""The calculation API: capacity from numbers only, for a session or a JWT."""

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse

from unicap.app.models import Chapter, User

URL = "/api/capacity/calculate/"


def payload(**changes: Any) -> dict[str, Any]:
    dentistry = {
        "name": "Dentistry",
        "students_per_phd": 10,
        "current_students": 50,
        "specializations": [
            {
                "name": "Dentistry",
                "type": "specialized",
                "fulltime_staff": 3,
                "parttime": 5,
                "masters": 3,
            },
            {"name": "Biology", "type": "supported", "fulltime_staff": 1},
        ],
    }

    return {"faculties": [dentistry], **changes}


def post(client: Client, data: dict[str, Any], **headers: str) -> Any:
    return client.post(URL, data, content_type="application/json", **headers)


def test_the_url() -> None:
    assert reverse("api:calculate") == URL


@pytest.mark.django_db
def test_anonymous_is_refused(client: Client) -> None:
    assert post(client, payload()).status_code in (401, 403)


@pytest.mark.django_db
def test_counts_then_calculates(admin_client: Client) -> None:
    response = post(admin_client, payload())

    assert response.status_code == 200

    data = response.json()
    dentistry = data["faculties"][0]

    # 3 FT + 3 PT (parttime up to the fulltime) + 1 supported FT, 3 masters = 1 PhD: 8 PhDs
    assert dentistry["phd_equivalents"] == 8
    assert data["capacity"] == 80
    assert dentistry["specializations"][0]["counted"] == {
        "fulltime_staff": 3,
        "fulltime_borrowed": 0,
        "parttime": 3,
        "masters": 3,
    }
    assert dentistry["specializations"][0]["signed"]["parttime"] == 5
    assert dentistry["free_seats"] == 30


@pytest.mark.django_db
def test_counted_numbers_are_only_calculated(admin_client: Client) -> None:
    data = post(admin_client, payload(count=False)).json()

    assert data["faculties"][0]["phd_equivalents"] == 10  # all 9 PhDs, 3 masters = 1 PhD


@pytest.mark.django_db
def test_the_masters_settings_apply(admin_client: Client) -> None:
    data = payload()
    data["faculties"][0]["specializations"][0]["masters_per_phd"] = 1
    data = post(admin_client, data).json()

    assert data["faculties"][0]["phd_equivalents"] == 10


@pytest.mark.django_db
def test_the_chapter_max_caps_it(admin_client: Client) -> None:
    assert post(admin_client, payload(max_students=25)).json()["capacity"] == 25


@pytest.mark.django_db
def test_violations_are_listed(admin_client: Client) -> None:
    data = payload()
    data["faculties"][0]["current_students"] = 200

    faculty = post(admin_client, data).json()["faculties"][0]

    assert not faculty["is_compliant"]
    assert "current_students_over_capacity" in [v["kind"] for v in faculty["violations"]]


@pytest.mark.django_db
def test_a_broken_shape_is_a_400(admin_client: Client) -> None:
    response = post(admin_client, {"faculties": [{"name": "X"}]})

    assert response.status_code == 400
    assert "students_per_phd" in str(response.json()["faculties"])


@pytest.mark.django_db
def test_a_broken_domain_rule_is_a_400(admin_client: Client) -> None:
    data = payload()
    data["faculties"][0]["specializations"][0] |= {"min_teachers": 5, "max_teachers": 2}

    response = post(admin_client, data)

    assert response.status_code == 400
    assert response.json()["code"] == "teachers_min_above_max"


@pytest.mark.django_db
def test_a_jwt_works_without_a_session(client: Client, admin_user: User) -> None:
    tokens = client.post(
        reverse("api:token"),
        {"username": "admin", "password": "password"},
        content_type="application/json",
    ).json()

    response = post(client, payload(), HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    assert response.status_code == 200


@pytest.mark.django_db
def test_no_chapter_is_read_or_written(admin_client: Client, chapter: Chapter) -> None:
    before = Chapter.objects.count(), chapter.contracts.count()

    post(admin_client, payload())

    assert (Chapter.objects.count(), chapter.contracts.count()) == before
