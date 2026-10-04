# Third-party notices

This file distinguishes upstream components from the study authors' code. An upstream license does not automatically license every file in this repository. See [LICENSE_STATUS.md](LICENSE_STATUS.md) for the pending original-code license choice and [data/LICENSE.txt](data/LICENSE.txt) for the separate derived-data scope.

## PatchCore sampler — Apache License 2.0

The runnable coreset implementation in `src/querygrid/sampling.py` is adapted from the approximate greedy sampler in [amazon-science/patchcore-inspection](https://github.com/amazon-science/patchcore-inspection), fixed commit **fcaa92f124fb1ad74a7acf56726decd4b27cbcad**. The upstream source is [src/patchcore/sampler.py](https://github.com/amazon-science/patchcore-inspection/blob/fcaa92f124fb1ad74a7acf56726decd4b27cbcad/src/patchcore/sampler.py).

Upstream attribution:

> Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

The Apache-2.0 license and upstream attribution notice are preserved, unmodified, in [provenance/licenses/patchcore-LICENSE.txt](provenance/licenses/patchcore-LICENSE.txt) and [provenance/licenses/patchcore-NOTICE.txt](provenance/licenses/patchcore-NOTICE.txt). The port makes seed control and selected indices explicit and removes the requirement to import the full upstream package. Consult the modified module for its actual implementation and the release tests for the checked equivalence boundary. These notices do not imply upstream endorsement of the study.

The historical `RecordingSampler` in `provenance/archive/S/static_reference_audit/static_core.py.txt` is the study's wrapper around the upstream sampler. It records indices and checks a deadline; it does not contain a second copy of the full upstream sampler.

The exact historical execution source had SHA256 `04b1e7b2fa64ce17a7718f7d20e026b7384c7486ef99807dd8451ec9340ea799`. A separately retrieved LF-only copy of the same fixed upstream file had SHA256 `39612cd2b486865ece304348f740f4bc700a1c2e8684fbab3c2ed016c7801f2d`. Comparing their bytes after CRLF-to-LF normalization gives exact equality. Both hashes are retained so line-ending differences are not mistaken for an algorithm change.

## DINOv2 — user-supplied dependency

The inference code uses [facebookresearch/dinov2](https://github.com/facebookresearch/dinov2) and a user-supplied pretrained checkpoint. Neither its source tree nor model weights are redistributed here. The locally inspected DINOv2 license is Apache-2.0; users should consult the license and model terms in the version they obtain from the official source. This statement does not grant rights in third-party model assets or identify every dependency bundled with upstream DINOv2.

## External candidate-rule source — referenced, not vendored

The separate E experiment transfers a capped candidate-selection rule from [racaro/industrial_image_anomaly_detection](https://github.com/racaro/industrial_image_anomaly_detection), commit **bb61a9644b0c3c6c0f1f890245a55d2d71bb265e**:

- [enhanced_features.py](https://github.com/racaro/industrial_image_anomaly_detection/blob/bb61a9644b0c3c6c0f1f890245a55d2d71bb265e/src/models/patchcore/enhanced_features.py), SHA256 `3af5e8496fae52c2601bf460537f89b2a3494098f925e70565e99208bfc09f5b`.
- [build_memory_bank.py](https://github.com/racaro/industrial_image_anomaly_detection/blob/bb61a9644b0c3c6c0f1f890245a55d2d71bb265e/src/models/patchcore/build_memory_bank.py), SHA256 `b137a8e4a6d3eabd45b4ec325a8486f744443e1e0876a47678467c13d56738b3`.

The fixed README's License section describes educational and research purposes but does not supply a standard redistribution license. A fixed-commit `LICENSE` request returned 404; a complete repository-tree API check was unavailable. **No definitive redistribution permission was established, so neither upstream source file is copied here.** Public visibility alone is not used as permission to republish upstream code. The source remains reviewable through the fixed links and hashes.

The study's own historical `candidate_plan.py.txt` and runnable candidate implementation express the audited integer-selection rule; they are not copies of those two upstream modules. This is a rule transplant, not a reproduction of that repository's full detector, backbone, coreset or evaluation. No MIT or Apache license is attributed to that upstream repository.

## Real-IAD — dataset attribution and separate terms

Real-IAD was introduced by Chengjie Wang, Wenbing Zhu, Bin-Bin Gao, Zhenye Gan, Jiangning Zhang, Zhihao Gu, Shuguang Qian, Mingang Chen and Lizhuang Ma, “Real-IAD: A Real-World Multi-View Dataset for Benchmarking Versatile Industrial Anomaly Detection,” CVPR 2024, pp. 22883–22892. [Paper](https://openaccess.thecvf.com/content/CVPR2024/html/Wang_Real-IAD_A_Real-World_Multi-View_Dataset_for_Benchmarking_Versatile_Industrial_Anomaly_CVPR_2024_paper.html).

The [official dataset card](https://huggingface.co/datasets/Real-IAD/Real-IAD), accessed 4 October 2026, identifies **CC-BY-NC-SA-4.0**, describes research use, and requires users to accept access conditions before obtaining its files. Obtain images and official labels through that source. The [project website](https://realiad4ad.github.io/Real-IAD/) links to this dataset; its separate website-template CC-BY-SA notice is not a license for the dataset.

No image, mask, checkpoint, descriptor, memory-bank tensor, dense anomaly map, original metadata archive or reserved-confirmation material is supplied by this provenance package. Original software licensing does not override the terms applicable to Real-IAD-derived identifiers and annotations. Released scalar results and role mappings are identified as study-derived metadata; their attribution and data terms are recorded in [data/LICENSE.txt](data/LICENSE.txt). Public availability of these files is not unrestricted permission to redistribute the source dataset.

## Other runtime dependencies

NumPy, SciPy, PyTorch, torchvision, Pillow and other installed packages retain their respective licenses. Package imports do not redistribute their entire source distributions here. Do not infer that all dependencies use MIT or Apache-2.0. This provenance package contains no third-party MIT-licensed source requiring a copied MIT notice; any additional vendored component requires its own review.
