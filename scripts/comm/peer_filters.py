import re

def is_common_equity(sym: str) -> bool:
    s = sym.upper()
    # filter out preferreds/notes/units/partials
    bad = [
        r".*-P[A-Z]$",  # T-PA, etc
        r".*[.-][A-Z]+$",  # CMCSA.A etc
        r".*[0-9]$",       # trailing digits often series/notes
        r"^TBB$|^TBC$|^VZA$|^T-PC$|^T-PA$",
    ]
    return not any(re.match(p, s) for p in bad)
