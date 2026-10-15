"""Plain-text tables."""

def render(rows):
    widths = [max(len(str(r[i])) for r in rows) for i in range(len(rows[0]))]
    return "\n".join(
        "  ".join(str(c).ljust(w) for c, w in zip(r, widths)).rstrip() for r in rows
    )
