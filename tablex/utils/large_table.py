from warnings import warn

warn(
    "'tablex.utils.large_table' has moved to 'tablex.lines.large_table'.",
    DeprecationWarning,
    stacklevel=2,
)

from tablex.lines.large_table import *  # noqa: F401,F403
