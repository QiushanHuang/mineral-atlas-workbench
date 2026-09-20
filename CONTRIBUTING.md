# Contributing / 参与贡献

[English](#english) · [简体中文](#简体中文)

<a id="english"></a>

## Report A Reproducible Issue

Include the software version, OS/Python version, `atlas_cli.py doctor` output, a minimal project JSON, the command or interface steps, and expected versus actual behavior. Attach only photographs or annotations you have permission to share. Remove personal paths and private metadata.

For crystallographic corrections, identify the coordinate setting, reference basis, source, and affected face IDs. Separate measured facts, photograph observations, and model assumptions. A small fitting residual or matching face count is not sufficient evidence for a new physical assignment.

## Development

Use Python 3.13 for the pinned optional environment and Node for viewer tests:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-fit.lock
.venv/bin/python -m unittest discover -s tests
.venv/bin/python scripts/run_js_checks.py
```

Core-only changes can be tested with a standard-library Python environment. Add a focused regression test for changed behavior. Preserve stable face IDs, uncertainty records, original-pixel annotations, and rotation/zoom behavior.

Never silently mirror a photograph or relabel a face to improve the fit. Keep fit points separate from independent holdout points. Document any unsupported symmetry setting or numerical approximation.

## Documentation And Releases

Keep `README.md` and `README.zh-CN.md` aligned, including links and install commands. Follow [RELEASING.md](docs/RELEASING.md) when changing the distribution. Use synthetic or explicitly shareable fixtures. Do not commit `evaluation/`, private photographs, local interpreter preferences, credentials, or run directories.

Submit a focused pull request with the concrete behavior change and relevant checks. Preserve authorship; do not add someone to the contributor list without their identity and contribution being established.

<a id="简体中文"></a>

## 问题反馈

请提供版本、系统/Python版本、`atlas_cli.py doctor`输出、最小参数JSON、复现步骤及预期/实际行为。只上传你有权公开的照片和标注，移除私人路径及元数据。

晶体学修正需要说明坐标设置、参考基底、资料来源与相关面ID；区分实测事实、照片观察和模型假设。低拟合误差或面数相同，不能单独证明新的实物标定。

## 开发与文档

上面的命令可运行完整检查；只有标准库时也可检查核心。按修改范围增加回归，保留稳定面ID、未知项、原始像素标注与旋转缩放行为。

不要为了降低误差偷偷镜像照片或改面号；拟合点与独立留出点应分开。同步维护中英文README，发布步骤见[RELEASING.md](docs/RELEASING.md)。不提交私人原图、运行缓存、本机解释器路径或凭据。

PR说明应包含具体行为变化和相关验证，贡献者署名须有明确身份与贡献依据。
