"""CPU reproduction from released, allowlisted score summaries.

No image reader, model, transport, network client or confirmation data is used.
Run ``python -m querygrid.analysis --data-dir data --output-dir outputs``.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import beta

from .inference import MANIFEST_IDENTITY_SHA256, STUDY_COUNTS, manifest_identity_digest

IDENTITY = ("category", "path", "group_key", "camera", "research_role", "anomaly_class")
PHASES = ("00", "01", "10", "11")
READOUTS = ("full",) + tuple("parity" + p for p in PHASES) + tuple("interior_parity" + p for p in PHASES)
METRICS = ("fpr", "supported_tpr", "any_tpr")
P1_METRICS = ("normal_group_fpr", "supported_group_tpr", "any_group_tpr")
P1_METHODS = tuple(f"{p}_s{s}" for p in ("odd", "balanced", "random") for s in range(3))
E_METHODS = tuple(f"{p}_s{s}" for p in ("native", "uniform", "native_shuffle") for s in range(3))
P1_PAIRS = (("balanced", "odd"), ("random", "odd"), ("random", "balanced"))
E_PAIRS = (("uniform", "native"), ("native_shuffle", "native"), ("uniform", "native_shuffle"))
X_METHODS = ("dino_odd_own", "dino_balanced_own", "balanced_delete_topleft", "balanced_delete_interior_sham")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf8")


def write_csv(path, rows):
    with Path(path).open("w", encoding="utf8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_manifest(rows):
    """Reject new roles, categories, duplicate views or incomplete five-view groups."""
    require(len(rows) == 2010 and len({r["path"] for r in rows}) == 2010, "Expected 2010 unique admitted views")
    require(Counter(r["research_role"] for r in rows) == {"source_fit": 875, "source_calibration": 380, "development": 755}, "Unexpected data role")
    groups = defaultdict(list)
    for r in rows:
        require(set(IDENTITY) <= set(r), "Missing identity field")
        require(r["category"] == "plastic_nut" and r["path"].startswith("plastic_nut/") and ".." not in Path(r["path"]).parts, "Invalid dataset-relative path")
        require(r["anomaly_class"] == "OK" or r["research_role"] == "development", "Non-normal fitting/calibration view")
        groups[r["group_key"]].append(r)
    require(len(groups) == 402, "Expected 402 acquisition groups")
    for rows_in_group in groups.values():
        require(sorted(r["camera"] for r in rows_in_group) == ["1", "2", "3", "4", "5"], "Incomplete cameras")
        require(len({r["research_role"] for r in rows_in_group}) == 1, "Group crosses roles")
    require(sum(r["anomaly_class"] != "OK" for r in rows) == 258, "Official abnormal-view count differs")
    roles = {role: [r for r in rows if r["research_role"] == role] for role in STUDY_COUNTS}
    require(manifest_identity_digest(roles) == MANIFEST_IDENTITY_SHA256, "Manifest identities/roles/labels differ from the canonical admitted set")
    return {r["path"]: r for r in rows}


def admit_scores(rows, manifest, methods):
    allowed = {p: r for p, r in manifest.items() if r["research_role"] != "source_fit"}
    require(len(rows) == 1135 and {r["path"] for r in rows} == set(allowed), "Query set is not the frozen 1135-view set")
    groups = defaultdict(list)
    for r in rows:
        require(all(r[k] == allowed[r["path"]][k] for k in IDENTITY), "Score identity differs from manifest")
        require(all(math.isfinite(float(r[m])) and float(r[m]) > 0 for m in methods), "Invalid score")
        groups[r["group_key"]].append(r)
    cal = sorted(g for g, v in groups.items() if v[0]["research_role"] == "source_calibration")
    normal = sorted(g for g, v in groups.items() if v[0]["research_role"] == "development" and all(r["anomaly_class"] == "OK" for r in v))
    bad = sorted(g for g, v in groups.items() if v[0]["research_role"] == "development" and any(r["anomaly_class"] != "OK" for r in v))
    require(tuple(map(len, (cal, normal, bad))) == (76, 44, 107), "Incorrect group strata")
    def maxima(keys, supported=False):
        return np.asarray([[max(float(r[m]) for r in groups[g] if not supported or r["anomaly_class"] != "OK") for m in methods] for g in keys])
    return groups, cal, normal, bad, (maxima(cal), maxima(normal), maxima(bad, True), maxima(bad))


def threshold(scores):
    rank = math.ceil(.95 * (len(scores) + 1)) - 1
    require(rank < len(scores), "Calibration set too small for an observed rank")
    return np.sort(scores, axis=0)[rank]


def resample_operations(cal, normal, supported, any_bad, replicates=5000, seed=20261031):
    """Paired group bootstrap. Seeds index fixed methods, never sampling units."""
    tau = threshold(cal)
    arrays = (normal, supported, any_bad)
    alarms = [a > tau for a in arrays]
    points = np.stack([a.mean(axis=0) for a in alarms], axis=1)
    rng = np.random.Generator(np.random.PCG64(seed))
    # This allocation order and int64 dtype reproduce the archived draw hashes.
    draws = [rng.integers(0, len(a), size=(replicates, len(a)), dtype=np.int64) for a in (cal, normal, supported)]
    rank = math.ceil(.95 * (len(cal) + 1)) - 1
    td = np.partition(cal[draws[0]], rank, axis=1)[:, rank, :]
    boot = {r: [] for r in ("fixed_calibration", "calibration_only", "joint")}
    for a, d in zip(arrays, (draws[1], draws[2], draws[2])):
        boot["fixed_calibration"].append((a[d] > tau).mean(axis=1))
        boot["calibration_only"].append((a[None, :, :] > td[:, None, :]).mean(axis=1))
        boot["joint"].append((a[d] > td[:, None, :]).mean(axis=1))
    return tau, alarms, points, {r: np.stack(v, axis=2) for r, v in boot.items()}, draws, td


def distribution(values, point, expanded=False):
    lo, hi = (float(v) for v in np.quantile(values, [.025, .975], method="linear"))
    if not expanded:
        return {"point": float(point), "lower": lo, "upper": hi}
    return {"point": float(point), "bootstrap_mean": float(np.mean(values)), "bootstrap_median": float(np.median(values)), "ci95": [lo, hi], "fraction_positive": float(np.mean(values > 0)), "fraction_nonnegative": float(np.mean(values >= 0))}


def analyze_operating(rows, manifest, study):
    methods, pairs, seed = (P1_METHODS, P1_PAIRS, 20261031) if study == "p1" else (E_METHODS, E_PAIRS, 20261104)
    groups, ck, nk, bk, arrays = admit_scores(rows, manifest, methods)
    tau, alarms, points, boot, draws, td = resample_operations(*arrays, seed=seed)
    ops, contrasts, method_intervals = [], [], []
    expanded = study == "p1"
    metrics = P1_METRICS if expanded else METRICS
    for j, m in enumerate(methods):
        fp, tp, atp = [int(a[:, j].sum()) for a in alarms]
        lo = 0.0 if fp == 0 else float(beta.ppf(.025, fp, 45 - fp))
        hi = 1.0 if fp == 44 else float(beta.ppf(.975, fp + 1, 44 - fp))
        if expanded:
            ops.append(dict(method=m, group_threshold=float(tau[j]), normal_groups=44, abnormal_groups=107, normal_false_positive_groups=fp, supported_detected_groups=tp, any_detected_groups=atp, normal_group_fpr=fp/44, supported_group_tpr=tp/107, any_group_tpr=atp/107, normal_fpr_cp95_lower=lo, normal_fpr_cp95_upper=hi))
        else:
            ops.append(dict(method=m, threshold=float(tau[j]), fp=fp, normal_groups=44, supported=tp, any=atp, abnormal_groups=107, fpr=fp/44, supported_tpr=tp/107, any_tpr=atp/107, fpr_cp95_lower=lo, fpr_cp95_upper=hi))
        for regime, values in boot.items():
            for q, metric in enumerate(metrics):
                method_intervals.append(dict(method=m, regime=regime, metric=metric, **distribution(values[:, j, q], points[j, q], expanded)))
    for candidate, reference in pairs:
        ci = [methods.index(f"{candidate}_s{s}") for s in range(3)]
        ri = [methods.index(f"{reference}_s{s}") for s in range(3)]
        dp = points[ci] - points[ri]
        for regime, values in boot.items():
            delta = values[:, ci] - values[:, ri]
            for s in (0, 1, 2, "fixed_seed_mean"):
                d = delta.mean(axis=1) if s == "fixed_seed_mean" else delta[:, s]
                p = dp.mean(axis=0) if s == "fixed_seed_mean" else dp[s]
                for q, metric in enumerate(metrics):
                    contrasts.append(dict(candidate=candidate, reference=reference, seed=s, regime=regime, metric=metric, **distribution(d[:, q], p[q], expanded)))
    hashes = {n: hashlib.sha256(a.tobytes(order="C")).hexdigest() for n, a in zip(("calibration", "normal", "abnormal"), draws)}
    if expanded:
        result = dict(operating_rows=ops, bootstrap_contrasts=contrasts, bootstrap_methods=method_intervals,
                      threshold_distributions=[dict(method=m, **distribution(td[:, j], tau[j], True), distinct_resampled_thresholds=int(len(np.unique(td[:, j])))) for j, m in enumerate(methods)],
                      bootstrap_draws={"sha256_raw_contiguous": {"calibration": hashes["calibration"], "normal_development": hashes["normal"], "abnormal_development": hashes["abnormal"]}})
    else:
        normal_log = []
        for s in range(3):
            v = np.asarray([np.mean([math.log(float(r[f"native_s{s}"]) / float(r[f"uniform_s{s}"])) for r in groups[g]]) for g in ck])
            normal_log.append(dict(seed=s, **distribution(v[draws[0]].mean(axis=1), v.mean())))
        primary = next(r for r in contrasts if r["candidate"] == "uniform" and r["reference"] == "native" and r["seed"] == "fixed_seed_mean" and r["regime"] == "joint" and r["metric"] == "supported_tpr")
        gains = [float(points[3+s, 1] - points[s, 1]) for s in range(3)]
        gate = dict(per_seed_delta_supported_tpr=gains, all_seeds_gain_ge_10pp=all(v >= .1 for v in gains), mean_joint_ci_lower_positive=primary["lower"] > 0, primary_pass=all(v >= .1 for v in gains) and primary["lower"] > 0, separate_fp_point_screen=all(ops[3+s]["fp"] <= ops[s]["fp"]+1 for s in range(3)), risk_noninferiority_established=False, independent_confirmation=False, main_contribution_established=False)
        cross = []
        for s in range(3):
            for p in ("native", "uniform", "native_shuffle"):
                for q in ("native", "uniform", "native_shuffle"):
                    j, k = methods.index(f"{p}_s{s}"), methods.index(f"{q}_s{s}")
                    cross.append(dict(seed=s, score_method=methods[j], threshold_method=methods[k], threshold=float(tau[k]), fp=int((arrays[1][:, j] > tau[k]).sum()), normal_groups=44, supported=int((arrays[2][:, j] > tau[k]).sum()), any=int((arrays[3][:, j] > tau[k]).sum()), abnormal_groups=107))
        result = dict(operating_points=ops, contrasts=contrasts, method_uncertainty=method_intervals, normal_log_native_over_uniform=normal_log, gate=gate, bootstrap_draw_sha256=hashes, threshold_cross=cross)
    return result, (groups, ck, nk, bk, draws, tau, td, points)


def analyze_p1_spatial(result, context, rows):
    groups, ck, nk, bk, draws, tau, td, points = context
    require(len(rows) == 1135 * 9 and len({(r['method'], r['path']) for r in rows}) == 1135 * 9, "Incomplete P1 spatial summaries")
    spatial = {(r["method"], r["path"]): r for r in rows}
    for group in groups.values():
        for r in group:
            for m in P1_METHODS:
                sr = spatial[(m, r["path"])]
                require(float(sr["max"]) == float(r[m]), "Full spatial maximum differs from scalar")
                require(max(float(sr[f"parity{p}_max"]) for p in PHASES) == float(sr["max"]), "Phase partition maximum differs")
    normal, peaks = [], []
    for candidate, reference in P1_PAIRS:
        for s in range(3):
            c, r = f"{candidate}_s{s}", f"{reference}_s{s}"
            vectors = {}
            for readout in READOUTS:
                field = "max" if readout == "full" else readout + "_max"
                v = np.asarray([np.mean([math.log(float(spatial[(r, row["path"])][field]) / float(spatial[(c, row["path"])][field])) for row in groups[g]]) for g in ck])
                vectors[readout] = v
                normal.append(dict(candidate=candidate, reference=reference, seed=s, endpoint=f"log_{reference}_over_{candidate}:{readout}", **distribution(v[draws[0]].mean(axis=1), v.mean(), True)))
            for readout in READOUTS[1:]:
                v = vectors["full"] - vectors[readout]
                normal.append(dict(candidate=candidate, reference=reference, seed=s, endpoint="full_minus_" + readout, **distribution(v[draws[0]].mean(axis=1), v.mean(), True)))
            j, k = P1_METHODS.index(c), P1_METHODS.index(r)
            normal.append(dict(candidate=candidate, reference=reference, seed=s, endpoint=f"log_tau_{reference}_over_{candidate}", **distribution(np.log(td[:, k] / td[:, j]), math.log(tau[k] / tau[j]), True)))
    for m in P1_METHODS:
        for pop, keys in (("source_calibration", ck), ("development_normal", nk)):
            rs = [spatial[(m, r["path"])] for g in keys for r in groups[g]]
            peaks.append(dict(method=m, population=pop, views=len(rs), representative_boundary_peaks=sum(int(r["argmax_row"]) in (0, 63) or int(r["argmax_col"]) in (0, 63) for r in rs), unique_peaks=sum(int(r["image_max_tie_count"]) == 1 for r in rs), **{f"representative_parity{p}": sum(str(int(r["argmax_row"]) % 2) + str(int(r["argmax_col"]) % 2) == p for r in rs) for p in PHASES}))
    main = next(r for r in result["bootstrap_contrasts"] if (r["candidate"], r["reference"], r["seed"], r["regime"], r["metric"]) == ("balanced", "odd", "fixed_seed_mean", "joint", "supported_group_tpr"))
    gates = {}
    for s in (1, 2):
        g = next(r["point"] for r in normal if (r["candidate"], r["reference"], r["seed"], r["endpoint"]) == ("balanced", "odd", s, "log_odd_over_balanced:full"))
        delta = float(points[3+s, 1] - points[s, 1])
        gates[str(s)] = dict(delta_supported_tpr=delta, normal_mean_log_odd_over_balanced=g, **{"pass": delta >= .1 and g > 0})
    passed = all(r["pass"] for r in gates.values()) and main["ci95"][0] > 0
    screen = all(points[6+s, 1] - points[3+s, 1] >= -.05 and round((points[6+s, 0] - points[3+s, 0]) * 44) <= 1 for s in range(3))
    result.update(normal_contrasts=normal, peak_rows=peaks, decision=dict(new_seed_gates=gates, fixed_seed_mean_joint_tpr=main, p1_effect_gate_pass=bool(passed), random_point_sufficiency_screen=bool(screen), p2_eligible_only_if_p0_and_identifiable_intervention=bool(passed), old_bank_scientific_gates_remain_failed=True, innovation_or_equal_population_risk_established=False))
    return spatial


def operating_summary(scorebank, readout, thresholdbank, unit, tau, groups, normal_keys, bad_keys, value):
    fp = sum(max(value(scorebank, readout, r["path"]) for r in groups[g]) > tau for g in normal_keys)
    any_count = sum(max(value(scorebank, readout, r["path"]) for r in groups[g]) > tau for g in bad_keys)
    supported = sum(max(value(scorebank, readout, r["path"]) for r in groups[g] if r["anomaly_class"] != "OK") > tau for g in bad_keys)
    return dict(score_bank=scorebank, readout=readout, threshold_bank=thresholdbank, threshold_unit=unit, threshold=float(tau), normal_groups=44, abnormal_groups=107, normal_false_positive_groups=int(fp), any_detected_abnormal_groups=int(any_count), supported_detected_abnormal_groups=int(supported), normal_group_fpr=fp/44, any_group_tpr=any_count/107, supported_group_tpr=supported/107)


def analyze_y(context, spatial):
    groups, ck, nk, bk, *_ = context
    banks = ("dino_odd_own", "dino_balanced_own")
    methods = dict(zip(banks, ("odd_s0", "balanced_s0")))
    def value(bank, readout, path):
        return float(spatial[(methods[bank], path)]["max" if readout == "full" else f"parity{readout}_max"])
    taus, swaps = {}, []
    for bank, readout, unit in itertools.product(banks, ("full", *PHASES), ("image", "group")):
        a = [value(bank, readout, r["path"]) for g in ck for r in groups[g]] if unit == "image" else [max(value(bank, readout, r["path"]) for r in groups[g]) for g in ck]
        taus[bank, readout, unit] = threshold(a)
    for readout, unit, scorebank, thresholdbank in itertools.product(("full", *PHASES), ("image", "group"), banks, banks):
        swaps.append(operating_summary(scorebank, readout, thresholdbank, unit, taus[thresholdbank, readout, unit], groups, nk, bk, value))
    vectors = {p: np.asarray([np.mean([float(np.log(value(banks[0], p, r["path"]) / value(banks[1], p, r["path"]))) for r in sorted(groups[g], key=lambda r: int(r["camera"]))]) for g in ck]) for p in ("full", *PHASES)}
    draws = np.random.Generator(np.random.PCG64(20261013)).integers(0, 76, size=(5000, 76))
    def endpoint(v):
        return {"estimate": float(v.mean()), "ci95": [float(x) for x in np.quantile(v[draws].mean(axis=1), [.025, .975])]}
    return dict(primary={"g_full": endpoint(vectors["full"]), "g_11": endpoint(vectors["11"]), "interaction": endpoint(vectors["full"] - vectors["11"])}, descriptive_phases={p: {"g_phase": endpoint(vectors[p]), "interaction": endpoint(vectors["full"] - vectors[p])} for p in PHASES}, threshold_swap=swaps)


def analyze_x(rows, manifest):
    groups, ck, nk, bk, _ = admit_scores(rows, manifest, X_METHODS)
    def value(bank, readout, path):
        return float(index[path][bank])
    index = {r["path"]: r for r in rows}
    result = []
    for method, calibration, unit in itertools.product(X_METHODS, ("fixed_original_balanced", "independently_recalibrated"), ("image", "group")):
        bank = "dino_balanced_own" if calibration == "fixed_original_balanced" else method
        cal = [float(r[bank]) for g in ck for r in groups[g]] if unit == "image" else [max(float(r[bank]) for r in groups[g]) for g in ck]
        r = operating_summary(method, "full", bank, unit, threshold(cal), groups, nk, bk, value)
        result.append(dict(method=method, calibration=calibration, threshold_unit=unit, threshold=r["threshold"], normal_groups=44, abnormal_groups=107, normal_false_positive_groups=r["normal_false_positive_groups"], abnormal_any_detected_groups=r["any_detected_abnormal_groups"], abnormal_supported_groups=r["supported_detected_abnormal_groups"], normal_group_fpr=r["normal_group_fpr"], abnormal_any_group_tpr=r["any_group_tpr"], abnormal_supported_group_tpr=r["supported_group_tpr"]))
    return result


def analyze_x_control(spatial_rows, deletions, manifest):
    """Check the saved 92+92 control and reproduce its conditional normal CIs."""
    counts = Counter(r["deletion"] for r in deletions)
    require(counts == {"target": 92, "sham": 92}, "X deletion count differs")
    strata = {}
    for kind in ("target", "sham"):
        selected = [r for r in deletions if r["deletion"] == kind]
        require(len({r["prototype"] for r in selected}) == 92, "Duplicate X deletion")
        for r in selected:
            require(r["path"] in manifest and manifest[r["path"]]["research_role"] == "source_fit", "X deletion outside fitting role")
            rr, cc = int(r["row"]), int(r["col"])
            require((rr == 0 or cc == 0) if kind == "target" else (1 <= rr <= 62 and 1 <= cc <= 62), "X deletion violates spatial rule")
        strata[kind] = Counter((r["camera"], int(r["row"]) % 2, int(r["col"]) % 2) for r in selected)
    require(strata["target"] == strata["sham"], "X camera/phase quotas differ")
    cal = defaultdict(list)
    for r in manifest.values():
        if r["research_role"] == "source_calibration":
            cal[r["group_key"]].append(r)
    keys = sorted(cal)
    index = {(r["method"], r["path"]): r for r in spatial_rows}
    require(len(index) == len(spatial_rows) == 380 * 4, "Incomplete X calibration summaries")
    vectors, camera_vectors = {}, {}
    for endpoint, field in (("full", "max"), ("top_left", "top_left_max"), ("interior", "interior_max")):
        def logratio(r):
            return float(np.log(float(index[("balanced_delete_topleft", r["path"])][field]) / float(index[("balanced_delete_interior_sham", r["path"])][field])))
        vectors[endpoint] = np.asarray([np.mean([logratio(r) for r in sorted(cal[g], key=lambda r: int(r["camera"]))]) for g in keys])
        for camera in range(1, 6):
            camera_vectors[camera, endpoint] = np.asarray([logratio(next(r for r in cal[g] if int(r["camera"]) == camera)) for g in keys])
    vectors["spatial_interaction"] = vectors["top_left"] - vectors["interior"]
    for camera in range(1, 6):
        camera_vectors[camera, "spatial_interaction"] = camera_vectors[camera, "top_left"] - camera_vectors[camera, "interior"]
    draws = np.random.Generator(np.random.PCG64(20261012)).integers(0, 76, size=(5000, 76))
    def summary(v):
        ci = [float(x) for x in np.quantile(v[draws].mean(axis=1), [.025, .975])]
        return dict(mean_log_contrast=float(v.mean()), conditional_percentile95=ci, geometric_ratio_or_ratio_of_ratios=float(np.exp(v.mean())), positive_lower_bound=ci[0] > 0)
    endpoints = {k: summary(v) for k, v in vectors.items()}
    return dict(unit="76 five-view source-normal groups", seed=20261012, bootstrap_samples=5000, endpoints=endpoints, diagnostic_gate_pass=endpoints["full"]["positive_lower_bound"] and endpoints["spatial_interaction"]["positive_lower_bound"], innovation_proven=False, per_camera=[dict(camera=camera, endpoint=endpoint, **summary(camera_vectors[camera, endpoint])) for camera in range(1, 6) for endpoint in vectors], deletion_counts=dict(counts), remaining_bank_size=4004)


def analyze_p2(edges, manifest):
    require(len(edges) == 375 and len({(r["path"], r["target_phase"]) for r in edges}) == 375, "P2 legal-edge set changed")
    for r in edges:
        require(r["path"] in manifest and manifest[r["path"]]["research_role"] == "source_fit" and manifest[r["path"]]["camera"] == r["camera"], "P2 edge outside fitting manifest")
        require(float(r["replace_relative"]) <= .1 and float(r["residual_relative"]) <= .1 and float(r["direct_ratio"]) <= .5 and r["all_hard_gates"] == "True", "P2 saved edge is not legal")
    cameras, hall = {}, []
    for camera in ("1", "2", "3", "4", "5"):
        paths = sorted(p for p, r in manifest.items() if r["research_role"] == "source_fit" and r["camera"] == camera)
        lookup = {p: i for i, p in enumerate(paths)}
        local = [r for r in edges if r["camera"] == camera]
        cost = np.full((len(paths), 48), 1000.0)
        for r in local:
            phase = ("00", "01", "10").index(r["target_phase"])
            cost[lookup[r["path"]], phase*16:(phase+1)*16] = float(r["cost"])
        ii, jj = linear_sum_assignment(cost)
        missing = int((cost[ii, jj] == 1000).sum())
        cameras[camera] = dict(all_slots_legal=missing == 0, assignment_total_cost=float(cost[ii, jj].sum()), sentinel_selections=missing, legal_image_phase_edges=len(local))
        for n in (1, 2, 3):
            for subset in itertools.combinations(("00", "01", "10"), n):
                available = len({r["path"] for r in local if r["target_phase"] in subset})
                hall.append(dict(camera=camera, phases="+".join(subset), available_sources=available, required_slots=16*n, deficit=max(0, 16*n-available)))
    failed = [c for c, r in cameras.items() if not r["all_slots_legal"]]
    return dict(status="MATCHING_INCONCLUSIVE" if failed else "MATCHING_FEASIBLE", failed_cameras=failed, assignment_passed=not failed, camera_assignment_summary=cameras, K=240, query_pixels_requested=0, hall_capacity=hall, mechanism_tested=False)


def compare_reference(actual, expected, path="", errors=None, counters=None):
    """Compare archived fields recursively; extra computed fields are permitted."""
    errors = [] if errors is None else errors
    counters = {"checked_leaves": 0, "max_absolute_numeric_error": 0.0} if counters is None else counters
    if isinstance(expected, dict):
        for k, v in expected.items():
            if k not in actual:
                errors.append(path + "/" + k + ": missing")
            else:
                compare_reference(actual[k], v, path + "/" + k, errors, counters)
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            errors.append(path + ": length mismatch")
        else:
            for i, (a, e) in enumerate(zip(actual, expected)):
                compare_reference(a, e, path + f"/{i}", errors, counters)
    else:
        counters["checked_leaves"] += 1
        if isinstance(expected, (int, float)) and not isinstance(expected, bool):
            diff = abs(float(actual) - expected)
            counters["max_absolute_numeric_error"] = max(counters["max_absolute_numeric_error"], diff)
            if not math.isfinite(float(actual)) or diff > 1e-12:
                errors.append(path + f": {actual!r} != {expected!r}")
        elif actual != expected:
            errors.append(path + f": {actual!r} != {expected!r}")
    return errors, counters


def reproduce(data_dir, output_dir):
    start = time.perf_counter()
    data, out = Path(data_dir), Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest = validate_manifest(read_csv(data / "manifests/plastic_nut.csv"))
    d = data / "derived"
    p1, context = analyze_operating(read_csv(d / "p1_scores.csv"), manifest, "p1")
    spatial = analyze_p1_spatial(p1, context, read_csv(d / "p1_spatial.csv"))
    e, _ = analyze_operating(read_csv(d / "e_scores.csv"), manifest, "e")
    y = analyze_y(context, spatial)
    x = analyze_x(read_csv(d / "x_scores.csv"), manifest)
    x_control = analyze_x_control(read_csv(d / "x_calibration_spatial.csv"), read_csv(d / "x_deletions.csv"), manifest)
    p2 = analyze_p2(read_csv(d / "p2_source_phase_edges.csv"), manifest)
    # Match the informational draw-description fields in the archived P1 schema.
    p1["bootstrap_draws"].update(generator="numpy.random.Generator(PCG64(20261031))", allocation_order=["calibration (5000,76)", "normal development (5000,44)", "abnormal development (5000,107)"], dtype="int64", indices_hash_endianness="little")
    results = dict(p1=p1, e=e, y=y, x=x, x_control=x_control, p2=p2)
    errors, counts = [], {"checked_leaves": 0, "max_absolute_numeric_error": 0.0}
    for study in ("p1", "e", "y", "p2"):
        compare_reference(results[study], read_json(d / f"reference_{study}.json"), study, errors, counts)
    expected_x = read_csv(d / "reference_x_operating.csv")
    for r in expected_x:
        for k in list(r):
            if k not in ("method", "calibration", "threshold_unit"):
                r[k] = float(r[k])
    compare_reference(x, expected_x, "x", errors, counts)
    compare_reference(x_control, read_json(d / "reference_x_primary.json"), "x_control", errors, counts)
    e_cross = read_csv(d / "reference_e_threshold_cross.csv")
    for r in e_cross:
        for k in r:
            if k not in ("score_method", "threshold_method"):
                r[k] = float(r[k])
    compare_reference(e["threshold_cross"], e_cross, "e_threshold_cross", errors, counts)
    inputs = sorted([*d.glob("*.csv"), *d.glob("*.json"), *(data / "manifests").glob("*.csv"), *(data / "manifests").glob("*.json")])
    receipt = dict(status="PASS" if not errors else "FAIL", **counts, errors=errors, wall_seconds=time.perf_counter()-start, numpy_version=np.__version__, manifest_identity_sha256=MANIFEST_IDENTITY_SHA256, identity_binding_does_not_authenticate_image_bytes=True, input_sha256={str(p.relative_to(data)).replace("\\", "/"): sha256(p) for p in inputs}, new_pixels=0, confirmation_access=0, gpu_seconds=0)
    write_json(out / "verification.json", receipt)
    require(not errors, "Archived-result comparison failed; see verification.json")
    write_json(out / "results.json", results)
    write_csv(out / "table1_full_query.csv", p1["operating_rows"])
    write_csv(out / "table2_threshold_exchange_all40.csv", y["threshold_swap"])
    write_csv(out / "e_threshold_cross_all27.csv", e["threshold_cross"])
    write_csv(out / "x_boundary_control_all16.csv", x)
    write_csv(out / "p2_hall_capacity.csv", p2["hall_capacity"])
    return receipt


def analyze_local_run(data_dir, inference_dir, output_dir, study):
    """Analyze a completed local run without asserting archived-result equality.

    The inference receipt and identities are validated before any statistic.
    Historical reference estimates and decisions are never overwritten.
    """
    start = time.perf_counter()
    data, source, out = Path(data_dir), Path(inference_dir), Path(output_dir)
    manifest_path = data / "manifests/plastic_nut.csv"
    manifest = validate_manifest(read_csv(manifest_path))
    receipt = read_json(source / "freeze.json")
    require(receipt.get("status") == "COMPLETE_LOCAL_RECONSTRUCTION" and receipt.get("study") == study, "Incomplete run or study mismatch")
    require(receipt.get("manifest_sha256") == sha256(manifest_path), "Local run did not bind the supplied admitted manifest")
    methods = P1_METHODS if study == "p1" else E_METHODS
    require(receipt.get("methods") == list(methods) and receipt.get("coreset_seeds") == [0, 1, 2], "All nine methods and the three fixed seeds are required")
    require(receipt.get("confirmation_role_rows") == 0 and receipt.get("evaluated_query_cells") == 4096, "Unexpected role or query domain")
    require(receipt.get("bank_size") == 4096, "Unexpected bank size")
    required = ("scalar_predictions.csv", "spatial_statistics.csv") if study == "p1" else ("scalar_predictions.csv",)
    for filename in required:
        require(receipt.get("sha256_files", {}).get(filename) == sha256(source / filename), f"Receipt hash mismatch: {filename}")
    require(not out.resolve().is_relative_to(data.resolve()), "Local-run outputs must be outside the released data directory")
    require(out.resolve() != source.resolve(), "Use an analysis output directory separate from inference outputs")
    out.mkdir(parents=True, exist_ok=True)
    require(not any((out / name).exists() for name in ("results.json", "local_run_analysis.json", "operating_points.csv")), "Preserve an existing analysis; choose a new output directory")
    result, context = analyze_operating(read_csv(source / "scalar_predictions.csv"), manifest, study)
    output = {study: result}
    if study == "p1":
        spatial = analyze_p1_spatial(result, context, read_csv(source / "spatial_statistics.csv"))
        output["local_query_exchange"] = analyze_y(context, spatial)
        write_csv(out / "query_exchange_all40.csv", output["local_query_exchange"]["threshold_swap"])
    else:
        write_csv(out / "threshold_cross_all27.csv", result["threshold_cross"])
    output["scope"] = "Statistics from one completed local reconstruction. No comparison with historical references was made; this is not independent confirmation or asserted historical equivalence. Frozen criteria are reported descriptively and do not reopen prior decisions."
    write_json(out / "results.json", output)
    write_csv(out / "operating_points.csv", result["operating_rows" if study == "p1" else "operating_points"])
    audit = dict(status="LOCAL_RUN_ANALYZED", study=study, compared_with_historical_references=False, historical_files_modified=False, manifest_sha256=sha256(manifest_path), manifest_identity_sha256=MANIFEST_IDENTITY_SHA256, identity_binding_does_not_authenticate_image_bytes=True, local_freeze_sha256=sha256(source / "freeze.json"), input_sha256={name: sha256(source / name) for name in required}, wall_seconds=time.perf_counter()-start, new_pixels=0, confirmation_access=0, gpu_seconds=0)
    write_json(out / "local_run_analysis.json", audit)
    return audit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--inference-dir", type=Path, help="Analyze a completed local run instead of reproducing the archived summaries")
    parser.add_argument("--study", choices=("p1", "e"), help="Required with --inference-dir")
    args = parser.parse_args(argv)
    if bool(args.inference_dir) != bool(args.study):
        parser.error("--inference-dir and --study must be supplied together")
    result = analyze_local_run(args.data_dir, args.inference_dir, args.output_dir, args.study) if args.inference_dir else reproduce(args.data_dir, args.output_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
