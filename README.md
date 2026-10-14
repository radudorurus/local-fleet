# Local Fleet Manager (`local_fleet`)

Custom Home Assistant integration designed for monitoring fleet vehicle operational parameters, maintenance schedules, legal document expirations, and tire structural age based on DOT codes.

## Features

* **Vehicle Identification**: Tracks VIN and vehicle model strings.
* **Odometer & Service Monitoring**: Tracks current mileage, calculates remaining distance, and calculates remaining days until required maintenance.
* **Legal Expirations**: Tracks validity periods and remaining days for ITP (technical inspection), RCA (compulsory insurance), and road vignette.
* **Tire Management**: 
  * Allows selecting active tire type (Summer, Winter, All-Season).
  * Evaluates tire structural age based on 4-digit DOT codes (WWYY).
  * Automatically calculates the safety benchmark using the oldest tire code from a CSV input.
* **UI Integration**: Fully dynamic status color transitions based on urgency thresholds.

## HACS Dependencies

For full visual component rendering, the following Lovelace frontend modules are required:
* `layout-card` (`custom:layout-card`)
* `lovelace-mushroom` (`custom:mushroom-template-card`)

## Installation

### Manual Installation
1. Copy the `local_fleet` directory into your Home Assistant `<config_dir>/custom_components/` directory.
2. Restart Home Assistant.
3. In Home Assistant, navigate to **Settings** -> **Devices & Services** -> **Add Integration** and search for `Local Fleet Manager`.

### HACS Installation (Custom Repository)
1. Open HACS in Home Assistant.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Add `https://github.com/radudorurus/local-fleet` with category **Integration**.
4. Click **Download** and restart Home Assistant.

[explanations to add about how the integration works. what dependencies needs]
[car_card_template.txt is also in the repo with comments]

## Configuration

Configuration is handled via UI config flow. You will be prompted to enter vehicle identification data, initial mileage, service intervals, expiration dates, and DOT codes for tire sets.

Options can be reconfigured at any time via **Settings** -> **Devices & Services** -> **Local Fleet Manager** -> **Configure**.
