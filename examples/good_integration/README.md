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
