<a id="english"></a>

# Mineral Atlas Workbench

[![English](https://img.shields.io/badge/Language-English-24292f)](#english)
[![简体中文](https://img.shields.io/badge/语言-简体中文-1677ff)](#中文)

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Workflow](https://img.shields.io/badge/Workflow-Offline%20%7C%20CLI%20%7C%20MCP-0f766e)](#three-ways-to-work)
[![Crystallography](https://img.shields.io/badge/Indices-hkl%20%7C%20hkil-47694b)](#crystal-faces-and-coordinate-systems)
[![Status](https://img.shields.io/badge/Release-v1.0.1-16a34a)](https://github.com/QiushanHuang/mineral-atlas-workbench/releases/latest)
[![Development](https://img.shields.io/badge/main-v1.1.0--dev.4-d6a34b)](https://github.com/QiushanHuang/mineral-atlas-workbench/tree/main)
[![CI](https://github.com/QiushanHuang/mineral-atlas-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/QiushanHuang/mineral-atlas-workbench/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-16a34a)](LICENSE)

<p align="center"><img src="assets/logo.png" width="150" alt="Mineral Atlas: a faceted green crystal with a selected gold face and topology nodes"></p>

**Mineral Atlas Workbench** is a local-first crystal-face workbench for teaching models, Miller indices, photograph comparison, and reproducible reports.

It is built for the moment when a report lists a face such as `(1 0 −1 0)`, but you still need to know **which face it is, how it meets its neighbors, and how that assignment relates to the photograph**.

The same computational core powers a browser interface, a command-line tool, and an agent plugin. Parameters and evidence stay with the result, so another person can reproduce the calculation instead of reconstructing the workflow from a conversation.

Online/photo reasoning now has an evidence-first workflow and reusable visual prompt. [Lessons and validation boundaries](docs/photo-analysis-lessons.md).

## v1.1.0-dev.4: four focused workspaces (`main`)

The `main` development version adds **轻松建模** at `/editor.html` after starting the workbench. Clone the source below to use it. The latest tagged release and its downloadable archives remain **v1.0.1**; those archives do not contain the new editor.

Model editing, photo correction, axes/parameters and saving/review now have separate workspaces. Photograph tools surround a larger canvas, with a right inspector that folds below it on narrow screens. Navigation preserves editing state and unfinished points; the header saves the current model or annotations, and saved links appear in Save and review. This layout iteration leaves recognition algorithms and the 14 public MCP tools unchanged. The accompanying skill version is **2.1.0-dev.4**. [Workspace guide](docs/layout-guide.md#english) · [Photograph correction](docs/photo-correction-guide.md#english) · [Picking and teaching](docs/beginner-ux-guide.md#english).

Start from seven presets or an existing project. Fixed front/side/top views make face movement, module edits, cutting planes and undo/redo easier to inspect. Define reference axes without changing the shape, or explicitly rebuild from recorded indices. Geometry analysis reports areas, volume, angles, index candidates, compatible groups in the current reference frame and zone candidates.

Draw and drag photograph edges or face regions, reclassify them, and reconfirm face associations after changing models. Draft, correction and review files are saved under the local `--out` directory, with content-hash names, paths and download links you can use to copy the files. Different existing content is preserved. Export an offline ZIP or exchange a structured review packet with an assistant you choose; review export/import does not connect to the cloud or upload photographs.

[Manual modeling guide](docs/manual-modeling-guide.md#english) · [Measured recognition results](docs/recognition-improvements-2026-10-02.md)

![Photo correction workspace with a large canvas, nearby drawing controls and a right inspector](assets/editor-photo-workspace.png)

Shown with the already-public 451 teaching example. Orange/green annotations and the purple fitted model remain separate; the overlay is a comparison aid, not an independent accuracy measurement.

The editor handles convex plane-based models with positive support distances. It does not provide nonconvex sculpting or unique reconstruction from arbitrary photographs. Final automatic rankings on the 68 old development photos are unchanged; image refinement remains a reviewable suggestion where it regressed. Real cloud vision accuracy has not been tested.

## Photo-first initial models

Start with 1–24 photographs, extract the object outline automatically, compare initial 3D candidates, then load one for review and refinement. [Uncertain morphology, partial views and 68-photo validation](docs/photo-evidence-series.md). Candidates use explicit shape-library priors; this is not unique reconstruction of arbitrary unseen objects.

## v1.0.1 — Model 611 correction

The lower six faces are longer and end at a wider six-sided rim. Face numbers and shared-edge connections are preserved. The unequal reference shape now has geometric symmetry `6mm`; reports and indices were regenerated. [Changes and before/after view](docs/611-correction.md).

## Why Mineral Atlas

- Locate a specific face by its index or face ID, rather than guessing from a drawing
- Keep three-axis and four-axis conventions explicit
- Compare candidate geometry with photographs without hiding uncertain labels
- Generate the five crystallographic report fields from the same data as the model
- Run the core workflow offline, without an account, API key, or runtime downloads
- Share a project file, an offline result, or the complete software and skill package

## Three Ways To Work

| Entry point | Best for | Requirements |
|---|---|---|
| Prebuilt atlas | Inspect the 15 reference models and 226 faces | A browser; no Python or server |
| Local workbench / CLI | Build new models, mark photographs, export reports | Python 3.10+; optional fitting dependencies |
| Agent plugin / skill | Reuse the evidence, modeling, and validation workflow in Codex or another compatible host | A compatible host and local Python |

The core does not send photographs to a remote service. The optional vision adapter only contacts a user-installed Ollama service on `127.0.0.1`; it does not download models.

## Real Photo Example: Model 451

This is one photo set explicitly authorized for public release by QiushanHuang: **three source photographs, two annotated camera fits, and a six-face trigonal reference model**.

| Source photograph | Computed reference model in the same pose |
|---|---|
| <img src="examples/451-photo-study/photos/01.jpg" width="280" alt="Original451 teaching-model photograph with face numbers1,2,3"> | <img src="examples/451-photo-study/model-preview.svg" width="500" alt="Computed451 model with F01 selected and four-index face labels"> |

The photographs are unchanged; the right panel is drawn from the saved model and fitted camera. It demonstrates how a face number becomes a selectable, indexed surface. The interactive example additionally provides rotation, real shared-edge topology, photograph switching, fitted wireframe overlays, and the five-field report.

**[Browse the complete example data](examples/451-photo-study/)** · **[Download the offline photo example](https://github.com/QiushanHuang/mineral-atlas-workbench/releases/download/v1.0.0/mineral-atlas-451-photo-example.zip)**

```bash
# Replay saved camera fits; standard-library Python is sufficient.
python3 scripts/build_photo_example.py --out atlas-runs/451-photo-study
```

Open the exported `index.html`, select **照片视角** and **线框叠加**, then switch photographs or enter `F01`. To refit with NumPy/SciPy, add `--refit`; this explicitly refreshes the example's saved fit files. [Full reproduction instructions](examples/451-photo-study/README.md).

The two fits have approximately **8.77px** and **11.99px** corner RMSE at960×1280. These are fitting errors, not independent accuracy measurements. Photo03 is supplementary observation only; the reference basis and provisional opposite-face labels remain documented. [Photo provenance and publication scope](examples/451-photo-study/DATA_NOTICE.md).

## Features

- Interactive crystal rotation, stable zoom, face selection, crystal axes, and opposite-face lookup
- Three-index `(h k l)` and four-index `(h k i l)` parsing, including negative and overbar notation
- Reference symmetry operations for the 32 crystallographic point-group classes
- [Offline 32-class standard and correction workflow](docs/point-group-audit.md): textbook shorthand, actual mirror counts, complete operation-set validation, and a reference table in every report
- Half-space construction from a direct basis, face indices, and support distances
- Real shared-edge adjacency, linked to the spatial model and face table
- Checks for incompatible bases, duplicate directions, missing closure, inactive faces, face-count conflicts, and invalid topology
- Plane, convexity, winding, positive-volume, Euler, index-normal, and declared-symmetry checks
- Original-pixel photograph annotations, silhouettes, and optional face-center constraints
- Optional deterministic coarse-to-fine camera fitting, robust losses, alternative correspondences, and independent holdout errors
- Five-field reports: **symmetry class, crystal system, axis selection, geometric constants, and crystal-face symbols**
- Content-addressed outputs with checksums, preserved inputs, and verified cache reuse
- 14 local MCP tools in the development build, including current-model photograph alignment, editing, annotations and structured review; a self-contained `mineral-face-atlas` skill

## v1.0.0 Release Highlights

This is the first public release of the shared offline workflow.

- Migrated 15 reference teaching models into portable project files.
- Unified three-axis and four-axis indexing without changing the fixed-scale rotation behavior.
- Added a browser workflow for parameters, geometry checks, photograph annotations, and exports.
- Replaced broad random camera initialization with deterministic coarse-to-fine fitting.
- Added standalone software, plugin, and skill distributions with no private source photographs.
- Added a synthetic camera fixture so the full annotation and fitting workflow can be checked without supplying a photograph.
- Added English and Chinese documentation, a project logo, contributor attribution, and CI.

## Installation

Product name: **Mineral Atlas Workbench**. Plugin name: `mineral-atlas-workbench`. Skill name: `mineral-face-atlas`.

### Download A Release

Download from [GitHub Releases](https://github.com/QiushanHuang/mineral-atlas-workbench/releases/latest):

- **`mineral-atlas-workbench-1.0.1.zip`** — software, plugin, examples, documentation, and tests
- **`mineral-face-atlas-skill-2.0.1.zip`** — standalone skill with its offline runtime
- **`release-checksums.json`** — SHA-256 hashes for both archives

Extract the complete archive. To inspect the prebuilt atlas, open **`查看预置图谱.html`** or `ui/reference-atlas.html`. This needs neither Python nor a server.

### Clone And Start The Workbench

```bash
git clone https://github.com/QiushanHuang/mineral-atlas-workbench.git
cd mineral-atlas-workbench
python3 atlas_cli.py serve --open
```

On Windows:

```powershell
py -3 atlas_cli.py serve --open
```

The server prints its loopback address and opens the browser. Results are written to `atlas-runs/`. Stop the server with `Ctrl+C`; exported result pages continue to work offline.

Launchers are also included: `启动工作台.command` for macOS, `启动工作台.bat` for Windows, and `start.sh` for Linux. The core has **no third-party Python dependencies**.

### Enable Photograph Fitting

Use Python 3.13 for the pinned fitting environment:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-fit.lock
.venv/bin/python atlas_cli.py serve --open
```

Windows:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-fit.lock
.venv\Scripts\python.exe atlas_cli.py serve --open
```

NumPy and SciPy enable fitting. Pillow provides image metadata checks. For automatic outlines, photo candidates and color/gradient face proposals, install `requirements-photo.lock` in the same virtual environment; it also includes OpenCV. Manual modeling and annotation editing do not require it. Tesseract and Ollama remain optional, separately installed tools. Run `python3 atlas_cli.py doctor` with the interpreter you intend to use to inspect capabilities.

## Quick Start

### In The New Editor

1. Open **轻松建模** and use **模型编辑** to choose a preset or load a project. Start with the fixed views; use face movement and undo to adjust the shape.
2. Switch to **照片修正**. Try the synthetic example or the public real-photo example, then draw an edge or outline a face. **自动拾取** can be turned off; hold Shift to bypass it temporarily.
3. Use **修正** to drag points, lines or a face region. **识别面** proposes a boundary for review; explicitly accept it before further editing.
4. In **晶轴与参数**, define reference axes and inspect geometry. Picking vertices returns you to the form; apply the axis change explicitly.
5. Use **保存与复核** to save the model and photograph annotations separately, or export an offline model/report.

Switching workspaces preserves unfinished points. It does not save them to disk; finish or cancel a drawing before saving its annotations. [Complete workspace guide](docs/layout-guide.md#english).

### In The Classic Workbench

1. Select a reference case or import a project JSON file.
2. Check the crystal system, basis, indices, and support distances.
3. Select **生成模型并校验** to build and validate the model.
4. Enter a face ID or index in the viewer, or select a face directly.
5. Optionally load a photograph and mark the corresponding face corners and silhouette.
6. Run fitting, inspect the remaining edges and uncertainty, and download the result archive.

For a complete numerical example, select **载入合成标注示例** in the photograph panel, then run fitting. The image is explicitly synthetic and includes independent holdout points. The current workbench UI is in Chinese; this README documents its controls in English.

### From The Command Line

```bash
python3 atlas_cli.py doctor
python3 atlas_cli.py build examples/cube.json --out atlas-runs
python3 atlas_cli.py build examples/439.json --out atlas-runs
```

The returned `path` identifies the result directory. Open its `index.html`, or validate its saved geometry:

```bash
python3 atlas_cli.py validate atlas-runs/<run-id>/model.json
```

For fitting, use the Python environment containing NumPy and SciPy:

```bash
python3 atlas_cli.py fit project.json annotation.json --image photo.jpg --out atlas-runs
```

## Agent Plugin And Skill

### Plugin / MCP

The repository includes both portable Agent Plugins manifests (`plugin.json`, `mcp.json`) and Codex compatibility manifests (`.codex-plugin/plugin.json`, `.mcp.json`). A plugin-capable host can load the complete folder.

For a concrete Codex CLI connection, print the command for your current interpreter:

```bash
python3 scripts/print_mcp_config.py --codex-command
```

Review and run the printed `codex mcp add` command, then use a new session. To enable fitting, run the configuration script with the fitting environment's Python. On Windows, `py -3 scripts/print_mcp_config.py` generates configuration using the resolved `python.exe` path.

For other MCP hosts, `python3 scripts/print_mcp_config.py` prints JSON configuration. It changes no client settings. The server uses stdio with MCP 2025-06-18 compatibility.

Available tools on `main` (14): `atlas_editor`, `atlas_editor_export`, `atlas_review_export`, `atlas_review_check`, `atlas_photo_annotations`, `atlas_photo_align`, `atlas_from_photos`, `atlas_build`, `atlas_validate`, `atlas_fit`, `atlas_doctor`, `atlas_inspect_image`, `atlas_ocr`, and `atlas_vision`. [Editor requests](docs/manual-modeling-guide.md#api) · [Photograph alignment requests](docs/photo-correction-guide.md#api). Seeded face proposals remain a private HTTP interface.

### Standalone Skill

From the complete software package:

```bash
python3 scripts/install_skill.py
```

This installs `~/.codex/skills/mineral-face-atlas` and preserves any previous version under `~/.codex/skill-backups`. Alternatively, extract the standalone skill archive and place its `mineral-face-atlas` folder in your host's skill directory.

Start a new session and invoke `$mineral-face-atlas`. You do not need to install a duplicate standalone skill if you already use the bundled plugin skill.

## Crystal Faces And Coordinate Systems

A project stores the direct basis, point group, indices, support distances, and evidence. A face direction is calculated as `n ∝ A⁻ᵀ(h,k,l)`.

For four-axis notation, the independent basis is `A = [a₁, a₂, c]`; `a₃ = −a₁ −a₂` and `h + k + i = 0`. The redundant `i` is removed before calculating the normal. Face symbols, form symbols, directions, and photograph labels are kept distinct.

The result is a **reference morphology**, not an atomic structure or an automatic measurement of a natural mineral. An uncalibrated photograph alone does not uniquely determine Miller indices, cell ratios, mineral species, or point group. Uncertain labels remain uncertain in the output.

See [the project schema](schema/project.schema.json), [axis and index conventions](skills/mineral-face-atlas/references/crystallography.md), and [photograph fitting](skills/mineral-face-atlas/references/photos.md).

## Outputs And Reproducibility

Each successful run includes:

| File | Purpose |
|---|---|
| `index.html` | Offline interactive model, face lookup, and adjacency graph |
| `report.html` | Five-field report and face-by-face evidence |
| `input.json` / `model.json` | Parameters and complete generated geometry |
| `quality.json` | Mathematical validation results |
| `receipt.json` | Input/code fingerprints, environment, and file checksums |
| `result.zip` | Portable output bundle |
| `annotation.json`, `view.json`, `fit-quality.json` | Additional records when exporting an image-backed fit |

The same inputs and code reuse a verified cache. Changed parameters or damaged cached artifacts produce a new result instead of overwriting the previous one. Floating-point details can vary across environments; vision-model interpretations are not guaranteed to be identical.

## Working Without Network Access

The core and the prebuilt atlas run offline. To prepare optional dependencies, use a connected machine matching the target OS, architecture, and Python version:

```bash
python scripts/prepare_offline.py --download --wheelhouse wheelhouse
```

Copy the software and wheelhouse to the offline machine, then use its virtual-environment Python:

```bash
python scripts/prepare_offline.py --install --wheelhouse wheelhouse
```

Installation checks the recorded hashes and uses `--no-index`. Python itself, OCR language packs, and vision-model weights are not bundled. Do not copy a developer's virtual environment across machines.

## Architecture

- `atlas/core.py` — indices, symmetry operations, half-space geometry, and checks
- `atlas/editor.py` / `atlas/editor_export.py` — editable drafts, reference axes, parameter analysis and offline revisions
- `atlas/review.py` / `atlas/photo_annotations.py` — local review protocol and source-bound photograph corrections
- `atlas/fit.py` — optional camera fitting and independent error reporting
- `atlas/project.py` — immutable build outputs, reports, and verified caching
- `atlas/images.py` — optional local image adapters
- `atlas/server.py` / `atlas/mcp.py` — loopback UI and stdio interfaces
- `templates/` / `ui/` — exported viewer and workbench
- `skills/mineral-face-atlas/` — evidence workflow, references, and reusable prompts

Read [workflow and algorithms](docs/ALGORITHMS.md) for the calculation details.

## Testing And Project Status

```bash
python3 -m unittest discover -s tests
python3 scripts/run_js_checks.py
python3 scripts/release.py --out dist
python3 scripts/verify_release.py dist
```

The core tests run without optional packages; fitting tests explicitly skip when NumPy/SciPy are absent. Node is needed only for viewer regression tests. CI checks the core on macOS, Linux, and Windows, plus a separate fitting environment and clean-checkout packaging.

The recorded fixed-case benchmark measured approximately **2.57× faster geometry construction** and **4.41× faster fitting** than the earlier implementation. These are small, scoped algorithm benchmarks, not general performance guarantees or mineral-recognition accuracy claims. See [quality and limitations](docs/QUALITY.md) and [raw verification records](verification/).

## Contributing

Bug reports, reproducible geometry cases, documentation fixes, and well-calibrated annotations are welcome. Please include the project JSON, expected behavior, and the relevant validation result. Do not upload private photographs or present a provisional index assignment as ground truth.

See [CONTRIBUTING.md](CONTRIBUTING.md), [AUTHORS.md](AUTHORS.md), and [SECURITY.md](SECURITY.md).

## Author And Acknowledgments

Created and maintained by **[QiushanHuang](https://github.com/QiushanHuang)**.

Development, documentation, and logo design were assisted by OpenAI Codex and image-generation tooling. These are development tools, not additional human contributors. Scientific references and third-party tools are credited in the documentation; they do not imply endorsement.

## License

[MIT](LICENSE). Copyright © 2026 QiushanHuang.

[English](#english) · [简体中文](#中文)

---

<a id="中文"></a>

# Mineral Atlas Workbench · 矿物晶面工作台

[![简体中文](https://img.shields.io/badge/语言-简体中文-1677ff)](#中文)
[![English](https://img.shields.io/badge/Language-English-24292f)](#english)

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![工作流](https://img.shields.io/badge/Workflow-Offline%20%7C%20CLI%20%7C%20MCP-0f766e)](#三种使用方式)
[![晶面指数](https://img.shields.io/badge/Indices-hkl%20%7C%20hkil-47694b)](#晶面与坐标系)
[![版本](https://img.shields.io/badge/Release-v1.0.1-16a34a)](https://github.com/QiushanHuang/mineral-atlas-workbench/releases/latest)
[![Development](https://img.shields.io/badge/main-v1.1.0--dev.4-d6a34b)](https://github.com/QiushanHuang/mineral-atlas-workbench/tree/main)
[![CI](https://github.com/QiushanHuang/mineral-atlas-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/QiushanHuang/mineral-atlas-workbench/actions/workflows/ci.yml)
[![许可证](https://img.shields.io/badge/License-MIT-16a34a)](LICENSE)

<p align="center"><img src="assets/logo.png" width="150" alt="矿物晶面工作台：绿色晶体、金色选中面与拓扑节点"></p>

**Mineral Atlas Workbench** 是一个本地优先的矿物晶面工作台，用于教学模型、米勒指数定位、照片对照和可复现报告。

它适合这样的场景：报告上写着 `(1 0 −1 0)`，但你还需要知道，**它究竟是哪一张面、与哪些面共棱，以及这个标记如何对应原图**。

浏览器界面、命令行和 agent 插件共用同一计算核心。参数和证据随结果保存，其他人可以复现计算，而不必从一段对话中重新拼出整个工作流。

已把本地与在线判读经验接入证据流程和可复制提示词。[经验总结与验证边界](docs/photo-analysis-lessons.md)。

## v1.1.0-dev.4 · 四个工作区（`main` 开发版）

使用下方源码克隆方式启动工作台，进入 **轻松建模**，或打开本机地址下的 `/editor.html`。这些功能位于 `main` 开发版；最新正式标签及其下载包仍为 **v1.0.1**，旧下载包不包含新版编辑器。

模型编辑、照片修正、晶轴参数和保存复核分为四个工作区；照片使用大画布、紧凑工具条和右侧检查面板，窄屏时面板可折叠。切换保留编辑状态和未完成点，顶部按当前工作区保存模型或标注，文件链接集中在“保存与复核”。本轮不改变识别算法，公共 MCP 工具仍为14个。配套技能版本为 **2.1.0-dev.4**。[工作区指南](docs/layout-guide.md#中文) · [照片纠错](docs/photo-correction-guide.md#中文) · [拾取与教学](docs/beginner-ux-guide.md#中文)。

从七种预设或已有项目开始，在固定正面、侧面、顶面中推拉面、联动模块、截角和撤销。手动定义参考轴可保持外形，也可显式按原指数重建。参数页给出面积、体积、角度、指数候选、当前参考方向中的相容几何群及晶带候选。

照片可重新画棱、圈面、拖动节点和重新分类；更换模型后逐条重新确认面关联。项目、纠错和复核文件保存到启动时 `--out` 指定的本机目录，界面显示带内容指纹的文件名、路径和下载链接，可复制给别人，不覆盖已有不同内容。模型可导出离线 ZIP；复核回复在本地导入，不自动联网或上传原图。

[手动建模指南](docs/manual-modeling-guide.md#中文) · [识别实测与限制](docs/recognition-improvements-2026-10-02.md)

![照片修正工作区：大画布、就近绘图工具与右侧检查面板](assets/editor-photo-workspace.png)

图中使用已公开的451教学示例。橙色／绿色标注与紫色拟合模型分开显示；叠加用于核对，不是独立精度证明。

当前支持正面距的凸体编辑，不支持非凸自由雕刻或任意照片的唯一重建。旧 68 张开发照片的最终自动排序与基线一致；存在回退的图像精修保留为待审查建议。真实云端视觉精度尚未实测。

## 照片生成初始模型

可直接输入1–24张照片，自动提取轮廓并生成多个3D形态候选，再载入工作台核对和精修。[模糊形态、残缺视角与68张照片验证](docs/photo-evidence-series.md)。候选来自显式形态库先验，尚不支持任意新物体的唯一3D重建。

## v1.0.1 · 611 下端外形修正

按照片2加长下方六面并加宽底部，保留面号和共棱关系。上下端比例不同后，参考外形的几何点群更新为`6mm`，相关指数和报告已同步。[更新说明与前后对照](docs/611-correction.md)。

## 为什么是 Mineral Atlas

- 按指数或面 ID 定位具体晶面，减少对着示意图猜面
- 明确区分三轴与四轴的坐标规定
- 将候选几何与照片对照，保留不确定的编号和标定
- 从模型的同一份数据生成晶体学五项报告
- 核心离线运行，不需要账号、API Key 或运行时下载
- 可分享参数、离线结果，或完整的软件与 skill 包

## 三种使用方式

|入口|适合什么工作|需要什么|
|---|---|---|
|预置图谱|浏览15组参考模型、226个面|浏览器；不需要Python或服务器|
|本机工作台 / CLI|建立新模型、标注照片、导出报告|Python 3.10+；配准依赖可选|
|Agent 插件 / skill|在Codex等兼容客户端中复用证据、建模和校验流程|兼容客户端与本机Python|

核心不会把照片发送到远程服务。可选视觉接口只调用用户已安装、运行在`127.0.0.1`上的Ollama，不自动下载模型。

## 实例：451 原图与晶面对照

这是QiushanHuang明确授权公开的一组照片：**三张原图、两张照片的角点标注与相机配准，以及六面三方参考模型**。

| 原始照片 | 同一视角下计算得到的参考模型 |
|---|---|
| <img src="examples/451-photo-study/photos/01.jpg" width="280" alt="451原始照片，可见面号1、2、3"> | <img src="examples/451-photo-study/model-preview.svg" width="500" alt="选中F01并显示四指数的451参考模型"> |

照片保持原样，右图由保存的几何和拟合相机计算绘制，展示面号如何对应到可定位的晶面。交互示例还可旋转模型、查看真实共棱拓扑、切换照片、叠加拟合线框，并查看五项报告。

**[查看完整示例数据](examples/451-photo-study/)** · **[下载离线原图示例包](https://github.com/QiushanHuang/mineral-atlas-workbench/releases/download/v1.0.0/mineral-atlas-451-photo-example.zip)**

```bash
# 使用已保存的配准参数，不需要安装NumPy/SciPy。
python3 scripts/build_photo_example.py --out atlas-runs/451-photo-study
```

打开输出的`index.html`，点击“照片视角”和“线框叠加”，再切换照片或输入`F01`定位。安装配准依赖后，加`--refit`可重新拟合；该选项会明确刷新示例的已保存拟合文件。[完整复现说明](examples/451-photo-study/README.md)。

两张照片在960×1280原始坐标下的角点RMSE约为**8.77px、11.99px**。这是拟合误差，不是独立精度验收；第三张仅作补充观察，参考轴比与暂配的相反面编号仍保留说明。[原图来源与公开范围](examples/451-photo-study/DATA_NOTICE.md)。

## 功能特性

- 晶体旋转、稳定缩放、点选面、晶轴显示与平行相反面定位
- 三指数`(h k l)`和四指数`(h k i l)`解析，支持负号与上划线
- 32类晶体学点群的参考对称操作
- 根据直接基底、晶面指数与支持距离进行半空间构形
- 真实共棱邻接图，与三维空间模型和面表联动
- 检查轴系不相容、重复方向、未闭合方向、隐没面、面数冲突和拓扑错误
- 检查平面性、凸性、绕序、正体积、Euler关系、指数反算法线及声明点群
- 原始像素照片标注、外轮廓和可选面中心约束
- 可选确定性粗到细相机配准、稳健损失、竞争解和独立留出误差
- **对称型、晶系、结晶轴选择、晶体几何常数特征、晶面符号**五项报告
- 内容寻址输出、文件校验、原始输入留存与已验证缓存
- 开发版14个本地MCP工具，包含当前模型照片对齐、编辑、照片纠错和结构化复核，以及可独立使用的`mineral-face-atlas` skill

## v1.0.0 更新重点

这是共用离线工作流的首个公开版本。

- 将15组参考教学模型迁移为可移植参数文件。
- 统一三轴与四轴标定，保留原有固定比例的旋转方式。
- 增加参数、构形检查、照片标注与导出的浏览器界面。
- 用确定性粗到细初始化替代大量随机相机起点。
- 提供软件、插件与独立skill分发包，不附私人原图。
- 提供合成相机示例，无需自备照片即可检查标注与配准流程。
- 补齐中英文说明、项目logo、贡献者署名与自动测试。

## 安装

产品展示名：**Mineral Atlas Workbench**。插件名：`mineral-atlas-workbench`。Skill名：`mineral-face-atlas`。

### 下载发布包

从[GitHub Releases](https://github.com/QiushanHuang/mineral-atlas-workbench/releases/latest)下载：

- **`mineral-atlas-workbench-1.0.1.zip`**：软件、插件、案例、文档与测试
- **`mineral-face-atlas-skill-2.0.1.zip`**：附带离线运行时的独立skill
- **`release-checksums.json`**：两份压缩包的SHA-256

完整解压后，打开**`查看预置图谱.html`**或`ui/reference-atlas.html`即可浏览已有模型，不需要Python，也不需要启动服务器。

### 克隆源码并启动工作台

```bash
git clone https://github.com/QiushanHuang/mineral-atlas-workbench.git
cd mineral-atlas-workbench
python3 atlas_cli.py serve --open
```

Windows：

```powershell
py -3 atlas_cli.py serve --open
```

程序会打印本机地址并打开浏览器。结果保存在`atlas-runs/`。按`Ctrl+C`停止服务后，已经导出的结果页仍可离线打开。

也可使用macOS的`启动工作台.command`、Windows的`启动工作台.bat`或Linux的`start.sh`。核心**不需要第三方Python库**。

### 启用照片配准

锁定的配准环境建议使用Python 3.13：

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-fit.lock
.venv/bin/python atlas_cli.py serve --open
```

Windows：

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-fit.lock
.venv\Scripts\python.exe atlas_cli.py serve --open
```

NumPy、SciPy用于配准，Pillow用于图像元数据检查。自动轮廓、照片候选和颜色／梯度面区识别需要在同一虚拟环境安装 `requirements-photo.lock`，其中还包含OpenCV；手动建模和画线修面不依赖这些可选库。Tesseract和Ollama是另外安装的可选工具。使用准备实际运行的Python执行`atlas_cli.py doctor`，即可检查当前能力。

## 快速开始

### 新版编辑器

1. 进入 **轻松建模 → 模型编辑**，选择预设或载入项目，用固定视图选面、推拉并撤销核对。
2. 切换到 **照片修正**，先试合成图或公开实物示例，再画线、圈面。**自动拾取**可以关闭，按住 Shift 可临时关闭。
3. 使用 **修正** 拖动节点、线或整个面区；**识别面**先给出边界候选，确认采用后继续修边。
4. 在 **晶轴与参数** 定义参考轴、查看几何量。点选模型顶点后会返回表单，确认并应用才生效。
5. 在 **保存与复核** 分别保存模型项目和照片标注，或导出离线模型与报告。

切换工作区保留未完成点，但不代表已写入文件；保存标注前先完成或取消绘制。[完整工作区指南](docs/layout-guide.md#中文)。

### 经典工作台

1. 选择参考案例，或导入项目JSON。
2. 核对晶系、基底、指数与支持距离。
3. 点击**生成模型并校验**。
4. 在模型中输入面ID或晶面指数，也可直接点击晶面。
5. 如需对照，导入照片，标记相应晶面的角点和整体外轮廓。
6. 执行配准，检查其余棱与不确定项，再下载结果包。

想检查完整数值流程，可点击照片面板中的**载入合成标注示例**，然后配准。它明确标为合成图，并带有独立留出点。当前工作台界面为中文，英文README提供对应操作说明。

### 命令行操作

```bash
python3 atlas_cli.py doctor
python3 atlas_cli.py build examples/cube.json --out atlas-runs
python3 atlas_cli.py build examples/439.json --out atlas-runs
```

返回的`path`就是结果目录。打开其中的`index.html`，或检查保存的几何：

```bash
python3 atlas_cli.py validate atlas-runs/<run-id>/model.json
```

使用安装了NumPy、SciPy的Python进行配准：

```bash
python3 atlas_cli.py fit project.json annotation.json --image photo.jpg --out atlas-runs
```

## Agent 插件与 Skill

### 插件 / MCP

仓库同时包含通用Agent Plugins格式的`plugin.json`、`mcp.json`，以及Codex兼容入口`.codex-plugin/plugin.json`、`.mcp.json`。支持本地插件目录的客户端可加载完整文件夹。

使用Codex CLI时，先打印适用于当前Python的命令：

```bash
python3 scripts/print_mcp_config.py --codex-command
```

检查并运行输出的`codex mcp add`命令，然后在新会话使用。需要配准时，用配准虚拟环境的Python运行配置脚本。Windows可用`py -3 scripts/print_mcp_config.py`，自动生成实际`python.exe`路径。

其他MCP客户端可运行`python3 scripts/print_mcp_config.py`获取JSON配置。脚本只打印，不修改客户端设置。服务器使用stdio，兼容MCP 2025-06-18协议。

`main` 开发版共有14个工具：`atlas_editor`、`atlas_editor_export`、`atlas_review_export`、`atlas_review_check`、`atlas_photo_annotations`、`atlas_photo_align`、`atlas_from_photos`、`atlas_build`、`atlas_validate`、`atlas_fit`、`atlas_doctor`、`atlas_inspect_image`、`atlas_ocr`、`atlas_vision`。[编辑器请求](docs/manual-modeling-guide.md#api) · [照片对齐请求](docs/photo-correction-guide.md#api)。点选面区仍使用私有 HTTP 接口，不增加公共工具。

### 独立 Skill

在完整软件目录中运行：

```bash
python3 scripts/install_skill.py
```

安装位置为`~/.codex/skills/mineral-face-atlas`，已有版本会先保存到`~/.codex/skill-backups`。也可以解压独立skill包，将`mineral-face-atlas`文件夹放入客户端的skill目录。

在新会话中调用`$mineral-face-atlas`。如果已经使用插件自带的skill，不必重复安装独立副本。

## 晶面与坐标系

项目文件保存直接基底、点群、指数、支持距离与证据。晶面方向通过`n ∝ A⁻ᵀ(h,k,l)`计算。

四轴使用独立基矩阵`A = [a₁, a₂, c]`，`a₃ = −a₁ −a₂`，并满足`h + k + i = 0`。求法线前去掉冗余的`i`。晶面、晶形、晶向和照片上的面号分别记录，不混为同一概念。

生成结果是**参考外形模型**，不是原子结构，也不是自动测定的天然矿物晶面。无标定照片不能唯一决定真实指数、晶胞轴比、矿物种属或点群；不确定编号会在输出中继续保留。

详见[参数schema](schema/project.schema.json)、[晶轴与指数](skills/mineral-face-atlas/references/crystallography.md)、[照片判读与配准](skills/mineral-face-atlas/references/photos.md)。

## 输出与复现

每次成功生成会输出：

|文件|用途|
|---|---|
|`index.html`|离线交互模型、按面定位与邻接图|
|`report.html`|五项报告及逐面证据|
|`input.json` / `model.json`|参数与完整几何|
|`quality.json`|数学检查结果|
|`receipt.json`|输入/程序指纹、环境与文件校验|
|`result.zip`|可移植结果包|
|`annotation.json`、`view.json`、`fit-quality.json`|附图配准导出时增加的记录|

相同输入与程序复用经过完整性检查的缓存。参数变化或缓存损坏时会生成新结果，不覆盖旧输出。不同环境的末位浮点数可能不同；视觉模型的文字判读不保证完全一致。

## 断网环境准备

核心与预置图谱可以离线运行。可选依赖应在与目标机**系统、架构、Python版本相同**的联网准备机上下载：

```bash
python scripts/prepare_offline.py --download --wheelhouse wheelhouse
```

把软件与wheelhouse复制到离线目标机后，使用目标虚拟环境的Python安装：

```bash
python scripts/prepare_offline.py --install --wheelhouse wheelhouse
```

安装会核对记录的哈希并使用`--no-index`，不访问网络。包内不包含Python运行时、OCR语言包或视觉模型权重。不要跨机器直接复制开发者的虚拟环境。

## 架构说明

- `atlas/core.py`：指数、对称操作、半空间几何与检查
- `atlas/editor.py` / `atlas/editor_export.py`：草稿编辑、参考轴、参数解析与离线修订
- `atlas/review.py` / `atlas/photo_annotations.py`：本地复核协议与原图绑定的纠错标注
- `atlas/fit.py`：可选相机配准与独立误差报告
- `atlas/project.py`：版本化输出、报告与已验证缓存
- `atlas/images.py`：可选本机图像接口
- `atlas/server.py` / `atlas/mcp.py`：本机界面与stdio接口
- `templates/` / `ui/`：导出查看器与工作台
- `skills/mineral-face-atlas/`：证据流程、参考资料与可复制提示词

计算细节见[工作流与算法](docs/ALGORITHMS.md)。

## 测试与项目状态

```bash
python3 -m unittest discover -s tests
python3 scripts/run_js_checks.py
python3 scripts/release.py --out dist
python3 scripts/verify_release.py dist
```

核心测试不依赖可选库；缺少NumPy、SciPy时明确跳过拟合测试。Node仅用于查看器回归，不是软件运行依赖。CI分别检查macOS、Linux、Windows核心，以及配准环境和干净源码打包。

已记录的固定案例测试中，构形速度约为旧实现的**2.57倍**，配准约为**4.41倍**。这属于小范围算法基准，不是通用性能保证，也不是矿物识别准确率。详见[质量与限制](docs/QUALITY.md)和[原始验证记录](verification/)。

## 参与贡献

欢迎提供可复现问题、几何案例、文档修正和有校准依据的标注。提交问题时请附参数JSON、预期行为和相关检查结果；不要上传私人照片，也不要把暂定指数作为实物真值。

详见[贡献指南](CONTRIBUTING.md)、[作者信息](AUTHORS.md)和[安全说明](SECURITY.md)。

## 作者与致谢

项目创建与维护：**[QiushanHuang](https://github.com/QiushanHuang)**。

代码、文档与logo设计使用了OpenAI Codex和图像生成工具辅助。它们属于开发工具，不作为额外的人类贡献者署名。科学资料和第三方工具在文档中列明来源，不表示相关机构为项目背书。

## 许可证

[MIT](LICENSE)。Copyright © 2026 QiushanHuang。

[简体中文](#中文) · [English](#english)
