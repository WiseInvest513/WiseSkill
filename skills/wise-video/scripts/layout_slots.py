#!/usr/bin/env python3
"""Generate deterministic foreground slots and CSS text roles for Wise explainers."""
import argparse
import json
import math
from pathlib import Path


def load_profile(path=None):
    target = Path(path) if path else Path(__file__).resolve().parents[1] / 'assets/layout/wise-layout-tokens.json'
    return json.loads(target.read_text(encoding='utf-8'))


def make_slots(count, region, column_gap=48, row_gap=32, columns=None):
    """1/2/3 items form a centered row; 4 items default to a centered 2x2 grid.

    Each item owns its complete image+text group. Incomplete final rows center
    within the same region. Coordinates are canvas-relative; subgroups can pass
    their own containing rectangle. No asset size or text fit is inferred.
    """
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError('count must be a positive integer')
    if columns is None:
        if count > 4:
            raise ValueError('For more than four items, choose columns explicitly from the content relationship')
        columns = 2 if count == 4 else count
    if isinstance(columns, bool) or not isinstance(columns, int) or not 1 <= columns <= count:
        raise ValueError('columns must be an integer between 1 and count')
    x, y, width, height = (float(region[k]) for k in ('x', 'y', 'width', 'height'))
    if not all(math.isfinite(v) for v in (x, y, width, height, column_gap, row_gap)):
        raise ValueError('geometry must be finite')
    if width <= 0 or height <= 0 or min(column_gap, row_gap) < 0:
        raise ValueError('region must be positive and gaps non-negative')
    rows = math.ceil(count / columns)
    slot_w = (width - column_gap * (columns - 1)) / columns
    slot_h = (height - row_gap * (rows - 1)) / rows
    if min(slot_w, slot_h) <= 0:
        raise ValueError('gaps leave no space for items')
    slots = []
    for i in range(count):
        row, col = divmod(i, columns)
        members = min(columns, count - row * columns)
        row_w = members * slot_w + (members - 1) * column_gap
        sx = x + (width - row_w) / 2 + col * (slot_w + column_gap)
        sy = y + row * (slot_h + row_gap)
        slots.append({'index': i, 'row': row, 'column': col, 'x': sx, 'y': sy,
                      'width': slot_w, 'height': slot_h,
                      'center_x': sx + slot_w / 2, 'center_y': sy + slot_h / 2})
    return slots


def text_css(profile):
    rules = []
    for role, style in profile['typography'].items():
        rules.append(f'[data-text-role="{role}"]' + '{' +
                     f'font-size:{style["font_size"]}px;font-weight:{style["font_weight"]};' +
                     f'line-height:{style["line_height"]};' + '}')
    return '\n'.join(rules)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('count', type=int, nargs='?')
    parser.add_argument('--profile')
    parser.add_argument('--region', nargs=4, type=float, metavar=('X', 'Y', 'W', 'H'))
    parser.add_argument('--columns', type=int)
    parser.add_argument('--gap', type=float)
    parser.add_argument('--row-gap', type=float)
    parser.add_argument('--css', action='store_true')
    args = parser.parse_args()
    profile = load_profile(args.profile)
    if args.css:
        print(text_css(profile))
        return
    if args.count is None:
        parser.error('count is required unless --css is used')
    region = dict(zip(('x', 'y', 'width', 'height'), args.region)) if args.region else profile['regions']['content']
    try:
        slots = make_slots(args.count, region,
                           profile['grid']['column_gap'] if args.gap is None else args.gap,
                           profile['grid']['row_gap'] if args.row_gap is None else args.row_gap,
                           args.columns)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps({'profile': profile['profile'], 'region': region, 'slots': slots}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
