# Holiday Planner CLI Tool

## Overview
The **Long Holiday Planner** is a command-line tool that helps users maximize their time off by identifying optimal leave days to create long holiday breaks. It processes public holidays from either an iCalendar (ICS) or CSV file and analyzes the year's working and non-working days to suggest leave days that can extend holidays efficiently.

## Features
- Supports **ICS (iCalendar)** and **CSV** input formats for public holidays.
- Identifies long holiday opportunities based on user-defined working days.
- Allows customization of what constitutes a "long holiday" (default: **4 consecutive off days**).
- Handles weekends intelligently based on user-defined working days.
- Optional **pandas** support for robust CSV parsing.
- Simple and efficient command-line interface.

## Installation
### Prerequisites
Ensure you have Python 3 installed.

### Install Required Dependencies
```bash
pip install icalendar
```
(Optional) Install **pandas** for better CSV parsing:
```bash
pip install pandas
```

## Usage
### Basic Command Format
```bash
python holiday_planner.py --file <path_to_file> --filetype <ics|csv> --year <year>
```

### Required Arguments
| Argument         | Description |
|-----------------|-------------|
| `--file`        | Path to the input file containing public holidays. |
| `--filetype`    | Format of the input file (`ics` or `csv`). |
| `--year`        | The year for which holiday planning is needed. |

### Optional Arguments
| Argument         | Description |
|-----------------|-------------|
| `--working-days` | Comma-separated list of working days (default: `0,1,2,3,4` for Mon-Fri). |
| `--threshold`    | Minimum consecutive off days to qualify as a long holiday (default: `4`). |
| `--use-pandas`   | (Optional) Use pandas for CSV parsing (requires pandas). |

### Example Commands
#### Example 1: Planning holidays using an ICS file
```bash
python holiday_planner.py --file holidays.ics --filetype ics --year 2025
```

#### Example 2: Using a CSV file with custom working days
```bash
python holiday_planner.py --file holidays.csv --filetype csv --year 2025 --working-days 0,1,2,3,4,5
```

#### Example 3: Using pandas for robust CSV parsing
```bash
python holiday_planner.py --file holidays.csv --filetype csv --year 2025 --use-pandas
```

## Output
- The tool prints a list of suggested leave days that maximize long holidays.
- Each leave suggestion includes:
  - **Leave Day**: Date and day of the week.
  - **Holiday Block Start**: The beginning of the continuous off-day block.
  - **Holiday Block End**: The end of the continuous off-day block.
  - **Total Off Days**: Length of the holiday block.
  
## Error Handling
- If the input file is missing or incorrect, an appropriate error message is displayed.
- Invalid CSV formats (e.g., missing or incorrectly formatted dates) are skipped with warnings.
- If `icalendar` is not installed, the script prompts for installation and exits.

## License
This project is open-source and available for modification and redistribution under the MIT License.

