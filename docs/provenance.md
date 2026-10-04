# Provenance of historical research code

## What is preserved

`provenance/source_manifest.json` lists **22 explicitly selected historical research scripts**, their original SHA256 hashes, release SHA256 hashes, sizes, transformation records and logical source identifiers. This is an allowlisted archive, not a copy of a research workspace. The archive contains source text only.

| Source alias | Study role | Included scripts |
|---|---|---|
| U/p1 | Full-query odd/balanced/random comparison with three fixed coreset seeds | Producer, analyzer, independent verifier and producer synthetic self-test |
| U/p2 | One frozen matched-replacement attempt | Producer, conditional analyzer, independent verifier and producer synthetic self-test |
| E | Capped-pool candidate-rule transfer | Producer, candidate-plan implementation, analyzer, independent verifier and result comparator |
| Y | Fixed-bank query-phase and crossed-threshold diagnosis | Analyzer and independent verifier |
| X | Boundary deletion and matched-count interior deletion diagnosis | Producer, analyzer, static intervention verifier and two independent analysis checks |
| B | Earlier construction comparison supplying the original odd/balanced banks | Historical producer |
| S | Shared numeric operations | Study-owned `static_core.py` wrapper with recorded PatchCore dependency |

The machine-specific directory prefixes are intentionally absent from the public manifest. Aliases retain the experiment-directory names needed to map this archive to the research history without disclosing a local user directory.

## Reference archive versus runnable release

All historical scripts end in **`.py.txt`**. They document the historical computation and are **archival/reference material, not runnable entry points**. Use the documented runnable release commands for new execution. Renaming these files and running them is not a supported reproduction procedure: the old scripts require historical admissions, frozen inputs, operating-system-specific monitors and dependencies that are not bundled here.

In particular, P2 stopped at pair matching; its overall fitting-coverage and query stages did not run. The presence of an analyzer is not evidence that it was used. Historical failure and unused conditional branches are preserved instead of being represented as successful interventions. The earlier B construction gates and E benefit criterion also remain failed. The code archive supplies provenance; it does not certify novelty, population-risk equivalence, correct localization or independent confirmation.

## Exact transformations

Each included study script was read as text, parsed without execution, and copied with these disclosed edits:

1. Added a three-line archival/reference header.
2. Normalized text encoding to UTF-8 without a BOM and line endings to LF.
3. Replaced explicitly identified environment prefixes with literal symbolic placeholders: `${PROJECT_ROOT}`, `${RESEARCH_WORKSPACE}`, `${USER_HOME}` `${AD2_DATA_ROOT}` or `${RESOURCE_DISK_ROOT}`. Replacements cover slash and backslash spellings. Each replacement's count and the original prefix's SHA256 are recorded; the private prefix itself is not republished.

No numerical constant, seed, gate, branch, label mapping, scientific formula or data value was intentionally changed. All 22 resulting script bodies parsed as Python. This syntax check did **not** import them, execute them, read research data or establish runnable equivalence. Old file-integrity checks intentionally refer to old hashes; replacing paths does not make their archived admission checks valid in a new environment.

The manifest's original hash can be compared with a locally held original. Its release hash can be checked directly against the archived file. The two hashes are deliberately different after sanitization; neither is represented as the other.

## Dependencies deliberately omitted

Six historical dependency references are hashed without copying their contents: the old static runner, matrix runner, transport wrapper, HTTP range reader, complete upstream PatchCore sampler and local acquisition helper. Their records explain why the archive is incomplete as an execution environment. Local authentication and data-acquisition integration are omitted. No credential file was opened in this audit.

DINOv2 source and checkpoint assets are obtained separately by the user. The E upstream source files are linked and hashed, but not vendored because clear redistribution permission was not verified. The PatchCore license and NOTICE are preserved under `provenance/licenses/`. See [third-party notices](../THIRD_PARTY_NOTICES.md) for exact upstream versions and boundaries.

## Data and publication boundary

Real-IAD is a reused third-party dataset. Its official dataset card identifies CC-BY-NC-SA-4.0 and gated file access. The source images, masks and official metadata archives are obtained from the [official dataset repository](https://huggingface.co/datasets/Real-IAD/Real-IAD); they are not reproduced in this source archive.

Aggregate study results, scalar predictions and sample-role mappings are different kinds of material. Aggregate tables can document the reported findings without redistributing image payloads. Sample paths, group identifiers and official labels must still be recognized as dataset-derived metadata. A public software license does not by itself authorize relicensing these fields. If such files are released elsewhere in this repository, their own attribution, access provenance and data-license notice apply. Do not publish reserved-confirmation identities or scores, and do not rename reused development records as confirmation records. There was no new confirmation access during this packaging task.

This audit establishes the advertised license on the public dataset card; it does not claim to have inspected account-specific access agreements or made a legal determination that every possible derivative file is free of database or contractual restrictions. Files with unresolved redistribution rights are excluded rather than silently assigned the software license.

## Security scan

`provenance/scan_release.py` performs a read-only scan of a candidate checkout and writes only a report of **file, line, category and classification**, never the matching value. It checks common credential formats, literal secret assignments, absolute personal/machine paths, private-message markers and prohibited payload extensions. It skips version-control internals and generated scan reports. Findings require review; a pattern scan is not proof that no secret can exist.

Run the scan again immediately before publication because other files can change after this audit:

```text
python provenance/scan_release.py --root . --output provenance/security_scan.json
```

The saved report is a point-in-time result, not a certification of later files. No remote repository is created or uploaded by the scanner or this provenance package.

## 中文核对

- 22份历史脚本仅作参考归档；原始与发布SHA分别保存，环境路径替换有清单。
- 原始图片、标签压缩包、权重、特征、确认集记录及凭据均不由本归档发布。
- PatchCore的Apache许可只适用于相应上游部分；E上游未核实明确再分发许可，保持引用而不复制。
- Real-IAD派生身份和标签不得套用原创软件许可；发布前须检查数据目录的独立归属与条款说明。
