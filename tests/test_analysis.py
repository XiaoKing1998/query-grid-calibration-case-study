"""Scientific behavior checks; runnable with unittest or pytest."""
import unittest
import json
from pathlib import Path
import tempfile

import numpy as np

from querygrid.analysis import analyze_local_run, compare_reference, read_csv, resample_operations, threshold, validate_manifest


class AnalysisTests(unittest.TestCase):
    def test_rank_and_strict_ties(self):
        cal = np.arange(1, 77, dtype=float)[:, None]
        normal = np.array([[74.], [75.], [20.]])
        bad = np.array([[73.], [100.]])
        tau, alarms, points, boot, draws, td = resample_operations(cal, normal, bad, bad, 64, 7)
        self.assertEqual(tau.tolist(), [74.])
        self.assertEqual(alarms[0].ravel().tolist(), [False, True, False])
        self.assertEqual(points[0, 0], 1/3)
        for b in range(64):
            expected_tau = sorted(cal[draws[0][b], 0])[73]
            self.assertEqual(td[b, 0], expected_tau)
            self.assertEqual(boot['joint'][b, 0, 0], np.mean(normal[draws[1][b], 0] > expected_tau))

    def test_own_calibration_scale_invariance_and_pairing(self):
        cal = np.arange(1, 77, dtype=float)[:, None] * np.array([[1., 2.]])
        normal = np.array([[74., 148.], [75., 150.], [20., 40.]])
        bad = np.array([[73., 146.], [100., 200.]])
        _, _, points, boot, _, _ = resample_operations(cal, normal, bad, bad, 128, 7)
        np.testing.assert_array_equal(points[0], points[1])
        for values in boot.values():
            np.testing.assert_array_equal(values[:, 0], values[:, 1])

    def test_too_small_calibration_rejected(self):
        with self.assertRaises(ValueError):
            threshold([1., 2.])

    def test_manifest_does_not_accept_new_role_or_partial_data(self):
        with self.assertRaises(ValueError):
            validate_manifest([dict(category='plastic_nut', path='plastic_nut/test.jpg', group_key='g', camera='1', research_role='confirmation', anomaly_class='OK')])

    def test_reference_check_catches_changed_estimate_and_missing_bound(self):
        errors, _ = compare_reference({'point': .1, 'lower': 0.}, {'point': .2, 'lower': 0., 'upper': .4})
        self.assertEqual(len(errors), 2)
        errors, _ = compare_reference({'point': .1 + 1e-15}, {'point': .1})
        self.assertEqual(errors, [])

    def test_local_run_rejects_incomplete_receipt_before_scores(self):
        data = Path(__file__).resolve().parents[1] / 'data'
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'inference'
            source.mkdir()
            (source / 'freeze.json').write_text(json.dumps({'status': 'FAILED_LOCAL_RECONSTRUCTION', 'study': 'p1'}), encoding='utf8')
            with self.assertRaisesRegex(ValueError, 'Incomplete run'):
                analyze_local_run(data, source, Path(directory) / 'analysis', 'p1')

    def test_canonical_manifest_binds_identity_beyond_counts(self):
        rows = read_csv(Path(__file__).resolve().parents[1] / 'data/manifests/plastic_nut.csv')
        rows[0]['path'] = rows[0]['path'].replace('.jpg', '_different.jpg')
        with self.assertRaisesRegex(ValueError, 'canonical admitted set'):
            validate_manifest(rows)

    def test_canonical_manifest_binds_anomaly_class_beyond_abnormal_count(self):
        rows = read_csv(Path(__file__).resolve().parents[1] / 'data/manifests/plastic_nut.csv')
        row = next(r for r in rows if r['anomaly_class'] != 'OK')
        row['anomaly_class'] = 'AK' if row['anomaly_class'] != 'AK' else 'HS'
        with self.assertRaisesRegex(ValueError, 'canonical admitted set'):
            validate_manifest(rows)

    def test_canonical_manifest_accepts_row_order_change(self):
        rows = read_csv(Path(__file__).resolve().parents[1] / 'data/manifests/plastic_nut.csv')
        self.assertEqual(len(validate_manifest(list(reversed(rows)))), 2010)


if __name__ == '__main__':
    unittest.main()
