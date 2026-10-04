# Reproducing the saved case-study results

## Scope and commands

This package reproduces statistics from existing, admitted score summaries. It does not perform new inference by default. No raw image, mask, feature tensor, dense anomaly map, credential or confirmation score is needed by the analysis module.

From the repository root, after installing the package and its CPU dependencies:

```sh
python -m querygrid.analysis --data-dir data --output-dir outputs
python -m querygrid.figures --results outputs/results.json --output-dir outputs/figures
python -m unittest discover -s tests -p test_analysis.py -v
```

The analysis command reconstructs estimates before comparing them with the archived reference files. A discrepancy above an absolute tolerance of `1e-12`, a changed identity, or a changed role fails the command. The reference files supply comparison targets; they are not inputs to score aggregation or bootstrap calculations. The commands have no dependency on an original research drive, a skill installation, or a network connection.

To analyze a completed local `querygrid run --study p1` or `--study e` reconstruction, use a separate output directory:

```sh
querygrid analyze --data-dir data --study p1 --inference-dir runs/p1 --output-dir outputs/local-p1
querygrid analyze --data-dir data --study e --inference-dir runs/e --output-dir outputs/local-e
```

This mode first checks the completed `freeze.json`, its manifest and score-file hashes, all nine method columns, all three fixed coreset seeds, the full query domain and the original bank budget. Both analysis modes bind the manifest's six identity, role and label fields to the canonical admitted-set hash shared with inference, then check every score identity against that manifest. This metadata binding does not authenticate local image bytes. Local-run analysis reports the same operating endpoints and bootstrap definitions, with P1's phase contrasts and 40 threshold exchanges or E's 27 exchanges. It does **not** compare its estimates with the archived targets or claim historical equality. Its receipt says `compared_with_historical_references: false`, and it refuses to write under the released data directory or overwrite an existing analysis. It does not combine a new P1 result with historical E results. The combined manuscript figure command above is for the archived-data reproduction output.

The release was checked with Python 3.14.4, NumPy 2.4.4, SciPy 1.17.1 and Matplotlib 3.10.8. The saved run in `data/derived/recomputed/verification.json` passed **6,932 reference-field checks**, with maximum absolute numeric difference **1.4210854715202004e-14**. CPU analysis took approximately two seconds on the development machine. Nine behavior tests passed. A separate interface smoke test used copied historical summaries and test-generated receipts to verify P1/E local-output analysis and refusal to overwrite prior outputs; it did not perform new inference. Both generated PNG figures were visually inspected; the corresponding PDFs use the same plot data. These are checks of numerical reproduction, not evidence of novelty, independent confirmation or external validity.

## Released inputs

The data and derived metadata are attributable to Real-IAD and have a separate dataset-derived license scope from the original software; see the package's data and licensing documentation. The release contains only the already admitted `plastic_nut` roles:

| Role | Views | Five-camera acquisition groups |
|---|---:|---:|
| Source fitting | 875 | 175 |
| Normal calibration | 380 | 76 |
| Development | 755 | 151 |

Development contains 44 all-normal groups and 107 groups with at least one officially anomalous view, totaling 258 anomalous views. `data/manifests/plastic_nut.csv` has the six fields `category,path,group_key,camera,research_role,anomaly_class`. Paths are dataset-relative. A filename-derived acquisition key is not a verified permanent physical-object identity. The original role assignment is retained; no development data are renamed as confirmation data.

| File under `data/derived/` | Purpose |
|---|---|
| `p1_scores.csv` | Nine full-query score columns for the frozen 1,135 calibration/development views |
| `p1_spatial.csv` | Per-view, per-bank full and regional maxima and representative full-peak summaries |
| `p1_coverage.csv` | Existing normal-view mean, 95th-percentile and maximum nearest-distance summaries; retained as provenance, not a new endpoint |
| `e_scores.csv` | Nine banks from the separate retained-pool/uniform-history transfer |
| `x_scores.csv`, `x_calibration_spatial.csv` | Four original/deletion-control banks, with calibration spatial summaries |
| `x_deletions.csv` | The 92 target and 92 interior-sham prototype identities |
| `p2_source_phase_edges.csv` | The 375 saved legal fitting-source/phase edges and their scalar matching criteria |
| `reference_*.json`, `reference_*.csv` | Compact fields extracted from the original saved results for exact numerical comparison |

`data/manifests/provenance.json` records logical source names and original file SHA-256 values without machine paths or authentication details. The recomputation receipt additionally hashes each released input. These summaries support score-level reproduction. They do not permit independent reconstruction of every original feature distance or the completeness of the original P2 vector search.

## Estimators and randomness

Every main operating comparison uses the complete 64 × 64 query grid. Image scores are maxima of exact squared nearest-neighbor distances. A group score is the maximum across five camera views. Each bank's own threshold is calibration rank **74 = ceil(0.95 × (76 + 1))**. Alarms use **strictly greater than** the threshold; ties do not alarm. The diagnostic image-calibration threshold is rank 362 of 380. Supported detection requires an alarm on an officially anomalous view; it does not establish defect localization. Any-view detection permits an alarm on any view of an abnormal group.

All intervals use 5,000 paired group-bootstrap repetitions, NumPy PCG64 and linear-interpolated percentile bounds. P1 uses seed `20261031`; E uses `20261104`. Draw arrays are allocated in this exact order: calibration `(5000,76)`, normal development `(5000,44)`, abnormal development `(5000,107)`, with `int64` indices. All methods and fixed coreset seeds share these indices within each experiment. The archived draw SHA-256 values are checked.

