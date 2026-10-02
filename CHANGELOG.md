# Changelog

## 1.1.0-dev.4 · 2026-10-02 (`main` development version)

The latest tagged release and its downloadable archives remain v1.0.1. The `main` source version is 1.1.0-dev.4, with standalone skill version 2.1.0-dev.4. It includes the modeling and photo-correction milestones below. Modeling/recognition algorithms and the 14 public MCP tools are unchanged by the final layout iteration.

- Organize model editing, photograph correction, axes/parameters and saving/review into four workspaces while retaining model state, annotation histories and unfinished drawing points during navigation.
- Give photograph correction a larger canvas, compact toolbar and right inspector; the inspector becomes collapsible below the canvas on narrow screens.
- Add context-sensitive header saving, reject annotation saves with unfinished points, and collect saved paths/download links in the delivery workspace.
- Support navigation-tab Left/Right and Home/End keys, legacy anchors and browser Back/Forward. Axis picking opens the model view, then returns to parameters for explicit application.
- Update both README languages, screenshots, the five-step editor walkthrough, optional image-dependency instructions and all four user guides. Keep development source instructions separate from stable download instructions.
- Verify 128 Python tests without skips in the configured optional environment, JavaScript geometry/editor regressions, desktop and 375-pixel browser interactions, and portable package relocation. These checks do not establish new recognition accuracy; see [validation scope](docs/QUALITY.md).
- 中文：新增四工作区布局、照片大画布与可折叠检查面板，集中保存入口；切换不提交未完成标注，不改变模型和识别算法。[布局使用指南](docs/layout-guide.md)。

## 1.1.0-dev.3 · 2026-10-02 (local development, unpublished)

The public release remains v1.0.1. The accompanying standalone skill version is 2.1.0-dev.3.

- Add direct photograph correction: drag endpoints, complete edge annotations, face-boundary segments or face interiors; optionally link coincident 2-D points, insert/remove nodes and redraw while preserving feature IDs.
- Load the public 451 photograph example with its existing manual silhouette and four manual boundary lines. These are supplied reference annotations, not automatic recognition results.
- Add seeded face-region previews with 12/24/40 color thresholds, explicit adoption and continued boundary editing. Reuse closed manual boundaries where available; retain rejection and uncertainty rather than inventing faces. Suggested outlines can also be adopted and corrected.
- Align the current v2 model to photo corrections, display a purple projected wireframe and offer one-to-one face-assignment candidates. Confirmed associations require another alignment; annotation or model changes invalidate the previous overlay. Camera fitting does not change geometry or establish independent specimen accuracy.
- Preserve optional local `feature.evidence` provenance in correction JSON; arbitrary provenance text is not included in the default cloud-review packet.
- Add CLI `photo-align`, HTTP `/api/photo-align` and public MCP `atlas_photo_align`, bringing the development interface to 14 tools. Seeded proposals remain private HTTP `/api/photo-face`.
- On two existing 451 photographs, manually derived seeds alone produced no acceptable regions. Adding their manual boundaries gave IoU 0.9396/0.9847, measuring supplied-boundary adherence rather than automatic face-discovery accuracy.
- 中文：新增实物照片拉线修面、保留 ID 重画、点选候选面后采纳修边，以及当前模型线框对齐和待确认面对应；原图、人工示例与算法候选来源分别保留。[使用指南](docs/photo-correction-guide.md)。

## 1.1.0-dev.2 · 2026-10-02 (local development, unpublished)

The public release remains v1.0.1. The accompanying standalone skill version is 2.1.0-dev.2.

- Add canvas-side drawing tools, contextual point hints, keyboard completion/undo, original-pixel coordinate entry and an optional local magnifier.
- Enable snapping at a default 12 CSS-pixel radius, with 6/12/20 choices, an off switch and Shift bypass. Reuse manual endpoints, with optional midpoint/intersection targets and independently switchable photograph corner suggestions.
- Add beginner, crystallography-study and classroom presentations. Single-view display and face/reference/candidate-index visibility controls change presentation without changing model data.
- Keep image-corner suggestions unconfirmed and local. Private HTTP `/api/photo-guides` reuses outline extraction without template search or model fitting; unavailable image dependencies leave manual picking usable. Public MCP remains at 13 tools, with no automatic installation or downloads.
- 中文：新增可关闭的辅助拾取、画布快捷键、坐标放点、放大镜和课堂展示方式；照片候选点不认定真实晶棱或指数。[操作指南](docs/beginner-ux-guide.md)。

