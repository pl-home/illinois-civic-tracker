"""Explicit, auditable noise flags. Hidden records remain indexed."""
import re

def ceremonial(description):
    value=description.strip().upper()
    return (value.startswith(('CONGRATS-','MEMORIAL-')) or "MEM'L" in value or
            bool(re.search(r'(?:MONTH|DAY|WEEK|HWY|HGWY|NAME)$',value)) or 'READING ROOM' in value)

def shell(description,synopsis):
    return description.strip().upper().endswith('-TECH') or description.lstrip().startswith('$') or 'technical change' in synopsis.casefold()
