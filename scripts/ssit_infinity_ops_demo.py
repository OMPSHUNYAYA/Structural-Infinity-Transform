import argparse
import math
from dataclasses import dataclass
from typing import List, Tuple


def clamp_lane(a: float, eps: float = 1e-12) -> float:
    if a <= -1.0:
        return -1.0 + eps
    if a >= 1.0:
        return 1.0 - eps
    return a


def lane_mean(a1: float, a2: float) -> float:
    # PDF-consistent merge for addition: (a1 + a2)/2 then clamp
    return clamp_lane(0.5 * (a1 + a2))


def lane_separation(a1: float, a2: float) -> float:
    # PDF-consistent separation for division/subtraction: abs(a1 - a2) then clamp
    return clamp_lane(abs(a1 - a2))


@dataclass(frozen=True)
class FiniteClass:
    lane: float

    def __repr__(self) -> str:
        return f"<finite-class, lane={self.lane:.12g}>"


@dataclass(frozen=True)
class ZeroClass:
    lane: float

    def __repr__(self) -> str:
        return f"<zero-class, lane={self.lane:.12g}>"


@dataclass(frozen=True)
class SymbolicInfinity:
    sign: int
    lane: float

    def __post_init__(self) -> None:
        if self.sign not in (-1, +1):
            raise ValueError("sign must be -1 or +1")
        object.__setattr__(self, "lane", float(clamp_lane(self.lane)))

    def _guard(self, other: object) -> "SymbolicInfinity":
        if not isinstance(other, SymbolicInfinity):
            raise TypeError("operation requires SymbolicInfinity")
        return other

    def __truediv__(self, other: object) -> FiniteClass:
        o = self._guard(other)
        return FiniteClass(lane_separation(self.lane, o.lane))

    def __add__(self, other: object) -> "SymbolicInfinity":
        o = self._guard(other)
        return SymbolicInfinity(self.sign, lane_mean(self.lane, o.lane))

    def __sub__(self, other: object) -> ZeroClass:
        o = self._guard(other)
        return ZeroClass(lane_separation(self.lane, o.lane))

    def __repr__(self) -> str:
        s = "+" if self.sign > 0 else "-"
        return f"<{s}INF, lane={self.lane:.12g}>"


def divisors_within_sqrt(n: int) -> List[int]:
    if n < 2:
        return []
    L = int(math.isqrt(n))
    ds: List[int] = []
    for d in range(2, L + 1):
        if n % d == 0:
            ds.append(d)
    return ds


def R_full(n: int) -> float:
    ds = divisors_within_sqrt(n)
    m = len(ds)
    if m < 2:
        return 0.0
    s = 0.0
    for i in range(m - 1):
        s += (1.0 - (ds[i] / ds[i + 1]))
    return s / float(m - 1)


def Omega_v13(n: int) -> SymbolicInfinity:
    r = R_full(n)
    lane = clamp_lane(2.0 * r - 1.0)
    return SymbolicInfinity(+1, lane)


def parse_pairs(pairs_s: str) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    if not pairs_s.strip():
        return out
    for part in pairs_s.split(","):
        piece = part.strip()
        if not piece:
            continue
        if ":" not in piece:
            raise ValueError("pairs must be formatted like 'a:b,c:d'")
        x_s, y_s = piece.split(":", 1)
        x = int(x_s.strip())
        y = int(y_s.strip())
        if x <= 0 or y <= 0:
            raise ValueError("n values must be positive integers")
        out.append((x, y))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(prog="ssit_infinity_ops_demo.py")
    ap.add_argument(
        "--pairs",
        type=str,
        default="2310:30030,72:84,720:840,2310:97,30030:97,97:100,100:121",
        help="comma-separated pairs 'a:b,c:d,...'",
    )
    args = ap.parse_args()
    pairs = parse_pairs(args.pairs)

    print("=== SSIT Infinity Ops Demo (v1.3 posture lane) ===")
    print("Omega(n) := <+INF, lane=a(n)> where a(n)=clamp(2*R_full(n)-1)")
    print("PDF-consistent ops:")
    print("  Omega1 / Omega2 -> finite-class( abs(a1 - a2) )")
    print("  Omega1 - Omega2 -> zero-class( abs(a1 - a2) )")
    print("  Omega1 + Omega2 -> <+INF, lane=clamp((a1 + a2)/2)>")
    print()

    for x, y in pairs:
        ox = Omega_v13(x)
        oy = Omega_v13(y)
        print(f"n1={x} Omega1={ox}")
        print(f"n2={y} Omega2={oy}")
        print(f"Omega1 / Omega2 = {ox / oy}")
        print(f"Omega1 - Omega2 = {ox - oy}")
        print(f"Omega1 + Omega2 = {ox + oy}")
        print("-" * 60)


if __name__ == "__main__":
    main()
