# UniCap — University Capacity Calculator

A Django web app that calculates how many students the university may take from its
teaching staff, following the ministry's counting rules. The rules live in a
framework-free domain package (`unicap/domain`); Django stores the data and shows it.

Everything belongs to a **chapter** (a term, or a scenario to try): its specializations,
faculties (with their numbers and shares), employees and contracts. Chapters never share
rows; duplicating one copies all of it.

## Features

- **Dashboard**: capacity, counted teachers, missing to targets and compliance, with
  per-faculty charts (capacity vs max / target / now, staff share vs its minimum). Drag
  widgets by their handle to reorder them (remembered per browser).
- **Board** (drag and drop, Alpine `sort`): an *Unsigned* lane and one lane per faculty.
  Cards are green when the ministry counts the contract, red when it does not, grey while
  unsigned, faded when left out of the calculation. While a card is dragged, the lane
  under it is outlined with the color it *would* get there and the hint says what the
  capacity would become (the server evaluates every possible drop). Click a card for its
  details, double-click to switch its contract on or off, drag lane headers to reorder
  lanes. Lane headers show capacity, students per PhD, staff % vs minimum and
  now · target · max; an *Issues* panel explains every violation and uncounted contract.
- **Optimizer**: pick a strategy (maximize students, fewest changes, less salaries, best
  staff percentage, ...), preview the before / after figures and every move, then apply.
  **Reset** unsigns every contract; **Duplicate chapter** copies it to try another scenario.
- **Reports** (their own sidebar section, under `/reports/`), each a page with one *export*
  menu (print, Word, PDF) and an admin-editable Word template:
  - **Capacity report**: the seven head counts (counted / signed) per faculty; its **pivot**
    shows them as one small specialized / supported by terms table per faculty.
  - **Calculation audit**: the counting rules, then every step behind each faculty's and the
    chapter's capacity, with the numbers used (`33 PhD equivalents × 20 students per PhD`)
    and the contracts not counted, each with its reason.
  - **Faculty reports**: each faculty's staff by name, or its pivot (counted by specialization).
  A PDF is the Word report converted by LibreOffice (`SOFFICE_PATH`), or by Word on Windows
  without it.
- **Staff mix**: beside every staff percentage, the faculty's signed teachers as percentages
  (specialized / supported, fulltime / parttime, PhDs / masters): drawn in the faculty modal
  and reports, a tooltip in tables, the board and the dashboard.
- **Tables** for contracts, employees, faculties, specializations and chapters:
  - search box (keywords, `!word` to exclude, or a DjangoQL query such as
    `students_per_phd > 12`), press `/` to focus it;
  - filters in a **right sidebar** (pinnable beside the table on wide screens, `Alt+F`);
  - click a heading to sort, `Shift`+click to add it as another level (▲1 ▼2);
  - **columns menu**: drag to reorder columns, uncheck to hide them (remembered);
  - row selection with bulk delete (one transaction: all or none);
  - a related row's name in a cell (an employee's faculty, a contract's specialization)
    opens that row's modal;
  - create / edit / details / delete in modals, "save & new", `Alt+N` for new;
  - on / off switches for specializations, employees and contracts;
  - export to Excel / CSV (what is filtered) and import (xlsx / csv, rows by name, all or none).
- **Employee form**: optionally, the faculties the employee cannot be counted in. Signed to
  one of them, the contract is never counted there (it still lowers the staff percentage),
  and the optimizer never signs it there.
- **Faculty form**: numbers plus its accepted specializations (specialized / supported,
  share %, min / max, teacher bounds) as rows you drag into order.
