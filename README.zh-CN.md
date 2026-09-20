# Mineral Atlas Workbench · 矿物晶面工作台

[![简体中文](https://img.shields.io/badge/语言-简体中文-1677ff)](#简体中文)
[![English](https://img.shields.io/badge/Language-English-24292f)](README.md#english)

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![工作流](https://img.shields.io/badge/Workflow-Offline%20%7C%20CLI%20%7C%20MCP-0f766e)](#三种使用方式)
[![晶面指数](https://img.shields.io/badge/Indices-hkl%20%7C%20hkil-47694b)](#晶面与坐标系)
[![版本](https://img.shields.io/badge/Status-v1.0.0-16a34a)](https://github.com/QiushanHuang/mineral-atlas-workbench/releases/latest)
[![CI](https://github.com/QiushanHuang/mineral-atlas-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/QiushanHuang/mineral-atlas-workbench/actions/workflows/ci.yml)
[![许可证](https://img.shields.io/badge/License-MIT-16a34a)](LICENSE)

<p align="center"><img src="assets/logo.png" width="150" alt="矿物晶面工作台：绿色晶体、金色选中面与拓扑节点"></p>

<a id="简体中文"></a>

**Mineral Atlas Workbench** 是一个本地优先的矿物晶面工作台，用于教学模型、米勒指数定位、照片对照和可复现报告。

它适合这样的场景：报告上写着 `(1 0 −1 0)`，但你还需要知道，**它究竟是哪一张面、与哪些面共棱，以及这个标记如何对应原图**。

浏览器界面、命令行和 agent 插件共用同一计算核心。参数和证据随结果保存，其他人可以复现计算，而不必从一段对话中重新拼出整个工作流。

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
- 7个本地MCP工具及可独立使用的`mineral-face-atlas` skill

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

- **`mineral-atlas-workbench-1.0.0.zip`**：软件、插件、案例、文档与测试
- **`mineral-face-atlas-skill-2.0.0.zip`**：附带离线运行时的独立skill
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

NumPy、SciPy用于配准，Pillow用于图像元数据检查。Tesseract和Ollama是另外安装的可选工具。使用准备实际运行的Python执行`atlas_cli.py doctor`，即可检查当前能力。

## 快速开始

### 浏览器操作

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

工具包括：`atlas_build`、`atlas_validate`、`atlas_fit`、`atlas_doctor`、`atlas_inspect_image`、`atlas_ocr`、`atlas_vision`。

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

[简体中文](#简体中文) · [English](README.md#english)
