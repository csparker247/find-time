# find-time
A simple tool for finding regular availability overlaps between event invitees.

## Usage
This project is available on [PyPI](https://pypi.org/project/find-time/):
```shell
python -m pip install find-time

find-time --help
```

## Availability file format

The following format is supported by `find_time.parse`:

```
# anything following a pound sign (#) is a comment
# blank lines are ignored

## entry format ##
# name:      Any string. Terminates when encountering a colon (:)
# day:       Full day names (Sunday, Monday, Tuesday, ...), three-letter 
#            abbreviations (Sun, Mon, Tue, ...), day short codes 
#            (Su, M, T, W, R, F, Sa), or day ranges (Mon-Fri, Tue-Thu, etc.).
#            Case-insensitive.
# time:      24-hour format {HH}:{MM} (e.g., 13:00) or 12-hour format with 
#            am/pm (e.g., 1pm, 1:00pm). Minutes optional - if omitted, :00 is assumed
#            (e.g., 15-17 means 15:00-17:00).
# timespan:  {time}-{time} which correlate to start and end time, e.g. 13:00-14:00
# entry:     {name}: {day} {timespan}(, {day} {timespan})*

##  example entries ##
# {name}: {day} {timespan}
John Smith: Monday 11:00-12:00

# {name}: {list of day shortcodes} {timespan}
# short codes: su,m,t,w,r,f,sa
John Smith: MWF 14:00-15:00

# {name}: {day} {timespan}, {day} {timespan}, ...
John Smith: TR 8:00-12:15, TR 15:30-17:00

# multiple entries for a single person
Jane Smith: MF 14:30-17:00
Jane Smith: W 15:30-17:00

# am/pm time format (12-hour)
Bob Johnson: Tuesday 9am-5pm
Alice Cooper: Wednesday 2:30pm-6:45pm

# shorthand time format (minutes omitted, defaults to :00)
Sahil: MWF 15-17, TR 8-10

# day ranges (Mon-Fri, Tue-Thu, etc.)
David Lee: Mon-Fri 9am-5pm
Sarah Connor: Tue-Thu 10:00-15:30

# combining features
Emily Stone: Mon-Wed 8:30am-12pm, Thu-Fri 2pm-5:30pm
```

## Special note
This tool was created quickly to evaluate availability overlaps for a small
number of invitees (one or two dozen). It is not optimized for performance and
really should not be trusted for large events.