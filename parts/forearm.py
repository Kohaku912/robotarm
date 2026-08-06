"""Compact dual-plate forearm + internal wrist-pitch MG90S."""

from __future__ import annotations

import Part

import params as P
from cad.sketch_pad import cut, cyl, fuse, pad_xy, rotate, translate
from parts.joint_features import bearing_seat, insert_m3, servo_body_pocket, shaft_clearance, tab_holes


def _split(length, male, female):
    adds, cuts = [], []
    sp = P.SPLIT_BOLT_SPACING - 2
    corners = [(-sp / 2, -sp / 2), (sp / 2, -sp / 2), (-sp / 2, sp / 2), (sp / 2, sp / 2)]
    cuts.append(cyl(P.CABLE_HOLE_D / 2 - 0.5, length + 2, (-1, 0, 0), "x"))
    if male:
        for py, pz in corners:
            adds.append(cyl(P.DOWEL_D / 2 - 0.1, 4.5, (length, py, pz), "x"))
            cuts.append(cyl(P.M3["clear_d"] / 2, 18, (length - 14, py, pz), "x"))
            cuts.append(cyl(P.M3["head_d"] / 2, P.M3["head_h"] + 0.3, (length - 3, py, pz), "x"))
    if female:
        for py, pz in corners:
            cuts.append(cyl(P.DOWEL_D / 2 + 0.15, 5, (-0.4, py, pz), "x"))
            cuts.append(insert_m3((-0.2, py, pz), "x"))
    return adds, cuts


def make_forearm_a() -> Part.Shape:
    L = P.FORE_SEG_A
    h = P.LINK_HEIGHT - 2
    yi = P.LINK_INNER / 2 - 1
    left = pad_xy([(0, -yi - P.PLATE_T), (L, -yi - P.PLATE_T), (L, -yi), (0, -yi)], h, z0=-h / 2)
    right = pad_xy([(0, yi), (L, yi), (L, yi + P.PLATE_T), (0, yi + P.PLATE_T)], h, z0=-h / 2)
    sp = pad_xy([(8, -yi), (16, -yi), (16, yi), (8, yi)], 3.5, z0=-2)
    body = fuse([left, right, sp])
    adds, cuts = _split(L, True, False)
    for y in (-yi - P.PLATE_T / 2, yi + P.PLATE_T / 2):
        for z in (-5, 5):
            cuts.append(cyl(P.M3["clear_d"] / 2, 12, (-1, y, z), "x"))
    return cut(fuse([body] + adds), cuts)


def make_forearm_b() -> Part.Shape:
    L = P.FORE_SEG_B
    h = P.LINK_HEIGHT - 2
    yi = P.LINK_INNER / 2 - 1
    left = pad_xy([(0, -yi - P.PLATE_T), (L, -yi - P.PLATE_T), (L, -yi), (0, -yi)], h, z0=-h / 2)
    right = pad_xy([(0, yi), (L, yi), (L, yi + P.PLATE_T), (0, yi + P.PLATE_T)], h, z0=-h / 2)
    sp = pad_xy([(8, -yi), (16, -yi), (16, yi), (8, yi)], 3.5, z0=-2)
    body = fuse([left, right, sp])
    adds, cuts = _split(L, False, True)
    p = P.MG90S
    cl = p["tab_l"] + 5
    cw = 2 * yi
    ch = p["body_h_total"] + 3
    cradle = pad_xy([(L - 3, -cw / 2), (L - 3 + cl, -cw / 2), (L - 3 + cl, cw / 2), (L - 3, cw / 2)], ch, z0=-ch / 2)
    body = fuse([body] + adds + [cradle])
    cx = L - 3 + cl / 2
    cuts += [translate(servo_body_pocket(p), cx, 0, 0), tab_holes(p, ch / 2 - 1)]
    bp_l = translate(rotate(bearing_seat(P.F685ZZ, "+z"), (1, 0, 0), 90), cx, -cw / 2, 0)
    bp_r = translate(rotate(bearing_seat(P.F685ZZ, "+z"), (1, 0, 0), -90), cx, cw / 2, 0)
    shaft = shaft_clearance(cw + 5, (cx, -cw / 2 - 2.5, 0), "y")
    cuts += [bp_l, bp_r, shaft]
    return cut(body, cuts)


def make_all():
    return {"10_forearm_a": make_forearm_a(), "11_forearm_b": make_forearm_b()}
