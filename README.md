# Local Fleet Manager (`local_fleet`)

Custom Home Assistant integration designed for monitoring fleet vehicle operational parameters, maintenance schedules, legal document expiration, and tire structural age based on DOT codes.

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

## How does it work? (detailed)
- The integration is built to read an excel file where the mileage of each car is stored.
This excel file must be local, in the Home Assistant directories.
(the default path/name is /config/downloads/jurnal_auto.xlsx which you may change upon your choice when adding new car or editing the car)
If you have it stored somewhere else in the network, you need to create an automation to be updated/copied regularly.
**As a verified good practice use file/sheet names without spaces**.
(mine stays on gdrive where is easily available to update from the phone, I share it everyone with the link, created a command automation executing each 6h which copies it from gdrive locally)
In a future version I may modify the config flow to allow choice of each data input to be selected individually for retrieval from file / manually input later, select which sensors to create from the optional ones, which will make this integration more flexible.

Create new car/device flow:
- VIN number field (cannot be modified/corrected later)
- car number plate (cannot be modified/corrected later, it is the prefix for all the sensors of the device)
- model (brand/model/engine/year description you want to see - editable later)
- path to the excel file (editable after creation)
- sheet name from the excel file where the data for this vehicle is placed (editable after creation)
- cell id (A2 for example) where the mileage is stored (editable after creation)
--------
After submitting info, the vehicle is created.
The following sensors are created empty requiring your input:
- technical inspection validity date
- next service km limit (usually 8000-30000km ahead from the last service mileage)
- next service date (in future, usually 1yr from the last service)
- insurance validity date
- vignette validity date
- summer_dots (editable - edit device after creation)
- winter_dots (editable - edit device after creation)
- all_season_dots (editable - edit device after creation)
------------
 (DOT, tire manufacturing dates, have to comply the following syntax: four sets of numbers WWYY representing week number and last 2 digits of the year separated by comma and space eg, "4423, 4323, 4425, 4325", the oldest tire is considered when calculating the age)
-------------
Calculated sensors created:
- summer_tire_age (uses summer_dots for calculation of the tire age)
- winter_tire_age (uses summer_dots for calculation of the tire age)
- all_season_tire_age (uses summer_dots for calculation of the tire age)
- ITP remaining days
- Km until next service
- RCA remaining days
- vignette remaining days
- next service remaining days  

The repository includes a card code with explanations and what dependencies needs.
[car_card_template.txt]

## Configuration

Configuration is handled via UI config flow. You will be prompted to enter vehicle identification data, initial mileage, service intervals, expiration dates, and DOT codes for tire sets.

Options can be reconfigured at any time via **Settings** -> **Devices & Services** -> **Local Fleet Manager** -> **Configure**.
