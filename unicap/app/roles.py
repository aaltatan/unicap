"""Who may do what: admins do everything (and alone open the admin panel); users get a role.

A role is a group whose permissions cover the app's data (chapters, specializations,
faculties and their shares, employees, contracts):

- viewers: see everything
- editors: see, add and change
- managers: see, add, change and delete

Admins put users in a role from the admin panel (or give single permissions there). The
settings and report templates are left to admins. `ensure_roles` runs after every migrate,
so the groups exist and hold exactly these permissions.
"""

from typing import Any

from django.contrib.auth.models import Group, Permission

DATA_MODELS = (
    "chapter",
    "specialization",
    "faculty",
    "facultyspecialization",
    "employee",
    "contract",
)

ROLES = {
    "viewers": ("view",),
    "editors": ("view", "add", "change"),
    "managers": ("view", "add", "change", "delete"),
}


def ensure_roles(**kwargs: Any) -> None:  # noqa: ARG001 - a post_migrate receiver
    """Create the role groups, and set each one's permissions to exactly its actions."""
    for name, actions in ROLES.items():
        group, _created = Group.objects.get_or_create(name=name)

        codenames = [f"{action}_{model}" for action in actions for model in DATA_MODELS]

        group.permissions.set(
            Permission.objects.filter(content_type__app_label="app", codename__in=codenames),
        )
