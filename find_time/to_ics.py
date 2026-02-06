import argparse
from datetime import datetime as dt, timedelta
from pathlib import Path

import find_time
from dateutil import tz
from icalendar import Calendar, Event

date_format = '%Y-%m-%d'


def next_weekday_after_date(weekday: int, date: dt):
    """
    Finds the next occurrence of a specific weekday after (or on) a given date.
    weekday: 0=Sunday, 1=Monday, ... (matching the Day enum in classes.py)
    date: The reference datetime
    """
    # date.isoweekday() returns Mon=1...Sun=7
    # weekday comes from Day enum (Sun=0...Sat=6)
    offset = (weekday - date.isoweekday()) % 7
    return date + timedelta(offset)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help='Input file')
    parser.add_argument('-o', '--output', required=True, help='Output file')
    parser.add_argument('-s', '--start-date', required=True,
                        help='Start date: YYYY-MM-DD')
    parser.add_argument('-e', '--end-date', required=True,
                        help='End date: YYYY-MM-DD')
    parser.add_argument('-t', '--timezone', help='Timezone',
                        default='US/Eastern')
    args = parser.parse_args()

    # Create Calendar
    cal = Calendar()
    cal.add('prodid', '-//Find Time Utilities//mxm.dk//')
    cal.add('version', '2.0')

    # Load people
    people = find_time.load(args.input)

    # Setup Timezone
    # gettz handles standard IANA timezone names (e.g. 'America/New_York')
    timezone = tz.gettz(args.timezone)
    if timezone is None:
        raise ValueError(f"Unknown timezone: {args.timezone}")

    # Parse start and end dates and attach the timezone info.
    # We do NOT convert to UTC here; we keep the local timezone.
    start_date = dt.strptime(args.start_date, date_format).replace(
        tzinfo=timezone)
    end_date = dt.strptime(args.end_date, date_format).replace(tzinfo=timezone)

    # RFC 5545 requires the 'UNTIL' part of an RRULE to be in UTC
    # if the DTSTART is timezone-aware.
    rrule_end = end_date.astimezone(tz.UTC)

    print(f'adding availability')
    for person in people:
        for a in person.availability_by_block():
            # 1. Calculate the date of the first occurrence
            d = next_weekday_after_date(a.day.value, start_date)

            # 2. Construct Start/End times
            h_start, m_start = a.start_int
            h_end, m_end = a.end_int

            # Combine date and time, keeping the timezone object attached.
            st = d.replace(hour=h_start, minute=m_start)
            et = d.replace(hour=h_end, minute=m_end)

            # 3. Create Event
            event = Event()
            event.add('summary', person.name)
            event.add('dtstart', st)
            event.add('dtend', et)

            # 4. Add Recurrence Rule
            # This tells the calendar to repeat weekly until the end date.
            # Because dtstart has a specific timezone (e.g. US/Eastern),
            # the calendar will respect that timezone for every recurrence,
            # handling DST changes correctly.
            event.add('rrule', {'freq': 'weekly', 'until': rrule_end})

            cal.add_component(event)

    print('writing .ics')
    # icalendar generates binary data, so we must write with 'wb'
    with Path(args.output).open('wb') as f:
        f.write(cal.to_ical())
    print('done')


if __name__ == '__main__':
    main()