## 1.1.0-dev.1 · 2026-10-02 (local development, unpublished)

The public release remains v1.0.1. This entry describes the current local implementation; final integration and packaging acceptance are tracked separately.

- Add `/editor.html` with seven presets, v1 input/v2 draft import, fixed orthogonal views, face/module movement, cutting planes, scale controls, undo/redo and before overlays.
- Separate reference-axis redefinition from rebuilding geometry with recorded indices. Analyze geometric measures, index candidates, compatible groups in the current reference frame and zone candidates; retain physical interpretation limits.
- Add editable photograph edges, silhouettes, face regions, occlusion and uncertainty marks. Preserve original-image identity and per-feature model bindings; stale face associations require explicit reconfirmation.
- Save draft/correction/review JSON and prompt text as content-addressed files in the local output directory, showing their paths and download links without depending on browser downloads. Preserve existing different content; export immutable offline model bundles. Add structured review packet/reply exchange with input/policy fingerprints and explicit suggestion selection, without cloud calls or image uploads.
- Expose the shared editor/review services through JSON CLI requests and expand the local MCP interface to 13 tools.
- Fix duplicate-photo tie ordering. The final automatic rankings on all 68 old development photographs match the baseline. Corner refinement and stronger automatic edge scoring remain diagnostic suggestions after observed regressions; reliable manual edges use the new residual. [Measurements and tradeoffs](docs/recognition-improvements-2026-10-02.md).
- Preserve the convex, positive-support-plane scope. Nonconvex sculpting, arbitrary-photo reconstruction and real cloud vision accuracy are not established by this iteration.
- 中文：新增固定视图手动建模、参考轴与参数解析、照片画线圈面及逐条绑定、本地复核协议和离线修订包；不自动联网，不把旧图回归当作准确率提升。[使用指南](docs/manual-modeling-guide.md)。

## Unreleased — Evidence-first visual analysis workflow

- Record practical failure modes and bounded lessons from the local photo/model pipeline.
- Route online assistants through uncertainty-preserving, cross-photo evidence checks and a portable visual prompt.
- Share prompt content with the loopback-only vision adapter, recording its fingerprint in results and including policy text in source/cache fingerprints.
- Keep text-scenario checks separate from real online image-recognition accuracy; no new remote upload service is introduced.

## Unreleased — Multi-view and incomplete morphology evidence

- Support up to 24 photos / 64 MiB, duplicate-aware grouping, conservative quality weights and robust aggregation.
- Preserve alternative/partial morphology descriptions as soft priors; retain unknown and negative clauses without turning them into positive claims.
- Use local-outline matching for explicit and suspected partial views; retain damaged-file evidence while continuing with usable photos.
- Export per-photo contributions, conflicts, leave-one-group-out stability and suggested next observations. These are not calibrated confidence probabilities.
- Validate 68 development photographs and the new failure boundaries; [full results and limitations](docs/photo-evidence-series.md).

## Earlier local iteration — Photo-first 3D candidates

- Add automatic local photo segmentation, silhouette/long-edge template search, and shared ranking for 1–4 views. No preselected model or manual face corners are required.
- Add a photo-first workbench flow, compact 3D candidate previews, CLI `from-photos`, and MCP `atlas_from_photos`. Candidate crystal parameters are explicit priors, never photograph-derived facts.
- Preserve exact hints, image/bank/source fingerprints, runtime versions and per-photo evidence in single/multi-photo exports.
- Validate 29 real development images across 14 cases and 30 synthetic views. [Results, failures and limits](docs/photo-candidates.md).

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
