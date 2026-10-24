"""Structural tests for the translation and icon JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.sa_ezycheck.binary_sensor import BINARY_SENSORS
from custom_components.sa_ezycheck.calendar import CALENDARS
from custom_components.sa_ezycheck.sensor import SENSORS

COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "sa_ezycheck"


def _load(name: str) -> dict:
    return json.loads((COMPONENT_DIR / name).read_text(encoding="utf-8"))


def test_strings_and_en_translation_are_byte_identical() -> None:
    strings = (COMPONENT_DIR / "strings.json").read_bytes()
    assert strings == (COMPONENT_DIR / "translations" / "en.json").read_bytes()


def test_icons_json_covers_every_entity_translation_key() -> None:
    icons = _load("icons.json")["entity"]

    for platform, descriptions in (
        ("sensor", SENSORS),
        ("binary_sensor", BINARY_SENSORS),
        ("calendar", CALENDARS),
    ):
        assert set(icons[platform]) == {
            description.translation_key for description in descriptions
        }
        for key, entry in icons[platform].items():
            assert "default" in entry, f"{key} is missing a default icon"


def test_strings_name_every_entity() -> None:
    entities = _load("strings.json")["entity"]

    for platform, descriptions in (
        ("sensor", SENSORS),
        ("binary_sensor", BINARY_SENSORS),
        ("calendar", CALENDARS),
    ):
        assert set(entities[platform]) == {
            description.translation_key for description in descriptions
        }
        for description in descriptions:
            assert entities[platform][description.translation_key]["name"]


def test_reconfigure_step_has_the_same_fields_as_the_user_step() -> None:
    steps = _load("strings.json")["config"]["step"]

    assert "reconfigure" in steps
    reconfigure = steps["reconfigure"]
    assert reconfigure["title"]
    assert reconfigure["description"]
    assert set(reconfigure["data"]) == set(steps["user"]["data"])
    assert set(reconfigure["data_description"]) == set(
        steps["user"]["data_description"]
    )


def test_every_data_field_has_a_description() -> None:
    config = _load("strings.json")["config"]["step"]
    options = _load("strings.json")["options"]["step"]

    for step in (*config.values(), *options.values()):
        assert set(step["data"]) == set(step["data_description"])


def test_persistent_fetch_failure_issue_has_translations() -> None:
    issue = _load("strings.json")["issues"]["persistent_fetch_failure"]

    assert issue["title"]
    assert "{threshold}" in issue["description"]
    assert "{entry_title}" in issue["description"]


def test_exception_translations_exist_for_user_facing_failures() -> None:
    exceptions = _load("strings.json")["exceptions"]

    assert "{error}" in exceptions["cannot_connect"]["message"]
    assert "{plate}" in exceptions["invalid_plate"]["message"]


def test_config_flow_errors_are_translated() -> None:
    errors = _load("strings.json")["config"]["error"]

    assert errors["cannot_connect"]
    assert errors["invalid_plate"]
