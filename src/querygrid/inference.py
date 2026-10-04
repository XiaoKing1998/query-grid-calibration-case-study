"""Local-file inference for the released P1 and separate sampling-transfer study.

The implementation is a portable reconstruction of the saved experiments.
It never downloads models, authenticates to a service, or discovers extra data.
All inputs must be enumerated in a role-restricted local manifest. Runtime
receipts describe this new execution; they do not replace historical receipts.
"""
from __future__ import annotations

import csv
import gc
import hashlib
import importlib
import io
import json
import math
import platform
import sys
import time
from collections import defaultdict
from pathlib import Path, PurePosixPath

import numpy as np

from .sampling import (
    CORESET_SEEDS, E_CONSTRUCTIONS, EXTERNAL_RULE_COMMIT, P1_CONSTRUCTIONS,
    PATCHCORE_COMMIT, approximate_greedy_coreset, candidate_digest,
    external_candidate_identities, p1_candidate_cells,
)

IDENTITY_FIELDS = ("category", "path", "group_key", "camera", "research_role", "anomaly_class")
STUDY_COUNTS = {"source_fit": 875, "source_calibration": 380, "development": 755}
ANOMALY_CLASSES = frozenset(("OK", "AK", "HS", "QS", "ZW"))
MANIFEST_IDENTITY_SHA256 = "c580ed868943876c96f6e135a7f2e3f9fd489e49f0c9e34d9cf49d6827a7a23e"
CHECKPOINT_SHA256 = "0b8b82f85de91b424aded121c7e1dcc2b7bc6d0adeea651bf73a13307fad8c73"
GRID = 64
FEATURE_DIM = 768
BANK_SIZE = 4096


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for data in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def _local_image_path(data_root: Path, relative: str) -> Path:
    """Reject lexical traversal, Windows drives, and symlinks outside the root."""
    pure = PurePosixPath(relative)
    if not relative or "\\" in relative or ":" in relative or pure.is_absolute():
        raise ValueError("Manifest paths must be relative POSIX paths")
    if any(part in ("", ".", "..") for part in relative.split("/")):
        raise ValueError("Manifest paths cannot contain traversal or empty components")
    resolved = (data_root / pure).resolve()
    if not resolved.is_relative_to(data_root):
        raise ValueError("Manifest image path escapes data-root")
    if not resolved.is_file():
        raise ValueError(f"Manifest image is missing: {relative}")
    return resolved


