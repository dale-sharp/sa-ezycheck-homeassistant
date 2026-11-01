# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed

- Refreshed the locked development dependencies. Nothing in the shipped integration
  changes, so there is no version bump.
  - `homeassistant` 2026.10.3 to 2026.10.4 and `pytest-homeassistant-custom-component`
    0.13.374 to 0.13.375, so the tests now run against Home Assistant 2026.10.4.
  - `ruff` 0.17.2 to 0.17.3 and `ty` 0.0.91 to 0.0.95.
  - Transitive updates, among them `grpcio` 1.85.1, `multidict` 7.2.1, `boto3` and
    `botocore` 1.43.123, `pytz` and `tzdata` 2026.6, `sentence-stream` 1.4.0, the `nab`
    packages 0.0.23, and the Bluetooth packages `pyobjc` 13.0 and `winrt` 4.1.0 or
    10.0.28000.2957.

---

## [0.1.1] - 2026-11-01

### Fixed

- Diagnostics no longer show the plate in the last error message, and a failed request no
  longer puts the plate in the error text.
- A registration expiry date in an unexpected format now fails the update, so the entities
  show as unavailable, instead of being reported as an unregistered vehicle.
- A plate the service refuses now stops the setup with an error. It used to be retried
  every few minutes without end.
- The repair issue for repeated failed updates now clears after a reload and when the
  entry is removed. It used to stay until Home Assistant restarted.

---

## [0.1.0] - 2026-10-25

### Added

- Initial release: track a South Australian vehicle's registration by plate, using the
  public registration check. The endpoint is undocumented and may change at any time.
- Setup by plate number, validated against the South Australian plate formats (custom,
  Japanese, personalised, classic, standard, premium, heavy vehicle, pre-1966 numeric and
  taxi) and then confirmed with the service. One entry and device per vehicle.
- Reconfigure flow to correct the plate, and an options flow for the scan interval
  (default 12 hours, minimum 60 minutes).
- Sensors: registration expiry date, days until expiry, inspection due date, make, body
  type, colour, CTP insurer, plate type, premium class and masked VIN (disabled by
  default).
- Binary sensors: registered, incident, pending suspension and inspection expired
  (disabled by default).
- Calendars with an all-day event for the registration expiry and, disabled by default,
  the inspection due date.
- Diagnostics with the plate, title and VIN digits redacted, and a repair issue after
  repeated failed updates.
- `quality_scale.yaml` covering every Integration Quality Scale rule. `brands` is still
  open until the placeholder icon is replaced.
