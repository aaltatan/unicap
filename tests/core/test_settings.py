"""App and section settings, the admin panel (admins only) and the users' roles."""

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse
from pytest_mock import MockerFixture
from selectolax.parser import HTMLParser

from tests.conftest import htmx
from unicap.app.models import (
    AppSettings,
    Chapter,
    Contract,
    EmployeeSettings,
    Faculty,
    FacultySettings,
    User,
)
from unicap.app.roles import DATA_MODELS, ROLES

# --- settings -----------------------------------------------------------------------------


def test_a_section_opens_with_its_own_rows_per_page(admin_client: Client, chapter: Chapter) -> None:
    FacultySettings.objects.update_or_create(pk=1, defaults={"per_page": 10})

    response = admin_client.get(reverse("edu:faculties:index"))

    assert response.context["per_page"] == 10


def test_an_empty_section_setting_takes_the_apps(admin_client: Client, chapter: Chapter) -> None:
    AppSettings.objects.update_or_create(pk=1, defaults={"per_page": 50, "modal_size": "md"})

    index = admin_client.get(reverse("hr:employees:index"))
    employee = chapter.employees.first()
    details = admin_client.get(reverse("hr:employees:details", args=(employee.pk,)), **htmx())

    assert index.context["per_page"] == 50
    assert details.context["modal_width"] == "md"


def test_the_url_still_chooses_rows_per_page(admin_client: Client, chapter: Chapter) -> None:
    EmployeeSettings.objects.update_or_create(pk=1, defaults={"per_page": 10})

    response = admin_client.get(reverse("hr:employees:index"), {"per_page": 100})

    assert response.context["per_page"] == 100


def test_faculties_open_extra_large_by_default(admin_client: Client, chapter: Chapter) -> None:
    faculty = Faculty.objects.for_chapter(chapter.pk).first()

    details = admin_client.get(reverse("edu:faculties:details", args=(faculty.pk,)), **htmx())
    form = admin_client.get(reverse("edu:faculties:update", args=(faculty.pk,)), **htmx())

    assert details.context["modal_width"] == "xl"
    assert form.context["modal_width"] == "xl"


@pytest.mark.parametrize("resizable", [True, False])
def test_modals_are_resizable_when_the_app_says_so(
    admin_client: Client,
    chapter: Chapter,
    resizable: bool,  # noqa: FBT001
) -> None:
    AppSettings.objects.update_or_create(pk=1, defaults={"resizable_modals": resizable})
    faculty = Faculty.objects.for_chapter(chapter.pk).first()

    response = admin_client.get(reverse("edu:faculties:details", args=(faculty.pk,)), **htmx())

    card = HTMLParser(response.content).css_first(".card")
    assert ("resize" in card.attributes["class"].split()) is resizable