- **Layout**: navigation sidebar on the start side (collapsible to icons, `Alt+S`; hover a
  table's link for its "new" button), keyboard shortcuts on English and Arabic keyboards,
  chapter switcher in the header, toasts, HTMX partial updates everywhere.
- **Light / dark / system** themes, **English / Arabic** with full **RTL** layout.

Every save is validated by the domain: the whole chapter is rebuilt as a domain `Chapter`
before the transaction commits, so a broken rule rolls it back and shows the domain's
message on the form.

## Stack

Python 3.10 · Django 5.2 · HTMX 2 · Alpine.js 3 (collapse, focus, mask, persist, sort,
autosize) · Tailwind CSS 3 · Vite 6 · django-cotton · django-filter · djangoql ·
django-import-export · MySQL (SQLite for tests / local use).

## Getting started

```bash
uv sync
npm install
cp .env.example .env        # then set SECRET_KEY, the database, ...
uv run manage.py migrate
uv run manage.py createsuperuser
uv run manage.py seed       # optional: a sample chapter
```

Run it (two terminals), with `VITE_DEV_MODE=True` in `.env`:

```bash
npm run dev
uv run manage.py runserver
```

Or build the assets once (`npm run build`, `VITE_DEV_MODE=False`) and run Django alone:
the build goes to `unicap/static/dist/` with its `manifest.json`. With built assets, restart
Django after each build: django-vite reads the manifest once at startup (a missing manifest
shows up as the `django_vite.W001` check warning, then `DjangoViteAssetNotFoundError`).

## Users, roles and settings

- **Admins** (superusers) control everything and alone open the admin panel (`/admin/`,
  linked from the sidebar): every model, the users, the settings and the report templates.
  Edits there are validated like in the app: a change that breaks a rule is rolled back.
- **Users** work in the app only; what they may do comes from their role (a group, set up by
  `migrate`), or from single permissions given in the admin panel:
  - `viewers`: see everything
  - `editors`: see, add and change
  - `managers`: see, add, change and delete
- **Settings** (admin panel, one row each): the app's (project name, rows per page, modal
  size, resizable modals, remembering tables' filters), and each section's (rows per page,
  form / details modal size; empty takes the app's).

## Backups

Backups (the sidebar's **backups**, admins by default; the `restore_backup` permission can be
given to others) are JSON files saved in `private/backups/` (`PRIVATE_MEDIA_ROOT`: outside the served media, so
only the backups page hands them out), rows written by name:

- the **whole system**: every chapter and the settings;
- a **chapter**: its settings and every row (from the backups page or the chapters table);
- a **section** of a chapter: its specializations, faculties, employees or contracts (from
  that table's *files* menu).

Restoring makes the target equal to the backup (rows created or updated by name, the others
removed), checked like any other write; a chapter backup can also become a new chapter. What
a restore replaces is saved as a backup first. Downloaded backups upload back, into this
installation or another.

## Project layout

```
manage.py, pyproject.toml, package.json, vite.config.mjs, tailwind.config.js
unicap/            the Django root (BASE_DIR)
  unicap/          the project: settings (base / development / testing / deployment), urls, wsgi
  domain/          business rules, standard library only (Python 3.10)
  app/             the one Django app (label "app"), one module per model / resource:
    models/        User, Chapter, Specialization, Faculty, FacultySpecialization, Employee, Contract
    querysets/  managers/  filters/  forms/  resources/   (base.py: the shared generic parts)
    constants/  views/  urls/  templatetags/  management/  migrations/
    snapshot.py    Snapshot (rows -> domain); middlewares, decorators, choices, ...
    reports/       Word reports: context (values for templates), docx (docxtpl + sandboxed
                   Jinja2), defaults/ (built-in templates; `manage.py report_templates`)
  templates/       app/ (pages: board, chapters, crud), components/ (cotton), registration/
  assets/          Tailwind CSS and Alpine components (Vite entry: unicap/assets/js/index.js)
  static/          static files; static/dist/ is the Vite build (`npm run build`)
  locale/ar/       Arabic translations
tests/             domain, managers, views
```

Every model translates itself: `to_domain()` returns the domain value (`Faculty` ->
`ChapterFaculty`, `Chapter` -> the whole aggregate), `from_domain()` copies a domain value
onto a new or existing row. `Chapter.objects.create_from_domain()` saves a whole domain
chapter (the `seed` command uses it).

## Performance

Each page has a ceiling of SQL queries, and none may grow with its rows
(`tests/core/test_query_counts.py`). To look into a page, open it with the development
server, then `/silk/` (django-silk, development settings only, superusers): every query of
the request, where it was run from, and its time. `scripts/profile_queries.py` prints the
same numbers for every page at once.

`.github/workflows/ci.yml` runs the lint, the migration check, the build, both test suites
and the domain's doctests on every push.

## Commands

```bash
uv run pytest                          # tests (fast: no browser)
npm run build && uv run pytest -m slow # browser tests (Playwright, tests/e2e/): the Alpine
                                       # components, right click, shortcuts, drag and drop;
                                       # first: uv run playwright install chromium
uv run python scripts/profile_queries.py   # SQL queries, repeats and time of every page
uv run ruff check . && uv run ruff format --check .
nox -s check                           # both
nox -s build                           # production assets + requirements files
uv run manage.py makemessages -l ar --ignore=node_modules --ignore=.venv --ignore=static
uv run python scripts/translations_ar.py   # fill the Arabic catalog
uv run manage.py compilemessages -l ar
uv run manage.py report_templates           # rewrite the built-in Word templates
```
