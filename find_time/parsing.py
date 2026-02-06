from pathlib import Path
from typing import Union, List

from lark import Lark, Transformer, v_args

from find_time.classes import TimeSpan, Person

_AVAIL_GRAMMAR = r"""

%import common.WS_INLINE
%import common.SH_COMMENT
%ignore WS_INLINE
%ignore SH_COMMENT

?start : _NL* entries _NL*

entries: entry (_NL+ entry)*
entry : name list_of_availability

name : NAME_TEXT ":"
NAME_TEXT : /[^:\n]+/

list_of_availability : availability ("," WS_INLINE* availability)*
availability : day WS_INLINE+ timerange
timerange : start_time "-" end_time
start_time: timestamp
end_time: timestamp
timestamp : HOUR ":" MINUTE | HOUR
HOUR : ("0" DIGIT | "1" DIGIT | "2" ("0".."3")) -> hour
     | DIGIT -> hour
MINUTE : ("0".."5" DIGIT) -> minute
DIGIT : "0".."9"

day : long_day | short_day_sequence

// Full day names and common 3-letter abbreviations
long_day : "sunday"i | "sun"i
         | "monday"i | "mon"i
         | "tuesday"i | "tue"i | "tues"i
         | "wednesday"i | "wed"i
         | "thursday"i | "thu"i | "thur"i | "thurs"i
         | "friday"i | "fri"i
         | "saturday"i | "sat"i

// Short day codes (must be in specific order to avoid ambiguity)
short_day_sequence : short_day+
short_day : "su"i -> sunday
          | "sa"i -> saturday
          | "m"i -> monday
          | "t"i -> tuesday
          | "w"i -> wednesday
          | "th"i -> thursday
          | "r"i -> thursday
          | "f"i -> friday

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
        return items[0]

    def long_day(self, items):
        day_str = str(items[0]).lower()
        return [self.DAY_MAP.get(day_str, day_str.capitalize())]

    def short_day_sequence(self, items):
        return items

    # Individual short day handlers
    def sunday(self, _):
        return 'Sunday'

    def monday(self, _):
        return 'Monday'

    def tuesday(self, _):
        return 'Tuesday'

    def wednesday(self, _):
        return 'Wednesday'

    def thursday(self, _):
        return 'Thursday'

    def friday(self, _):
        return 'Friday'

    def saturday(self, _):
        return 'Saturday'

    def timerange(self, items):
        start_time, end_time = items
        return start_time, end_time

    def timestamp(self, items):
        if len(items) == 1:
            # Only hour provided
            hour = items[0]
            minute = "00"
        else:
            # Hour and minute provided
            hour, minute = items
        return f"{hour}:{minute}"

    def hour(self, items):
        hour_val = ''.join(str(item) for item in items)
        return hour_val.zfill(2)

    def minute(self, items):
        minute_val = ''.join(str(item) for item in items)
        return minute_val


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