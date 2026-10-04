"""Render the manuscript comparisons from the independently reproduced results."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def find(rows, **criteria):
    found = [r for r in rows if all(r[k] == v for k, v in criteria.items())]
    if len(found) != 1:
        raise ValueError(f"Expected one result for {criteria}; found {len(found)}")
    return found[0]


def render(results_path, output_dir):
    source = Path(results_path)
    result = json.loads(source.read_text(encoding="utf8"))
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42, "ps.fonttype": 42})
    normal = result["p1"]["normal_contrasts"]
    phase = [find(normal, candidate="balanced", reference="odd", seed=0, endpoint="log_odd_over_balanced:" + r) for r in ("full", "parity00", "parity01", "parity10", "parity11")]
    figure1, axes = plt.subplots(1, 2, figsize=(7.1, 2.9), layout="constrained")
    ax = axes[0]
    v = np.asarray([r["point"] for r in phase])
    ci = np.asarray([r["ci95"] for r in phase])
    ax.errorbar(np.arange(5), v, yerr=np.vstack((v-ci[:, 0], ci[:, 1]-v)), fmt="o", capsize=3, color="#246c9b")
    ax.axhline(0, color="0.5", linewidth=.7)
    ax.set(xticks=np.arange(5), xticklabels=["Full", "00", "01", "10", "11"], ylabel="Mean log score ratio (odd / balanced)", xlabel="Query domain", title="(a) Original two banks (seed 0)")
    interaction_rows = []
    for offset, endpoint, color, label in ((-.09, "full_minus_parity11", "#246c9b", "Full − phase 11"), (.09, "full_minus_interior_parity11", "#b36a2a", "Full − interior phase 11")):
        rows = [find(normal, candidate="balanced", reference="odd", seed=s, endpoint=endpoint) for s in range(3)]
        interaction_rows.extend(rows)
        v = np.asarray([r["point"] for r in rows]); ci = np.asarray([r["ci95"] for r in rows])
        axes[1].errorbar(np.arange(3)+offset, v, yerr=np.vstack((v-ci[:, 0], ci[:, 1]-v)), fmt="o", capsize=3, color=color, label=label)
    axes[1].axhline(0, color="0.5", linewidth=.7)
    axes[1].set(xticks=range(3), xticklabels=["0", "1", "2"], ylabel="Paired log-ratio contrast", xlabel="Fixed coreset seed", title="(b) Full-grid contrasts\n(reference retains boundary)")
    axes[1].legend(frameon=False, fontsize=7, loc="lower right")
    for ext in ("pdf", "png"):
        figure1.savefig(out / f"figure1_query_support.{ext}", dpi=300)
    plt.close(figure1)

    figure2, ax = plt.subplots(figsize=(7.1, 2.9), layout="constrained")
    plotted = []
    specifications = [("p1", "balanced", "odd", "Balanced − odd"), ("p1", "random", "balanced", "Random − balanced"), ("e", "uniform", "native", "Uniform − retained pool (E)")]
    for i, (study, candidate, reference, label) in enumerate(specifications):
        rows = result[study]["bootstrap_contrasts" if study == "p1" else "contrasts"]
        for offset, regime, color, marker in ((-.10, "fixed_calibration", "#246c9b", "o"), (.10, "joint", "#b36a2a", "s")):
            r = find(rows, candidate=candidate, reference=reference, seed="fixed_seed_mean", regime=regime, metric="supported_group_tpr" if study == "p1" else "supported_tpr")
            lo, hi = r["ci95"] if study == "p1" else (r["lower"], r["upper"])
            ax.errorbar(100*r["point"], i+offset, xerr=np.asarray([[100*(r["point"]-lo)], [100*(hi-r["point"])]]), fmt=marker, capsize=3, color=color, label=regime.replace("_", " ") if i == 0 else None)
            plotted.append(dict(study=study, **r))
    ax.axvline(0, color="0.5", linewidth=.7)
    ax.set(yticks=range(3), yticklabels=[r[3] for r in specifications], xlabel="Fixed-seed mean supported-detection difference (percentage points)")
    ax.invert_yaxis()
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    for ext in ("pdf", "png"):
        figure2.savefig(out / f"figure2_calibration_uncertainty.{ext}", dpi=300)
    plt.close(figure2)
    provenance = dict(results_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), figure1_phase_rows=phase, figure1_interaction_rows=interaction_rows, figure2_rows=plotted, interval_scope="Conditional pointwise 95% paired group-bootstrap percentile intervals; fixed coreset seeds are not independent data samples.", boundary_scope="Only the interior-phase-11 side excludes the boundary. The full-grid reference retains boundary queries.", transfer_scope="E is a separate 20,000-candidate rule transfer, not an external replication of the phase interaction.")
    (out / "figure_data.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf8")
    return provenance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("outputs/results.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/figures"))
    args = parser.parse_args(argv)
    render(args.results, args.output_dir)
    print(f"Saved two figures as PDF and PNG in {args.output_dir}")


if __name__ == "__main__":
    main()
