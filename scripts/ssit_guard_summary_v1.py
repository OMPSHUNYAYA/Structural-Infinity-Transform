# File name: ssit_guard_summary_v1.py

import argparse
import csv
import hashlib
import math
import os

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def to_float(s: str):
    if s is None:
        return None
    t = str(s).strip()
    if t == "" or t.upper() == "INF":
        return None
    try:
        return float(t)
    except Exception:
        return None

def to_int(s: str, default: int = 0) -> int:
    t = str(s).strip()
    if t == "":
        return default
    return int(t)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan_csv", type=str, required=True)
    ap.add_argument("--out_report", type=str, required=True)
    ap.add_argument("--top_k", type=int, default=50)
    args = ap.parse_args()

    scan_csv = args.scan_csv
    out_report = args.out_report
    top_k = int(args.top_k)

    zone_counts = {}
    set_counts = {"INFSET": 0, "FINSET": 0}
    guard_count = 0
    shock_count = 0

    top_ido = []
    top_K = []
    top_infprox = []
    top_score = []

    with open(scan_csv, "r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            n = int(row["n"])
            set_type = row["set_type"]
            zone = row.get("zone", "")
            guard_flag = to_int(row.get("guard_flag", "0"), 0)
            shock_flag = to_int(row.get("shock_flag", "0"), 0)

            set_counts[set_type] = set_counts.get(set_type, 0) + 1
            zone_counts[zone] = zone_counts.get(zone, 0) + 1
            guard_count += 1 if guard_flag == 1 else 0
            shock_count += 1 if shock_flag == 1 else 0

            if set_type != "FINSET":
                continue

            lane = to_float(row.get("lane_a", ""))
            depth = to_float(row.get("D_inf", ""))
            ido = row.get("ido_dominators", "")
            ido_v = None
            if ido is not None and str(ido).strip() != "":
                try:
                    ido_v = int(ido)
                except Exception:
                    ido_v = None

            K = to_float(row.get("K", ""))

            if ido_v is not None:
                top_ido.append((ido_v, n))

            if K is not None:
                top_K.append((K, n))

            if zone == "INFINITY_PROXIMAL":
                top_infprox.append((n, lane, depth))

            if lane is not None and depth is not None:
                score = (-lane) * (1.0 - depth)
                top_score.append((score, n))

    top_ido.sort(reverse=True)
    top_K.sort(reverse=True)
    top_score.sort(reverse=True)

    scan_sha = sha256_file(scan_csv)

    os.makedirs(os.path.dirname(out_report) or ".", exist_ok=True)
    with open(out_report, "w", encoding="utf-8") as f:
        f.write("SSIT Guard Summary v1\n")
        f.write("=====================\n\n")
        f.write(f"scan_csv_sha256={scan_sha}\n\n")

        f.write("Counts\n")
        f.write("------\n")
        f.write(f"FINSET_count={set_counts.get('FINSET',0)}\n")
        f.write(f"INFSET_count={set_counts.get('INFSET',0)}\n")
        f.write(f"guard_flag_count={guard_count}\n")
        f.write(f"shock_flag_count={shock_count}\n\n")

        f.write("Zone counts\n")
        f.write("-----------\n")
        for k in sorted(zone_counts.keys()):
            f.write(f"{k}={zone_counts[k]}\n")
        f.write("\n")

        f.write(f"Top {top_k} FINSET by ido_dominators\n")
        f.write("----------------------------------\n")
        for v, n in top_ido[:top_k]:
            f.write(f"n={n} ido_dominators={v}\n")
        f.write("\n")

        f.write(f"Top {top_k} FINSET by curvature K\n")
        f.write("-------------------------------\n")
        for v, n in top_K[:top_k]:
            f.write(f"n={n} K={v:.12g}\n")
        f.write("\n")

        f.write(f"First {top_k} FINSET in INFINITY_PROXIMAL zone\n")
        f.write("--------------------------------------------\n")
        for item in top_infprox[:top_k]:
            n, lane, depth = item
            lane_s = f"{lane:.12g}" if lane is not None else ""
            depth_s = f"{depth:.12g}" if depth is not None else ""
            f.write(f"n={n} lane={lane_s} depth={depth_s}\n")
        f.write("\n")

        f.write(f"Top {top_k} FINSET by infinity-likeness score\n")
        f.write("-------------------------------------------\n")
        f.write("score(n)=(-lane_a)*(1-D_inf)\n")
        for v, n in top_score[:top_k]:
            f.write(f"n={n} score={v:.12g}\n")

if __name__ == "__main__":
    main()
