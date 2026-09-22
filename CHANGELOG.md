# Changelog

## 1.0.1 — 2026-09-22 · Model 611 lower-end correction

- Lengthen the six lower faces and widen the terminal hexagon following the user-confirmed photo-2 proportions. Preserve all face IDs, adjacency, and the upper-end geometry.
- Regenerate the 611 reference input, offline atlas, indices and reports. Its unequal end slopes yield geometric `6mm`, replacing the old symmetric `6/mmm` reference claim.
- Add lower-height, terminal-width, numbering, adjacency and symmetry regression checks; retain the previous input and a reproducible comparison figure.
- Package software/plugin 1.0.1 and standalone skill 2.0.1. Other 14 reference models and the authorized 451 dataset are unchanged; no 611 photos are published.
- 中文：修正611下方六面的长度与收口比例，同步模型、参考指数、报告及软件/技能包；旧版保留，详见[更新说明](docs/611-correction.md)。

### Included — Point-group standard and workflow audit

- Correct 671/675 to the textbook shorthand `Lᵢ⁶ 3L² 3P`, separately reporting four actual mirror planes.
- Ship a single offline 32-class catalogue with generated reports, viewers, result bundles, and the skill runtime.
- Validate the declared group, system, shorthand, and complete axis-dependent operation set; retain conflicting input wording with a warning.
- Include the catalogue in source/cache hashes; independently re-enumerate the fifteen reference models.
- Preserve photo-label ambiguity, reference-index limits, existing geometry and fixed rotation scale.

### Included — Authorized Photo Example

- Publish the explicitly authorized451 set: three unchanged photographs, two original-pixel annotations, saved camera fits, and reference geometry.
- Add a computed face-index figure to both README language sections, preserving same-page language navigation.
- Add a standard-library saved-fit exporter and dataset integrity/reprojection tests.
- Provide a separate downloadable photo-example bundle; the original v1.0.0 software and skill assets remain unchanged.

## 1.0.0 — First Public Release

- Offline browser workbench, CLI, and seven stdio MCP tools sharing one core.
- Three-axis/four-axis indices and reference operations for 32 point-group classes.
- Fifteen reference models, 226 faces, stable rotation/zoom, and shared-edge topology.
- Original-pixel annotations, optional camera fitting, alternative-solution warnings, and independent holdout checks.
- Five-field reports, immutable output bundles, verified caches, and portable parameters.
- Standalone `mineral-face-atlas` skill distribution, version 2.0.0.
- English/Chinese READMEs with language switching, installation and release guides, contributor attribution, and a crystal-face logo.
- Explicit UTF-8 file handling and clean-checkout packaging for public distribution.

Reference indices remain model assignments, not automatic physical measurements. Private source photographs are not included.
