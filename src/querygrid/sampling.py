"""Candidate rules and coreset selection for the released case-study code.

This is a portable reconstruction, not an unmodified historical experiment file.
The approximate greedy algorithm follows amazon-science/patchcore-inspection,
commit fcaa92f124fb1ad74a7acf56726decd4b27cbcad, src/patchcore/sampler.py
(Apache-2.0). See THIRD_PARTY_NOTICES.md and the bundled license information.
Projection is used for selection only; returned bank vectors retain their
original feature coordinates. No model or dataset is loaded by this module.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence

import numpy as np

P1_CONSTRUCTIONS = ("odd", "balanced", "random")
E_CONSTRUCTIONS = ("native", "uniform", "native_shuffle")
CORESET_SEEDS = (0, 1, 2)
GRID_SIZE = 64
CELLS = GRID_SIZE * GRID_SIZE
PATCHCORE_COMMIT = "fcaa92f124fb1ad74a7acf56726decd4b27cbcad"
EXTERNAL_RULE_COMMIT = "bb61a9644b0c3c6c0f1f890245a55d2d71bb265e"


def _path_seed(namespace: str, path: str) -> int:
    return int.from_bytes(hashlib.sha256((namespace + path).encode("utf-8")).digest()[:8], "little")


def p1_candidate_cells(path: str, construction: str | None = None):
    """Return ordered fine-grid identities, preserving the historical RNG calls.

    Every image contributes 256 candidates. Odd and balanced share 256 sampled
    coarse cells; balanced chooses one fine token per cell and exactly 64 tokens
    per parity. The quotas do not constrain the subsequently selected bank.
    """
    if not isinstance(path, str) or not path:
        raise ValueError("A nonempty manifest-relative path is required")
    coarse = np.random.default_rng(_path_seed("bank256:", path)).choice(1024, 256, replace=False)
    rr, cc = coarse // 32, coarse % 32
    phase = np.random.default_rng(_path_seed("phase256:", path)).permutation(np.tile(np.arange(4), 64))
    result = {
        "odd": (2 * rr + 1) * 64 + 2 * cc + 1,
        "balanced": (2 * rr + phase // 2) * 64 + 2 * cc + phase % 2,
        "random": np.random.default_rng(_path_seed("random256-v1:", path)).choice(4096, 256, replace=False),
    }
    if construction is None:
        return result
    if construction not in result:
        raise ValueError(f"Unknown P1 construction: {construction}")
    return result[construction]


def _native_candidate_ids(order: np.ndarray, *, cells: int, batch_images: int,
                          reservoir_size: int, candidate_count: int) -> np.ndarray:
    """Repeated capped concatenation, followed by a fresh seed-42 final draw.

    This is the transferred public rule, not textbook reservoir sampling.
    The first incoming batch is retained as in the original implementation.
    """
    rng = np.random.default_rng(42)
    reservoir = None
    for start in range(0, len(order), batch_images):
        incoming = (order[start:start + batch_images, None] * cells + np.arange(cells)[None]).ravel()
        if reservoir is None:
            reservoir = incoming
        else:
            combined = np.concatenate([reservoir, incoming])
            reservoir = (combined[rng.choice(len(combined), size=reservoir_size, replace=False)]
                         if len(combined) > reservoir_size else combined)
    if reservoir is None or len(reservoir) < candidate_count:
        raise ValueError("Not enough source candidates for the fixed final draw")
    return reservoir[np.random.default_rng(42).choice(len(reservoir), size=candidate_count, replace=False)]


def external_candidate_identities(paths: Sequence[str], construction: str | None = None, *,
                                  cells: int = CELLS, batch_images: int = 8,
                                  reservoir_size: int = 50000, candidate_count: int = 20000):
    """Return ordered global patch IDs: source_index * cells + patch_index.

    Production uses the defaults. Smaller dimensions are exposed solely for
    synthetic tests. Input paths must already have the frozen source ordering.
    Uniform is a distributional full-history control, not an equal-CPU-cost
    emulation of the two-stage native rule.
    """
    if not paths or len(set(paths)) != len(paths):
        raise ValueError("Source paths must be nonempty and unique")
    if min(cells, batch_images, reservoir_size, candidate_count) <= 0:
        raise ValueError("Candidate dimensions must be positive")
    if candidate_count > reservoir_size or candidate_count > len(paths) * cells:
        raise ValueError("Candidate count exceeds the available budget")
    natural = np.arange(len(paths), dtype=np.int64)
    shuffled = np.asarray(sorted(natural.tolist(), key=lambda i: (
        hashlib.sha256(("external-sampling-shuffle-v1:" + paths[i]).encode("utf-8")).digest(), paths[i]
    )), dtype=np.int64)
    options = dict(cells=cells, batch_images=batch_images, reservoir_size=reservoir_size,
                   candidate_count=candidate_count)
    pools = {
        "native": _native_candidate_ids(natural, **options),
        "uniform": np.random.default_rng(42).choice(len(paths) * cells, size=candidate_count, replace=False),
        "native_shuffle": _native_candidate_ids(shuffled, **options),
    }
    if construction is None:
        return pools
    if construction not in pools:
        raise ValueError(f"Unknown external construction: {construction}")
    return pools[construction]


def candidate_digest(indices: np.ndarray) -> str:
    """Hash ordered identities using a platform-independent integer encoding."""
    return hashlib.sha256(np.asarray(indices, dtype="<i8").tobytes(order="C")).hexdigest()


def approximate_greedy_coreset(features: np.ndarray, bank_size: int = 4096, seed: int = 0, *,
                                device: str = "cuda", projection_dim: int = 128,
                                starting_points: int = 10,
                                check_budget: Callable[[], None] | None = None):
    """Select original vectors with the pinned PatchCore arithmetic and RNG order.

    A CPU-initialized, untrained Linear(D, 128, bias=False) is moved to the
    requested device. Ten legacy-NumPy random anchors initialize mean Euclidean
    distances. Greedy updates retain the smaller distance. Argmax tie behavior
    matches PyTorch; degenerate all-identical inputs can select repeated IDs,
    which are deliberately not repaired because that would change the method.
    """
    import torch

    if not isinstance(features, np.ndarray) or features.ndim != 2 or features.dtype != np.float32:
        raise ValueError("Coreset input must be a two-dimensional float32 numpy array")
    if not np.isfinite(features).all() or features.shape[1] == 0:
        raise ValueError("Coreset input must be finite and have feature columns")
    if not 0 < bank_size < len(features):
        raise ValueError("Bank size must be positive and smaller than the candidate pool")
    if projection_dim <= 0 or starting_points <= 0:
        raise ValueError("Projection and anchor dimensions must be positive")
    target = torch.device(device)
    original = torch.from_numpy(np.ascontiguousarray(features))
    # Only the CPU generator creates projection weights. Keep caller RNG state.
    with torch.random.fork_rng(devices=[]), torch.no_grad():
        torch.manual_seed(seed)
        if features.shape[1] == projection_dim:
            reduced = original.to(target)
        else:
            mapper = torch.nn.Linear(features.shape[1], projection_dim, bias=False).to(target)
            reduced = mapper(original.to(target))
        # RandomState reproduces np.random.seed(seed); np.random.choice(...).
        anchors = np.random.RandomState(seed).choice(len(features), min(starting_points, len(features)), replace=False)

        def distances(a, b):
            if check_budget is not None:
                check_budget()
            aa = a.unsqueeze(1).bmm(a.unsqueeze(2)).reshape(-1, 1)
            bb = b.unsqueeze(1).bmm(b.unsqueeze(2)).reshape(1, -1)
            ab = a.mm(b.T)
            return (-2 * ab + aa + bb).clamp(0, None).sqrt()

        current = torch.mean(distances(reduced, reduced[anchors.tolist()]), axis=-1).reshape(-1, 1)
        selected = []
        for _ in range(bank_size):
            index = torch.argmax(current).item()
            selected.append(index)
            next_distance = distances(reduced, reduced[index:index + 1])
            current = torch.min(torch.cat([current, next_distance], dim=-1), dim=1).values.reshape(-1, 1)
    indices = np.asarray(selected, dtype=np.int64)
    # Index the original 768-dimensional features, never the projected features.
    return features[indices].copy(), indices
