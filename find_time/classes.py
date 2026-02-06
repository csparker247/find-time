from copy import deepcopy
from enum import Enum
from typing import Union, Iterable, Tuple, List

# Constant for minutes in a day
MINUTES_IN_DAY = 24 * 60


class Day(Enum):
    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6


def str_to_day(s: str) -> Day:
    s = s.title()
    if s in ('Sunday', 'Sun', 'Su'):
        return Day.SUNDAY
    elif s in ('Monday', 'Mon', 'M'):
        return Day.MONDAY
    elif s in ('Tuesday', 'Tue', 'T'):
        return Day.TUESDAY
    elif s in ('Wednesday', 'Wed', 'W'):
        return Day.WEDNESDAY
    elif s in ('Thursday', 'Thu', 'Th', 'R'):
        return Day.THURSDAY
    elif s in ('Friday', 'Fri', 'F'):
        return Day.FRIDAY
    elif s in ('Saturday', 'Sat', 'Sa'):
        return Day.SATURDAY


def str_to_time(s: str) -> int:
    """Converts HH:MM string to integer minutes from midnight."""
    h, _, m = s.partition(':')
    if not m:
        m = '0'
    return int(h) * 60 + int(m)


def time_to_int(time: int) -> Tuple[int, int]:
    """Converts integer minutes back to (hour, minute) tuple."""
    return divmod(time, 60)


class TimeSpan:
    _day: Day = None
    _start: int = None  # Changed to int (minutes)
    _end: int = None  # Changed to int (minutes)

    def __init__(self, day: Day, start: Union[int, str], end: Union[int, str]):
        if isinstance(day, str):
            day = str_to_day(day)
        self._day = day

        # Convert string inputs to integer minutes
        if isinstance(start, str):
            start = str_to_time(start)
        if isinstance(end, str):
            end = str_to_time(end)

        self._start = int(start)
        self._end = int(end)

        # Fix Midnight Wrapping:
        # If end time is less than start time (e.g., 23:00 to 01:00),
        # assume it wraps to the next day by adding 24 hours (1440 mins).
        if self._end < self._start:
            self._end += MINUTES_IN_DAY

    @property
    def day(self) -> Day:
        return self._day

    @property
    def start(self) -> int:
        return self._start

    @property
    def end(self) -> int:
        return self._end

    @property
    def start_int(self) -> Tuple[int, int]:
        return time_to_int(self._start)

    @property
    def end_int(self) -> Tuple[int, int]:
        # If end is > 24:00, normalize it for display
        display_end = self._end % MINUTES_IN_DAY if self._end > MINUTES_IN_DAY else self._end
        # Handle specific case where 24:00 should display as 24:00 (or 00:00 depending on preference)
        # Here we just use divmod standard behavior
        return time_to_int(display_end)

    @property
    def start_str(self) -> str:
        h, m = self.start_int
        return f'{h:02}:{m:02}'

    @property
    def end_str(self) -> str:
        h, m = self.end_int
        return f'{h:02}:{m:02}'

    def contains(self, span: 'TimeSpan') -> bool:
        return span._start >= self._start and span._end <= self._end

    def split_at_midnight(self) -> List['TimeSpan']:
        """Splits a span that crosses midnight into two spans on adjacent days."""
        if self._end <= MINUTES_IN_DAY:
            return [self]

        # Part 1: From start to Midnight (on current day)
        s1 = TimeSpan(self._day, self._start, MINUTES_IN_DAY)

        # Part 2: From Midnight to end (on next day)
        next_day_val = (self._day.value + 1) % 7
        next_day = Day(next_day_val)

        # Remainder time
        remainder = self._end - MINUTES_IN_DAY
        s2 = TimeSpan(next_day, 0, remainder)

        return [s1, s2]

    def __repr__(self):
        return f'{self._day.name} {self.start_str}-{self.end_str}'


class EventTime:
    def __init__(self, day: Day, start: int, end: int):
        self._day = day
        self._time = TimeSpan(day, start, end)
        self._available = set()
        self._not_available = set()

    @property
    def time(self) -> TimeSpan:
        return self._time

    @property
    def num_available(self) -> int:
        return len(self._available)

    @property
    def num_invited(self) -> int:
        return len(self._available) + len(self._not_available)

    @property
    def available(self) -> List[str]:
        return list(self._available)

    @property
    def not_available(self) -> List[str]:
        return list(self._not_available)

    def add_person(self, person: 'Person'):
        if person.is_available(self._time):
            self._available.add(person.name)
        else:
            self._not_available.add(person.name)

    def can_combine(self, other: 'EventTime') -> bool:
        # Check if adjacent and availability matches
        if self._time.day != other._time.day:
            return False
        if self._time.end != other._time.start:
            return False
        return (self._available == other._available and
                self._not_available == other._not_available)

    @classmethod
    def combine(cls, a: 'EventTime', b: 'EventTime') -> 'EventTime':
        day = a.time.day
        start = min(a.time.start, b.time.start)
        end = max(a.time.end, b.time.end)
        event = cls(day=day, start=start, end=end)
        event._available = deepcopy(a.available)
        event._not_available = deepcopy(a.not_available)
        return event


class Person:
    _availability = None

    def __init__(self, name: str):
        self._name = name
        self._availability = {d: [] for d in Day}

    def __repr__(self):
        return f'Attendee(name={self._name})'

    def __str__(self):
        return self._name

    @property
    def name(self):
        return self._name

    def add_availability(self, span: TimeSpan):
        # Automatically split spans that cross midnight
        # so they are filed under the correct days
        for s in span.split_at_midnight():
            self._availability[s.day].append(s)
            self._availability[s.day].sort(key=lambda x: x.start)

    def availability_by_block(self) -> Iterable[TimeSpan]:
        for day in self._availability.values():
            for span in day:
                yield span

    def availability_by_day(self):
        return self._availability.values()

    def is_available(self, span: Union[TimeSpan, EventTime]) -> bool:
        if isinstance(span, EventTime):
            span = span.time

        # Ensure we are looking at the same day
        day_spans = self._availability[span.day]

        for s in day_spans:
            if s.contains(span):
                return True
        return False