def test_tables_forget_their_state_when_the_app_says_so(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    AppSettings.objects.update_or_create(pk=1, defaults={"remember_table_state": False})

    html = HTMLParser(admin_client.get(reverse("edu:faculties:index")).content)

    assert html.css_first("form#filters-form[data-remember-url]") is None


def test_the_project_name_comes_from_the_settings(admin_client: Client, chapter: Chapter) -> None:
    AppSettings.objects.update_or_create(pk=1, defaults={"project_name": "Capacity Office"})

    response = admin_client.get(reverse("board:dashboard"))

    assert "Capacity Office" in HTMLParser(response.content).css_first("title").text()


# --- the admin panel ----------------------------------------------------------------------


ADMIN_PAGES = [
    "admin:index",
    "admin:app_chapter_changelist",
    "admin:app_specialization_changelist",
    "admin:app_faculty_changelist",
    "admin:app_employee_changelist",
    "admin:app_contract_changelist",
    "admin:app_reporttemplate_changelist",
    "admin:app_appsettings_change",
    "admin:app_facultysettings_change",
    "admin:auth_group_changelist",
    "admin:app_user_changelist",
]


@pytest.mark.parametrize("url_name", ADMIN_PAGES)
def test_admins_open_every_admin_page(
    admin_client: Client, chapter: Chapter, url_name: str
) -> None:
    assert admin_client.get(reverse(url_name)).status_code == 200


@pytest.mark.django_db
def test_users_cannot_open_the_admin_even_as_staff(client: Client) -> None:
    staff = User.objects.create_user("staff", password="password", is_staff=True)  # noqa: S106
    staff.groups.add(Group.objects.get(name="managers"))
    client.force_login(staff)

    response = client.get(reverse("admin:index"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("admin:login"))


def test_only_admins_see_the_admin_link(
    admin_client: Client,
    viewer_client: Client,
    chapter: Chapter,
) -> None:
    link = f"nav a[href='{reverse('admin:index')}']"

    assert HTMLParser(admin_client.get(reverse("board:dashboard")).content).css_first(link)
    assert not HTMLParser(viewer_client.get(reverse("board:dashboard")).content).css_first(link)


def test_an_admin_edit_that_breaks_a_rule_is_rolled_back(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    other = Chapter.objects.create(name="other")
    foreign = Faculty.objects.create(chapter=other, name="Elsewhere", students_per_phd=10)
    contract = Contract.objects.filter(chapter=chapter).first()

    response = admin_client.post(
        reverse("admin:app_contract_change", args=(contract.pk,)),
        {
            "chapter": chapter.pk,
            "employee": contract.employee_id,
            "faculty": foreign.pk,  # a faculty of another chapter
            "contract_type": contract.contract_type,
            "employment_type": contract.employment_type,
            "degree": contract.degree,
            "is_active": "on",
            "position": contract.position,
            "notes": "",
        },
        follow=True,
    )

    contract.refresh_from_db()
    assert contract.faculty_id != foreign.pk
    assert any(m.level_tag == "error" for m in response.context["messages"])


# --- roles --------------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(("role", "actions"), ROLES.items())
def test_each_role_holds_its_permissions(role: str, actions: tuple[str, ...]) -> None:
    group = Group.objects.get(name=role)

    codenames = set(group.permissions.values_list("codename", flat=True))

    assert codenames == {f"{action}_{model}" for action in actions for model in DATA_MODELS}


def test_a_viewer_may_look_but_not_change(client: Client, chapter: Chapter) -> None:
    user = User.objects.create_user("reader", password="password")  # noqa: S106
    user.groups.add(Group.objects.get(name="viewers"))
    client.force_login(user)

    assert client.get(reverse("edu:faculties:index")).status_code == 200
    assert client.get(reverse("edu:faculties:create"), **htmx()).status_code == 403

    faculty = Faculty.objects.for_chapter(chapter.pk).first()
    html = HTMLParser(client.get(reverse("edu:faculties:index")).content)
    assert not html.css(f"#table [hx-get='{faculty.get_update_url()}']")


@pytest.mark.parametrize(
    ("size", "width"),
    [("md", "32rem"), ("lg", "42rem"), ("xl", "56rem"), ("full", "100vw")],
)
def test_a_modal_is_drawn_as_wide_as_its_setting_says(
    admin_client: Client,
    chapter: Chapter,
    size: str,
    width: str,
) -> None:
    EmployeeSettings.objects.update_or_create(
        pk=1, defaults={"details_modal_size": size, "form_modal_size": size}
    )
    employee = chapter.employees.first()

    for url_name in ("hr:employees:details", "hr:employees:update"):
        response = admin_client.get(reverse(url_name, args=(employee.pk,)), **htmx())

        assert f"width: min({width}, calc(100vw - 1.5rem))" in response.content.decode()


def test_the_apps_modal_size_is_drawn_when_the_section_has_none(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    AppSettings.objects.update_or_create(pk=1, defaults={"modal_size": "xl"})
    employee = chapter.employees.first()

    response = admin_client.get(reverse("hr:employees:create"), **htmx())
    details = admin_client.get(reverse("hr:employees:details", args=(employee.pk,)), **htmx())

    assert "width: min(56rem," in response.content.decode()
    assert "width: min(56rem," in details.content.decode()


# --- the development settings on a server ------------------------------------------------


@pytest.mark.parametrize(
    ("installed", "apps"),
    [
        ((), []),  # a server: the production requirements alone
        (("silk",), ["silk"]),
        (("django_extensions", "silk"), ["django_extensions", "silk"]),
    ],
)
def test_development_tools_are_used_only_when_installed(
    mocker: MockerFixture, installed: tuple[str, ...], apps: list[str]
) -> None:
    """`manage.py` defaults to these settings: a missing dev package must not stop it."""
    import importlib  # noqa: PLC0415
    import importlib.util  # noqa: PLC0415

    from unicap.unicap.settings import development  # noqa: PLC0415

    mocker.patch.object(
        importlib.util, "find_spec", lambda name: name if name in installed else None
    )

    try:
        settings = importlib.reload(development)

        assert apps == settings.DEV_APPS
        assert [
            app for app in settings.INSTALLED_APPS if app in ("silk", "django_extensions")
        ] == apps
        assert ("silk.middleware.SilkyMiddleware" in settings.MIDDLEWARE) is ("silk" in installed)
    finally:
        mocker.stopall()
        importlib.reload(development)


def test_production_settings_need_no_development_package() -> None:
    from unicap.unicap.settings import base  # noqa: PLC0415

    assert not {"silk", "django_extensions"} & set(base.INSTALLED_APPS)
    assert not [name for name in base.MIDDLEWARE if "silk" in name]
