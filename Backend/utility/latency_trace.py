"""Sequential latency steps (each measured once; sums should match wall-clock total)."""

from __future__ import annotations

from typing import Any


class LatencyTrace:
    def __init__(self) -> None:
        self._steps: list[dict[str, Any]] = []

    def record(self, label: str, sec: float) -> None:
        self._steps.append(
            {"step": len(self._steps) + 1, "label": label, "sec": round(float(sec), 3)}
        )

    def extend(self, steps: list[dict[str, Any]]) -> None:
        for s in steps:
            sec = s.get("sec")
            if sec is None:
                continue
            self.record(str(s.get("label") or "step"), float(sec))

    def sum_sec(self) -> float:
        return round(sum(float(s["sec"]) for s in self._steps), 3)

    def to_list(self) -> list[dict[str, Any]]:
        return [dict(s) for s in self._steps]

    @classmethod
    def from_label_sec_pairs(cls, pairs: list[tuple[str, float]]) -> LatencyTrace:
        t = cls()
        for label, sec in pairs:
            if sec is None or float(sec) <= 0:
                continue
            t.record(label, float(sec))
        return t

    def append_gap_if_needed(self, wall_total: float, *, label: str = "Other / overhead") -> None:
        gap = round(float(wall_total) - self.sum_sec(), 3)
        if gap > 0.01:
            self.record(label, gap)
        elif gap < -0.01:
            # Steps slightly exceed wall (rounding); do not inflate totals.
            pass
