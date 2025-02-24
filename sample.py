import argparse
import datetime
import csv
import sys

# Optional Pandas import for more robust CSV parsing
PANDAS_AVAILABLE = False
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pass

# Try importing the icalendar package; if not installed, prompt the user.
try:
    from icalendar import Calendar
except ImportError:
    print("Please install the icalendar package: pip install icalendar")
    sys.exit(1)

def parse_args():
    """
    Parses command line arguments for the Long Holiday Planner tool.

    Returns:
        argparse.Namespace: An object containing the parsed arguments.
    """
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
    parser.add_argument('--include-sundays', action='store_true',
                        help="Automatically include all Sundays of the year as holidays.")
    if PANDAS_AVAILABLE:
        parser.add_argument('--use-pandas', action='store_true', help="Use pandas for CSV parsing (more robust).")
    return parser.parse_args()

def parse_ics(file_path):
    """
    Parses an ICS file to extract holiday dates.

    Args:
        file_path (str): Path to the ICS file.

    Returns:
        set: A set of datetime.date objects representing holidays.
    """
    holidays = set()
    try:
        with open(file_path, 'rb') as f:
            cal = Calendar.from_ical(f.read())
            for component in cal.walk():
                if component.name == "VEVENT":
                    dt = component.get('dtstart').dt
                    if isinstance(dt, datetime.datetime):
                        dt = dt.date()
                    holidays.add(dt)
    except FileNotFoundError:
        print(f"Error: ICS file not found at path: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing ICS file: {e}")
        sys.exit(1)
    return holidays

def parse_csv(file_path, use_pandas=False):
    """
    Parses a CSV file to extract holiday dates, assuming the first column is the date.

    Args:
        file_path (str): Path to the CSV file.
        use_pandas (bool, optional): If True and pandas is available, use pandas for parsing. Defaults to False.

    Returns:
        set: A set of datetime.date objects representing holidays.
    """
    holidays = set()
    try:
        if use_pandas and PANDAS_AVAILABLE:
            try:
                df = pd.read_csv(file_path)
                df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0]).dt.date
                holidays = set(df.iloc[:, 0])
            except Exception as e:
                print(f"Error parsing CSV with pandas, falling back to standard csv parser. Error: {e}")
                use_pandas = False # Fallback to standard CSV parser
        if not use_pandas:
            with open(file_path, newline='') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    try:
                        dt = datetime.datetime.strptime(row[0], '%Y-%m-%d').date()
                        holidays.add(dt)
                    except ValueError:
                        print(f"Warning: Skipping row due to invalid date format in CSV: {row[0]}. Ensure format is YYYY-MM-DD.")
                        continue # Skip rows that can't be parsed as valid dates
    except FileNotFoundError:
        print(f"Error: CSV file not found at path: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing CSV file: {e}")
        sys.exit(1)
    return holidays


def generate_year_dates(year):
    """
    Generates a list of all dates for a given year.

    Args:
        year (int): The year for which to generate dates.

    Returns:
        list: A list of datetime.date objects for each day of the year.
    """
    start = datetime.date(year, 1, 1)
    end = datetime.date(year, 12, 31)
    delta = datetime.timedelta(days=1)
    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += delta
    return dates

def compute_off_days(year, holidays, working_days, include_sundays=False):
    """
    Computes the set of 'off days' for the year.

    Combines provided public holidays and automatically determined weekend days
    based on the specified working days.

    Args:
        year (int): The year to compute off days for.
        holidays (set): A set of datetime.date objects representing public holidays.
        working_days (list): A list of integers representing working days (0=Mon,...,6=Sun).
        include_sundays (bool, optional): If True, all Sundays are included as holidays. Defaults to False.

    Returns:
        set: A set of datetime.date objects representing all off days (holidays + weekends).
    """
    dates = generate_year_dates(year)
    off_days = set(holidays)

    if include_sundays:
        for d in dates:
            if d.weekday() == 6:  # Sunday is weekday index 6
                off_days.add(d)
    # Days that are not in the user-defined working days are considered weekends
    for d in dates:
        if d.weekday() not in working_days:
            off_days.add(d)
    return off_days

def get_continuous_block(candidate, off_set):
    """
    Finds the continuous block of off days connected to a candidate day.

    Given a candidate day that has been added to the off_set, this function
    determines the start and end dates of the continuous block of off days
    that the candidate day is part of.

    Args:
        candidate (datetime.date): The candidate day (leave day) being considered.
        off_set (set): The set of all off days (including the candidate day).

    Returns:
        tuple: (start_date, end_date, block_length) -
                start_date (datetime.date): Start date of the continuous block.
                end_date (datetime.date): End date of the continuous block.
                block_length (int): Length of the continuous block in days.
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
    Identifies potential leave days to create long holidays.

    Scans each working day of the year, and if taking it as leave would
    extend a continuous block of off days to meet or exceed the threshold,
    it's recorded as a suggestion.

    Args:
        year (int): The year to find leave suggestions for.
        off_days (set): Set of all off days in the year.
        working_days (list): List of working day indices.
        threshold (int): Minimum length of continuous off days for a suggestion.

    Returns:
        list: A list of dictionaries, each representing a leave suggestion with:
                'leave_day', 'block_start', 'block_end', 'block_length'.
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
    """
    Main function to parse arguments, process holiday files,
    generate leave suggestions, and display results.
    """
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
        holidays = parse_csv(args.file, use_pandas=args.use_pandas if PANDAS_AVAILABLE else False) # Use pandas if available and flag is set
    else:
        print("Unsupported file type. Use 'ics' or 'csv'.")
        return

    # Compute off days (holidays + weekends based on working_days + Sundays if requested)
    off_days = compute_off_days(args.year, holidays, working_days, args.include_sundays)

    # Generate leave suggestions by checking if taking a leave on a working day
    # would extend a continuous off period to at least the threshold
    suggestions = find_leave_suggestions(args.year, off_days, working_days, args.threshold)

    # Calculate total number of working days in the year (by definition: days with weekday in working_days)
    total_working_days = sum(1 for d in generate_year_dates(args.year) if d.weekday() in working_days)
    # Impact per leave day on attendance
    leave_impact_percentage = (1 / total_working_days) * 100

    # Display the suggestions
    print("\n✨ **Long Holiday Suggestions** ✨")
    if suggestions:
        for s in suggestions:
            print(f"  📅 Take leave on: {s['leave_day'].strftime('%Y-%m-%d')} ({s['leave_day'].strftime('%A')})")
            print(f"   ➡️ Extends break from: {s['block_start'].strftime('%Y-%m-%d')} to {s['block_end'].strftime('%Y-%m-%d')} (Total {s['block_length']} days off)")
            print(f"   📉 Attendance impact (per leave day): Approximately {leave_impact_percentage:.2f}%\n")
    else:
        print("No potential long holiday suggestions found for the given parameters.")

if __name__ == "__main__":
    main()