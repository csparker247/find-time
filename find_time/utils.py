from typing import List, Iterable, Union

from find_time.classes import Person, Day, EventTime


def print_avail(attendees: Union[Person, Iterable[Person]]):
    if isinstance(attendees, Person):
        attendees = (attendees,)
    for person in attendees:
        print(f'{person.name}:')
        for day_spans in person.availability_by_day():
            if len(day_spans) == 0:
                continue
            day = day_spans[0].day
            print(f' - {day.name.title()}:', ', '.join(
                [f'{span.start_str}-{span.end_str}' for span in day_spans]))


def calc_overlap(people: Iterable[Person], days: Iterable[Day] = Day,
                 hours: Iterable[int] = range(0, 24), blocks_per_hour: int = 4,
                 merge: bool = False) -> List[EventTime]:
    # Switch to minutes for integer precision
    # Assumes blocks_per_hour divides 60 evenly (e.g. 1, 2, 4, 6, 12, etc.)
    block_duration_mins = 60 // blocks_per_hour

    # collect blocks
    blocks = []
    for day in days:
        for start_hour in hours:
            # Generate sub-blocks in minutes
            for i in range(blocks_per_hour):
                start_mins = (start_hour * 60) + (i * block_duration_mins)
                end_mins = start_mins + block_duration_mins

                event = EventTime(day=day, start=start_mins, end=end_mins)
                for person in people:
                    event.add_person(person)
                blocks.append(event)

    if merge:
        blocks = merge_adjacent(blocks)
    return blocks


def merge_adjacent(blocks: Iterable[EventTime]) -> List[EventTime]:
    """Merges adjacent time blocks where availability does not differ."""
    if not blocks:
        return []

    combined = []
    current = blocks[0]
    for block in blocks[1:]:
        if current.can_combine(block):
            current = EventTime.combine(current, block)
        else:
            combined.append(current)
            current = block
    combined.append(current)
    return combined