- Fixed calibration: resample development groups; keep thresholds fixed.
- Calibration only: resample calibration groups and recompute thresholds; keep development groups fixed.
- Joint: independently resample calibration and the two development strata, then recompute thresholds and endpoints.

Differences are computed within corresponding coreset seeds and then averaged equally over the three fixed seeds. Seeds are never resampled and do not count as independent observations. Normal phase contrasts average view-level log ratios within groups before averaging groups. Their bootstrap uses the same P1 calibration draw array. Y retains its original bootstrap seed `20261013`; the boundary control X retains `20261012`. Reusing P1 intervals for Y's original analysis would change the frozen Monte Carlo realization, so both are reproduced separately.

The intervals are pointwise and descriptive, conditional on fixed fitting data, candidate pools and banks. They exclude research-question selection, repeated development use, unobserved normal tails and possible dependence above the acquisition group. They are not multiplicity-adjusted or confirmatory. Clopper–Pearson false-positive intervals assume independent exchangeable Bernoulli groups; zero observed false positives among 44 groups still has a two-sided 95% upper bound of about 8.04%. Equal observed false-positive counts do not imply equal population risk.

## Reproduced results and limits

### P1: candidate construction, complete queries and calibration

Supported detections out of 107 groups are odd **20/20/16**, balanced **87/74/79**, and ordinary random **70/79/71**, for seeds 0/1/2. The balanced-minus-odd fixed-seed mean difference is **57.32 percentage points**, with joint calibration/development interval **[30.22, 76.01]**. This passes the frozen local P1 gate. It is a comparison of the specified candidate constructions and does not establish an improvement over the default published PatchCore pipeline.

The full-minus-phase-11 normal contrast is **0.094434, 0.112246 and 0.119300** across the three seeds, with positive conditional lower bounds. Complete-query normal scores and phase-restricted normal scores can therefore rank these fixed candidate constructions differently. Candidate quotas apply before coreset selection; final prototypes are not phase matched. The full-minus-interior-phase-11 comparison retains boundary queries on its full-grid side and cannot isolate a boundary mechanism.

The random-minus-balanced fixed-seed mean difference is **−6.23 percentage points**, with joint interval **[−24.92, 0.93]**. Random sampling failed the predeclared point screen: at every seed, supported detection must be within five percentage points below balanced, with at most one additional false-positive group. This failure establishes neither equivalence nor a need for a complex sampler.

### Y: all 40 threshold exchanges

Y recomputes two score banks × two threshold banks × five query domains × two calibration units. For the original full-query banks, separate group thresholds give supported counts **20 versus 87** and one observed false-positive group each. The common lower balanced threshold gives **87 versus 87**, with false-positive counts **22 versus 1**. The common higher odd threshold gives supported counts **20 versus 18**.

At the common balanced phase-11 threshold, supported counts are **70 versus 61**, with one observed false-positive group each. This does not establish an equal-risk reversal. Phase 11 omits three quarters of the query grid and remains a diagnostic. Phase-specific operating comparisons use the original two banks only; the normal phase contrasts in P1 use all three seeds.

### X: limited boundary-deletion control

The analyzer verifies 92 target boundary deletions and 92 interior-sham deletions, matching camera and phase counts, with 4,004 prototypes retained. It reproduces all 16 operating rows and the original normal-score bootstrap endpoints. At each bank's own group threshold, supported detections are **82 and 84**, versus **87** for the intact balanced bank and **20** for odd, all with one observed false positive. The particular deletion control did not reproduce the original gap. Source identities and feature geometry were not fully matched, so other boundary-mediated explanations remain possible.

X's original normal-score diagnostic gate passed. That is not a failed numerical result and should not be relabelled as one. It supplies a bounded control and does not establish a general mechanism. Earlier analysis-report repairs are preserved in the project provenance rather than reinterpreted as new experiments.

### P2: the matching design was inconclusive

The saved legal edges are checked against the fitting manifest and the frozen distance criteria. An exact assignment and all nonempty phase-subset capacity checks are rerun. Camera 5 needs 48 slots but has two forced sentinel selections. Its phase-01 capacity is **15/16**; the joint phase-01/10 capacity is **30/32**; all three phases together have **47/48** distinct sources. No legal 240-slot intervention was available.

The original execution stopped before calibration or development queries. The public analysis does not simulate those unexecuted outcomes. Failure of this fixed matching design is not a falsification of a broad mechanism and is not evidence for an alternative mechanism. P3 was not entered.

### E: failed benefit criterion in the separate candidate-rule transfer

The separate 20,000-candidate retained-pool rule transfer is not an external replication of the phase interaction or a reproduction of the source implementation's complete detector. Uniform-history sampling yields supported counts **31/31/31**, compared with **42/40/53** for the retained-pool rule. Its fixed-seed mean difference is **−13.08 percentage points**, with joint interval **[−25.23, 8.41]**. The frozen requirement of a gain of at least ten percentage points in every seed and a positive joint lower bound failed. All nine banks have zero observed false positives out of 44 groups. This does not establish population-risk equivalence or retained-pool superiority.

The three earlier bank-construction scientific gates remain failed. Successful numerical reproduction changes none of these scientific decisions. This package supports a limited empirical case study; it does not claim a new sampling method, an identified spatial cause, broad superiority or mature external confirmation.

## Outputs

`results.json` contains the full recomputed results. `verification.json` records the archived comparisons and input hashes. The command also writes the nine-row main table, all 40 Y threshold exchanges, all 27 E threshold exchanges, all 16 X operating comparisons and all 35 P2 capacity checks. `querygrid.figures` produces two PDF/PNG plots and `figure_data.json`, which binds every plotted row to the reproduced result file. Plot appearance is a portable Matplotlib rendering; the source numerical values reproduce the manuscript comparisons.
