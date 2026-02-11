# Oracle Custom Component for Home Assistant

This is a custom component integration for Home Assistant.

## Installation

### HACS

1. Go to HACS > Integrations > ... > Custom Repositories.
2. Add the URL of this repository.
3. Select "Integration" as the category.
4. Click "Add".
5. Search for "Oracle" and install it.
6. Restart Home Assistant.

### Manual

1. Copy the `custom_components/oracle` directory to your Home Assistant `config/custom_components/` directory.
2. Configure the integration via Settings > Devices & Services > Add Integration > Oracle. Provide the AdGuard Home base URL (e.g. `http://adguardhome.local`) and credentials.
2. Restart Home Assistant.

## Configuration

This integration supports configuration via the UI.

1. Go to Settings > Devices & Services.
2. Click "Add Integration".
3. Search for "Oracle".
4. Follow the setup instructions. The integration will create per-device switches named `Oracle Controlled <device>` and sensors named `Oracle <device> Queries Today`.

Owner: ikocev
