#!/usr/bin/env python3
"""Strict dotted-numeric schema version parsing shared by project validators."""
import re

_VERSION_RE = re.compile(r'^\d+(?:\.\d+)*$')


def parse_version(value):
    """Return a tuple of ints for strict dotted-numeric versions like '1.8'."""
    if not isinstance(value, str) or not _VERSION_RE.fullmatch(value):
        raise ValueError('must use dotted numeric format such as 1.8')
    return tuple(int(part) for part in value.split('.'))


def version_at_least(value, target):
    current = parse_version(value)
    wanted = parse_version(target)
    width = max(len(current), len(wanted))
    return current + (0,) * (width - len(current)) >= wanted + (0,) * (width - len(wanted))
