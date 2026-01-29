import argparse
import csv
import datetime as _dt
import math
import os
import shutil
from collections import Counter, defaultdict
from heapq import heappush, heappushpop

import matplotlib.pyplot as plt


def _to_float(x, default=None):
    if x is None:
        return default
    s = str(x).strip()
    if s == "":
        return default
    try:
        return float(s)
    except Exception:
        return default


def _to_int(x, default=None):
    if x is None:
        return default
    s = str(x).strip()
    if s == "":
        return default
    try:
        return int(float(s))
    except Exception:
        return default


def _norm(s):
    return str(s).strip().lower().replace(" ", "").replace("-", "").replace("_", "")


def _find_best_field(fieldnames, exact_keys, contains_any=None):
    """
    1) exact match by normalized name
    2) fallback: choose first field whose normalized name contains all tokens in contains_any
    """
    if not fieldnames:
        return None

    norm_map = {_norm(f): f for f in fieldnames}

    # exact keys
    for k in exact_keys:
        nk = _norm(k)
        if nk in norm_map:
            return norm_map[nk]

    # contains tokens
    if contains_any:
        for f in fieldnames:
            nf = _norm(f)
            ok = True
            for tok in contains_any:
                if _norm(tok) not in nf:
                    ok = False
                    break
            if ok:
                return f

    return None


