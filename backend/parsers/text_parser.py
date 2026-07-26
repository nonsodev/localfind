"""
parsers/text_parser.py — Read plain text and markdown files.
"""


def parse_text(file_path: str) -> str:
    """Return content of a plain text file, trying common encodings."""
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    return ""
