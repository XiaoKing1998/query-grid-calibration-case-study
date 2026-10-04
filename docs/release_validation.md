# Code-release validation, 4 October 2026

The release is a portable reconstruction plus an archive of existing evidence. The checks below validate software and saved-result reproduction; they are not new scientific experiments.

| Check | Observed result |
|---|---|
| Standard-library unit suite | 29 tests passed; 3.025 seconds reported by unittest |
| Final wheel build, no dependency installation or build isolation | Passed; wheel SHA256 `8c27249befba4324d1d1f9d92f55a09798bb8becc96911b2b1903b7dd4fceee3` |
| Reproduction using the built wheel | 6,932 reference fields passed; maximum absolute error `1.4210854715202004e-14`; analysis wall time 1.502729800 seconds |
| Synthetic sampler fixtures | Three fixed seeds match the pinned upstream CPU implementation's ordered indices and original vectors |
| Manifest admission | Canonical identity/role binding; substitution, role leakage, path traversal, and external symlinks rejected in synthetic tests |
| Runtime budget input | Nonfinite, zero, and negative limits rejected before manifest access |
| Local-output analysis interface | Saved-summary smoke test passed; generated receipts explicitly identified as test fixtures |
| Historical source archive | 136 archive checks passed, with original and sanitized hashes kept separately |
| Figures | Two PNG statistical figures opened and visually checked; corresponding PDFs use the same source values |

Commands below use repository-relative paths. Validation ran in the existing research Python environment; original experiments were not rerun and that environment's dependencies were not changed.

```sh
python -B -W error::ResourceWarning -m unittest discover -s tests -v
python -m pip wheel --no-deps --no-build-isolation . -w /path/to/validation/final-wheel
# With PYTHONPATH pointing to the built pure-Python wheel:
python -B -m querygrid analyze --data-dir data --output-dir /path/to/validation/wheel-reproduction
```

The checked environment is listed in the main README. The wheel is a local validation artifact; the source repository also supplies the external data tables required for score-level reproduction. It includes the PatchCore license and NOTICE in its distribution files.

The final security scan records hashes and findings in `provenance/security_scan.json`. Image-extension findings for the two generated statistical PNGs were manually reviewed. Build output and egg-info are local generated artifacts, excluded from publication. A pattern scan is not a proof that arbitrary secrets are absent.

No real-image GPU rerun was performed for this release. No new source image, mask, feature tensor, or confirmation record was accessed. P1/E have configurable local inference; X/P2 have historical source and saved-summary analyses. Full historical bank equality and independent confirmation are not claimed.