def manifest_identity_digest(roles: dict[str, list[dict]]) -> str:
    """Bind six identity/role/label fields, independently of CSV formatting.

    Role order is fit, calibration, development. Within each role, sort by
    UTF-8 group key, integer camera, then UTF-8 relative path. The canonical
    payload is compact UTF-8 JSON containing lists in IDENTITY_FIELDS order.
    This authenticates admitted metadata, not user-supplied image contents.
    """
    values = []
    for role in STUDY_COUNTS:
        for row in sorted(roles[role], key=lambda r: (
                r["group_key"].encode("utf-8"), int(r["camera"]), r["path"].encode("utf-8"))):
            values.append([int(row[key]) if key == "camera" else row[key] for key in IDENTITY_FIELDS])
    payload = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_manifest(manifest: str | Path, data_root: str | Path, *,
                      expected_counts: dict[str, int] | None = None):
    """Validate the full allowlist before decoding an image or loading a model.

    The public run entry point always uses the historical study counts.
    expected_counts is available for synthetic validation tests only.
    """
    root = Path(data_root).resolve()
    if not root.is_dir():
        raise ValueError("data-root must be an existing local directory")
    with Path(manifest).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not set(IDENTITY_FIELDS).issubset(reader.fieldnames):
            raise ValueError("Manifest is missing required identity/role/label columns")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Manifest column names must be unique")
        records = list(reader)
    expected = STUDY_COUNTS if expected_counts is None else expected_counts
    if set(expected) != set(STUDY_COUNTS):
        raise ValueError("Only fitting, normal calibration, and development roles are admitted")
    roles = {role: [] for role in STUDY_COUNTS}
    paths, resolved_paths = set(), set()
    groups = defaultdict(list)
    for raw in records:
        if None in raw:
            raise ValueError("Manifest row has more fields than its header")
        row = {key: raw.get(key, "") for key in IDENTITY_FIELDS}
        if any(not isinstance(value, str) or not value.strip() for value in row.values()):
            raise ValueError("Manifest identity fields must be nonempty")
        if any(value != value.strip() for value in row.values()):
            raise ValueError("Manifest identity fields cannot have leading or trailing whitespace")
        if row["category"] != "plastic_nut":
            raise ValueError("This release admits only the original plastic_nut case study")
        if row["research_role"] not in roles:
            raise ValueError("Additional or confirmation roles are forbidden")
        if row["anomaly_class"] not in ANOMALY_CLASSES:
            raise ValueError("Anomaly class is outside the admitted plastic_nut labels")
        try:
            camera = int(row["camera"])
        except ValueError as exc:
            raise ValueError("Camera must be an integer from 1 through 5") from exc
        if camera not in range(1, 6):
            raise ValueError("Camera must be an integer from 1 through 5")
        row["camera"] = camera
        if row["research_role"] != "development" and row["anomaly_class"] != "OK":
            raise ValueError("Fitting and calibration inputs must be officially normal")
        path = _local_image_path(root, row["path"])
        if row["path"] in paths or path in resolved_paths:
            raise ValueError("Duplicate or aliased manifest image")
        paths.add(row["path"])
        resolved_paths.add(path)
        roles[row["research_role"]].append(row)
        groups[row["group_key"]].append(row)
    if {role: len(values) for role, values in roles.items()} != expected:
        raise ValueError(f"Manifest counts must equal {expected}")
    for key, values in groups.items():
        if len(values) != 5 or {row["camera"] for row in values} != set(range(1, 6)):
            raise ValueError(f"Each source group needs exactly one view from cameras 1..5: {key}")
        if len({row["research_role"] for row in values}) != 1:
            raise ValueError("A source group cannot span research roles")
    for values in roles.values():
        values.sort(key=lambda row: (row["group_key"].encode("utf-8"), row["camera"], row["path"].encode("utf-8")))
    if expected_counts is None:
        dev_groups = [v for v in groups.values() if v[0]["research_role"] == "development"]
        normal = sum(all(r["anomaly_class"] == "OK" for r in values) for values in dev_groups)
        abnormal_views = sum(r["anomaly_class"] != "OK" for r in roles["development"])
        if (len(dev_groups), normal, abnormal_views) != (151, 44, 258):
            raise ValueError("Development labels differ from the admitted 151-group historical cohort")
        if manifest_identity_digest(roles) != MANIFEST_IDENTITY_SHA256:
            raise ValueError("Manifest identities or roles differ from the frozen historical allowlist")
    return roles


def region_masks() -> dict[str, np.ndarray]:
    rr, cc = np.indices((GRID, GRID))
    interior = (rr >= 1) & (rr <= 62) & (cc >= 1) & (cc <= 62)
    result = {"top_left": (rr == 0) | (cc == 0), "bottom_right": (rr == 63) | (cc == 63),
              "outer_ring": (rr == 0) | (rr == 63) | (cc == 0) | (cc == 63), "interior": interior}
    for a in (0, 1):
        for b in (0, 1):
            parity = (rr % 2 == a) & (cc % 2 == b)
            result[f"parity{a}{b}"] = parity
            result[f"interior_parity{a}{b}"] = parity & interior
    return {name: value.ravel() for name, value in result.items()}


def summarize_distances(row: dict, method: str, distances: np.ndarray) -> dict:
    """Full-grid primary score and diagnostic regional maxima, including ties."""
    if distances.shape != (4096,) or not np.isfinite(distances).all() or np.any(distances < 0):
        raise ValueError("Expected 4096 finite nonnegative squared distances")
    peak = int(np.argmax(distances))
    ties = distances == distances[peak]
    result = {key: row[key] for key in IDENTITY_FIELDS}
    result.update(method=method, max=float(distances[peak]), full_max=float(distances[peak]),
                  argmax_row=peak // GRID, argmax_col=peak % GRID,
                  image_max_tie_count=int(ties.sum()), evaluated_query_cells=4096)
    for name, mask in region_masks().items():
        values = distances[mask]
        index = int(np.flatnonzero(mask)[np.argmax(values)])
        result.update({name + "_max": float(distances[index]), name + "_argmax_row": index // GRID,
                       name + "_argmax_col": index % GRID,
                       name + "_max_tie_count": int(np.count_nonzero(values == distances[index])),
                       "image_max_ties_" + name: int((ties & mask).sum())})
    return result


def configure_torch():
    import torch
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.set_float32_matmul_precision("highest")
    return torch


