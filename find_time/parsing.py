from pathlib import Path
from typing import Union, List

from lark import Lark, Transformer, v_args

from find_time.classes import TimeSpan, Person

_AVAIL_GRAMMAR = r"""

%import common.WS_INLINE
%import common.SH_COMMENT
%ignore SH_COMMENT

?start : _NL* entries _NL*

entries: entry (_NL+ entry)*
entry : name _WS list_of_availability _WS?

name : NAME_TEXT ":"
NAME_TEXT : /[^:\n]+/

list_of_availability : availability (_WS? "," _WS? availability)*
availability : day _WS timerange
timerange : start_time _WS? ("-"|"–") _WS? end_time
start_time: timestamp
end_time: timestamp
timestamp : HOUR ":" MINUTE PERIOD? | HOUR PERIOD?
HOUR.2 : /[0-2]?[0-9]/
MINUTE.2 : /[0-5][0-9]/
PERIOD : "am"i | "pm"i

// Inline whitespace (spaces/tabs) - can be multiple
_WS: WS_INLINE+

day : day_range | long_day | short_day_sequence

// Day ranges (e.g., Mon-Fri, Tuesday-Thursday)
day_range : long_day_single ("-"|"–") long_day_single

// Full day names and common 3-letter abbreviations
long_day_single : LONG_DAY_NAME

LONG_DAY_NAME : "sunday"i | "sun"i
              | "monday"i | "mon"i
              | "tuesday"i | "tue"i | "tues"i
              | "wednesday"i | "wed"i
              | "thursday"i | "thu"i | "thur"i | "thurs"i
              | "friday"i | "fri"i
              | "saturday"i | "sat"i

long_day : long_day_single

// Short day codes as a single pattern
short_day_sequence : SHORT_DAY_CODES
SHORT_DAY_CODES : /(su|sa|th|[mtwrf])+/i

// Newlines, blank lines (with optional indentation), and comments
_NL: (/\r?\n[\t ]*/ | SH_COMMENT)+
"""


