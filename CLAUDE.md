# CLAUDE.md

Guidance for Claude when working in this repository.

## Project overview

A Django web application with an HTMX-driven UI and a REST API, organized as one Django app, `unicap/app/`, with project wiring in `unicap/unicap/` and the business rules in `unicap/domain/`. `unicap/` is the Django root (`BASE_DIR`); `manage.py` and the tooling configs stay at the repository root.

- UI: server-rendered Django templates + django-cotton components, HTMX for partial updates, Alpine.js for small client-side state.
- API: Django REST Framework with JWT auth (simplejwt) plus session auth.
- Business rules: live in an **independent domain package** (pure Python, framework-free). Django is the delivery and persistence layer only.

## Tech stack

### Backend

| Area | Tool |
| --- | --- |
| Language | Python 3.13 (`.python-version`, `requires-python = ">=3.13"`). Use modern syntax: `X \| Y` unions, `match`, PEP 695 generics (`class X[T]`, `def f[T]`), `type` statements, `typing.Self`, `enum.StrEnum` |
| Framework | Django 5.2 |
| Database | MySQL (`mysqlclient`, `sql_mode=traditional`); SQLite in-memory for tests |
| Config | `python-decouple` (`config("DB_NAME")` etc.), settings split into `unicap/unicap/settings/{base,development,testing,deployment}.py` |
| API | `djangorestframework`, `djangorestframework-simplejwt`, `django-cors-headers` |
| Filtering / search | `django-filter`, `djangoql` (custom `DjangoQLSearchFilter` backend) |
| Import / export | `django-import-export[xlsx]` (resources per model), `docxtpl` for MS Word templates |
| UI helpers | `django-cotton` (components in `components/`), `django-htmx`, `django-widget-tweaks`, `heroicons[django]`, `django-vite` |
| Misc | `django-solo` (singleton settings models), `django-cleanup`, `django-braces`, `django-extensions`, `pillow`, `puremagic` (file type validation) |
| i18n | English + Arabic (`LANGUAGES = (("en", ...), ("ar", ...))`), all user-facing strings wrapped in `gettext_lazy as _`; translations in `unicap/locale/` |

### Frontend

- Vite 6 (`vite.config.mjs`, entry `unicap/assets/js/index.js`, output to `unicap/static/dist/` with `manifest.json`; django-vite reads it via `static_url_prefix: "dist"`, templates load `{% vite_asset 'unicap/assets/js/index.js' %}`)
- Tailwind CSS (+ `@tailwindcss/container-queries`, `tailwind-scrollbar`)
- HTMX 2
- Alpine.js 3 (+ `collapse`, `focus`, `mask`, `persist`, `sort`, `alpine-autosize`)

### Tooling

- Package management: `uv` (`uv.lock`, `pyproject.toml` with `[dependency-groups] dev`); npm for JS
- Tasks: `nox` (`noxfile.py` → `build` session: `npm run build`, compiles `requirements.txt`, freezes `dev-requirements.txt`, cleans caches)
- Tests: `pytest`, `pytest-django`, `pytest-cov`, `pytest-mock`, `pytest-order`, `factory-boy`, `selectolax` (HTML assertions), `playwright` (e2e, marked `slow`)
- Profiling: `django-silk` (mounted at `/silk/` only when `DEBUG`)
- Lint/format: Ruff (`select = ["ALL"]` style, line length 100) — see Coding style

### Commands

```bash
uv sync                                 # install python deps
npm install && npm run dev              # vite dev server
uv run manage.py runserver
uv run pytest                                  # fast tests (slow are deselected by default)
uv run pytest -m slow                          # e2e / playwright
uv run pytest --cov=unicap --cov-report=html
nox -s build                            # production build + requirements export
uv run manage.py makemessages -l ar && uv run manage.py compilemessages
```

## Architecture

