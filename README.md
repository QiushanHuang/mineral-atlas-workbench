# Mineral Atlas Workbench

[![English](https://img.shields.io/badge/Language-English-24292f)](#english)
[![简体中文](https://img.shields.io/badge/语言-简体中文-1677ff)](README.zh-CN.md#简体中文)

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Workflow](https://img.shields.io/badge/Workflow-Offline%20%7C%20CLI%20%7C%20MCP-0f766e)](#three-ways-to-work)
[![Crystallography](https://img.shields.io/badge/Indices-hkl%20%7C%20hkil-47694b)](#crystal-faces-and-coordinate-systems)
[![Status](https://img.shields.io/badge/Status-v1.0.0-16a34a)](https://github.com/QiushanHuang/mineral-atlas-workbench/releases/latest)
[![CI](https://github.com/QiushanHuang/mineral-atlas-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/QiushanHuang/mineral-atlas-workbench/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-16a34a)](LICENSE)

<p align="center"><img src="assets/logo.png" width="150" alt="Mineral Atlas: a faceted green crystal with a selected gold face and topology nodes"></p>

<a id="english"></a>

**Mineral Atlas Workbench** is a local-first crystal-face workbench for teaching models, Miller indices, photograph comparison, and reproducible reports.

It is built for the moment when a report lists a face such as `(1 0 −1 0)`, but you still need to know **which face it is, how it meets its neighbors, and how that assignment relates to the photograph**.

The same computational core powers a browser interface, a command-line tool, and an agent plugin. Parameters and evidence stay with the result, so another person can reproduce the calculation instead of reconstructing the workflow from a conversation.

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

## Features

- Interactive crystal rotation, stable zoom, face selection, crystal axes, and opposite-face lookup
- Three-index `(h k l)` and four-index `(h k i l)` parsing, including negative and overbar notation
- Reference symmetry operations for the 32 crystallographic point-group classes
- Half-space construction from a direct basis, face indices, and support distances
- Real shared-edge adjacency, linked to the spatial model and face table
- Checks for incompatible bases, duplicate directions, missing closure, inactive faces, face-count conflicts, and invalid topology
- Plane, convexity, winding, positive-volume, Euler, index-normal, and declared-symmetry checks
- Original-pixel photograph annotations, silhouettes, and optional face-center constraints
- Optional deterministic coarse-to-fine camera fitting, robust losses, alternative correspondences, and independent holdout errors
- Five-field reports: **symmetry class, crystal system, axis selection, geometric constants, and crystal-face symbols**
- Content-addressed outputs with checksums, preserved inputs, and verified cache reuse
- Seven local MCP tools and a self-contained `mineral-face-atlas` skill

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

- **`mineral-atlas-workbench-1.0.0.zip`** — software, plugin, examples, documentation, and tests
- **`mineral-face-atlas-skill-2.0.0.zip`** — standalone skill with its offline runtime
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

NumPy and SciPy enable fitting. Pillow provides image metadata checks. Tesseract and Ollama remain optional, separately installed tools. Run `python3 atlas_cli.py doctor` with the interpreter you intend to use to inspect capabilities.

## Quick Start

### In The Browser

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

Available tools: `atlas_build`, `atlas_validate`, `atlas_fit`, `atlas_doctor`, `atlas_inspect_image`, `atlas_ocr`, and `atlas_vision`.

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

[English](#english) · [简体中文](README.zh-CN.md#简体中文)
