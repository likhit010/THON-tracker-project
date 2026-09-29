"""Terminal formatting helpers (no third-party libraries needed)."""
from __future__ import annotations

from typing import Iterable, Sequence

BLUE, GOLD, GREEN, BOLD, RESET = "\033[94m", "\033[93m", "\033[92m", "\033[1m", "\033[0m"


def money(x: float) -> str:
    return f"${x:,.2f}"


def progress_bar(percent: float, width: int = 30) -> str:
    filled = int(min(percent, 100) / 100 * width)
    color = GREEN if percent >= 100 else GOLD if percent >= 50 else BLUE
    return f"{color}{'█' * filled}{'░' * (width - filled)}{RESET} {percent:5.1f}%"


def table(headers: Sequence[str], rows: Iterable[Sequence], align: str | None = None) -> str:
    rows = [[str(c) for c in r] for r in rows]
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(headers)]
    align = align or "l" * len(headers)

    def fmt(cells):
        return "  ".join(c.rjust(w) if a == "r" else c.ljust(w) for c, w, a in zip(cells, widths, align))

    line = "  ".join("─" * w for w in widths)
    return "\n".join([BOLD + fmt(headers) + RESET, line, *(fmt(r) for r in rows)])


def banner(text: str) -> str:
    return f"\n{BOLD}{BLUE}{'═' * 60}\n  {text}\n{'═' * 60}{RESET}"


def spark(values: list[float]) -> str:
    """Tiny sparkline chart for daily totals."""
    ticks = "▁▂▃▄▅▆▇█"
    if not values:
        return ""
    hi = max(values) or 1
    return "".join(ticks[min(int(v / hi * (len(ticks) - 1)), len(ticks) - 1)] for v in values)