```
manage.py  pyproject.toml  package.json  vite.config.mjs  tailwind.config.js
unicap/                  # Django root (BASE_DIR)
  unicap/                # project: settings/  urls.py  wsgi.py  asgi.py  constants.py
  domain/                # independent, framework-free business logic (provided separately)
  app/                   # the single Django app, label "app" (perms "app.view_employee", FKs "app.Chapter")
    models/              # one module per model (chapter.py, faculty.py, ...), re-exported in __init__.py
    querysets/           # one QuerySet per model: all ORM query implementation; base.py = shared mixins
    managers/            # one Manager per model: public query API, injected into models; base.py = shared
    constants/           # ORDERING_FIELDS, SEARCH_FIELDS, Literal types for select/prefetch fields
    views/               # functional views, one module per resource (plural name: employees.py); crud.py
    urls/                # one module per resource / area, aggregated in urls/__init__.py as `patterns`
    forms/  filters/  resources/   # one module per model; base.py = shared
    templatetags/  management/  migrations/  admin.py  middlewares.py  decorators.py  choices.py
  templates/
    app/<area>/...       # pages (board, chapters, crud)
    components/<area>/...  # cotton components & partials (layout, board, chapters, edu, hr)
  assets/                # JS / CSS sources (Vite)
  static/                # static files; dist/ = Vite build output
  locale/
tests/<area>/<resource>/ # factories (factory-boy), test modules
```

### Layer rules (strict)

Dependencies point inward only: **templates → views → managers/querysets → domain**. The domain package never imports Django.

#### 1. Domain package — the single source of business logic

- Every business rule, calculation, policy, validation rule and eligibility check comes from the domain package I provide. Do **not** invent or duplicate business rules inside `unicap/app/`.
- The domain package is pure Python: dataclasses / typed value objects, pure functions, and composable specifications (pyspecification-style `Predicate`s combined with `&`, `|`, `~`).
- If a needed rule is missing from the domain package, stop and ask — don't hard-code it in Django.

#### 2. QuerySets — the implementation of domain rules against the database

- Everything that reads or aggregates data is implemented as Django ORM on a custom `QuerySet` (`annotate`, `filter`, `Q`, `F`, `Case/When`, `Subquery`, `Window`, `GeneratedField`, db functions in `unicap/app/utils/`).
- Translate domain specifications to ORM expressions: domain predicates for querying use `operator="bitwise"` so they compose into `Q` objects (`Q & Q`, `Q | Q`, `~Q`) and push filtering to the database instead of Python loops.
- QuerySet methods are chainable and return the QuerySet type (`-> "EmployeeQuerySet"`, or `Self` from `typing`). Name them by intent: `annotate_*`, `get_*`, `with_*`, `for_*`.
- Constrain `select_related`/`prefetch_related` with `Literal` types from `constants/<model>.py` (`SELECT_RELATED_FIELDS`, `PREFETCH_RELATED_LOOKUPS`).
- Shared behaviour goes into generic mixins in `unicap/app/querysets/base.py` (e.g. `JournalsTotalsQuerysetMixin[QS]`).

#### 3. Managers — the public API, injected into models

- Each model gets its own manager in `managers/<model>.py`; the manager exposes the queryset's methods and sets the default `get_queryset()` (base annotations, default `select_related`).
- Prefer `class EmployeeManager(BaseManager.from_queryset(EmployeeQuerySet))` over hand-written delegation methods unless you need a different signature/defaults.
- Write operations that span multiple rows/models (create-with-relations, bulk updates, state transitions) are manager methods wrapped in `transaction.atomic()`, validating with domain rules first.
- Inject into the model: `objects = EmployeeManager()`. Models hold fields, `Meta`, constraints, choices and URL helpers only — no business logic, no query logic.

#### 4. Views — functional, thin, no business logic

- **Function-based views only** (`def employees_list(request: HttpRequest) -> HttpResponse`). No class-based views for new code; DRF endpoints use `@api_view` functions.
- Protect with decorators: `@login_required`, `@permission_required("hr.view_employee", raise_exception=True)`, `@require_http_methods([...])`.
- A view only: parses input (form / filter / serializer), calls **one** manager or domain entry point, chooses a template/status, and returns a response (including HTMX headers such as `HX-Trigger`, `HX-Redirect`, `HX-Retarget`, `HX-Reswap`).
- No `if`-based business decisions, calculations, or raw ORM chains in views — call a named manager method (`Employee.objects.get_upcoming_birthdays(this="month")`).
- Detect HTMX with `request.htmx` (django-htmx) to return a partial vs full page.
- URLs: `path(route=..., view=views.list_employees, name="index", kwargs={"title": _("employees")})`, namespaced per app.

#### 5. Templates / frontend — presentation only

- Templates render already-computed values; no business decisions, no calculations, no calling model methods that hit the database. If a template needs a value, annotate it in the queryset or pass it from the view.
- Build UI from cotton components (`<c-...>`) in `unicap/templates/components/`; use `widget_tweaks` for form rendering and `heroicons` for icons.
- HTMX handles server interaction; Alpine.js handles purely visual state (open/close, masks, sorting UI). No business rules in JS.
- Tailwind utility classes only; entry point `unicap/assets/js/index.js` / `unicap/assets/css/main.css`. Reference assets via `django-vite` tags.
- Every visible string is translatable (`{% translate %}` / `_()`), and layouts must work in RTL (Arabic).

