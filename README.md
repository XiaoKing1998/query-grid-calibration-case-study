# Candidate sampling, query grids, and normal calibration

Code and derived results for a descriptive industrial anomaly-detection case study on **Real-IAD `plastic_nut`**. The study examines how candidate sampling interacts with the query domain and a threshold estimated from normal data. It does not introduce a validated general-purpose detector.

Repository: https://github.com/XiaoKing1998/query-grid-calibration-case-study

## What is included

- **P1:** odd/odd, balanced, and ordinary random candidates, three fixed coreset seeds, a 4,096-vector memory bank, and the complete 64 × 64 query grid.
- **E:** a separate transfer of a public candidate-selection rule, with native, uniform, and shuffled-order controls. This is not a replication of the upstream detector.
- **Y:** all 40 saved threshold-exchange comparisons and spatial diagnostics.
- **X:** the saved boundary-deletion control, including all 16 operating-point combinations.
- **P2:** the saved source–phase feasibility analysis, including the failed matching constraint.
- Scalar scores, spatial summaries, role manifests, frozen reference results, group-bootstrap analysis, figure code, synthetic tests, and source provenance.

The release separates the runnable portable implementation in `src/querygrid/` from the path-sanitized historical scripts in `provenance/archive/`. The archive files use `.py.txt` and are reference material. They retain the failed experiments and are not an alternative executable pipeline.

No source images, masks, weights, feature tensors, memory-bank tensors, dense anomaly maps, complete original metadata archive, or reserved confirmation data are distributed.

## Recompute the saved results on CPU

Run these commands from the repository root, using Python 3.11 or later:

```sh
python -m venv .venv
# Activate .venv using the command for your shell.
python -m pip install -e .
python -m querygrid analyze --data-dir data --output-dir outputs
python -m querygrid figures --results outputs/results.json --output-dir outputs/figures
```

The analysis reads only the supplied study-derived tables. It compares recomputed values with the archived reference results and writes `outputs/verification.json`. A failed comparison raises an error. It also writes the full operating tables, threshold-exchange tables, matching-capacity table, and `results.json`. Figure outputs include PNG, PDF, and the plotted values in `figure_data.json`.

The checked environment used Python 3.14.4, NumPy 2.4.4, SciPy 1.17.1, Matplotlib 3.10.8, and Pillow 12.2.0. The dependency ranges above allow installation on other environments; they do not assert bitwise numerical agreement. The reference comparison uses an absolute tolerance of `1e-12`.

## Reconstruct P1 or E from locally obtained images

This optional path requires legally obtained Real-IAD images, a local DINOv2 source checkout, the specified DINOv2 checkpoint, and PyTorch. Obtain them from the official providers under their terms. The program does not download assets or authenticate to external services.

```sh
python -m pip install -e ".[inference]"
python -m querygrid run --study p1 --manifest data/manifests/plastic_nut.csv --data-root /path/to/realiad --dinov2-repo /path/to/dinov2 --checkpoint /path/to/dinov2_vitb14_pretrain.pth --output outputs/p1-local --max-wall-seconds 7200
```

The paths and the 7,200-second limit are examples. Choose a runtime budget appropriate to your hardware before starting; the program stops on a deadline check without treating partial output as a completed run. Use `--study e` and a separate empty output directory for E. The seeds are fixed at `0,1,2`; this interface does not expose a larger parameter search.

The production entry point admits the original 2,010 manifest identities and role assignments: 875 fitting views, 380 normal-calibration views, and 755 development views. It checks local paths, roles, cameras, and the canonical manifest. Names alone do not prove that user-supplied image bytes equal the original images. Checkpoint SHA256 must be:

```text
0b8b82f85de91b424aded121c7e1dcc2b7bc6d0adeea651bf73a13307fad8c73
```

Images are resized to 896 × 896; DINOv2 ViT-B/14 produces 64 × 64 tokens of dimension 768. A 128-dimensional random projection is used only for approximate greedy coreset selection. The final bank retains 768-dimensional features. Every primary comparison scores the complete query grid. The portable implementation records input/code hashes, selected identities, scalar and spatial summaries, timing, and a final `freeze.json`. It refuses to overwrite an existing run.

The portable inference path was checked with synthetic data and upstream sampler fixtures. **A new image-to-result GPU run was not performed for this code release**, and historical bank-by-bank equality is not asserted. Historical and new run receipts have different meanings; see [provenance](docs/provenance.md).

After a completed local run, analyze its own output separately:

```sh
python -m querygrid analyze --data-dir data --study p1 --inference-dir outputs/p1-local --output-dir outputs/p1-analysis
```

Use `--study e` for E. This path checks the run receipt and input hashes; it does not compare the new estimates with historical reference results or replace them. The two manuscript plots use the combined historical reproduction. X and P2 are released as historical source plus analysis of saved summaries, without a new configurable image-inference command.

## Details that affect interpretation

- Balanced sampling selects **one point at each of the same 256 sampled coarse-grid positions**, assigning 64 candidates to each of four phases. It does not select four points per coarse cell, and the final bank need not be phase-balanced.
- The principal comparisons use the full query domain. Reduced query domains and boundary deletion are diagnostic controls, not improvements to the primary detection task.
- Equal empirical false-alarm counts do not establish equal population risk. Threshold uncertainty is included through paired group resampling of normal calibration and development groups.
- Supported detection does not establish correct defect localization. Multiple construction seeds are not independent data samples.
- Reused development data are not independent confirmation. Numerical reproduction does not establish novelty or upgrade the three failed bank-construction scientific gates.

See [results and statistical scope](docs/results.md) for the saved outcomes and [data documentation](data/README.md) for file definitions and admission rules.

## Tests

```sh
python -m unittest discover -s tests -p test_analysis.py -v
# Sampling and inference-unit tests additionally require PyTorch.
python -m unittest discover -s tests -v
```

Sampling fixtures were checked with PyTorch 2.11.0+cu128 on CPU. Exact floating-point fixtures can depend on PyTorch and linear-algebra versions. The tests use synthetic images and tensors; they do not open the Real-IAD image collection.

## Attribution and reuse

Original-code licensing is recorded in [LICENSE_STATUS.md](LICENSE_STATUS.md). Until the authors select a license, public source availability alone does not grant a general reuse license. [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) retains upstream attribution, including the PatchCore Apache-2.0 license and notice. Real-IAD-derived material is covered separately by [data/LICENSE.txt](data/LICENSE.txt); a software license must not be applied indiscriminately to the data.

Authors: Zhiqiang Wang, Guiying Zhang, and leixi Chen. Contact: gyzhang84@163.com. Supported by the National Natural Science Foundation of China (Grant No. 12572211).

OpenAI Codex assisted with code preparation, numerical checks, and manuscript drafting. The authors have confirmed their review and verification of AI-assisted material and responsibility for the final manuscript. The portable code and release checks are documented separately in this repository.
