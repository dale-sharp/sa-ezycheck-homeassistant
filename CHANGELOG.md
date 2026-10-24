# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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