class _AvailFileTransformer(Transformer):
    """Transform parsed grammar into Person objects with availability."""

    # Day name mappings
    DAY_MAP = {
        'sunday': 'Sunday', 'sun': 'Sunday', 'su': 'Sunday',
        'monday': 'Monday', 'mon': 'Monday', 'm': 'Monday',
        'tuesday': 'Tuesday', 'tue': 'Tuesday', 'tues': 'Tuesday', 't': 'Tuesday',
        'wednesday': 'Wednesday', 'wed': 'Wednesday', 'w': 'Wednesday',
        'thursday': 'Thursday', 'thu': 'Thursday', 'thur': 'Thursday',
        'thurs': 'Thursday', 'th': 'Thursday', 'r': 'Thursday',
        'friday': 'Friday', 'fri': 'Friday', 'f': 'Friday',
        'saturday': 'Saturday', 'sat': 'Saturday', 'sa': 'Saturday',
    }

    # Day order for ranges
    DAY_ORDER = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    def start(self, items):
        return items[0] if items else []

    def entries(self, items):
        return items

    def entry(self, items):
        name, availability = items
        availability = [TimeSpan(*a) for a in availability]
        return name, availability

    def name(self, items):
        name_text = items[0]
        return str(name_text).strip()

    def list_of_availability(self, items):
        # Flatten list of availability spans
        flat = []
        for item in items:
            if isinstance(item, list):
                flat.extend(item)
            else:
                flat.append(item)
        return flat

    def availability(self, items):
        days, (start_time, end_time) = items
        avail = []
        for day in days:
            avail.append((day, start_time, end_time))
        return avail

    def day(self, items):
        day_result = items[0]
        # If it's a string (single day), wrap in list
        if isinstance(day_result, str):
            return [day_result]
        # If it's already a list (day range or short sequence), return as-is
        return day_result

    def long_day(self, items):
        return items[0]

    def long_day_single(self, items):
        day_str = str(items[0]).lower()
        return self.DAY_MAP.get(day_str, day_str.lower())

    def day_range(self, items):
        start_day, end_day = items
        start_idx = self.DAY_ORDER.index(start_day)
        end_idx = self.DAY_ORDER.index(end_day)

        # Handle wraparound (e.g., Fri-Mon wraps around the week)
        if start_idx <= end_idx:
            return self.DAY_ORDER[start_idx:end_idx + 1]
        else:
            return self.DAY_ORDER[start_idx:] + self.DAY_ORDER[:end_idx + 1]

    def short_day_sequence(self, items):
        # Parse the combined short code string (e.g., "MWF" -> ["Monday", "Wednesday", "Friday"])
        short_code_map = {
            'su': 'Sunday',
            'sa': 'Saturday',
            'm': 'Monday',
            't': 'Tuesday',
            'w': 'Wednesday',
            'th': 'Thursday',
            'r': 'Thursday',
            'f': 'Friday'
        }

        # Get the matched string
        codes_str = str(items[0]).lower()

        # Parse the string to extract individual day codes
        result = []
        i = 0
        while i < len(codes_str):
            # Try two-character codes first (su, sa, th)
            if i + 1 < len(codes_str) and codes_str[i:i+2] in short_code_map:
                result.append(short_code_map[codes_str[i:i+2]])
                i += 2
            # Then single-character codes
            elif codes_str[i] in short_code_map:
                result.append(short_code_map[codes_str[i]])
                i += 1
            else:
                i += 1  # Skip unknown characters

        return result

    def timerange(self, items):
        start_time, end_time = items
        return start_time, end_time

    def start_time(self, items):
        # Just unwrap - the timestamp has already been transformed
        return items[0]

    def end_time(self, items):
        # Just unwrap - the timestamp has already been transformed
        return items[0]

    def timestamp(self, items):
        hour = None
        minute = "00"
        period = None

        # Parse items - HOUR and MINUTE come as Token objects, period as string
        for item in items:
            item_str = str(item).lower()
            if item_str in ('am', 'pm'):
                period = item_str
            elif hour is None:
                # This is the HOUR token
                hour = str(item)
                # Validate hour is in valid range (0-23)
                hour_int = int(hour)
                if hour_int > 23:
                    raise ValueError(f"Invalid hour: {hour}")
            else:
                # This is the MINUTE token
                minute = str(item)

        # Ensure hour is zero-padded
        if hour:
            hour = hour.zfill(2)

        # Convert to 24-hour format if AM/PM specified
        if period:
            hour_int = int(hour)
            if period == 'pm' and hour_int != 12:
                hour_int += 12
            elif period == 'am' and hour_int == 12:
                hour_int = 0
            hour = str(hour_int).zfill(2)

        return f"{hour}:{minute}"


def parse(value: str) -> List[Person]:
    """Parse availability string into list of Person objects.

    Args:
        value: String containing availability entries

    Returns:
        List of Person objects with their availability timespans

    Raises:
        lark.exceptions.LarkError: If parsing fails
    """
    # Create parser
    parser = Lark(_AVAIL_GRAMMAR, start='start', parser='lalr')

    # Parse and transform
    parsed = parser.parse(value)
    transformed = _AvailFileTransformer().transform(parsed)

    # Ensure we have a list
    if not transformed:
        return []
    if not isinstance(transformed, list):
        transformed = [transformed]

    # Convert parsed entries to Person objects
    attendees = {}
    for name, availability in transformed:
        if name in attendees:
            attendee = attendees[name]
        else:
            attendee = Person(name)
            attendees[name] = attendee

        # Add each availability span
        for ts in availability:
            attendee.add_availability(ts)

    return list(attendees.values())


def load(path: Union[str, Path]) -> List[Person]:
    """Load and parse availability file.

    Args:
        path: Path to availability file

    Returns:
        List of Person objects with their availability

    Raises:
        FileNotFoundError: If file doesn't exist
        lark.exceptions.LarkError: If parsing fails
    """
    if isinstance(path, str):
        path = Path(path)

    with path.open() as f:
        return parse(f.read())