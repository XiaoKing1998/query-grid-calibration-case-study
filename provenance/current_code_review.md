# Read-only release-code and publication review

Date: 4 October 2026. Reviewed `src/querygrid/inference.py` and `src/querygrid/sampling.py` as source text only. No model, image, feature, score or confirmation record was loaded or recomputed for this review.

Inspected SHA256:

- `inference.py`: `cb6b77c3136c5bcb290f8980c7f83f1f6cc43ad0301beb0186144d1e01237c85`
- `sampling.py`: `e36a5d2b940c91850cd24551abbe0b6fdc2df9bf079beb93405fb91a71005a72`

## Confirmed controls

- Image paths must be relative POSIX paths. The code rejects drives, backslashes, absolute paths, empty/dot/parent components, and symlink resolution outside the resolved data root.
- Only the plastic-nut fitting, normal-calibration and development roles are admitted; role counts, five-camera grouping and development-label totals are checked before image decoding.
- The supplied checkpoint is verified against a fixed SHA256. DINOv2 is imported from a supplied local checkout with `pretrained=False` and `torch.load(..., weights_only=True)`. These two reviewed modules contain no downloader, authentication client, credential-store read or remote upload.
- Model checkpoints and complete third-party source trees are not embedded in these modules. `sampling.py` states the PatchCore commit and Apache attribution and identifies the external rule's commit.
- Output directories must be new or empty; an exclusive run claim prevents two ordinary runs from claiming the same output directory. Historical evidence is not overwritten by the intended workflow.
- Saved outputs are identities, scalar/regional summaries, hashes and receipts. The reviewed writer does not save source pixels, dense feature arrays, banks or dense anomaly maps. Receipt fields use relative source-code paths rather than the user's local root directories.

The local DINOv2 checkout is executable Python supplied by the user; this review does not certify arbitrary substituted third-party code. This is a dependency boundary, not evidence of a network action in the reviewed modules.

## Finding sent to the implementation owner

**OPEN at the inspected hashes: historical identity admission is weaker than its wording.** `validate_manifest` checks count/group/label summaries but does not bind the exact historical 2,010 identity-and-role records. Another manifest with the same aggregate counts can pass. Both success and failure receipts nevertheless set `confirmation_access` to zero unconditionally. Role names alone cannot establish which physical data were supplied.

Recommended repair: bind the production entry point to a fixed canonical identity/role digest or the shipped manifest's exact hash; keep synthetic test overrides outside the production call. Also distinguish “no confirmation-labelled roles admitted” from a claim about the provenance of arbitrary local image bytes. The latter would require comparison with authenticated original image hashes. A portable reconstruction should report only the guarantee it actually checks. This finding was sent to the implementation owner and root maintainer; no source file was changed by this reviewer.

**Lower-priority logging observation:** failure JSON saves only the exception type and stage, which is appropriate. The final bare re-raise can still produce local-path details in a console traceback from a library error. It does not upload those details, but unreviewed console logs should not be published. Sanitizing the public CLI's error presentation is one possible response.

## License follow-up completed

- Added `data/LICENSE.txt` with the CC-BY-NC-SA-4.0 identifier, standard license/legal-text links, Real-IAD attribution, scope for adapted metadata/tables, and separation from software terms. No license legal text was invented or copied from memory.
- Added `LICENSE_STATUS.md`: original-code publication is authorized, but no general original-code license has been selected. No MIT license was assigned.
- Updated `THIRD_PARTY_NOTICES.md` to point to those scope documents.

The Real-IAD license identification comes from the official dataset card read earlier in this same packaging audit. Subsequent attempts to reopen the Creative Commons standard-license page failed with tool connection errors; its links are supplied for the actual terms rather than represented as freshly read legal text. No account-specific agreement or credential store was opened.

## Security scan snapshot

At 03:44 UTC, the updated scanner inspected 63 candidate-release files and reported **zero findings**, including zero credential-pattern findings. The earlier test's absolute path was replaced by a synthetic rejection fixture by its owner. This does not close the identity-admission finding above: a secret-pattern scan and a semantic code review check different properties. `security_scan.json` records the exact file hashes for its snapshot; rerun after final concurrent edits.

## Status

License files and privacy scan are prepared. The identity-admission and receipt wording issue remains open for the implementation owner at the hashes stated above. This review did not create or publish a GitHub repository, execute inference, or change the study's historical evidence.

## Maintainer closure after repair

The primary maintainer checked the repaired source and reran the tests. The identity-admission finding is closed for `inference.py` SHA256 `81026e2c2b449b3f323f18169527ea347779aea701846dd018a892e4d967e946`. Production validation now binds the six identity/role/label fields to canonical SHA256 `c580ed868943876c96f6e135a7f2e3f9fd489e49f0c9e34d9cf49d6827a7a23e`. Synthetic tests reject a substituted cohort with unchanged counts. The analysis module imports the same digest implementation. Receipts distinguish zero confirmation-role rows from authentication of local image bytes. The final test receipt records the tested source hashes and totals.

Nonfinite and nonpositive runtime limits are rejected before manifest access. The public command requires an explicit limit. The lower-priority console-log observation remains relevant: only reviewed release files are uploaded, not unfiltered local tracebacks.

The primary maintainer opened and visually checked both released PNG files. They contain statistical plots of scalar estimates and confidence intervals, with no source photographs, masks or dense anomaly maps. The corresponding PDFs are generated by the same figure code. The security scanner continues to flag image extensions for manual review; these two findings are accepted for the hashes recorded in the final release scan.