## Coding style (from pyspecification)

- **Typing everywhere, Python 3.13 syntax.** Annotate every parameter and return value, with PEP 695 syntax as in pyspecification:
  - Generics: `class Predicate[T, R: ReturnType]`, not `TypeVar` + `Generic[T, R]`.
  - Generic functions: `def object_rule[T, R, **P](...)` with `Concatenate` (from `typing`), not module-level `TypeVar`/`ParamSpec`.
  - Type aliases: `type RulesDict = dict[str, Callable[..., Predicate[Any, Any]]]`, not `TypeAlias`.
  - `Self`, `override`, `Unpack` for kwargs come from `typing`, not `typing_extensions`.
  - Use built-in generics (`list[int]`, `dict[str, Any]`) and `X | None` unions.
  - `Protocol` for structural types, `Literal` for closed option sets, `collections.abc` imports (`Callable`, `Mapping`, `Iterable`, `Generator`).
  - Add `from __future__ import annotations` only where forward references need it; avoid it in Django model modules, where it can break some field/annotation introspection.
- **Functional first.** Small pure functions, first-class callables, decorators and factories over deep class hierarchies. Compose behaviour (`rule_a & rule_b`) instead of nesting `if`s.
- **Keyword-only / positional-only markers** for clarity: `def __init__(self, fn, /, *, operator: OperatorType, name: str | None = None)`.
- **Private helpers** prefixed with `_` and placed after the public functions in a module.
- **Early returns & guard clauses**; use walrus for check-and-use (`if unknown := sorted(...): raise ...`); `match` for dispatch over kinds.
- **Errors:** a package base exception (`class DomainError(Exception)`) with specific subclasses carrying a clear message built in `__init__`. Build the message in a `msg` variable, then `raise XError(msg)`; chain with `raise ... from error`. Messages name the offending value and list valid alternatives.
- **Docstrings:** Google style (`Args:`, `Raises:`, `Example:`) with a runnable example block (doctest `>>>` or fenced `python`). One-line summary first.
- **Explicit public API:** each package `__init__.py` re-exports its public names and defines a sorted `__all__`.
- **Naming:** `snake_case` functions, `PascalCase` classes, `UPPER_CASE` constants; rule/filter functions use Django-lookup style names (`age__between`, `name__istartswith`).
- **Imports:** stdlib → third-party → local, absolute for the project and domain (`from unicap.domain import ...`; `from unicap.app.models import ...` from outside the app), relative within the app (`from ..querysets import EmployeeQuerySet`).
- **Ruff** with `select = ["ALL"]`, `target-version = "py313"`, line length 100 (the `UP` rules then enforce the modern syntax above). Silence rules narrowly with `# noqa: CODE` on the line, or `# ruff: noqa: CODE` at file top when justified — never blanket `noqa`.
- **Trailing commas** in multi-line calls/literals so formatting stays one-item-per-line.

## Testing

- `pytest` + `pytest-django`; settings `unicap.unicap.settings.testing` (in-memory SQLite, MD5 hasher).
- Test layout mirrors the app's areas: `tests/<area>/<resource>/`, factories in `_conftest/factories.py` using `factory.django.DjangoModelFactory`.
- Domain package: pure unit tests, no DB, heavy `@pytest.mark.parametrize` (see pyspecification tests).
- QuerySets/managers: test each method against factory data with `@pytest.mark.django_db`.
- Views: test status codes, permissions, HTMX headers and rendered HTML (`selectolax`), not business outcomes — those are covered by domain and manager tests.
- Type-annotate tests and fixtures (`-> None`); mark slow/e2e tests with `@pytest.mark.slow`.

## Do / Don't

- ✅ Add a rule → domain package; expose it to Django → queryset method; publish it → manager method; use it → one call in a function view.
- ✅ Keep migrations generated by `makemigrations`; never hand-edit applied migrations.
- ❌ Business logic in views, templates, serializers, forms, signals, admin or JS.
- ❌ Raw SQL or Python-side filtering of querysets when the ORM can do it.
- ❌ Class-based views in new code.
- ❌ Untyped functions or bare `except:`.
- ❌ Pre-3.12 typing idioms (`TypeVar` + `Generic`, `TypeAlias`, `typing_extensions` for names `typing` has) — the project runs on 3.13.