def _safe_scatter(xs, ys, *, s=10, label=None):
    if xs and ys and len(xs) == len(ys):
        plt.scatter(xs, ys, s=s, label=label)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan_csv", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--top_k", type=int, default=200)
    ap.add_argument("--max_points", type=int, default=300000)
    ap.add_argument("--clean_out_dir", type=int, default=0)
    ap.add_argument("--lane_cut", type=float, default=-0.3)  # <-- the single vertical line
    args = ap.parse_args()

    # out_dir hygiene
    os.makedirs(args.out_dir, exist_ok=True)
    if args.clean_out_dir == 1:
        # delete ONLY old run_* folders + LATEST_RUN.txt; keep anything else untouched
        for name in os.listdir(args.out_dir):
            p = os.path.join(args.out_dir, name)
            if os.path.isdir(p) and name.startswith("run_"):
                shutil.rmtree(p, ignore_errors=True)
        latest_ptr = os.path.join(args.out_dir, "LATEST_RUN.txt")
        if os.path.exists(latest_ptr):
            try:
                os.remove(latest_ptr)
            except Exception:
                pass

    run_id = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_folder = os.path.join(args.out_dir, f"run_{run_id}")
    os.makedirs(run_folder, exist_ok=True)

    # always write a single-line pointer to latest run folder (your “single line” traceability fix)
    with open(os.path.join(args.out_dir, "LATEST_RUN.txt"), "w", encoding="utf-8") as w:
        w.write(f"run_{run_id}\n")

    # candidate keys (kept, but now we also auto-detect)
    lane_keys = ["lane", "a", "a_n", "a(n)", "posture_lane", "lane_a"]
    depth_keys = ["D_inf", "d_inf", "depth", "depth_inf", "Dinf", "D_inf(n)"]
    zone_keys = ["zone", "stability_zone"]
    guard_keys = ["guard", "guard_flag", "is_guard"]
    k_keys = ["K", "curvature", "kappa", "K(n)"]
    ido_keys = ["ido_dominators", "ido", "ido_dom", "dominators"]

    zone_counts = Counter()

    guard_points_lane = []
    guard_points_depth = []
    guard_points_guard = []

    zone_points = defaultdict(lambda: ([], []))

    top_k_by_k = []
    top_k_by_ido = []

    rows_seen = 0
    rows_used = 0

    # discovered fields (written to summary for audit)
    lane_field = None
    depth_field = None
    zone_field = None
    guard_field = None
    k_field = None
    ido_field = None

    with open(args.scan_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise SystemExit("scan_csv has no header")

        fieldnames = list(reader.fieldnames)

        # auto-detect fields robustly
        lane_field = _find_best_field(fieldnames, lane_keys, contains_any=["lane"]) or _find_best_field(
            fieldnames, lane_keys, contains_any=["a"]
        )
        depth_field = _find_best_field(fieldnames, depth_keys, contains_any=["d", "inf"]) or _find_best_field(
            fieldnames, depth_keys, contains_any=["depth"]
        )
        zone_field = _find_best_field(fieldnames, zone_keys, contains_any=["zone"])
        guard_field = _find_best_field(fieldnames, guard_keys, contains_any=["guard"])
        k_field = _find_best_field(fieldnames, k_keys, contains_any=["k"])  # weak fallback; we also validate values
        ido_field = _find_best_field(fieldnames, ido_keys, contains_any=["ido"])

        for row in reader:
            rows_seen += 1
            if args.stride > 1 and (rows_seen % args.stride != 0):
                continue

            zone = row.get(zone_field) if zone_field else row.get("zone")
            if zone is None or str(zone).strip() == "":
                zone = "UNKNOWN"
            zone_counts[zone] += 1

            lane = _to_float(row.get(lane_field)) if lane_field else None
            depth = _to_float(row.get(depth_field)) if depth_field else None
            guard = _to_int(row.get(guard_field), default=0) if guard_field else 0

            k_val = _to_float(row.get(k_field)) if k_field else None
            ido_val = _to_int(row.get(ido_field)) if ido_field else None

            # require lane/depth for geometric plots + for top lists (they store lane/depth too)
            if lane is None or depth is None:
                continue

            rows_used += 1

            if rows_used <= args.max_points:
                guard_points_lane.append(lane)
                guard_points_depth.append(depth)
                guard_points_guard.append(guard if guard is not None else 0)

                xs, ys = zone_points[zone]
                xs.append(lane)
                ys.append(depth)

            if k_val is not None and not math.isnan(k_val):
                item = (k_val, lane, depth, zone, guard)
                if len(top_k_by_k) < args.top_k:
                    heappush(top_k_by_k, item)
                else:
                    heappushpop(top_k_by_k, item)

            if ido_val is not None:
                item = (ido_val, lane, depth, zone, guard)
                if len(top_k_by_ido) < args.top_k:
                    heappush(top_k_by_ido, item)
                else:
                    heappushpop(top_k_by_ido, item)

    # split guard points
    guard0_x, guard0_y, guard1_x, guard1_y = [], [], [], []
    for x, y, g in zip(guard_points_lane, guard_points_depth, guard_points_guard):
        if g == 1:
            guard1_x.append(x)
            guard1_y.append(y)
        else:
            guard0_x.append(x)
            guard0_y.append(y)

    written_files = []

    # 1) guard vs non-guard
    plt.figure()
    plt.title("SSIT Phase II: guard vs non-guard (FINSET only)")
    plt.xlabel("lane a(n)")
    plt.ylabel("D_inf(n)")

    _safe_scatter(guard0_x, guard0_y, s=10, label="guard=0")
    _safe_scatter(guard1_x, guard1_y, s=10, label="guard=1")

    # single cut-line
    plt.axvline(args.lane_cut, linewidth=1.0, linestyle="--", label=f"lane_cut={args.lane_cut:g}")

    handles, labels = plt.gca().get_legend_handles_labels()
    if labels:
        plt.legend()
    plt.tight_layout()
    out_path = os.path.join(run_folder, "ssit_guard_scatter.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    written_files.append(os.path.basename(out_path))

    # 2) lane vs depth by zone
    plt.figure()
    plt.title("SSIT Phase II: lane a(n) vs depth D_inf(n) by zone")
    plt.xlabel("lane a(n)")
    plt.ylabel("D_inf(n)")
    for z, (xs, ys) in zone_points.items():
        if not xs:
            continue
        plt.scatter(xs, ys, s=10, label=str(z))
    plt.axvline(args.lane_cut, linewidth=1.0, linestyle="--", label=f"lane_cut={args.lane_cut:g}")
    handles, labels = plt.gca().get_legend_handles_labels()
    if labels:
        plt.legend()
    plt.tight_layout()
    out_path = os.path.join(run_folder, "ssit_lane_vs_depth_by_zone.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    written_files.append(os.path.basename(out_path))

    # 3) top IDO rank plot (robust: if empty, still produce a readable plot)
    plt.figure()
    plt.title("Top FINSET by IDO dominators (rank plot)")
    plt.xlabel("rank")
    plt.ylabel("ido_dominators")
    top_k_by_ido.sort(key=lambda t: t[0], reverse=True)
    ido_vals = [t[0] for t in top_k_by_ido]
    if ido_vals:
        plt.plot(list(range(len(ido_vals))), ido_vals)
    else:
        plt.text(0.5, 0.5, "NO DATA (missing/empty IDO column)", ha="center", va="center", transform=plt.gca().transAxes)
    plt.tight_layout()
    out_path = os.path.join(run_folder, "ssit_topIDO_rank_plot.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    written_files.append(os.path.basename(out_path))

    # 4) top curvature K rank plot
    plt.figure()
    plt.title("Top curvature events by K (FINSET only)")
    plt.xlabel("rank")
    plt.ylabel("K(n)")
    top_k_by_k.sort(key=lambda t: t[0], reverse=True)
    k_vals = [t[0] for t in top_k_by_k]
    if k_vals:
        plt.plot(list(range(len(k_vals))), k_vals)
    else:
        plt.text(0.5, 0.5, "NO DATA (missing/empty K column)", ha="center", va="center", transform=plt.gca().transAxes)
    plt.tight_layout()
    out_path = os.path.join(run_folder, "ssit_topK_rank_plot.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    written_files.append(os.path.basename(out_path))

    # 5) zone counts
    plt.figure()
    plt.title("Zone counts (stride-applied)")
    plt.xlabel("zone")
    plt.ylabel("count")
    zones = list(zone_counts.keys())
    counts = [zone_counts[z] for z in zones]
    plt.bar(zones, counts)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    out_path = os.path.join(run_folder, "ssit_zone_counts.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    written_files.append(os.path.basename(out_path))

    # summary
    summary_path = os.path.join(run_folder, "ssit_plot_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as w:
        w.write("SSIT plot summary\n")
        w.write(f"run_id={run_id}\n")
        w.write(f"run_dir={run_folder}\n")
        w.write(f"scan_csv={args.scan_csv}\n")
        w.write(f"rows_seen={rows_seen}\n")
        w.write(f"rows_used_after_stride={rows_used}\n")
        w.write(f"stride={args.stride}\n")
        w.write(f"max_points_plotted={args.max_points}\n")
        w.write(f"lane_cut={args.lane_cut}\n")
        w.write("detected_fields:\n")
        w.write(f"  lane_field={lane_field}\n")
        w.write(f"  depth_field={depth_field}\n")
        w.write(f"  zone_field={zone_field}\n")
        w.write(f"  guard_field={guard_field}\n")
        w.write(f"  ido_field={ido_field}\n")
        w.write(f"  k_field={k_field}\n")
        w.write("zone_counts_stride_applied:\n")
        for z, c in zone_counts.most_common():
            w.write(f"  {z}: {c}\n")
        w.write(f"top_k={args.top_k}\n")
        w.write("top_ido_dominators:\n")
        for v, lane, depth, zone, guard in top_k_by_ido[:10]:
            w.write(f"  ido={v} lane={lane:.12g} depth={depth:.12g} zone={zone} guard={guard}\n")
        w.write("top_curvature_K:\n")
        for v, lane, depth, zone, guard in top_k_by_k[:10]:
            w.write(f"  K={v:.12g} lane={lane:.12g} depth={depth:.12g} zone={zone} guard={guard}\n")
        w.write("written_files:\n")
        for fn in written_files:
            w.write(f"  {fn}\n")

    print(f"[OK] run_id={run_id}")
    print(f"[OK] wrote: {run_folder}")
    print(f"[OK] summary: {summary_path}")


if __name__ == "__main__":
    main()
