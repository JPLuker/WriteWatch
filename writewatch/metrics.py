"""Selectable metrics derived only from aggregate session statistics."""
from datetime import datetime

CATALOG = {
    'time': ('Session time', 'Manual session clock, excluding pauses; not active typing time.'),
    'net': ('Net words', 'Saved additions minus removals; may be negative.'),
    'added': ('Words added', 'Cumulative additions between observed saves, including saved undos.'),
    'removed': ('Words removed', 'Cumulative removals between observed saves.'),
    'changes': ('Total word changes', 'Words added plus removed; not unique words or keystrokes.'),
    'net_pace': ('Net words per minute', 'Net words divided by session time; not typing speed.'),
    'change_pace': ('Word changes per minute', 'Additions plus removals divided by session time.'),
    'observations': ('Observed changes', 'Observations with word-occurrence changes; not every save.'),
    'change_size': ('Word changes per observation', 'Average additions plus removals per changed observation.'),
    'removed_share': ('Removal share', 'Removed words as a percentage of all observed word changes.'),
    'pages': ('Pages', 'Self-reported pages or explicitly labeled estimates, when a page goal is used.'),
    'goal': ('Goal progress', 'The target and progress toward it, when a goal is set.'),
}


def defaults(mode):
    return ['time', 'net'] + (['added', 'removed'] if mode == 'Revision' else []) + ['pages', 'goal']


def default_preferences():
    return {mode: defaults(mode) for mode in ('Writing', 'Revision')}


def validate_preferences(value):
    if not isinstance(value, dict) or set(value) != {'Writing', 'Revision'}:
        raise ValueError('Invalid metric preferences')
    for enabled in value.values():
        if not isinstance(enabled, list) or any(not isinstance(key, str) or key not in CATALOG for key in enabled) or len(enabled) != len(set(enabled)):
            raise ValueError('Invalid metric selection')
    return value


def rows(session, enabled):
    """Return (key, label, value); unavailable data is omitted, never invented."""
    values = {'time': f'{int(session.seconds)//60}m {int(session.seconds)%60:02d}s', 'net': f'{session.net:+,}', 'observations': f'{session.saves:,}'}
    if session.seconds > 0:
        values['net_pace'] = f'{session.net * 60 / session.seconds:+,.1f}'
    if session.revision_metrics:
        changes = session.added + session.removed
        values.update(added=f'{session.added:,}', removed=f'{session.removed:,}', changes=f'{changes:,}')
        if session.seconds > 0:
            values['change_pace'] = f'{changes * 60 / session.seconds:,.1f}'
        if session.saves > 0:
            values['change_size'] = f'{changes / session.saves:,.1f}'
        if changes > 0:
            values['removed_share'] = f'{session.removed * 100 / changes:.1f}%'
    if session.unit in ('pages', 'estimated_pages'):
        values['pages'] = f'{round(session.page_count, 1) or 0:,.1f}'
    if session.goal:
        values['goal'] = f'{round(session.progress * 100)}% · {session.goal_label}'
    result = []
    for key, (title, _) in CATALOG.items():
        if key in enabled and key in values:
            if key == 'pages':
                title = 'Estimated pages' if session.unit == 'estimated_pages' else 'Pages (self-reported)'
            result.append((key, title, values[key]))
    return result


def summary(session, enabled):
    date = datetime.fromisoformat(session.started).strftime('%b %d, %Y')
    heading = 'Session complete' if session.status == 'done' else 'Interrupted session'
    lines = [f'WriteWatch · {date}', f'Revision · {heading}' if session.mode == 'Revision' else heading]
    for key, title, value in rows(session, enabled):
        lines.append(f'{value} net words' if key == 'net' else f'{title}: {value}')
    return '\n'.join(lines + ['#WriteWatch'])
