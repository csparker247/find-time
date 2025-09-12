from pathlib import Path
from typing import Union, List

from lark import Lark, Transformer

from find_time.classes import TimeSpan, Person

_AVAIL_GRAMMAR = r"""

%import common.WS_INLINE
%import common.SH_COMMENT
%ignore WS_INLINE
%ignore SH_COMMENT

?start : _NL* _entries 

_entries: entry [_NL _entries*]
entry : name list_of_availability

name : /.*?:/

list_of_availability : availability ("," availability)*
availability : day timerange
timerange : start_time"-"end_time
start_time: _timestamp
end_time: _timestamp
_timestamp : HOUR [":" MINUTE]
HOUR : ["0"] DIGIT | "1" DIGIT | "2" "0".."3"
MINUTE : "0".."5" DIGIT
DIGIT : "0".."9"

day : LONG_DAY | _short_day_list

_short_day_list : SHORT_DAY (SHORT_DAY)*
SHORT_DAY : "su"i 
          | "m"i 
          | "t"i 
          | "w"i 
          | "th"i | "r"i 
          | "f"i 
          | "sa"i | "s"i

LONG_DAY : "sunday"i | "sun"i
         | "monday"i | "mon"i
         | "tuesday"i | "tue"i
         | "wednesday"i | "wed"i
         | "thursday"i | "thu"i
         | "friday"i | "fri"i
         | "saturday"i | "sat"i

_NL: (/\r?\n[\t ]*/ | SH_COMMENT)+
"""


class _AvailFileTransformer(Transformer):
    def start(self, start):
        return start

    def entry(self, entry):
        name, availability = entry
        availability = [TimeSpan(*a) for a in availability]
        return name, availability

    def name(self, name):
        name, = name
        return name[:-1]

    def list_of_availability(self, l):
        flat = [x for xs in l for x in xs]
        return flat

    def availability(self, l):
        day, (start_time, end_time) = l
        avail = []
        for d in day:
            avail.append((d, start_time, end_time))
        return *avail,

    def day(self, l):
        return [str(v) for v in l]

    def timerange(self, l):
        start_time, end_time = l
        return start_time, end_time

    def start_time(self, s):
        hour, minute = s
        if minute is None:
            minute = "00"
        return hour + ":" + minute

    def end_time(self, s):
        hour, minute = s
        if minute is None:
            minute = "00"
        return hour + ":" + minute


def parse(value: str) -> List[Person]:
    # read and parse file
    parser = Lark(_AVAIL_GRAMMAR, start='start')
    parsed = parser.parse(value)
    parsed = _AvailFileTransformer().transform(parsed)
    if isinstance(parsed, tuple):
        parsed = [parsed]

    # convert parsed entries to attendees
    attendees = {}
    for name, availability in parsed:
        if name in attendees.keys():
            attendee = attendees[name]
        else:
            attendee = Person(name)
            attendees[name] = attendee

        # iterate over each availability span
        for ts in availability:
            attendee.add_availability(ts)

    return list(attendees.values())


def load(path: Union[str, Path]) -> List[Person]:
    if isinstance(path, str):
        path = Path(path)

    # read and parse file
    with path.open() as f:
        parsed = parse(f.read())

    return parsed
