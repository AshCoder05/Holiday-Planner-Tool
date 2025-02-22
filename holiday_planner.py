import argparse
import datetime
import csv
import sys

# Try importing the icalendar package; if not installed, prompt the user.
try:
    from icalendar import Calendar
except ImportError:
    print("Please install the icalendar package: pip install icalendar")
    sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(description="Long Holiday Planner CLI Tool")
    parser.add_argument('--file', type=str, required=True, 
                        help="Path to the input file (ICS or CSV) containing holiday dates.")
    parser.add_argument('--filetype', type=str, required=True, choices=['ics', 'csv'],
                        help="Input file type: 'ics' for iCalendar files or 'csv' for CSV files.")
    parser.add_argument('--year', type=int, required=True, 
                        help="Year to plan for (e.g., 2023).")
    parser.add_argument('--working-days', type=str, default="0,1,2,3,4",
                        help="Comma-separated list of working day indices (0=Mon,...,6=Sun). Default: 0,1,2,3,4")
    parser.add_argument('--threshold', type=int, default=4,
                        help="Minimum continuous off days to qualify as a long holiday (default: 4)")
    return parser.parse_args()

def parse_ics(file_path):
    """Parse an ICS file and return a set of holiday dates."""
    holidays = set()
    with open(file_path, 'rb') as f:
        cal = Calendar.from_ical(f.read())
        for component in cal.walk():
            if component.name == "VEVENT":
                dt = component.get('dtstart').dt
                if isinstance(dt, datetime.datetime):
                    dt = dt.date()
                holidays.add(dt)
    return holidays

def parse_csv(file_path):
    """Parse a CSV file assuming the first column is the date in YYYY-MM-DD format."""
    holidays = set()
    with open(file_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            try:
                dt = datetime.datetime.strptime(row[0], '%Y-%m-%d').date()
                holidays.add(dt)
            except Exception as e:
                continue  # Skip rows that can't be parsed
    return holidays

def generate_year_dates(year):
    """Generate a list of all dates for the given year."""
    start = datetime.date(year, 1, 1)
    end = datetime.date(year, 12, 31)
    delta = datetime.timedelta(days=1)
    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += delta
    return dates

def compute_off_days(year, holidays, working_days):
    """
    Compute the set of 'off days' for the year by combining
    provided public holidays and automatically determined weekend days.
    """
    dates = generate_year_dates(year)
    off_days = set(holidays)
    # Days that are not in the user-defined working days are considered weekends
    for d in dates:
        if d.weekday() not in working_days:
            off_days.add(d)
    return off_days

def get_continuous_block(candidate, off_set):
    """
    Given a candidate day that has been added to the off_set,
    find the continuous block of off days that it connects.
    """
    delta = datetime.timedelta(days=1)
    start = candidate
    end = candidate

    # Expand backwards
    prev = candidate - delta
    while prev in off_set:
        start = prev
        prev -= delta

    # Expand forwards
    nxt = candidate + delta
    while nxt in off_set:
        end = nxt
        nxt += delta

    block_length = (end - start).days + 1
    return start, end, block_length

def find_leave_suggestions(year, off_days, working_days, threshold):
    """
    Scan each working day in the year that is not already an off day.
    If adding that day as a leave day would merge adjacent off days
    and result in a continuous block with length >= threshold,
    record it as a suggestion.
    """
    dates = generate_year_dates(year)
    suggestions = []

    for d in dates:
        # Only consider days that are supposed to be working days
        if d.weekday() in working_days and d not in off_days:
            # Check if either the previous day or next day is already off.
            if (d - datetime.timedelta(days=1) in off_days) or (d + datetime.timedelta(days=1) in off_days):
                # Temporarily add this candidate day as off
                new_off = set(off_days)
                new_off.add(d)
                start, end, block_length = get_continuous_block(d, new_off)
                if block_length >= threshold:
                    suggestions.append({
                        "leave_day": d,
                        "block_start": start,
                        "block_end": end,
                        "block_length": block_length
                    })
    return suggestions

def main():
    args = parse_args()

    # Parse working days from CLI input (e.g., "0,1,2,3,4")
    try:
        working_days = [int(x.strip()) for x in args.working_days.split(',')]
    except Exception:
        print("Error parsing working days. Please use a comma-separated list of integers (0=Mon,...,6=Sun).")
        return

    # Read the holiday data from the specified file
    if args.filetype.lower() == 'ics':
        holidays = parse_ics(args.file)
    elif args.filetype.lower() == 'csv':
        holidays = parse_csv(args.file)
    else:
        print("Unsupported file type. Use 'ics' or 'csv'.")
        return

    # Compute off days (holidays + weekends based on working_days)
    off_days = compute_off_days(args.year, holidays, working_days)

    # Generate leave suggestions by checking if taking a leave on a working day 
    # would extend a continuous off period to at least the threshold
    suggestions = find_leave_suggestions(args.year, off_days, working_days, args.threshold)

    # Calculate total number of working days in the year (by definition: days with weekday in working_days)
    total_working_days = sum(1 for d in generate_year_dates(args.year) if d.weekday() in working_days)
    # Impact per leave day on attendance
    leave_impact_percentage = (1 / total_working_days) * 100

    # Display the suggestions
    print("\nLong Holiday Suggestions:")
    if suggestions:
        for s in suggestions:
            print(f"• Take leave on {s['leave_day']} to extend your break from {s['block_start']} to {s['block_end']} (Total {s['block_length']} days off).")
            print(f"  (This will reduce your attendance by approximately {leave_impact_percentage:.2f}%.)\n")
    else:
        print("No potential long holiday suggestions found for the given parameters.")

if __name__ == "__main__":
    main()
