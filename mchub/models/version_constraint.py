import re

from packaging.version import InvalidVersion, Version


CONSTRAINT_RE = re.compile(
    r"^(~>|>=|<=|!=|>|<|=)?\s*"
    r"(v?\d+(?:\.\d+){0,2}(?:[-+][0-9A-Za-z.-]+)?)$"
)


def parse_version(value):
    try:
        return Version(value)
    except InvalidVersion as error:
        raise ValueError(f"Invalid version: {value}") from error


def parse_terraform_version_constraint(expression):
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("Version constraint cannot be empty")

    constraints = []
    for raw_constraint in expression.split(","):
        match = CONSTRAINT_RE.fullmatch(raw_constraint.strip())
        if match is None:
            raise ValueError(f"Invalid Terraform version constraint: {expression}")

        operator = match.group(1) or "="
        raw_version = match.group(2)
        version = parse_version(raw_version)
        upper_bound = None

        if operator == "~>":
            release = list(version.release)
            version_core = raw_version.lstrip("v").split("-", 1)[0].split("+", 1)[0]
            component_count = len(version_core.split("."))
            if component_count >= 3:
                upper_bound = Version(f"{release[0]}.{release[1] + 1}.0")
            else:
                upper_bound = Version(f"{release[0] + 1}.0.0")

        constraints.append((operator, version, upper_bound))

    return constraints


def matches_terraform_version_constraint(version, expression):
    candidate = parse_version(version)

    for operator, expected, upper_bound in parse_terraform_version_constraint(
        expression
    ):
        if operator == "=" and candidate != expected:
            return False
        if operator == "!=" and candidate == expected:
            return False
        if operator == ">" and candidate <= expected:
            return False
        if operator == ">=" and candidate < expected:
            return False
        if operator == "<" and candidate >= expected:
            return False
        if operator == "<=" and candidate > expected:
            return False
        if operator == "~>" and not (candidate >= expected and candidate < upper_bound):
            return False

    return True
