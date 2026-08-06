"""Re-export vendor solids for assembly references."""

from vendor.models import f685zz, f695zz, horn_mg90s, horn_mg996r, mg90s, mg996r


def mg996r_body():
    return mg996r()


def mg90s_body():
    return mg90s()


def bearing_f695zz():
    return f695zz()


def bearing_f685zz():
    return f685zz()
