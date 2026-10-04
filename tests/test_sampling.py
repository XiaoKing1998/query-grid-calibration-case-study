"""Synthetic-only tests. No study image, model download, or CUDA execution."""


import csv


import importlib


import json


import tempfile


import unittest
from unittest.mock import patch


from pathlib import Path


import numpy as np


from querygrid.inference import (
    IDENTITY_FIELDS, _local_image_path, _write_csv, _write_json, embed_image, nearest_squared,
    manifest_identity_digest, region_masks, run_study, summarize_distances, validate_manifest,
)


from querygrid.sampling import (
    approximate_greedy_coreset, candidate_digest,
    external_candidate_identities, p1_candidate_cells,
)



def _optional_import(name):
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        raise unittest.SkipTest(f"Optional dependency unavailable: {name}") from exc


def _synthetic_manifest(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    rows = []
    for role in ("source_fit", "source_calibration", "development"):
        for camera in range(1, 6):
            name = f"{role}_{camera}.jpg"
            (root / name).write_bytes(b"synthetic path-only placeholder; never decoded")
            rows.append(dict(category="plastic_nut", path=name, group_key=role, camera=camera,
                             research_role=role, anomaly_class="OK"))
    manifest = tmp_path / "manifest.csv"
    return root, rows, manifest


def _save_manifest(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=IDENTITY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)



class SamplingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="querygrid-synthetic-")
        self.addCleanup(temporary.cleanup)
        self.tmp_path = Path(temporary.name)

    def test_invalid_wall_budget_fails_before_manifest_access(self):
        for limit in (float("nan"), float("inf"), float("-inf"), 0, -1):
            with self.subTest(limit=limit):
                with patch("querygrid.inference.validate_manifest") as validate:
                    with self.assertRaisesRegex(ValueError, "finite and positive"):
                        run_study(study="p1", manifest=self.tmp_path / "absent.csv",
                            data_root=self.tmp_path / "absent-data", output=self.tmp_path / "output",
                            checkpoint=self.tmp_path / "absent-checkpoint", dinov2_repo=self.tmp_path / "absent-repo",
                            device="cpu", max_wall_seconds=limit)
                    validate.assert_not_called()
                    assert not (self.tmp_path / "output").exists()

    def test_manifest_digest_ignores_input_order_but_binds_identity_and_role(self):
        root, rows, manifest = _synthetic_manifest(self.tmp_path)
        _save_manifest(manifest, rows)
        roles = validate_manifest(manifest, root, expected_counts={r: 5 for r in (
            "source_fit", "source_calibration", "development")})
        original = manifest_identity_digest(roles)
        for values in roles.values():
            values.reverse()
        assert manifest_identity_digest(roles) == original
        roles["source_fit"][0]["path"] = "replacement-synthetic.jpg"
        assert manifest_identity_digest(roles) != original

    def test_production_rejects_substituted_cohort_with_matching_counts(self):
        rows = []
        for role, count in (("source_fit", 175), ("source_calibration", 76), ("development", 151)):
            for group in range(count):
                for camera in range(1, 6):
                    abnormal = role == "development" and group >= 44 and (
                        camera <= 2 or (group < 88 and camera == 3))
                    rows.append(dict(category="plastic_nut", path=f"{role}/{group}_{camera}.jpg",
                        group_key=f"{role}_{group}", camera=camera, research_role=role,
                        anomaly_class="AK" if abnormal else "OK"))
        manifest = self.tmp_path / "substituted.csv"
        _save_manifest(manifest, rows)
        # No real files: isolate the metadata allowlist after path validation.
        with patch("querygrid.inference._local_image_path", side_effect=lambda root, relative: root / relative):
            with self.assertRaisesRegex(ValueError, "frozen historical allowlist"):
                validate_manifest(manifest, self.tmp_path)

    def test_p1_candidate_membership_pairing_and_frozen_order(self):
        path = "plastic_nut/train/OK/synthetic_C1_0001.jpg"
        pools = p1_candidate_cells(path)
        expected = {
            "odd": "aae418753918b58eeda3c4946c1eb65d6cf7c6bbc164d94db45078cf857a34e5",
            "balanced": "3f5342efbd9d5106ee7adaa80b4e4bb0a2245c1c44a5e92cc7b3517b2e7f740b",
            "random": "cb9433dfa3d1a819602ed6c541e4a8a9e86890561425983751d09cec13351450",
        }
        for name, values in pools.items():
            assert candidate_digest(values) == expected[name]
            assert len(values) == len(np.unique(values)) == 256
            assert values.min() >= 0 and values.max() < 4096
            assert np.array_equal(values, p1_candidate_cells(path, name))
        odd, balanced = pools["odd"], pools["balanced"]
        assert np.all((odd // 64) % 2 == 1) and np.all(odd % 2 == 1)
        assert np.array_equal((odd // 128) * 32 + (odd % 64) // 2,
                              (balanced // 128) * 32 + (balanced % 64) // 2)
        parity = (balanced // 64) % 2 * 2 + balanced % 2
        assert np.array_equal(np.bincount(parity), [64, 64, 64, 64])
        assert not np.array_equal(pools["random"], p1_candidate_cells(path + "x", "random"))


    def test_external_rule_matches_historical_synthetic_identity_fixture(self):
        # Fixture checked against the saved candidate-rule implementation, using
        # synthetic path strings only. It checks ordering as well as membership.
        paths = [f"synthetic/image_{i:04d}.jpg" for i in range(875)]
        pools = external_candidate_identities(paths)
        expected = {
            "native": "c688b51acc161ffd0c6d3bf023e65e8bb361ac45085e7873b15440ea15fbef09",
            "uniform": "3b9cba3f68c038ca1232cbaf01a1f3fcbc2ce48e966acd556db9ae86eb6a32f3",
            "native_shuffle": "587c35d5f0ec106cb96f2b85bd33a5ef59a1ed62c5089d785ad6a9ae4cc8bd36",
        }
        for name, values in pools.items():
            assert candidate_digest(values) == expected[name]
            assert len(values) == len(np.unique(values)) == 20000
            assert values.min() >= 0 and values.max() < 875 * 4096
        # The capped stream is order-sensitive; direct full-history sampling is not.
        reversed_pools = external_candidate_identities(list(reversed(paths)))
        assert np.array_equal(pools["uniform"], reversed_pools["uniform"])
        assert not np.array_equal(pools["native_shuffle"], reversed_pools["native_shuffle"])


    def test_external_final_draw_uses_a_fresh_rng(self):
        pools = external_candidate_identities(["a", "b"], cells=4, batch_images=1,
                                             reservoir_size=6, candidate_count=3)
        first = np.random.default_rng(42).choice(8, 6, replace=False)
        final = first[np.random.default_rng(42).choice(6, 3, replace=False)]
        assert np.array_equal(pools["native"], final)


    def test_external_invalid_dimensions_fail(self):
        cases = [([], {}), (["a", "a"], {}), (["a"], {"candidate_count": 5000}),
                 (["a"], {"cells": 0}), (["a"], {"reservoir_size": 1, "candidate_count": 2})]
        for paths, kwargs in cases:
            with self.subTest(paths=paths, kwargs=kwargs), self.assertRaises(ValueError):
                external_candidate_identities(paths, **kwargs)


    def test_coreset_matches_upstream_cpu_fixture_and_returns_original_features(self):
        torch = _optional_import("torch")
        torch.set_num_threads(1)
        features = np.random.default_rng(7029).standard_normal((64, 768), dtype=np.float32)
        expected = [[15, 28, 10, 39, 32, 1, 6, 56],
                    [11, 1, 45, 18, 28, 56, 6, 32],
                    [22, 1, 11, 58, 8, 15, 40, 26]]
        for seed in range(3):
            with self.subTest(seed=seed):
                calls = []
                bank, indices = approximate_greedy_coreset(features, 8, seed, device="cpu",
                                                          check_budget=lambda: calls.append(True))
                # Checked independently against the pinned sampler on the recorded CPU runtime.
                assert indices.tolist() == expected[seed]
                assert bank.shape == (8, 768)
                assert np.array_equal(bank, features[indices])
                assert len(calls) == 9


    def test_coreset_keeps_caller_cpu_rng_states(self):
        torch = _optional_import("torch")
        torch.set_num_threads(1)
        np.random.seed(791)
        torch.manual_seed(913)
        numpy_state, torch_state = np.random.get_state(), torch.random.get_rng_state().clone()
        features = np.arange(72, dtype=np.float32).reshape(12, 6)
        approximate_greedy_coreset(features, 3, 0, device="cpu", projection_dim=4)
        restored = np.random.get_state()
        assert numpy_state[0] == restored[0] and np.array_equal(numpy_state[1], restored[1])
        assert numpy_state[2:] == restored[2:]
        assert torch.equal(torch_state, torch.random.get_rng_state())


    def test_coreset_preserves_upstream_degenerate_tie_behavior(self):
        _optional_import("torch")
        bank, ids = approximate_greedy_coreset(np.zeros((12, 4), np.float32), 3, device="cpu", projection_dim=4)
        assert ids.tolist() == [0, 0, 0]
        assert bank.shape == (3, 4)


    def test_coreset_budget_exception_is_not_swallowed(self):
        _optional_import("torch")
        def stop():
            raise TimeoutError("synthetic limit")
        with self.assertRaises(TimeoutError):
            approximate_greedy_coreset(np.ones((12, 4), np.float32), 3, device="cpu", check_budget=stop)


    def test_exhaustive_squared_distance_across_query_chunks(self):
        torch = _optional_import("torch")
        query = np.array([[1, 1], [4, 5], [0, 0], [-1, 2], [5, 5]], dtype=np.float32)
        bank = torch.tensor([[0., 0.], [3., 4.]], dtype=torch.float32)
        expected = ((query[:, None, :] - bank.numpy()[None, :, :]) ** 2).sum(-1).min(-1)
        assert np.array_equal(nearest_squared(query, bank, chunk=2), expected)


    def test_region_summaries_include_boundary_full_grid_and_ties(self):
        row = dict(category="plastic_nut", path="synthetic.png", group_key="synthetic", camera=1,
                   research_role="source_calibration", anomaly_class="OK")
        masks = region_masks()
        for phase in ("00", "01", "10", "11"):
            assert masks["parity" + phase].sum() == 1024
            assert masks["interior_parity" + phase].sum() == 961
        distances = np.zeros(4096, np.float32)
        distances[0] = distances[-1] = 10
        distances[65] = 4
        result = summarize_distances(row, "odd_s0", distances)
        assert result["max"] == result["full_max"] == 10
        assert (result["argmax_row"], result["argmax_col"], result["image_max_tie_count"]) == (0, 0, 2)
        assert result["parity11_max"] == 10 and result["interior_parity11_max"] == 4
        assert result["image_max_ties_outer_ring"] == 2
        assert result["image_max_ties_interior"] == 0


    def test_manifest_sorting_and_complete_group_membership(self):
        tmp_path = self.tmp_path
        root, rows, manifest = _synthetic_manifest(tmp_path)
        _save_manifest(manifest, list(reversed(rows)))
        roles = validate_manifest(manifest, root, expected_counts={r: 5 for r in ("source_fit", "source_calibration", "development")})
        assert all([row["camera"] for row in values] == [1, 2, 3, 4, 5] for values in roles.values())


    def test_manifest_rejects_role_leakage_and_identity_errors(self):
        tmp_path = self.tmp_path
        root, original, manifest = _synthetic_manifest(tmp_path)
        cases = ("confirmation", "non_normal_fit", "unknown_class", "duplicate_camera", "mixed_group", "alias_path", "whitespace")
        for mutation in cases:
            rows = [dict(row) for row in original]
            if mutation == "confirmation":
                rows[-1]["research_role"] = "confirmation"
            elif mutation == "non_normal_fit":
                rows[0]["anomaly_class"] = "AK"
            elif mutation == "unknown_class":
                rows[-1]["anomaly_class"] = "unknown"
            elif mutation == "duplicate_camera":
                rows[1]["camera"] = 1
            elif mutation == "mixed_group":
                rows[-1]["group_key"] = "source_fit"
            elif mutation == "whitespace":
                rows[0]["path"] += " "
            else:
                rows[1]["path"] = rows[0]["path"]
            _save_manifest(manifest, rows)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_manifest(manifest, root, expected_counts={r: 5 for r in ("source_fit", "source_calibration", "development")})


    def test_local_path_rejects_traversal_and_absolute_paths(self):
        tmp_path = self.tmp_path
        # Synthetic drive syntax for rejection; this is not a user or project path.
        drive_path = "Z" + ":" + "/synthetic-rejected.jpg"
        for path in ("../escape.jpg", "/absolute.jpg", drive_path, "a\\b.jpg", "./a.jpg", "a//b.jpg"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                _local_image_path(tmp_path.resolve(), path)


    def test_local_path_rejects_external_symlink(self):
        tmp_path = self.tmp_path
        root = tmp_path / "data"
        root.mkdir()
        outside = tmp_path / "outside.jpg"
        outside.write_bytes(b"synthetic")
        try:
            (root / "alias.jpg").symlink_to(outside)
        except OSError:
            self.skipTest("The platform does not allow creating a test symlink")
        with self.assertRaises(ValueError):
            _local_image_path(root.resolve(), "alias.jpg")


    def test_preprocessing_contract_with_synthetic_image_and_fake_model(self):
        tmp_path = self.tmp_path
        torch = _optional_import("torch")
        image_module = _optional_import("PIL.Image")
        image = tmp_path / "synthetic.png"
        image_module.new("RGB", (1024, 1024), (255, 0, 128)).save(image)
        class FakeModel:
            def get_intermediate_layers(self, x, n, norm):
                assert tuple(x.shape) == (1, 3, 896, 896)
                assert n == (11,) and norm is True
                expected = (torch.tensor([1., 0., 128 / 255]) - torch.tensor([.485, .456, .406])) / torch.tensor([.229, .224, .225])
                assert torch.allclose(x[0, :, 0, 0], expected)
                return [torch.zeros((1, 4096, 768), dtype=torch.float32)]
        features, receipt = embed_image(FakeModel(), image, device="cpu")
        assert features.shape == (4096, 768)
        assert receipt["bytes"] == image.stat().st_size and len(receipt["sha256"]) == 64


    def test_manifest_rejects_duplicate_headers_and_extra_fields(self):
        tmp_path = self.tmp_path
        root, rows, manifest = _synthetic_manifest(tmp_path)
        _save_manifest(manifest, rows)
        original = manifest.read_text()
        for mutation in ("duplicate_header", "extra_field"):
            lines = original.splitlines()
            if mutation == "duplicate_header":
                lines[0] += ",path"
            else:
                lines[1] += ",unexpected"
            manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_manifest(manifest, root, expected_counts={r: 5 for r in ("source_fit", "source_calibration", "development")})


    def test_result_writers_publish_complete_files_and_preserve_failed_partial(self):
        tmp_path = self.tmp_path
        csv_path, json_path = tmp_path / "scores.csv", tmp_path / "receipt.json"
        _write_csv(csv_path, [{"method": "synthetic", "value": 2.0}])
        _write_json(json_path, {"status": "synthetic_complete"})
        with csv_path.open(newline="", encoding="utf-8") as handle:
            assert list(csv.DictReader(handle))[0]["value"] == "2.0"
        assert json.loads(json_path.read_text())["status"] == "synthetic_complete"
        assert not list(tmp_path.glob("*.partial"))
        failure_path = tmp_path / "invalid.json"
        with self.assertRaises(ValueError):
            _write_json(failure_path, {"invalid": float("nan")})
        assert not failure_path.exists()
        assert failure_path.with_name("invalid.json.partial").exists()
        with self.assertRaises(FileExistsError):
            _write_json(failure_path, {"valid": 1})



if __name__ == "__main__":
    unittest.main()
