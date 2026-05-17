# Aqara Unofficial  for Home Assistant

> **Unofficial beta release** — this is a community-made Home Assistant custom integration. It is **not affiliated with, endorsed by, or supported by Aqara or Lumi United Technology**. Some devices, entities, resource IDs or cloud responses may change. Bugs are expected; please open an issue with logs and device model details.

Aqara Unofficial  connects selected Aqara cloud devices to Home Assistant through the **Aqara** and exposes useful entities such as locks, sensors, switches, number controls and camera/doorbell event states.

Created and maintained by **AzadGLR**.

## Features

- UI-based setup through Home Assistant config flow.
- Aqara authentication with App ID, Key ID, App Key and verification code.
- Device selection during setup and in integration options.
- Entity names and state text follow the Home Assistant language (`en` / `tr`).
- Cloud polling with separate fast event polling and slower resource polling.
- Aqara U200 lock entity and power/battery sensors.
- Aqara Video Doorbell G4 event states, switches and volume controls.
- Aqara Hub M3 diagnostic, volume, temperature, humidity and status entities.
- Aqara Camera E1 / G-series style cloud event status where supported by Aqara resource history.
- Debug services for qlink traits and camera event discovery.

## Tested devices

### Aqara Smart Lock U200

- Lock entity
- Online sensor
- Battery percentage
- Current voltage
- Low battery state

### Aqara Video Doorbell G4 / Camera Hub G4

- Online sensor
- Battery sensor
- Doorbell status
- Recognized person / face recognition event
- Tamper status
- High/low temperature status
- Privacy mode
- Face detection notification switch
- Motion/PIR recording switch
- Face recording switch
- Doorbell notification switch
- Doorbell recording switch
- Anti-tamper alarm switch
- High/low temperature alarm switches
- Doorbell volume
- Camera volume
- Alarm volume

### Aqara Hub M3

- Online sensor
- Internal temperature
- Humidity
- Temperature
- Alarm status
- Music status
- Binding status
- Wi-Fi channel
- Restart count and restart reason
- Device online resource diagnostic binary sensor
- Music volume
- Alarm volume
- Doorbell volume
- System volume
- Alarm duration
- Doorbell duration
- Accidental deletion prevention switch

### Aqara Camera E1 / `lumi.camera.acn006`

- Online sensor
- Motion detection status based on discovered camera event history

## Supported / partially supported models

| Device | Aqara model | Support level |
| --- | --- | --- |
| Aqara Smart Lock U200 | `aqara.matter.4447_10242` | Tested |
| Aqara Video Doorbell G4 | `lumi.camera.agl002` | Tested |
| Aqara Hub M3 | `lumi.gateway.agl004` | Tested |
| Aqara Camera E1 / cloud camera event model | `lumi.camera.acn006` | Tested / partial |

Other Aqara devices may appear in the device list, but unsupported models will only expose an online sensor until resource definitions are added.

## Requirements

- Home Assistant with custom integrations enabled.
- HACS is recommended for installation and updates.
- An Aqara Developer account.
- Aqara Open API credentials:
  - App ID
  - Key ID
  - App Key
- Aqara account email/phone for authorization.
- Devices already added to the Aqara Home app and visible under the selected cloud region.

## Getting Aqara API credentials

1. Go to the Aqara Developer Platform: <https://developer.aqara.com/?lang=en>
2. Register or log in.
3. Create a project/application.
4. Create or obtain the Open API credentials:
   - `App ID`
   - `Key ID`
   - `App Key`
5. Make sure the selected cloud region matches the region of your Aqara Home account and devices.

Supported regions in this integration: `CN`, `USA`, `KR`, `RU`, `GER`, `SG`.

## Installation with HACS

1. Open Home Assistant.
2. Go to **HACS** → **Integrations**.
3. Open the three-dot menu and choose **Custom repositories**.
4. Add the repository URL:

```text
https://github.com/Azadglr/aqara-unofficial
```

5. Category: **Integration**.
6. Install **Aqara Unofficial (Open API)**.
7. Restart Home Assistant.
8. Go to **Settings** → **Devices & services** → **Add integration**.
9. Search for **Aqara Unofficial**.

## Manual installation

Copy the integration folder to:

```text
/config/custom_components/aqara_unofficial
```

Then restart Home Assistant and add the integration from the UI.

## Configuration

During setup you will be asked for:

- Aqara account
- Cloud region
- Optional refresh token
- App ID
- Key ID
- App Key

If no refresh token is provided, the integration will request an authorization code from Aqara. Enter the verification code in the next step.

After authentication, select the devices you want to expose in Home Assistant.

## Options

The integration options allow you to:

- Change selected devices.
- Configure recognized people names for G4 face recognition events.

Recognized people mapping format:

```text
1328531273258582016 = Azad
1234567890 = Family Member
```

## Services

### `aqara_unofficial.dump_qlink_traits`

Writes qlink trait configuration to:

```text
/config/aqara_unofficial_qlink_traits.json
```

### `aqara_unofficial.discover_camera_events`

Probes camera event resource history and writes discovery output to:

```text
/config/aqara_unofficial_camera_events_*.json
```

Service fields: `size`, `batch_size`, `include_all`.

## Polling behavior

- Fast event polling: every 3 seconds by default.
- Resource polling: every 60 seconds by default.

This is cloud polling, not local push. Event latency depends on Aqara cloud availability and the device model.

## Known limitations

- This is an unofficial beta integration.
- Aqara resource IDs may vary by region, firmware or account.
- Camera events are cloud-polled and may not be instant.
- Some camera event names are inferred from discovered resources.
- Unsupported devices will not expose full entities until definitions are added.
- The integration does not stream camera video.
- The integration does not replace native Matter, HomeKit, Zigbee2MQTT or Aqara Home functionality.

## Troubleshooting

Enable debug logging:

```yaml
logger:
  logs:
    custom_components.aqara_unofficial: debug
```

Use `aqara_unofficial.dump_qlink_traits` and `aqara_unofficial.discover_camera_events` for debugging supported camera/trait resources.

## Repository structure

```text
custom_components/aqara_unofficial/
  __init__.py
  aiot_cloud.py
  aiot_manager.py
  binary_sensor.py
  config_flow.py
  const.py
  entity_base.py
  localize.py
  lock.py
  number.py
  resource_definitions.py
  sensor.py
  services.yaml
  switch.py
  manifest.json
  translations/
    en.json
    tr.json
```

## Important migration note

This beta uses the integration domain `aqara_unofficial`. If you previously installed a build using another domain, Home Assistant may treat this as a new integration and new entity IDs may be created.

## Disclaimer

This project is not affiliated with or endorsed by Aqara or Lumi United Technology. Aqara is a trademark of its respective owner. Use this integration at your own risk.

## Author

Created and maintained by **AzadGLR**.
