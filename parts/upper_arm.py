"""Compact dual-plate upper arm with internal elbow MG90S cradle at distal end."""

from __future__ import annotations

import Part

import params as P
from cad.sketch_pad import cut, cyl, fuse, pad_xy, rotate, translate
from parts.joint_features import bearing_seat, insert_m3, servo_body_pocket, shaft_clearance, soft_stop_pad, tab_holes


def _plate(length: float, height: float) -> Part.Shape:
    return pad_xy([(0, 0), (length, 0), (length, height), (0, height)], P.PLATE_T)


def _split(length, male, female):
    adds, cuts = [], []
    sp = P.SPLIT_BOLT_SPACING
    corners = [(-sp / 2, -sp / 2), (sp / 2, -sp / 2), (-sp / 2, sp / 2), (sp / 2, sp / 2)]
    # through cable in mid plane
    cuts.append(cyl(P.CABLE_HOLE_D / 2, length + 2, (-1, 0, 0), "x"))
    if male:
        for py, pz in corners:
            adds.append(cyl(P.DOWEL_D / 2 - 0.1, 4.5, (length, py, pz), "x"))
            cuts.append(cyl(P.M3["clear_d"] / 2, 20, (length - 16, py, pz), "x"))
            cuts.append(cyl(P.M3["head_d"] / 2, P.M3["head_h"] + 0.3, (length - 3, py, pz), "x"))
    if female:
        for py, pz in corners:
            cuts.append(cyl(P.DOWEL_D / 2 + 0.15, 5, (-0.4, py, pz), "x"))
            cuts.append(insert_m3((-0.2, py, pz), "x"))
    return adds, cuts


def make_upper_arm_a() -> Part.Shape:
    """Proximal dual plates + spacers (assembled as one printable pair fused for export simplicity)."""
    L = P.UPPER_SEG_A
    h = P.LINK_HEIGHT
    yi = P.LINK_INNER / 2
    left = translate(_plate(L, h), 0, -yi - P.PLATE_T, -h / 2)
    right = translate(_plate(L, h), 0, yi, -h / 2)
    # rotate plates: currently extruded in Z from XY — need plates in XZ with thickness Y
    # Rebuild: plate as pad in XZ via pad_xy on X-length × Z-height then... use box-like pad along Y
    left = pad_xy([(0, -yi - P.PLATE_T), (L, -yi - P.PLATE_T), (L, -yi), (0, -yi)], h, z0=-h / 2)
    right = pad_xy([(0, yi), (L, yi), (L, yi + P.PLATE_T), (0, yi + P.PLATE_T)], h, z0=-h / 2)
    sp_a = pad_xy([(8, -yi), (18, -yi), (18, yi), (8, yi)], 4, z0=-2)
    sp_b = pad_xy([(L - 22, -yi), (L - 12, -yi), (L - 12, yi), (L - 22, yi)], 4, z0=-2)
    body = fuse([left, right, sp_a, sp_b])
    adds, cuts = _split(L, True, False)
    for y in (-yi - P.PLATE_T / 2, yi + P.PLATE_T / 2):
        for z in (-6, 6):
            cuts.append(cyl(P.M3["clear_d"] / 2, 14, (-1, y, z), "x"))
    body = fuse([body] + adds) if adds else body
    return cut(body, cuts)


def make_upper_arm_b() -> Part.Shape:
    L = P.UPPER_SEG_B
    h = P.LINK_HEIGHT
    yi = P.LINK_INNER / 2
    left = pad_xy([(0, -yi - P.PLATE_T), (L, -yi - P.PLATE_T), (L, -yi), (0, -yi)], h, z0=-h / 2)
    right = pad_xy([(0, yi), (L, yi), (L, yi + P.PLATE_T), (0, yi + P.PLATE_T)], h, z0=-h / 2)
    sp = pad_xy([(10, -yi), (20, -yi), (20, yi), (10, yi)], 4, z0=-2)
    body = fuse([left, right, sp])
    adds, cuts = _split(L, False, True)
    p = P.MG90S
    # Distal internal cradle block spanning inner width
    cl = p["tab_l"] + 6
    cw = P.LINK_INNER
    ch = p["body_h_total"] + 4
    cradle = pad_xy([(L - 4, -cw / 2), (L - 4 + cl, -cw / 2), (L - 4 + cl, cw / 2), (L - 4, cw / 2)], ch, z0=-ch / 2)
    body = fuse([body] + adds + [cradle])
    cx = L - 4 + cl / 2
    cuts += [translate(servo_body_pocket(p), cx, 0, 0), tab_holes(p, ch / 2 - 1)]
    bp = translate(rotate(bearing_seat(P.F695ZZ, "+z"), (1, 0, 0), 90), cx, -cw / 2, 0)
    shaft = shaft_clearance(cw + 6, (cx, -cw / 2 - 3, 0), "y")
    stop = translate(soft_stop_pad(5, 3), cx + 8, cw / 2 + 0.5, -ch / 2)
    body = fuse([body, stop])
    cuts += [bp, shaft]
    return cut(body, cuts)


def make_all():
    return {"06_upper_arm_a": make_upper_arm_a(), "07_upper_arm_b": make_upper_arm_b()}