def nearest_squared(query: np.ndarray, bank, *, chunk: int = 256) -> np.ndarray:
    """Exhaustive FP32 squared Euclidean NN, matching historical arithmetic."""
    import torch
    if query.ndim != 2 or query.dtype != np.float32 or not np.isfinite(query).all():
        raise ValueError("Queries must be a finite float32 feature matrix")
    if bank.ndim != 2 or bank.dtype != torch.float32 or bank.shape[1] != query.shape[1] or not len(bank):
        raise ValueError("Bank must be a nonempty float32 matrix in the original feature space")
    if chunk <= 0 or not len(query):
        raise ValueError("Query count and chunk size must be positive")
    with torch.no_grad():
        bank_norm = (bank * bank).sum(1)
        output = []
        for q in torch.from_numpy(np.ascontiguousarray(query)).to(bank.device).split(chunk):
            distance = (q * q).sum(1, keepdim=True) + bank_norm[None] - 2 * (q @ bank.T)
            output.append(distance.clamp_min_(0).min(1).values.cpu().numpy())
    return np.concatenate(output)


def load_dino(dinov2_repo: str | Path, checkpoint: str | Path, *, device: str = "cuda"):
    """Load a user-supplied local checkout and the exact historical checkpoint."""
    import torch
    repo, weights = Path(dinov2_repo).resolve(), Path(checkpoint).resolve()
    if not (repo / "dinov2/hub/backbones.py").is_file():
        raise ValueError("dinov2-repo must contain dinov2/hub/backbones.py")
    if not weights.is_file() or _sha(weights) != CHECKPOINT_SHA256:
        raise ValueError("Checkpoint is missing or differs from the pinned ViT-B/14 checkpoint")
    for name, module in tuple(sys.modules.items()):
        if name == "dinov2" or name.startswith("dinov2."):
            location = getattr(module, "__file__", None)
            if location and not Path(location).resolve().is_relative_to(repo):
                raise ValueError("Another DINOv2 checkout is already imported in this process")
    sys.path.insert(0, str(repo))
    try:
        backbones = importlib.import_module("dinov2.hub.backbones")
    finally:
        sys.path.remove(str(repo))
    if not Path(backbones.__file__).resolve().is_relative_to(repo):
        raise ValueError("DINOv2 import did not resolve to the supplied local checkout")
    model = backbones.dinov2_vitb14(pretrained=False)
    model.load_state_dict(torch.load(weights, map_location="cpu", weights_only=True), strict=True)
    return model.eval().requires_grad_(False).to(device)


