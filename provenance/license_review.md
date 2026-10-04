# Source and license review

Review date: 4 October 2026. Scope: this research-code release, the historical source allowlist, the third-party sampler, the external candidate-rule source, and Real-IAD-derived publication artifacts. The decisions below are packaging decisions based on identified sources; they do not grant rights beyond the actual licenses.

## Decisions

| Material | Verified source | Release treatment |
|---|---|---|
| Study-owned historical P1/P2/E/Y/X code, earlier B producer, shared S numeric wrapper | 22 original files individually hashed in `source_manifest.json` | Sanitized reference copies, not runnable claims; governed by the authors' applicable software license except separately identified upstream material |
| PatchCore approximate greedy sampler | Pinned upstream commit, Apache-2.0 LICENSE, Amazon NOTICE | Adapted runnable implementation carries attribution; preserve full upstream license and notice |
| DINOv2 source/checkpoint | Official repository; local source LICENSE begins Apache-2.0 | External user-supplied dependency; no code or weights copied |
| External E upstream modules | Pinned repository, two previously verified source hashes, fixed README License section | No definitive redistribution license verified; source links and hashes only; no upstream module copied |
| The study's E integer candidate-rule implementation | Own frozen `candidate_plan.py` and original research analysis scripts | Own authored implementation with explicit external rule attribution; not described as a full upstream reproduction |
| Real-IAD source assets and official metadata archive | Official HF dataset card says CC-BY-NC-SA-4.0, research use and gated access | Obtain from the original host; excluded from this code/provenance archive |
| Study sample-role metadata and scalar results | Existing approved development/fitting/calibration records; not new source data collection | Dataset-derived attribution and data terms must be separate from original code; no reserved-confirmation material |

## Primary-source checks

- [PatchCore LICENSE at fixed commit](https://github.com/amazon-science/patchcore-inspection/blob/fcaa92f124fb1ad74a7acf56726decd4b27cbcad/LICENSE): the Apache-2.0 redistribution section requires preserving the license, relevant attribution and change notices. The local version's complete LICENSE and NOTICE were copied byte-for-byte into `provenance/licenses/` and hashed. The Amazon NOTICE contains its copyright attribution. A raw-download browser request was restricted, but the rendered pinned license and already saved local license were readable.
- [DINOv2 official repository](https://github.com/facebookresearch/dinov2): dependency identity only in this release. The existing locally supplied LICENSE was read and identifies Apache-2.0. No new complete model-license review or checkpoint download was made.
- [E fixed README](https://raw.githubusercontent.com/racaro/industrial_image_anomaly_detection/bb61a9644b0c3c6c0f1f890245a55d2d71bb265e/README.md): educational/research description in its License section is not represented as a verified MIT/Apache redistribution license. Its fixed `LICENSE` endpoint returned 404. The browser could not retrieve the complete fixed tree and a no-authentication HTTP tree request failed, so this review does not assert that every possible path lacks license text. The conservative release decision is to avoid copying those modules. The [public repository](https://github.com/racaro/industrial_image_anomaly_detection) was accessible and showed the same general license description.
- [GitHub licensing documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository): public visibility is distinct from a license to redistribute source outside the platform's viewing/forking terms. This informed exclusion of unresolved third-party source, not a claim that the research algorithm cannot be discussed.
- [Real-IAD official HF card](https://huggingface.co/datasets/Real-IAD/Real-IAD): CC-BY-NC-SA-4.0 is displayed; file access requires accepting conditions and sharing contact information. No login or credential store was accessed. The [official project website](https://realiad4ad.github.io/Real-IAD/) links the HF dataset. Its CC-BY-SA website-template notice is separate.

## Derived-data boundary

The data-packaging collaborator reports that the proposed public metadata contains only the original **2,010 approved views**: 875 fitting, 380 normal-calibration and 755 development images. The proposed derived artifacts include P1/E/X scalar scores, P1 regional maxima and P2 fitting-match summaries. These statements identify the intended scope; a final manifest and role validator must check the actual exported files before upload. The provenance archive does not itself contain these data tables.

Sample paths, camera/group keys and official labels originate in or refer to the dataset, whereas computed scores and frozen study roles are study-derived values. Do not describe all of these columns as unrestricted MIT software. Preserve the dataset citation, license identification, transformation description and exclusion of source images/masks. Gated access should continue to use the official source rather than republishing its original archive. We have not inspected account-specific agreements; this is a limitation, not an invented additional permission requirement.

## Integrity and engineering checks

All 22 original and transformed script bodies parsed as Python without execution. Original bytes and sanitized bytes have distinct SHA256 fields. A first helper call using the platform default text encoding failed on Unicode before writing its proposed path cleanup; it was corrected to explicit UTF-8 and then completed. The remaining resource-disk path in Y was replaced with `${RESOURCE_DISK_ROOT}` and recorded. No numerical logic or threshold was deliberately changed.

The historical executed PatchCore sampler (CRLF) and the separately fetched pinned sampler (LF) are equal after line-ending normalization. This is direct text comparison, not a rerun of the GPU algorithm. The executable port and its equivalence tests are maintained separately from this reference archive.

## Publication decision and outstanding checks

The historical source archive and PatchCore license/NOTICE are prepared for the proposed publication. No unresolved upstream E module is included. Final repository publication still requires the parent maintainer to review the **actual final file set**, ensure the separately packaged derived data have their own attribution/terms, rerun the release security scan after all concurrent edits, and confirm every flagged location or omitted payload is handled. These are concrete final-package checks; no new experiment or third-party message is requested.

No GitHub repository, commit, upload or external message was created by this review.
