# Dataset-derived evidence in this release

These files contain metadata and score summaries derived from **Real-IAD**. They are separate from the original software license. See [LICENSE.txt](LICENSE.txt) for the dataset-derived material's license, attribution and restrictions. The official source is [Real-IAD on Hugging Face](https://huggingface.co/datasets/Real-IAD/Real-IAD). Access to original images remains subject to the dataset's terms; this package does not provide or bypass that access.

## Included roles and excluded material

The manifest contains only the already admitted `plastic_nut` subset: 875 fitting views, 380 normal-calibration views and 755 development views, in 402 complete five-camera groups. There are no confirmation rows. These roles preserve their original historical assignments. The data were reused during development and do not constitute an independent confirmation set.

No original images, masks, dense anomaly maps, extracted feature tensors, memory-bank vectors, authentication material, HTTP headers or signed download URLs are included. The official labels JSON is not redistributed in full. Only the 2,010 admitted rows retain the per-view anomaly-class metadata needed to distinguish supported from any-view detections.

All view paths are dataset-relative. `group_key` values are filename-derived acquisition identifiers and have not been verified as permanent physical-object identities. Machine-specific source paths and authentication-source details were removed. Provenance uses logical source labels, original basenames and SHA-256 hashes.

Analysis and local inference share a canonical SHA-256 binding of the six identity, role and label fields: `c580ed868943876c96f6e135a7f2e3f9fd489e49f0c9e34d9cf49d6827a7a23e`. The binding is independent of CSV row order and formatting. Matching counts alone is insufficient. This check authenticates the admitted metadata, **not** the bytes of locally supplied images.

## File inventory

### `manifests/`

- `plastic_nut.csv`: the complete 2,010-view allowlist. Columns are `category,path,group_key,camera,research_role,anomaly_class`. `OK` denotes an officially normal view.
- `provenance.json`: logical original evidence sources and hashes, scope, role counts and the count of admitted abnormal development views.

### `derived/`: input evidence

- `p1_scores.csv`: 1,135 calibration/development identities plus the nine `odd_s0..2`, `balanced_s0..2` and `random_s0..2` full-query score columns.
- `p1_spatial.csv`: the same nine banks' per-view full and regional maxima, representative maximum coordinates and maximum tie counts. These are compact scalar summaries, not maps. Region names preserve the original grid definitions.
- `p1_coverage.csv`: normal-view mean, 95th-percentile and maximum squared nearest-neighbor distances, retained for provenance.
- `e_scores.csv`: 1,135 identities plus the nine `native_s0..2`, `uniform_s0..2` and `native_shuffle_s0..2` scores from the separate 20,000-candidate transfer.
- `x_scores.csv`: full-query scores from the original odd and balanced banks, and the balanced bank after the target or sham 92-prototype deletion.
- `x_calibration_spatial.csv`: normal-calibration maxima for the four X banks, retaining full, top/left and interior readouts needed to reproduce X's original conditional intervals.
- `x_deletions.csv`: the 92 target and 92 sham prototype identities. These permit checks of the saved equal-count, camera and phase constraints.
- `p2_source_phase_edges.csv`: the 375 saved legal source-image/phase matching edges and scalar matching criteria. These permit a new exact assignment and Hall-capacity calculation from the saved graph. They do not independently reconstruct all original vector distances or prove that every possible vector pair was searched.

### `derived/`: archived comparison targets

- `reference_p1.json`: original P1 operating points, method/contrast intervals, normal phase contrasts, peak summaries, threshold distributions, draw hashes and frozen decisions.
- `reference_e.json`: original E operating points, intervals, normal-score contrasts, draw hashes and failed benefit gate.
- `reference_e_threshold_cross.csv`: all 27 E score/threshold exchanges.
- `reference_y.json`: original Y normal contrasts and all 40 score/threshold/query-domain/calibration-unit combinations.
- `reference_x_operating.csv`: all 16 X operating comparisons.
- `reference_x_primary.json`: X's original normal-score bootstrap endpoints, per-camera summaries and limited diagnostic gate.
- `reference_p2.json`: the saved matching failure, per-camera assignment costs and missing-slot counts. It is a design failure, not a tested mechanism result.

Reference files are used **after** recomputation to detect differences. They do not supply the recomputed estimates. No reference is silently updated when a new local run changes a result.

### `derived/recomputed/`: release validation outputs

- `results.json`: results rebuilt from the released summaries.
- `verification.json`: reference-field comparison count, numeric error, input hashes and CPU-only execution receipt.
- `local_interface_test.json`: a local-output interface smoke test using copied historical summaries and test-generated receipts; this is not a new inference result.
- `table1_full_query.csv`: the nine P1 operating points.
- `table2_threshold_exchange_all40.csv`: all 40 Y exchanges.
- `e_threshold_cross_all27.csv`: all 27 E exchanges.
- `x_boundary_control_all16.csv`: all 16 X operating comparisons.
- `p2_hall_capacity.csv`: all 35 camera/phase-subset capacity checks.
- `figures/figure1_query_support.pdf` and `.png`: normal phase comparisons and paired full-grid contrasts.
- `figures/figure2_calibration_uncertainty.pdf` and `.png`: fixed-calibration and joint intervals for the three manuscript detection comparisons.
- `figures/figure_data.json`: exact plotted result rows, source-result hash and interpretation limits.

See [the results guide](../docs/results.md) for commands, estimators, observed outcomes and scientific limits. The successful local reproduction does not change any prior failed or inconclusive scientific gate.
