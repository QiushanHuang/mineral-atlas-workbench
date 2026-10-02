# 实物照片拉线纠错与模型对齐 / Photo correction and alignment

[简体中文](#中文) · [English](#english) · [CLI / API](#api)

本页对应 `main` 的软件 **v1.1.0-dev.4**、技能 **v2.1.0-dev.4**；最新正式标签及下载包仍为 **v1.0.1**。页面分区见[四工作区指南](layout-guide.md#中文)。

<a id="中文"></a>

## 从实物照片开始

在“轻松建模 → 照片修正”选择自己的照片，或点击“实物照片示例”。示例使用项目公开的 451 教学模型照片，并载入**既有人工外轮廓与四条人工面界线**。这些线来自过去的人工标注，不是本轮自动识别；可以直接拖动它们练习纠错。

照片上的棱线、外轮廓、面区域、遮挡和不确定线分别保存。默认拾取、Shift 自由落点和快捷键继续可用，见[拾取与教学指南](beginner-ux-guide.md#中文)。

“聚焦物体”会放大物体所在区域，实物示例载入后自动聚焦。它只改变画布的查看范围，原图不裁剪、不改写，标注仍使用原图坐标；需要查看背景时切回“全图”。展开较大的工具选项后，面板不再悬浮遮挡画布，可以边看照片边调整。

## 重新拉线或改面边界

切到“修正”，展开“重新拉线 / 修改面边界”。

|操作|结果|
|---|---|
|拖动圆点|移动这个端点|
|拖动一条棱线|平移整条标注线|
|拖动面区域的一条边|移动这条边的两个端点|
|拖动面区域内部|平移整个二维区域|
|在线上加节点 / 删除一个节点|补充转折点或去掉多余点；不接受退化或自交边界|
|重画所选标注|完成后替换该标注的点列并保留 ID；取消则保留原标注|

“联动二维重合点”开启时，落在同一照片位置的关联节点一起移动；只想改当前标注时关闭它。这里的重合关系是二维绘图关系，不能据此确定实体中两个顶点相同。修正可撤销，也可重做。

如果自动轮廓建议有帮助，点击“采用照片轮廓以便修正”，再拖点或重画。采纳只是把建议变为可编辑的标注；边界是否属于物体仍需核对。

## 点选一个面，检查后再采用

1. 点击“识别面”，在目标面内部点一下，尽量避开编号、文字和强阴影。
2. 检查青色候选区域。已有棱线和轮廓能围成闭合区域时优先使用它们，否则按种子附近颜色与梯度寻找区域。
3. 颜色范围可选 **12 / 24 / 40**：较严格、标准、较宽松，默认 24。它是图像算法阈值，不是物理测量量。修改后点击“按当前范围重试”。
4. 边界合适时点击“采用这个面，继续修边”，随后仍可拖点、拉边、增删节点。候选不合适就放弃，补分界棱线或手工圈面。

未采用的预览不会写入标注。区域触及图像边缘、明显泄漏、过小或边界过于复杂时，程序可拒绝生成候选。照片中的同色邻面、文字和阴影不能仅靠颜色可靠区分；程序不会把拒绝结果补凑成一个面，也不会据此自动确定三维晶面、晶轴或指数。

## 与当前模型对齐

载入或调整当前 v2 模型，检查整体外轮廓，再点击“用棱和面对齐当前模型”。**紫色是模型投影线框**；橙色棱线、蓝色面区等是你的照片标注。对齐只拟合相机，不修改三维外形。

手工面区与可见模型面按一对一规则产生候选对应，列表可能说明歧义或无法对应。核对照片与紫色叠加后，再点击“确认这个面对应”。确认会更新标注，因此需要**重新对齐**，才能在下一次计算中使用该关联。

修改照片标注、更换照片或改变模型后，旧叠加失效，不会继续冒充当前结果。若线框仍不能贴合，应先判断是标注、相机还是外形不合适，再修正并重算。显示的残差使用了参与拟合的轮廓、棱和面，不能作为独立实物精度。

## 保存来源与结果

“保存纠错文件”保存原图指纹、EXIF 显示尺寸、标注点列，以及可选的 `feature.evidence` 来源说明。例如，说明可以记录“已有人工示例边界”或“用户采用的本机面区候选”。来源说明留在本地 JSON；当前云端复核包只导出允许的几何字段，默认不会把这些任意文本一并加入。程序不自动上传照片。

对齐记录另存到本机输出目录，界面提供记录链接。纠错文件不含原图，重新使用时应同时载入对应照片。保存模型与保存纠错是两份不同记录。

## 两张 451 照片的有限检查

对 [01](../examples/451-photo-study/photos/01.jpg) 和 [02](../examples/451-photo-study/photos/02.jpg)，种子均来自既有人工面角点的均值，因此“仅种子”也不是全自动试验。

|条件|照片 01|照片 02|
|---|---|---|
|仅人工种子，无手绘边界|拒绝：边界过于复杂|拒绝：区域过小|
|人工种子＋已有真实边界线|待检查候选，IoU **0.9396**|待检查候选，IoU **0.9847**|

有线条件主要验证算法是否遵守已给的人工边界，不能将这两个 IoU 称为自动发现面的准确率。原图与原标注未修改。完整输入指纹、失败原因和耗时保留在本地开发验收记录中；此处只报告有限检查的结果和限制。

<a id="api"></a>

## CLI、HTTP 与 MCP

`photo-align` 读取请求 JSON。请求包含完整 v2 `draft`、PNG/JPEG base64 `image`，以及可选的单张照片 `annotation`；`expected_fingerprint` 可用于拒绝过期模型。文件路径不能直接代替 `image`。

例如，将保存的模型、纠错文件和对应照片命名为 `draft.json`、`corrections.json`、`photo.jpg`，在同一工作目录准备请求：

```python
import base64, hashlib, json
from pathlib import Path

raw = Path('photo.jpg').read_bytes()
saved = json.loads(Path('corrections.json').read_text(encoding='utf-8'))
items = saved['annotations'] if 'annotations' in saved else [saved]
matching = [a for a in items
            if a['source_sha256'] == hashlib.sha256(raw).hexdigest()]
if len(matching) != 1:
    raise ValueError('需要与这张原图匹配的唯一纠错记录')
request = {
    'draft': json.loads(Path('draft.json').read_text(encoding='utf-8')),
    'image': base64.b64encode(raw).decode('ascii'),
    'annotation': matching[0],
}
Path('photo-align-request.json').write_text(
    json.dumps(request, ensure_ascii=False, indent=2), encoding='utf-8')
```

```sh
python3 atlas_cli.py photo-align photo-align-request.json --out atlas-runs
```

返回值包括投影线框、候选面对应、拟合残差、模型／图像／标注指纹，以及本地记录路径和链接。接口对应关系如下：

|入口|用途|范围|
|---|---|---|
|CLI `photo-align`|当前 v2 模型相机对齐|本机 JSON 请求|
|HTTP `POST /api/photo-align`|相同对齐流程|工作台本机会话|
|MCP `atlas_photo_align`|相同对齐流程并保存记录|新增公共工具；开发版共 **14** 个|
|HTTP `POST /api/photo-face`|种子点面区预览，参数 `image`、`annotation`、`seed`、`tolerance`|私有界面入口，不是公共 MCP 工具|

图像建议和相机拟合使用已有可选依赖。缺少依赖时仍可手工画线、圈面和保存；工作台不会自动安装组件。

<a id="english"></a>

## Correct a photograph directly

This guide covers software **1.1.0-dev.4** and skill **2.1.0-dev.4** on `main`; the latest tagged release archives remain **v1.0.1**. See the [workspace guide](layout-guide.md#english) for the layout.

Choose a photograph or open **实物照片示例**. The example loads a publicly distributed 451 teaching-model photograph with its **existing manual silhouette and four manual face-boundary edges**. Those lines are reference annotations, not newly recognized edges.

**聚焦物体** enlarges the object region; the real-photo example focuses automatically. This changes the canvas view only: the original image is not cropped or rewritten, and annotations retain original-image coordinates. Use **全图** to restore the full view. Large expanded tool panels no longer float over and obscure the canvas.

In **修正**, drag endpoints, translate an entire edge annotation, move one face-boundary segment, or translate a face region by dragging its interior. Add or remove nodes as needed. Redrawing replaces the points while preserving the feature ID; cancellation leaves the original annotation intact. The linked-point checkbox moves coincident 2-D nodes together, without claiming that they represent the same 3-D vertex. Undo/redo remains available.

You can also adopt a suggested photograph outline and then edit it. Snapping and Shift bypass work as described in the [beginner guide](beginner-ux-guide.md#english).

## Preview a seeded face region

Select **识别面** and click inside a visible face, avoiding printed labels and strong shadows. Inspect the cyan preview before accepting it. Closed manual boundaries take priority; otherwise a bounded color/gradient region is proposed. The color thresholds are **12 / 24 / 40**, with 24 as the default. They are algorithm settings, not physical measurements.

Accepting creates an editable annotation; you can continue dragging boundaries or adding and removing nodes. Rejection, incomplete boundaries and unsuitable regions remain explicit. A proposed 2-D region does not establish a real 3-D face, crystallographic axes or indices.

## Align the current model

Load a v2 draft, check the silhouette, and select **用棱和面对齐当前模型**. Purple lines show the projected model, while the orange/blue features are your annotations. Only the camera is fitted; the model geometry does not change.

Manual regions receive one-to-one candidate assignments to visible model faces, with ambiguity or unmatched regions retained. Confirm an assignment only after inspection, then align again to use that new association. Changing annotations, photographs or the model invalidates the old overlay. Residuals use fitting inputs and are not independent measures of specimen accuracy.

Correction JSON retains optional `feature.evidence` provenance. The current cloud-review export does not include this arbitrary local text by default; it exports only its permitted geometric fields. No photograph upload happens automatically. Alignment records are saved separately in the local output directory.

On two existing 451 photographs, seeds derived from manual corners produced no acceptable region without boundary lines. With those manual boundaries, proposal IoU was **0.9396 / 0.9847**. This tests adherence to supplied boundaries, not automatic face-discovery accuracy; even the seed-only condition was manually assisted. The original photographs and annotations were unchanged.

The [CLI/API section](#api) shows how to prepare a JSON request and run `photo-align`. HTTP `/api/photo-align` and public MCP `atlas_photo_align` use the same flow; the development build now has **14 MCP tools**. Seeded face proposals use private HTTP `/api/photo-face`, not an additional MCP tool. Missing optional dependencies leave manual correction and saving available, without automatic installation.
