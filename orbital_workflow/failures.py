"""Small local steering diagnostics, separate from observations and credit.

Explicit request validators identify command/parameter errors. An unexpected
operation exception is unknown; its exception class is not a root-cause proof.
Only category, declared tool and parameter identifier reach the responsible
Episode. Audit references stay private. A ToolAcquisitionFailure is unfinished
work, not a zero-scored observation, and never advances the numerical history.
"""

import re


CATEGORIES = frozenset({"wrong_command", "wrong_parameters", "tool_code", "unknown"})
TOOL_NAMES = frozenset({"sim.run", "sim.compare", "math.arithmetic", "math.numeric",
                        "math.symbolic", "math.lean"})
_FIELD = re.compile(r"[A-Za-z_][A-Za-z0-9_.:-]{0,127}")


def failure_diagnostic(category, *, tool=None, field=None):
    """Construct only declared codes and parameter names, never error prose."""
    if category not in CATEGORIES:
        raise ValueError("Unknown action failure category")
    if tool is not None and tool not in TOOL_NAMES:
        raise ValueError("Failure tool must be a declared tool name or null")
    if field is not None and (not isinstance(field, str) or _FIELD.fullmatch(field) is None):
        raise ValueError("Failure field must be a parameter identifier or null")
    return {"category": category, "tool": tool, "field": field}


def normalize_failure(value):
    if not isinstance(value, dict) or set(value) != {"category", "tool", "field"}:
        raise ValueError("Action failure diagnostics have exactly category, tool and field")
    return failure_diagnostic(value["category"], tool=value["tool"], field=value["field"])


class ActionRequestError(ValueError):
    """A known command/parameter problem identified at its request boundary."""

    def __init__(self, category="wrong_parameters", *, tool=None, field=None):
        self.diagnostic = failure_diagnostic(category, tool=tool, field=field)
        super().__init__(category)


class ToolAcquisitionFailure(RuntimeError):
    """An attempted tool returned no observation; no successful unit exists."""

    def __init__(self, diagnostic, *, audit_references=()):
        self.diagnostic = normalize_failure(diagnostic)
        self.audit_references = tuple(audit_references)
        super().__init__(self.diagnostic["category"])
