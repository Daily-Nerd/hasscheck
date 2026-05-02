# Demo Good Integration

Example fixture used by HassCheck tests and local report demos.

## Installation

Install via HACS (recommended) or manually by copying `custom_components/demo_good/`
into your Home Assistant `custom_components/` directory.

### HACS

1. Open HACS → Integrations.
2. Search for **Demo Good Integration**.
3. Click Install.

### Manual Install

1. Download the latest release.
2. Copy `custom_components/demo_good/` to `<HA config>/custom_components/`.
3. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for "Demo Good Integration".
3. Follow the config flow — no YAML required.

### Options

All options are configurable from the integration page after initial setup.

## Troubleshooting

- **Integration not found**: Ensure the `custom_components/demo_good/` directory was copied correctly and Home Assistant was restarted.
- **Auth failure**: Verify your credentials and re-run the config flow.

Enable debug logging by adding to `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.demo_good: debug
```

## Removal

1. Go to **Settings → Devices & Services**.
2. Find Demo Good Integration and click **Delete**.
3. Optionally remove `custom_components/demo_good/` from your file system.

## Privacy

This integration runs entirely **local** — no data is sent to external services or cloud.
No telemetry is collected. All communication stays within your local network.

## Examples

### Turn on a light via automation

```yaml
action: light.turn_on
target:
  entity_id: light.demo_good_main
data:
  brightness_pct: 80
```

### Monitor state in a dashboard

Add the sensor entity `sensor.demo_good_status` to a Lovelace card of your choice.

## Supported Devices

This integration supports the following hardware and services:

- Demo Good Hub (all firmware versions)
- Demo Good Bridge v2 and later
- Demo Good Cloud API (requires active subscription)

## Limitations

- Only one instance of the integration can be configured per Home Assistant instance.
- Local polling interval minimum is 30 seconds; lower values are silently clamped.
- The integration does not support energy monitoring on devices running firmware < 2.0.

## HACS Installation

1. Open HACS in your Home Assistant sidebar.
2. Go to **Integrations**.
3. Click the three-dot menu (⋮) in the top-right corner and choose **Custom repositories**.
4. Enter `https://github.com/Daily-Nerd/demo_good_integration` and select **Integration**.
5. Click **Add**, then search for *Demo Good Integration* and install it.
6. Restart Home Assistant when prompted.
