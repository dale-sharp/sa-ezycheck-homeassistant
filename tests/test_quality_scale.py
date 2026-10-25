# Copyright (C) 2026 dale-sharp
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Structural tests for quality_scale.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

QUALITY_SCALE = (
    Path(__file__).parent.parent
    / "custom_components"
    / "sa_ezycheck"
    / "quality_scale.yaml"
)

# https://contributors.home-assistant.io/core/quality-scale/rules/
TIER_RULES = {
    "bronze": {
        "action-setup", "appropriate-polling", "brands", "common-modules", "config-flow",
        "config-flow-test-coverage", "dependency-transparency", "docs-actions",
        "docs-conditions", "docs-high-level-description", "docs-installation-instructions",
        "docs-removal-instructions", "docs-triggers", "entity-event-setup",
        "entity-unique-id", "has-entity-name", "runtime-data", "test-before-configure",
        "test-before-setup", "unique-config-entry",
    },
    "silver": {
        "action-exceptions", "config-entry-unloading", "docs-configuration-parameters",
        "docs-installation-parameters", "entity-unavailable", "integration-owner",
        "log-when-unavailable", "parallel-updates", "reauthentication-flow", "test-coverage",
    },
    "gold": {
        "devices", "diagnostics", "discovery", "discovery-update-info", "docs-data-update",
        "docs-examples", "docs-known-limitations", "docs-supported-devices",
        "docs-supported-functions", "docs-troubleshooting", "docs-use-cases",
        "dynamic-devices", "entity-category", "entity-device-class",
        "entity-disabled-by-default", "entity-translations", "exception-translations",
        "icon-translations", "reconfiguration-flow", "repair-issues", "stale-devices",
    },
    "platinum": {"async-dependency", "inject-websession", "strict-typing"},
}  # fmt: skip


def _rules() -> dict[str, dict[str, str]]:
    return yaml.safe_load(QUALITY_SCALE.read_text(encoding="utf-8"))["rules"]


def test_every_rule_of_every_tier_is_listed_exactly_once() -> None:
    expected = set().union(*TIER_RULES.values())

    assert set(_rules()) == expected


def test_every_rule_has_a_valid_status_and_a_comment() -> None:
    for name, rule in _rules().items():
        assert rule["status"] in {"done", "exempt", "todo"}, name
        assert rule["comment"].strip(), name
