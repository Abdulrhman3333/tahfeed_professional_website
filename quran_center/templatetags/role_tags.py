from django import template

register = template.Library()


@register.filter
def dict_get(value, key):
    if isinstance(value, dict):
        return value.get(key)
    return None


@register.filter
def short_name(full_name):
    """Abbreviate a three-part Arabic name to save horizontal space.

    "أحمد عبدالله العتيبي" → "أحمد ع. العتيبي"
    First name full, middle name(s) → first letter + ".", last name full.
    Falls back gracefully for names with fewer parts.
    """
    if not full_name:
        return ''
    parts = full_name.split()
    if len(parts) <= 2:
        return full_name
    first = parts[0]
    middle = ' '.join(p[0] + '.' for p in parts[1:-1])
    last = parts[-1]
    return f'{first} {middle} {last}'


@register.filter
def status_css_class(status):
    """Map a stored status value to a CSS class for color-coded buttons."""
    return {
        'حاضر': 'status-present',
        'غائب': 'status-absent',
        'متأخر': 'status-late',
        'مستأذن': 'status-excused',
        'غياب بعذر': 'status-excused-absent',
    }.get(status, 'status-present')


@register.filter
def status_abbrev(status):
    """Map a stored status value to the short label shown on buttons."""
    return {
        'حاضر': 'ح',
        'غائب': 'غ',
        'متأخر': 'تأ',
        'مستأذن': 'نص',
        'غياب بعذر': 'عذر',
    }.get(status, 'ح')


@register.filter
def status_display_name(status):
    """Map a stored value to the human-readable display label.

    Preserves the existing quirk where stored 'مستأذن' displays as 'منصرف'.
    """
    return {
        'حاضر': 'حاضر',
        'غائب': 'غائب',
        'متأخر': 'متأخر',
        'مستأذن': 'منصرف',
        'غياب بعذر': 'غياب بعذر',
    }.get(status, status)
