"""Tests guarding that platforms and entity descriptions are registered consistently."""

from __future__ import annotations

from pathlib import Path

from custom_components.sa_ezycheck import PLATFORMS
from custom_components.sa_ezycheck.binary_sensor import BINARY_SENSORS
from custom_components.sa_ezycheck.calendar import CALENDARS
from custom_components.sa_ezycheck.sensor import SENSORS

COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "sa_ezycheck"


def test_every_registered_platform_has_a_module() -> None:
    for platform in PLATFORMS:
        assert (COMPONENT_DIR / f"{platform.value}.py").is_file(), platform


def test_every_platform_module_is_registered() -> None:
    modules = {
        path.stem
        for path in COMPONENT_DIR.glob("*.py")
        if path.stem
        in {"sensor", "binary_sensor", "switch", "calendar", "event", "number"}
    }

    assert modules == {platform.value for platform in PLATFORMS}


def test_entity_descriptions_have_unique_keys_and_translation_keys() -> None:
    for descriptions in (SENSORS, BINARY_SENSORS, CALENDARS):
        keys = [description.key for description in descriptions]
        translation_keys = [description.translation_key for description in descriptions]

        assert len(set(keys)) == len(keys)
        assert all(translation_keys)
        assert len(set(translation_keys)) == len(translation_keys)
