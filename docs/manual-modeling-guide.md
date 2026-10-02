# 轻松建模 / Manual modeling

[简体中文](#中文) · [English](#english)

本页对应 `main` 开发版 **v1.1.0-dev.4**；最新正式标签及下载包仍为 **v1.0.1**。新版页面入口见[四工作区指南](layout-guide.md#中文)。

<a id="中文"></a>

## 开始调整

在完整开发目录运行 `python3 atlas_cli.py serve --open`，进入“轻松建模”，或在程序打印的本机地址后打开 `/editor.html`。编辑器需要本机 Python 服务；导出的离线预览不需要服务。

在“模型编辑”的“新建 / 载入模型”中，可以新建基础体、载入参考模型，或用“打开项目”读入旧 v1 参数 JSON、新 v2 草稿 JSON。旧文件不会被覆盖。照片生成的候选也可载入后继续手调。

|预设 ID|中文|English|
|---|---|---|
|`box`|方柱 / 长方体|Box|
|`triangular_prism`|三角柱|Triangular prism|
|`hexagonal_prism`|六方柱|Hexagonal prism|
|`pyramid`|单锥|Pyramid|
|`dipyramid`|双锥|Dipyramid|
|`rhombohedron`|菱面体|Rhombohedron|
|`truncated_box`|截角方体|Truncated box|

正面、侧面、顶面和三维预览同步选择同一张面，点击面不会自动转动相机。先用固定视图调整；需要转动时打开“自由旋转预览”。“正对选中面”“标准方向”“适合窗口”分别控制方向和显示范围。

1. 在图上点面，选择“仅选中面”“同模块的面”或“选中面与平行相反面”。模块来自预设或有记录的分组，不凭外观猜归属。
2. 用滑块或数值沿法线推拉；正数向外，负数向内。滑块松开只记一次操作。宽、厚、高可分别按比例修改。
3. “截角 / 截平”提供切面方向预设，再调整外法线和支持距离。高级单面参数可修改当前面的方向、距离和说明。
4. 用“撤销 / 重做”和“修改前叠加”核对。导致面消失、未闭合或退化的操作会被拒绝，最后一个有效模型保留。

当前编辑对象是由正支持距离平面构成的凸体；内部几何原点必须在实体内部。它适合教学多面体，不支持非凸自由雕刻、曲面 CAD 或任意手绘线自动恢复深度。

## 参考轴与参数

可以填入正交、单斜 b 唯一轴、六方四轴预设或自定义基底；也可点选两个顶点确定 a/c 方向、使用选中面法线，或点选参考原点。基底矩阵的列是独立轴；六方设置满足 `a3 = −a1 − a2`。

- **定义轴 · 保持外形**：只重定义参考轴和原点，实体几何不变，重新解析该轴下的指数候选。
- **按原指数和新轴重建外形**：保留各面的已记录参考指数，按新轴重建外形。每张面都须有可用原指数；不会拿未确认候选补齐。

参考原点与内部几何原点分别记录。轴箭头用于看方向，没有独立标定时，轴比、指数和长度均不能作为实测晶胞数据。

参数页给出体积、面积、面距、棱长、共棱邻接和二面角。外二面角是相邻外法线夹角，凸体内二面角为 `180° − 外二面角`。指数候选带搜索范围和角偏差，无合适低阶解时保留未知。几何群检查只在**当前参考方向**测试 32 类操作，不遍历任意姿态；晶带候选表示多面法线共同垂直于某个方向。两者均不认定实物点群或晶格。

## 在照片上重新拉线、圈面

载入原图后，选择真实棱、外轮廓、面区域、遮挡或不确定线，逐点绘制并点击“完成”。线至少两点，区域至少三点；闭合区域不必重复起点。每张照片最多一条完整外轮廓。

切到“修正”可调整节点。选中已有标注后，可重新分类、更新或清除面关联、删除、撤销和重做。照片尺寸按 EXIF 转正后的显示像素保存，文件指纹仍来自原始字节。

面关联同时保存 `face_id` 和该**条特征**的 `model_fingerprint`。更换模型或修改草稿后，即使仍有同名 F01，也须逐项重新确认或清除关联；更新一条标注不会替其他旧标注确认。用户圈出的面区不是自动识别出的晶面，也不证明原图面号或指数。

展开“比较其他模型候选”，点击“用这些修正重新识别候选”后，手工外轮廓和明确棱线参与本地匹配；遮挡影响可用证据，不确定线仅保留。面区域可作为待核对约束参与匹配；与当前模型的对齐和面对应见[照片纠错指南](photo-correction-guide.md#中文)，区域边界不会自动变成已确认晶棱。候选仍主要来自已有模板库。

旧 68 张开发照片的最终默认候选名次与原基线一致，不能据此声称自动识别准确率提高。原图角点细化和自动棱线新评分在部分旧例发生回退，因此保留为诊断建议，未默认替换。具体改善、回退及合成试验见[识别改进记录](recognition-improvements-2026-10-02.md)。

## 保存与复核

“保存与复核”工作区中的“保存项目 JSON”“保存纠错文件”“生成复核包”和“下载复核提示词”会先把文件写入本机工作台输出目录，再显示可打开或下载的链接及本地路径。输出目录由启动时的 `--out` 指定，例如 `python3 atlas_cli.py serve --out atlas-runs --open`；省略时默认为 `atlas-runs/`。

文件名包含内容指纹，例如 `draft-<指纹>.json`、`annotations-<指纹>.json`、`review-<指纹>.json` 和 `prompt-<指纹>.txt`。相同内容复用已有文件，不同内容另存；即使同名位置已有其他内容，也不会覆盖它。界面“已保存到本机”表示本地持久化完成，不表示浏览器已另行下载。可以直接按显示路径找到文件并复制给别人；纠错 JSON 不含原图，复用时仍需对应照片。

|操作|保存什么|如何继续|
|---|---|---|
|保存项目 JSON|草稿、参考轴、来源和操作历史|在编辑器“打开项目”|
|保存纠错文件|原图指纹、显示尺寸和逐条标注|先载入对应原图，再载入纠错 JSON|
|导出离线模型与参数报告|`draft.json`、`model.json`、`analysis.json`、检查记录、HTML 预览和 `result.zip`|离线打开 `index.html`；继续编辑时导入 `draft.json`|
|生成复核包 / 下载提示词|脱敏几何摘要、手工标注、策略及输入指纹|由你交给选择的助手；程序不联网、不上传原图|

复核回复须遵守包内 `response_template`。导入后先检查建议与证据，再逐项勾选；未勾选不会采纳。仅允许有限的面移动、轴设置和截切命令，全部回到本地核心重算。模型或策略已改变、未知面号、过期关联、无证据或非法命令会被拒绝。原图没有包含在当前复核包中，回复不能把用户标注冒充像素观察。

本轮未调用真实云端视觉服务。协议校验与本地重算一致性不等于云端识别精度已验证。

<a id="api"></a>

## CLI、HTTP 与 MCP

将下面内容保存为 `editor-create.json`：

```json
{"action":"create","preset":"hexagonal_prism","id":"my-model","title":"参考六方柱"}
```

```sh
python3 atlas_cli.py editor editor-create.json > editor-result.json
```

返回对象含 `draft`、`model`、`analysis`、`fingerprint` 和 `warnings`。后续请求可用 `action: "import"` 配合 `spec` 导入旧输入，或 `action: "analyze"` 配合 `draft` 重新解析。下面从结果中取出完整草稿，生成面移动请求：

```sh
python3 - <<'PY'
import json
with open('editor-result.json', encoding='utf-8') as f:
    result = json.load(f)
request = {'action': 'apply', 'draft': result['draft'],
           'expected_fingerprint': result['fingerprint'],
           'command': {'type': 'move_faces', 'face_ids': ['F01'], 'delta': 0.05, 'scope': 'selected'}}
with open('editor-change.json', 'w', encoding='utf-8') as f:
    json.dump(request, f, ensure_ascii=False)
PY
python3 atlas_cli.py editor editor-change.json > editor-changed.json
```

`draft` 字段接收对象，不能填文件路径。保存改后草稿的导出请求：

```sh
python3 -c "import json; r=json.load(open('editor-changed.json',encoding='utf-8')); json.dump({'draft':r['draft']},open('editor-export.json','w',encoding='utf-8'),ensure_ascii=False)"
python3 atlas_cli.py editor-export editor-export.json --out atlas-runs
```

`review-export request.json` 接受 `draft` 与可选 `annotations`；`review-check request.json` 接受 `packet`、`response`、`current_fingerprint` 和可选 `selected_ids`。二者只返回 JSON，不联系远程服务，也不执行建议。

HTTP 对应 `/api/editor`、`/api/editor-export`、`/api/review-export`、`/api/review-check` 和 `/api/photo-annotations`，复用相同服务参数。UI 另用 `POST /api/save-document` 保存文档，参数为 `kind`（`draft`、`annotations`、`review` 或 `prompt`）与 `document`，返回本地 `path`、可下载 `url`、`sha256` 和字节数。该保存辅助接口不新增公共 MCP 工具，MCP 仍为 14 个。本机客户端应使用 `/api/config` 返回的令牌并遵守同源限制。所有这些保存操作只写本机目录，不自动上传。

开发版提供 14 个 MCP 工具：

|用途|工具|
|---|---|
|编辑与另存|`atlas_editor`、`atlas_editor_export`|
|复核与手绘证据|`atlas_review_export`、`atlas_review_check`、`atlas_photo_annotations`|
|照片候选与配准|`atlas_from_photos`、`atlas_fit`、`atlas_photo_align`|
|原有构形与检查|`atlas_build`、`atlas_validate`、`atlas_doctor`|
|本地图像辅助|`atlas_inspect_image`、`atlas_ocr`、`atlas_vision`|

最后两项 OCR/视觉工具仍依赖用户已安装的本机组件；编辑、参数解析与复核协议不需要这些组件。输入结构见[编辑器 schema](../schema/editor.schema.json)、[照片标注 schema](../schema/photo-annotation.schema.json)、[复核 schema](../schema/review.schema.json)。

<a id="english"></a>

## English guide

This guide describes **v1.1.0-dev.4** on `main`; the latest tagged release and archives remain **v1.0.1**. See the [four-workspace guide](layout-guide.md#english) for the current layout. Start `python3 atlas_cli.py serve --open`, then choose **轻松建模** or open `/editor.html` at the printed loopback address. Editing uses the local Python service; exported previews work without it.

Create one of the seven presets listed above, load a reference case, or open a v1 input/v2 draft JSON. Front, side and top views share face selection with the 3D preview; selecting a face keeps the camera still. Move a single face, a recorded module, or a parallel opposite pair; change proportions, add a cutting plane, and inspect the result with undo/redo and the before overlay. Free rotation is optional. Invalid operations retain the last valid model. The editor handles convex bodies with positive plane support distances, not nonconvex sculpting or curved CAD.

**定义轴 · 保持外形** redefines reference axes without changing the shape. **按原指数和新轴重建外形** rebuilds the shape using existing recorded indices and a new basis; it requires an index for every face. Axis presets, two-vertex direction picking, face normals and a selected reference origin are available. Basis columns are the independent axes. Reference coordinates do not establish measured cell parameters.

Analysis includes area, volume, edge length, adjacency, dihedral angles and low-order index candidates with angular errors. Compatible geometric groups are tested in the current reference frame only. Zone candidates report shared normal constraints. Neither result determines physical crystallography; missing or ambiguous indices remain unresolved.

On a photograph, draw edges, a closed silhouette, face regions, occlusions or uncertain lines. Finish the feature, then drag its nodes, reclassify it or update/clear its model-face association. Each associated feature carries its own model fingerprint. A changed model requires reconfirming each association, even when a face keeps the same ID. Manual silhouettes and reliable edges enter local candidate fitting; face regions provide reviewable constraints. See [photo correction](photo-correction-guide.md#english) for current-model alignment and face correspondence. Save correction JSON separately and reload it after loading the matching source photographs.

The editor's draft, correction, review and prompt buttons first write a file into the workbench output directory, then show a download link and local path. Choose the directory with `serve --out atlas-runs`; the default is `atlas-runs/`. Names include a content hash, such as `draft-<hash>.json` or `prompt-<hash>.txt`. Identical content reuses its file; changed content is saved separately, without overwriting different content at an existing name. The saved status confirms local persistence, not a completed browser download. You can copy the file from the displayed path to someone else; correction JSON requires the matching source photographs separately.

Save the draft JSON for continued editing, or export `result.zip` for offline viewing and parameter inspection. A review packet contains geometry, manual annotations and the shared prompt, with no source images or automatic upload. Import a structured reply, inspect its evidence and explicitly select suggestions. Stale identities, unknown faces and invalid commands are rejected; accepted operations run through the same local core. No real cloud vision service was tested in this iteration.

The CLI JSON examples and the 14-tool MCP table above apply to both languages. `editor` returns a draft, model, analysis and fingerprint; `editor-export` writes an offline bundle. `review-export` and `review-check` exchange local JSON only. The UI also uses `POST /api/save-document` with `kind` and `document` to persist files, receiving `path`, `url`, `sha256` and byte count. This private UI helper does not add a public MCP tool. HTTP clients use the matching `/api/` routes and the loopback token from `/api/config`.

The final automatic rankings on the 68 previously seen development photographs are unchanged from the baseline. Corner refinement and stronger automatic edge scoring remain diagnostic suggestions because some old cases regressed. See [measured results and limits](recognition-improvements-2026-10-02.md) and [historical dataset boundaries](photo-evidence-series.md). These results do not establish improved unseen-object or cloud recognition accuracy.
