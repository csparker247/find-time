import argparse
from functools import partial

import find_time
from find_time.classes import str_to_day

sorting = {
    'none': lambda x: x,
    'available<': partial(sorted, key=lambda x: x.num_available),
    'available>': partial(sorted, key=lambda x: x.num_available, reverse=True),
    'length<': partial(sorted, key=lambda x: x.time.end - x.time.start),
    'length>': partial(sorted, key=lambda x: x.time.end - x.time.start,
                       reverse=True),
    'start<': partial(sorted,
                      key=lambda x: x.time.day.value * 1440 + x.time.start),
    'start>': partial(sorted,
                      key=lambda x: x.time.day.value * 1440 + x.time.start,
                      reverse=True),
}

filters = {
    'minh': lambda x, m: x.time.end - x.time.start >= m,
    'maxh': lambda x, m: x.time.end - x.time.start <= m,
}


def event_filter(s: str):
    if s.lower() == 'none':
        return lambda x: True

    key, _, val = s.partition('=')
    fn = partial(filters.get(key), m=float(val))
    return fn


def build_filter(filter_list):
    def apply_filter(x):
        for f in filter_list:
            fn = event_filter(f)
            if not fn(x):
                return False
        return True

    return apply_filter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, metavar='PATH',
                        help='path to availability file')
    parser.add_argument('--sort', nargs='+', choices=sorting.keys(),
                        type=str.lower, default=['available>'],
                        metavar='FN',
                        help='Sort availability blocks by the provided '
                             'function. Can be specified multiple times. '
                             'Sorting will be applied in order of appearance. '
                             "Options: 'none', 'available<', 'available>', "
                             "'length<', 'length>'.")
    parser.add_argument('--filter', nargs='+', default=['none'], metavar='FN',
                        help='Filter time blocks. Options: '
                             "'none', 'minh', 'maxh'")
    parser.add_argument('--days', nargs='+', type=str, metavar='D',
                        default=['M', 'T', 'W', 'R', 'F'],
                        help='Days of the week to evaluate. One or more of: '
                             "'Su', 'M', 'T', 'W', 'R', 'F', 'Sa'")
    parser.add_argument('--hours', nargs=2, type=int, default=[8, 17],
                        metavar=('START', 'END'),
                        help='Start and end hours to evaluate, in 24hr time.')
    parser.add_argument('--blocks-per-hour', type=int, default=4, metavar='N',
                        help='Number of time blocks-per-hour to check')
    parser.add_argument('--merge', action=argparse.BooleanOptionalAction,
                        default=True, help='merge adjacent time blocks')
    parser.add_argument('--show-empty', action=argparse.BooleanOptionalAction,
                        default=False,
                        help='show time blocks with no availability')
    parser.add_argument('--nprint', type=int, default=10, metavar='N',
                        help='Number of results to print. If < 0, print all.')
    args = parser.parse_args()

    # load attendees
    invitees = find_time.load(args.input)

    # evaluate time blocks and merge them based on availability
    days = [str_to_day(s) for s in args.days]
    hours = range(*args.hours)
    bph = args.blocks_per_hour
    merge = args.merge
    blocks = find_time.calc_overlap(invitees,
                                    days=days,
                                    hours=hours,
                                    blocks_per_hour=bph,
                                    merge=merge)

    # sort time blocks
    for sort_type in args.sort:
        blocks = sorting[sort_type](blocks)

    # construct filter functions
    apply_filter = build_filter(args.filter)

    # print all blocks
    if args.nprint < 0:
        args.nprint = None

    # print time blocks
    # idx != enumerate index
    idx = 0
    for block in blocks:
        # we've printed the limit
        if args.nprint is not None and idx >= args.nprint:
            break

        # skip empty as requested
        if not args.show_empty and block.num_available == 0:
            continue

        # skip values which don't pass the filter
        if not apply_filter(block):
            continue

        idx += 1
        print(
            f'{idx}) {block.time} ({block.num_available} of {block.num_invited} available):')
        print(' - Available:', ', '.join(sorted(block.available)))
        print(' - Unavailable:', ', '.join(sorted(block.not_available)))
        print()


if __name__ == '__main__':
    main()
