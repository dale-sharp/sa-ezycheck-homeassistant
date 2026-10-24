# SA EzyCheck

[![hacs][hacs-badge]][hacs-url]

Track South Australian vehicle registration expiry, CTP insurer, inspection status and more from South Australia's public registration check.

> [!WARNING]
> **Read this first.**
>
> - **This integration relies on an undocumented API endpoint.** It calls the `CheckRegistrationExpiryDateServlet` page on `ecom.transport.sa.gov.au`, which is not a published or supported API. It can change, move, start requiring authentication or disappear at any time, and the integration may break without notice.
> - **Be respectful when setting the scan interval.** This is a public government service that was built for people checking one vehicle, not for automated polling. Registration details change a few times a year, so the default of 12 hours is already frequent. Do not set it lower than you need, and do not add more vehicles than you actually own or look after.
> - **This project is not affiliated with, endorsed by or connected to EzyReg, Service SA or mySAGOV**, or the South Australian Government. Those names belong to their owners and are used here only to describe where the data comes from.

Use it to get a reminder before a vehicle's registration runs out, to keep an eye on the family cars from one dashboard, or to check whether a vehicle has a pending suspension. Each plate you add becomes a device with sensors for the expiry date, the days remaining and the details the registration check reports.

This is an unofficial, community-built integration. It reads the same public registration expiry check that the South Australian Government offers on its website.

## Requirements

- Home Assistant 2026.3.0 or newer.
- A South Australian number plate. No account or API key is needed, because the service is public.

## Installation

### HACS (recommended)

1. In HACS, open **Integrations** and add `https://github.com/dale-sharp/sa-ezycheck-homeassistant` as a custom repository (category: Integration), or search for it once it is in the default list.
2. Download **SA EzyCheck** and restart Home Assistant.
3. Go to **Settings > Devices & services > Add integration** and search for **SA EzyCheck**.

### Manual

1. Copy `custom_components/sa_ezycheck` from the latest release into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant and add the integration as above.

## Configuration

Adding the integration asks for one thing:

| Field | Meaning |
|---|---|
| Plate number | The vehicle's South Australian plate. Case, spaces, hyphens and dots are ignored, so `s123 abc` is stored as `S123ABC`. Accepted formats are custom plates (letters, or letters and numbers, up to 7 characters, including Japanese, personalised and classic plates and every modern standard format), pre-1966 numbers-only plates (5 or 6 digits) and metropolitan taxi plates (`TAXI` plus 3 or 4 numbers). |

The plate's format is checked first, then the service confirms it before the entry is created. Add the integration once for each vehicle.

### Reconfiguration

**Reconfigure** (the three-dot menu of the entry) changes the plate number, for example to fix a typo. Entities keep their history.

**Configure** (Options) sets the scan interval, in minutes. The default is 720 (12 hours) and the minimum is 60. The entry reloads when you save.

## Entities

Each vehicle is one device named after its plate, with the vehicle make as the manufacturer and the body type as the model. Entity IDs follow the device name, so for plate `ABC123` the entities are `sensor.abc123_<name>` and `binary_sensor.abc123_<name>`.

### Sensors

| Entity | State |
|---|---|
| `sensor.abc123_registration_expiry` | Registration expiry date. Unknown when the vehicle is unregistered. Carries the attributes `conditional_details`, `registered_configuration`, `registered_gvm_gcm`, `manufacturer_gvm_gcm`, `vehicle_conditions` and `inspection_type`, each present only when the service reports a value. |
| `sensor.abc123_days_until_expiry` | Whole days until expiry, negative once overdue. Recalculated every midnight. |
| `sensor.abc123_inspection_due` | Date an inspection is due, when one is required. |
| `sensor.abc123_make` | Vehicle make, for example `FORD`. |
| `sensor.abc123_body_type` | Body type, for example `SEDAN`. |
| `sensor.abc123_colour` | Primary colour. |
| `sensor.abc123_ctp_insurer` | Compulsory third party insurer. |
| `sensor.abc123_plate_type` | Plate type, for example `CUSTOM`. Diagnostic. |
| `sensor.abc123_premium_class` | CTP premium class. Diagnostic. |
| `sensor.abc123_masked_vin` | VIN with all but the last four characters hidden. Diagnostic, disabled by default. |

### Binary sensors

| Entity | On when |
|---|---|
| `binary_sensor.abc123_registered` | The vehicle has a registration expiry date. |
| `binary_sensor.abc123_incident` | The service flags an incident against the vehicle. |
| `binary_sensor.abc123_pending_suspension` | A suspension is pending. |
| `binary_sensor.abc123_inspection_expired` | The service reports the inspection as expired. Disabled by default: it reads `YES` for ordinary vehicles that are not subject to inspection. |

A flag the service does not report shows as unknown.

### Calendars

| Entity | Event |
|---|---|
| `calendar.abc123_registration` | An all-day event on the registration expiry date, titled `ABC123 registration expires`. No event when the vehicle is unregistered or the date has passed. |
| `calendar.abc123_inspection` | An all-day event on the inspection due date, titled `ABC123 inspection due`, when the service reports one. Disabled by default; enable it from the entity's settings if you want it. |

The calendars update with each poll. They appear in Home Assistant's Calendar dashboard and can be used with calendar triggers, for example to be reminded a week before the expiry date.

## How data is updated

Home Assistant asks the registration check for the plate every 12 hours by default (minimum 60 minutes). Because the endpoint is undocumented and public, keep the interval as long as you can tolerate. Each update is one HTTP request returning the vehicle's details. The days-until-expiry sensor does not need a request: it is recalculated at midnight from the stored expiry date.

If a plate has moved between vehicles, the service returns a record for each. The integration uses the registered one, and the one expiring last if several are.

## Example automation

Notify when the registration is within 30 days of expiring:

```yaml
automation:
  - alias: Registration expiring soon
    triggers:
      - trigger: numeric_state
        entity_id: sensor.abc123_days_until_expiry
        below: 30
    actions:
      - action: notify.notify
        data:
          message: >-
            Registration for ABC123 expires on
            {{ states('sensor.abc123_registration_expiry') }}.
```

## Known limitations

- The endpoint is undocumented. It may change or stop working at any time, and there is no support channel for it.
- The service reports no quota, so the polling interval has a 60 minute floor to stay polite.
- Only the data the check publishes is available. There is no way to renew a registration or see owner details.
- The service reports `inspectionExpired` as `YES` for many ordinary vehicles, which is why that binary sensor is disabled by default.
- Values such as the make are shown as the service writes them, in capitals.

## Troubleshooting

**"The registration check did not accept this plate number"**: check the plate. The service rejects plates it does not recognise.

**Entities unavailable**: the service could not be reached. After three failed updates in a row a repair issue appears, and it clears itself when an update succeeds.

**Debug logging**: add this to `configuration.yaml`, restart, then reproduce the problem:

```yaml
logger:
  logs:
    custom_components.sa_ezycheck: debug
```

**Diagnostics**: on **Settings > Devices & services > SA EzyCheck**, open the three-dot menu of the entry and choose **Download diagnostics**. The plate, title and VIN digits are redacted.

## Removal

1. Go to **Settings > Devices & services**, open **SA EzyCheck**, and choose **Delete** from the menu.
2. Optionally remove the integration in HACS and restart Home Assistant.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Released under the AGPL-3.0-or-later license. See [LICENSE](LICENSE).

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[hacs-url]: https://github.com/hacs/integration
