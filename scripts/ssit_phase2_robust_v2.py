import argparse
import csv
import hashlib
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def clamp_lane(a: float, eps: float = 1e-12) -> float:
    if a <= -1.0:
        return -1.0 + eps
    if a >= 1.0:
        return 1.0 - eps
    return a

def safe_float_str(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and math.isinf(x):
        return "INF"
    return f"{x:.12g}" if isinstance(x, float) else str(x)

def quantile_floor(sorted_vals, q: float) -> float:
    m = len(sorted_vals)
    if m == 0:
        return 0.0
    if m == 1:
        return float(sorted_vals[0])
    idx = int(math.floor(q * (m - 1)))
    if idx < 0:
        idx = 0
    if idx > (m - 1):
        idx = m - 1
    return float(sorted_vals[idx])

def sis_band(depth: float, q33: float, q66: float) -> str:
    if depth <= q33:
        return "THIN"
    if depth <= q66:
        return "MEDIUM"
    return "THICK"

def spf_sieve(n_max: int):
    spf = list(range(n_max + 1))
    spf[0] = 0
    if n_max >= 1:
        spf[1] = 1
    lim = int(math.isqrt(n_max))
    for i in range(2, lim + 1):
        if spf[i] == i:
            start = i * i
            step = i
            for j in range(start, n_max + 1, step):
                if spf[j] == j:
                    spf[j] = i
    return spf

def factorize(n: int, spf):
    fs = []
    while n > 1:
        p = spf[n]
        e = 0
        while n % p == 0:
            n //= p
            e += 1
        fs.append((p, e))
    return fs

def gen_divisors_from_factors(factors):
    divs = [1]
    for p, e in factors:
        base = list(divs)
        pe = 1
        for _ in range(e):
            pe *= p
            for d in base:
                divs.append(d * pe)
    return divs

def compute_ds_upto_sqrt(n: int, spf):
    L = int(math.isqrt(n))
    fs = factorize(n, spf)
    divs = gen_divisors_from_factors(fs)
    ds = []
    for d in divs:
        if 2 <= d <= L:
            ds.append(d)
    ds.sort()
    return ds, L

def first_divisor_min_fast(n: int, spf):
    if n <= 1:
        return None
    if spf[n] == n:
        return None
    return spf[n]

def Hs_and_I_fast(n: int, spf):
    dmin = first_divisor_min_fast(n, spf)
    sqrt_n = math.sqrt(n)
    if dmin is None:
        Hs = 1.0
        I = float("inf")
        is_inf = True
        prime_proxy = 1
    else:
        Hs = dmin / sqrt_n
        if Hs >= 1.0:
            Hs = 1.0
            I = float("inf")
            is_inf = True
        else:
            I = 1.0 / (1.0 - Hs)
            is_inf = False
        prime_proxy = 0
    return Hs, I, is_inf, dmin, prime_proxy

def r_full_from_ds(ds):
    m = len(ds)
    if m < 2:
        return 0.0
    s = 0.0
    for i in range(m - 1):
        s += (1.0 - (ds[i] / ds[i + 1]))
    return s / float(m - 1)

def lane_from_ds(ds):
    R = r_full_from_ds(ds)
    return clamp_lane(2.0 * R - 1.0)

def D_inf_from_ds(ds, L):
    if L < 2:
        return 0.0
    denom = math.log(L + 1.0)
    if denom <= 0.0:
        return 0.0
    s = 0.0
    for d in ds:
        s += (math.log(d + 1.0) / denom)
    if (L - 1) > 0:
        s = s / float(L - 1)
    if s < 0.0:
        return 0.0
    if s > 1.0:
        return 1.0
    return s

@dataclass(frozen=True)
class OmegaTyped:
    kind: str
    sign: int
    lane: float
    depth: float
    SIS: str

    def __repr__(self) -> str:
        if self.kind == "INFSET":
            return f"<{self.sign}INF*, lane={self.lane:.12g}, depth={self.depth:.12g}, tag=INFSET>"
        return f"<{self.sign}INF, lane={self.lane:.12g}, depth={self.depth:.12g}, SIS={self.SIS}, tag=FINSET>"

def zone_label(kind: str, lane: float, depth: float, lane_stable: float, lane_infty: float, depth_infprox: float) -> str:
    if kind == "INFSET":
        return "INFSET"
    if lane <= lane_infty and depth <= depth_infprox:
        return "INFINITY_PROXIMAL"
    if lane <= lane_stable:
        return "TRANSITIONAL"
    return "STABLE_FINITE"

class Fenwick:
    def __init__(self, n: int):
        self.n = n
        self.bit = [0] * (n + 1)

    def add(self, i: int, delta: int):
        while i <= self.n:
            self.bit[i] += delta
            i += i & -i

    def sum(self, i: int) -> int:
        s = 0
        while i > 0:
            s += self.bit[i]
            i -= i & -i
        return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_max", type=int, default=1500000)
    ap.add_argument("--out_dir", type=str, default="ssit_out_phase2_robust_v2")
    ap.add_argument("--near_eps", type=float, default=0.02)
    ap.add_argument("--lane_stable", type=float, default=-0.3)
    ap.add_argument("--lane_infty", type=float, default=-0.7)
    ap.add_argument("--depth_infprox_quantile", type=float, default=0.33)
    ap.add_argument("--shock_quantile", type=float, default=0.95)
    args = ap.parse_args()

    n_max = int(args.n_max)
    near_eps = float(args.near_eps)

    os.makedirs(args.out_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, "ssit_phase2_robust_v2_scan.csv")
    report_path = os.path.join(args.out_dir, "ssit_phase2_robust_v2_report.txt")

    spf = spf_sieve(n_max)

    I_vals = [None] * (n_max + 2)
    Hs_vals = [None] * (n_max + 2)
    dmin_vals = [None] * (n_max + 2)
    isinf_vals = [0] * (n_max + 2)
    primeproxy_vals = [0] * (n_max + 2)
    lane_vals = [0.0] * (n_max + 2)
    depth_vals = [0.0] * (n_max + 2)
    SIS_vals = [""] * (n_max + 2)

    inf_count = 0
    fin_count = 0
    nearinf_count = 0
    prime_proxy_count = 0

    depths_fin = []

    for n in range(2, n_max + 1):
        Hs, I, is_inf, dmin, prime_proxy = Hs_and_I_fast(n, spf)
        ds, L = compute_ds_upto_sqrt(n, spf)
        lane = lane_from_ds(ds)
        depth = D_inf_from_ds(ds, L)

        I_vals[n] = I
        Hs_vals[n] = Hs
        dmin_vals[n] = dmin
        isinf_vals[n] = 1 if is_inf else 0
        primeproxy_vals[n] = prime_proxy
        lane_vals[n] = lane
        depth_vals[n] = depth

        if prime_proxy:
            prime_proxy_count += 1

        if is_inf:
            inf_count += 1
        else:
            fin_count += 1
            depths_fin.append(depth)
            if (1.0 - near_eps) <= Hs < 1.0:
                nearinf_count += 1

    depths_fin_sorted = sorted(depths_fin)
    q33 = quantile_floor(depths_fin_sorted, 0.33)
    q66 = quantile_floor(depths_fin_sorted, 0.66)

    for n in range(2, n_max + 1):
        if isinf_vals[n]:
            SIS_vals[n] = ""
        else:
            SIS_vals[n] = sis_band(depth_vals[n], q33, q66)

    d2I_vals = [None] * (n_max + 2)
    K_vals = [None] * (n_max + 2)
    Ks = []

    for n in range(3, n_max):
        Im1 = I_vals[n - 1]
        I0 = I_vals[n]
        Ip1 = I_vals[n + 1]
        if Im1 is None or I0 is None or Ip1 is None:
            continue
        if math.isinf(Im1) or math.isinf(I0) or math.isinf(Ip1):
            continue
        d2 = Ip1 - 2.0 * I0 + Im1
        d2I_vals[n] = d2
        K = abs(d2)
        K_vals[n] = K
        Ks.append(K)

    Ks_sorted = sorted(Ks)
    Kq = quantile_floor(Ks_sorted, float(args.shock_quantile))

    depth_infprox = quantile_floor(depths_fin_sorted, float(args.depth_infprox_quantile))
    lane_stable = float(args.lane_stable)
    lane_infty = float(args.lane_infty)

    zone_vals = [""] * (n_max + 2)
    shock_vals = [0] * (n_max + 2)
    guard_vals = [0] * (n_max + 2)

    for n in range(2, n_max + 1):
        kind = "INFSET" if isinf_vals[n] else "FINSET"
        zone = zone_label(kind, lane_vals[n], depth_vals[n], lane_stable, lane_infty, depth_infprox)
        zone_vals[n] = zone
        K = K_vals[n]
        shock = 1 if (K is not None and K >= Kq) else 0
        shock_vals[n] = shock
        guard_vals[n] = 1 if (zone == "INFINITY_PROXIMAL" or shock == 1) else 0

    fin_items = []
    for n in range(2, n_max + 1):
        if isinf_vals[n]:
            continue
        fin_items.append((lane_vals[n], depth_vals[n], n))

    depth_coords = sorted({d for (_a, d, _n) in fin_items})
    depth_rank = {d: i + 1 for i, d in enumerate(depth_coords)}

    fin_items_sorted = sorted(fin_items, key=lambda x: (x[0], x[1], x[2]))

    fw = Fenwick(len(depth_coords))
    ido_dominators = [0] * (n_max + 2)

    i = 0
    m = len(fin_items_sorted)
    while i < m:
        j = i
        while j < m and fin_items_sorted[j][0] == fin_items_sorted[i][0]:
            j += 1
        for k in range(i, j):
            _a, d, n = fin_items_sorted[k]
            r = depth_rank[d]
            ido_dominators[n] = fw.sum(r)
        for k in range(i, j):
            _a, d, _n = fin_items_sorted[k]
            fw.add(depth_rank[d], 1)
        i = j

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "n",
            "set_type",
            "d_min",
            "H_s",
            "I",
            "I_is_inf",
            "prime_proxy",
            f"in_NearInf_eps_{near_eps}",
            "lane_a",
            "D_inf",
            "SIS",
            "d2I",
            "K",
            "zone",
            "shock_flag",
            "guard_flag",
            "ido_dominators"
        ])

        for n in range(2, n_max + 1):
            is_inf = bool(isinf_vals[n])
            set_type = "INFSET" if is_inf else "FINSET"
            w.writerow([
                n,
                set_type,
                "" if dmin_vals[n] is None else dmin_vals[n],
                safe_float_str(Hs_vals[n]),
                safe_float_str(I_vals[n]),
                1 if is_inf else 0,
                primeproxy_vals[n],
                1 if (not is_inf and (1.0 - near_eps) <= Hs_vals[n] < 1.0) else 0,
                safe_float_str(lane_vals[n]),
                safe_float_str(depth_vals[n]),
                SIS_vals[n],
                safe_float_str(d2I_vals[n]),
                safe_float_str(K_vals[n]),
                zone_vals[n],
                shock_vals[n],
                guard_vals[n],
                "" if is_inf else ido_dominators[n]
            ])

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("SSIT Phase II (Robust) v2 — Zones + Shock + Guard + IDO Dominators\n")
        f.write("==================================================================\n\n")
        f.write(f"run_utc={now}\n")
        f.write(f"n_max={n_max}\n")
        f.write(f"near_eps={near_eps}\n")
        f.write(f"lane_stable={lane_stable}\n")
        f.write(f"lane_infty={lane_infty}\n")
        f.write(f"depth_infprox_quantile={float(args.depth_infprox_quantile)}\n")
        f.write(f"depth_infprox_value={depth_infprox:.12g}\n")
        f.write(f"shock_quantile={float(args.shock_quantile)}\n")
        f.write(f"shock_K_threshold={Kq:.12g}\n\n")
        f.write("Definitions (ASCII)\n")
        f.write("------------------\n")
        f.write("`H_s(n) = d_min(n) / sqrt(n)`\n")
        f.write("`I(n) = 1 / (1 - H_s(n))` when `H_s(n) < 1`; else `I(n)=INF` (INFSET)\n")
        f.write("`lane a(n) = clamp(2*R_full(n) - 1)` where `R_full` is mean spacing ratio of divisors within sqrt(n)\n")
        f.write("`D_inf(n)` is weighted divisor density within `2..floor(sqrt(n))` normalized to `[0,1]`\n")
        f.write("SIS bands are terciles of `D_inf` over FINSET: THIN / MEDIUM / THICK\n")
        f.write("Curvature proxy: `K(n) = abs(I(n+1) - 2*I(n) + I(n-1))` over finite triples\n")
        f.write("Shock flag: `K(n) >= shock_K_threshold`\n")
        f.write("Zones (FINSET only): STABLE_FINITE / TRANSITIONAL / INFINITY_PROXIMAL\n")
        f.write("Guard flag: 1 iff zone is INFINITY_PROXIMAL or shock_flag=1\n")
        f.write("IDO dominators (FINSET only): count of FINSET objects `o` with `o.lane < lane(n)` and `o.depth <= depth(n)`\n\n")
        f.write("Counts\n")
        f.write("------\n")
        f.write(f"INFSET_count={inf_count}\n")
        f.write(f"FINSET_count={fin_count}\n")
        f.write(f"NearInf_FINSET_count={nearinf_count}\n")
        f.write(f"prime_proxy_count={prime_proxy_count}\n\n")
        f.write("SHA-256\n")
        f.write("-------\n")
        f.write(f"scan_csv_sha256={sha256_file(csv_path)}\n")

if __name__ == "__main__":
    main()