def embed_image(model, path: Path, *, device: str = "cuda"):
    import torch
    from PIL import Image
    raw = path.read_bytes()
    with Image.open(io.BytesIO(raw)) as image:
        if image.size != (1024, 1024):
            raise ValueError("The historical preprocessing requires 1024 by 1024 source images")
        array = np.array(image.convert("RGB").resize((896, 896), Image.Resampling.BILINEAR), dtype=np.float32) / 255.
    x = torch.from_numpy(array.transpose(2, 0, 1)).to(device)
    means = torch.tensor([.485, .456, .406], device=device)[:, None, None]
    stds = torch.tensor([.229, .224, .225], device=device)[:, None, None]
    x = (x - means) / stds
    with torch.no_grad():
        features = model.get_intermediate_layers(x[None], n=(11,), norm=True)[0][0].cpu().numpy()
    if features.shape != (4096, 768) or features.dtype != np.float32 or not np.isfinite(features).all():
        raise ValueError("DINOv2 did not return the required 64x64x768 finite FP32 features")
    return features, {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _write_csv(path: Path, records: list[dict]):
    if not records:
        raise ValueError("Cannot write an empty result table")
    partial = path.with_name(path.name + ".partial")
    with partial.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    partial.replace(path)


def _write_json(path: Path, value: dict):
    partial = path.with_name(path.name + ".partial")
    with partial.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
    partial.replace(path)


def run_study(*, study: str, manifest: str | Path, data_root: str | Path,
              output: str | Path, checkpoint: str | Path, dinov2_repo: str | Path,
              device: str = "cuda", seeds=CORESET_SEEDS, max_wall_seconds: float | None = None) -> dict:
    """Run one fixed nine-bank study on the manifest allowlist, using local I/O.

    Decoding is one image at a time. Fitting images are embedded once per study;
    calibration/development images are embedded once and queried against all
    nine banks. Dense maps, embeddings, banks and source pixels are not saved.
    """
    started = time.perf_counter()
    if study not in ("p1", "e") or tuple(seeds) != CORESET_SEEDS:
        raise ValueError("Supported studies are p1/e with the fixed coreset seeds 0,1,2")
    if max_wall_seconds is not None and (not math.isfinite(max_wall_seconds) or max_wall_seconds <= 0):
        raise ValueError("Wall-clock limit must be finite and positive")
    roles = validate_manifest(manifest, data_root)
    out, root = Path(output).resolve(), Path(data_root).resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError("Output must be a new or empty directory; existing evidence is never overwritten")
    out.mkdir(parents=True, exist_ok=True)
    # An exclusive claim closes the concurrent empty-directory check race.
    # A failed run keeps the claim and partial evidence; callers use a new output.
    with (out / "run_claim.json").open("x", encoding="utf-8") as handle:
        json.dump({"study": study, "manifest_sha256": _sha(Path(manifest)),
                   "status": "IN_PROGRESS_NOT_A_COMPLETION_RECEIPT"}, handle, indent=2)
    deadline = None if max_wall_seconds is None else started + max_wall_seconds

    def check_budget():
        if deadline is not None and time.perf_counter() > deadline:
            raise RuntimeError("Execution wall-clock limit reached")

    timings = {"fit_embedding_seconds": 0., "query_embedding_seconds": 0.,
               "coreset_seconds": {}, "nearest_seconds": {}}
    torch = None
    stage = "configuration"
    try:
        torch = configure_torch()
        target = torch.device(device)
        if target.type == "cuda" and not torch.cuda.is_available():
            raise ValueError("CUDA is unavailable; select an explicitly supported local device")
        if target.type not in ("cpu", "cuda"):
            raise ValueError("Only CPU and CUDA execution are supported")
        if target.type == "cuda":
            torch.cuda.reset_peak_memory_stats(target)
        model = load_dino(dinov2_repo, checkpoint, device=str(target))
        fit = roles["source_fit"]
        constructions = P1_CONSTRUCTIONS if study == "p1" else E_CONSTRUCTIONS
        methods = [f"{construction}_s{seed}" for construction in constructions for seed in seeds]
        if study == "p1":
            ids = {name: np.concatenate([i * 4096 + p1_candidate_cells(row["path"], name)
                    for i, row in enumerate(fit)]) for name in constructions}
        else:
            ids = external_candidate_identities([row["path"] for row in fit])
        pools = {name: np.empty((len(values), FEATURE_DIM), dtype=np.float32) for name, values in ids.items()}
        destinations = {name: [np.flatnonzero(values // 4096 == i) for i in range(len(fit))]
                        for name, values in ids.items()}
        image_receipts = []
        stage = "fitting_features"
        for i, row in enumerate(fit):
            check_budget()
            begin = time.perf_counter()
            features, receipt = embed_image(model, _local_image_path(root, row["path"]), device=str(target))
            timings["fit_embedding_seconds"] += time.perf_counter() - begin
            image_receipts.append({**row, **receipt})
            for name in constructions:
                where = destinations[name][i]
                pools[name][where] = features[ids[name][where] % 4096]
            if (i + 1) % 100 == 0:
                print(f"FIT_DINO896 {i + 1}/{len(fit)}", flush=True)
        banks, bank_hashes, bank_identities = {}, {}, []
        stage = "coreset_selection"
        for name in constructions:
            for seed in seeds:
                check_budget()
                method = f"{name}_s{seed}"
                begin = time.perf_counter()
                bank, chosen = approximate_greedy_coreset(pools[name], BANK_SIZE, seed,
                    device=str(target), projection_dim=128, starting_points=10, check_budget=check_budget)
                if len(np.unique(chosen)) != BANK_SIZE:
                    raise ValueError("Degenerate candidates produced duplicate prototype IDs; no repair is applied")
                if target.type == "cuda":
                    torch.cuda.synchronize(target)
                timings["coreset_seconds"][method] = time.perf_counter() - begin
                bank_hashes[method] = hashlib.sha256(bank.tobytes(order="C")).hexdigest()
                for prototype, index in enumerate(chosen):
                    global_id = int(ids[name][index])
                    source, cell = divmod(global_id, 4096)
                    bank_identities.append({"method": method, "construction": name, "seed": seed,
                        "prototype": prototype, "candidate_index": int(index), "global_patch_id": global_id,
                        "source_index": source, **fit[source], "row": cell // 64, "col": cell % 64})
                banks[method] = torch.from_numpy(bank.copy()).to(target)
                timings["nearest_seconds"][method] = 0.
                print(f"BANK_READY {method}", flush=True)
            del pools[name]
            gc.collect()
        del pools, bank, features
        scores, spatial, normal_statistics = [], [], []
        stage = "complete_query"
        query = roles["source_calibration"] + roles["development"]
        for i, row in enumerate(query):
            check_budget()
            begin = time.perf_counter()
            features, receipt = embed_image(model, _local_image_path(root, row["path"]), device=str(target))
            timings["query_embedding_seconds"] += time.perf_counter() - begin
            image_receipts.append({**row, **receipt})
            record = dict(row)
            for method in methods:
                check_budget()
                begin = time.perf_counter()
                distances = nearest_squared(features, banks[method], chunk=256)
                timings["nearest_seconds"][method] += time.perf_counter() - begin
                summary = summarize_distances(row, method, distances)
                spatial.append(summary)
                record[method] = summary["max"]
                if row["research_role"] == "source_calibration":
                    normal_statistics.append({**summary,
                        "mean_squared_nearest": float(distances.mean()),
                        "p95_squared_nearest": float(np.quantile(distances, .95)),
                        "max_squared_nearest": summary["max"]})
            scores.append(record)
            if (i + 1) % 100 == 0:
                print(f"QUERY_DINO896 {i + 1}/{len(query)}", flush=True)
        check_budget()
        stage = "saving_summaries"
        tables = {"scalar_predictions.csv": scores, "spatial_statistics.csv": spatial,
                  "normal_statistics.csv": normal_statistics, "bank_identities.csv": bank_identities,
                  "image_receipts.csv": image_receipts}
        for filename, records in tables.items():
            _write_csv(out / filename, records)
        repo = Path(dinov2_repo).resolve()
        code_hashes = {str(path.relative_to(repo)).replace("\\", "/"): _sha(path)
                       for path in sorted((repo / "dinov2").rglob("*.py"))}
        receipt = {"status": "COMPLETE_LOCAL_RECONSTRUCTION", "study": study,
            "implementation": "portable release; historical exact-bank equivalence is not asserted",
            "manifest_sha256": _sha(Path(manifest)), "checkpoint_sha256": _sha(Path(checkpoint)),
            "manifest_identity_sha256": manifest_identity_digest(roles),
            "source_sha256": {"inference.py": _sha(Path(__file__)),
                              "sampling.py": _sha(Path(__file__).with_name("sampling.py"))},
            "dinov2_source_sha256": code_hashes, "methods": methods, "coreset_seeds": list(seeds),
            "candidate_count_each": len(next(iter(ids.values()))), "bank_size": BANK_SIZE,
            "feature_dimension": FEATURE_DIM, "projection_dimension_selection_only": 128,
            "patchcore_commit": PATCHCORE_COMMIT, "external_rule_commit": EXTERNAL_RULE_COMMIT if study == "e" else None,
            "input_roles": STUDY_COUNTS, "evaluated_query_cells": 4096,
            "candidate_identity_sha256": {name: candidate_digest(value) for name, value in ids.items()},
            "bank_hashes": bank_hashes, "sha256_files": {name: _sha(out / name) for name in tables},
            "output_rows": {name: len(records) for name, records in tables.items()},
            "timings": timings, "wall_seconds": time.perf_counter() - started,
            "peak_cuda_allocated_bytes": int(torch.cuda.max_memory_allocated(target)) if target.type == "cuda" else None,
            "environment": {"python": platform.python_version(), "numpy": np.__version__,
                            "torch": torch.__version__, "cuda": torch.version.cuda, "device": str(target)},
            "dense_maps_features_or_banks_saved": False, "confirmation_role_rows": 0,
            "local_image_content_not_bound_to_historical_hashes": True,
            "new_execution_not_historical_confirmation": True}
        _write_json(out / "freeze.json", receipt)
        return receipt
    except Exception as exc:
        # Do not serialize arbitrary exception text containing user paths.
        failure = {"status": "FAILED_LOCAL_RECONSTRUCTION", "stage": stage,
                   "error_type": type(exc).__name__, "wall_seconds": time.perf_counter() - started,
                   "completed_receipt": False, "confirmation_role_rows": 0}
        _write_json(out / "failure.json", failure)
        raise
