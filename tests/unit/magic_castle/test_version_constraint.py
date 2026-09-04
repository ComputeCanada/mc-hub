import pytest

from mchub.models.version_constraint import (
    matches_terraform_version_constraint,
    parse_terraform_version_constraint,
)


@pytest.mark.parametrize(
    ("version", "constraint", "expected"),
    [
        ("14.0.0", ">= 14.0.0, < 15.0.0", True),
        ("14.9.1", ">= 14.0.0, < 15.0.0", True),
        ("15.0.0", ">= 14.0.0, < 15.0.0", False),
        ("14.1.7", "~> 14.1.0", True),
        ("14.2.0", "~> 14.1.0", False),
        ("14.9.0", "~> 14.1", True),
        ("15.0.0", "~> 14.1", False),
        ("v14.1.2", "= 14.1.2", True),
        ("14.1.2", "!= 14.1.2", False),
    ],
)
def test_matches_terraform_version_constraint(version, constraint, expected):
    assert matches_terraform_version_constraint(version, constraint) is expected


@pytest.mark.parametrize("constraint", ["", "^14.0.0", ">= nope", ">= 14 || < 15"])
def test_rejects_invalid_constraint(constraint):
    with pytest.raises(ValueError):
        parse_terraform_version_constraint(constraint)
