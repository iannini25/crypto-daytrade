"""Formatação de números em pt-BR."""


def br(x, d=2):
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, d=1):
    return br(100 * x, d) + "%"
