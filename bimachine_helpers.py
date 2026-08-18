import re

ICON_LIGATURE_RE = re.compile(r"^[a-z_]+$")
INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def extract_name(row):
    raw = row.locator("td").nth(0).inner_text()
    lines = [line.strip() for line in raw.split("\n") if line.strip()]
    for line in lines:
        if not ICON_LIGATURE_RE.match(line):
            return line
    return lines[0] if lines else "?"


def sanitize_filename(name):
    return INVALID_FILENAME_CHARS.sub("-", name).strip()
