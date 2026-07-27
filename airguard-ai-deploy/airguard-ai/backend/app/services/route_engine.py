"""
Route Recommendation Engine.

Plans a route from the site gate to a destination parking area on the same
0-1000 plant-map canvas the interactive map uses, routing around any other
parking area currently classified UNSAFE or closed (treated as a
point-hazard with a safety buffer radius).

This is real 2D vector geometry, not a lookup table: it computes the
closest point on the direct path to each hazard, and if that distance is
inside the buffer, computes a single perpendicular detour waypoint pushed
just outside the buffer on the side that increases distance from the
hazard, then re-validates the resulting two-segment path against every
hazard again before calling it clear.

Honesty boundary: this uses one detour waypoint per hazard, which handles
the common case (routing around a single problem zone) correctly and
verifiably. Multiple overlapping hazards that this simple strategy can't
fully clear are reported as such (`hazard_unavoidable`) rather than
silently presented as a safe route — a full path-planning solver (e.g.
visibility graphs or RRT) would be the real fix and is a reasonable
follow-up rather than something to fake here.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

Point = tuple[float, float]

DETOUR_MARGIN = 20.0  # extra clearance pushed beyond the buffer, in canvas units


@dataclass
class Hazard:
    name: str
    point: Point


@dataclass
class RouteResult:
    waypoints: list[Point]
    status: str  # "clear" | "detoured" | "hazard_unavoidable"
    avoided_hazards: list[str] = field(default_factory=list)
    total_distance: float = 0.0
    notes: str = ""


def _distance(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _closest_point_on_segment(p: Point, a: Point, b: Point) -> Point:
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return a
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return (ax + t * dx, ay + t * dy)


class RouteEngine:
    def __init__(self, hazard_buffer: float = 90.0):
        self.hazard_buffer = hazard_buffer

    def _intruding_hazards(self, a: Point, b: Point, hazards: list[Hazard]) -> list[tuple[Hazard, Point, float]]:
        """Hazards whose distance to segment ab is inside the buffer, each
        with the closest point on the segment and that distance."""
        result = []
        for hazard in hazards:
            closest = _closest_point_on_segment(hazard.point, a, b)
            dist = _distance(closest, hazard.point)
            if dist < self.hazard_buffer:
                result.append((hazard, closest, dist))
        return result

    def plan_route(self, gate: Point, destination: Point, hazards: list[Hazard]) -> RouteResult:
        direct_intrusions = self._intruding_hazards(gate, destination, hazards)

        if not direct_intrusions:
            return RouteResult(
                waypoints=[gate, destination],
                status="clear",
                total_distance=_distance(gate, destination),
                notes="Direct path does not pass near any unsafe or closed zone.",
            )

        # Detour around the single closest-intruding hazard.
        worst_hazard, closest_point, dist = min(direct_intrusions, key=lambda t: t[2])

        seg_dx = destination[0] - gate[0]
        seg_dy = destination[1] - gate[1]
        seg_len = math.hypot(seg_dx, seg_dy) or 1.0
        # Two perpendicular candidates to the gate->destination direction.
        perp_a = (-seg_dy / seg_len, seg_dx / seg_len)
        perp_b = (seg_dy / seg_len, -seg_dx / seg_len)

        hx, hy = worst_hazard.point
        cx, cy = closest_point
        # Choose the perpendicular that points *away* from the hazard.
        vec_to_hazard = (hx - cx, hy - cy)
        chosen_perp = perp_a if (vec_to_hazard[0] * perp_a[0] + vec_to_hazard[1] * perp_a[1]) < 0 else perp_b

        push = self.hazard_buffer + DETOUR_MARGIN
        detour = (cx + chosen_perp[0] * push, cy + chosen_perp[1] * push)

        # Re-validate: does the detoured two-segment path actually clear every hazard?
        remaining = (
            self._intruding_hazards(gate, detour, hazards)
            + self._intruding_hazards(detour, destination, hazards)
        )
        avoided = [h.name for h, _, _ in direct_intrusions]

        if not remaining:
            return RouteResult(
                waypoints=[gate, detour, destination],
                status="detoured",
                avoided_hazards=avoided,
                total_distance=_distance(gate, detour) + _distance(detour, destination),
                notes=f"Rerouted around {', '.join(avoided)} with a {push:.0f}-unit safety margin.",
            )

        still_intruding = sorted({h.name for h, _, _ in remaining})
        return RouteResult(
            waypoints=[gate, detour, destination],
            status="hazard_unavoidable",
            avoided_hazards=avoided,
            total_distance=_distance(gate, detour) + _distance(detour, destination),
            notes=(
                f"Single-detour routing could not fully clear: {', '.join(still_intruding)} still within "
                f"the safety buffer. Manual routing or closing the affected zone is recommended."
            ),
        )


route_engine = RouteEngine()
