class UserError(Exception):
    """A write the app refuses for a reason the user can fix (not a domain rule).

    Views show its message the same way as a `DomainError`'s.
    """
