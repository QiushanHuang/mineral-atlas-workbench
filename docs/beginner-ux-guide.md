# 轻松标照片与课堂演示 / Photo picking and teaching

[简体中文](#中文) · [English](#english)

本页对应 `main` 的软件 **v1.1.0-dev.4**、技能 **v2.1.0-dev.4**；最新正式下载包仍为v1.0.1。建模、参考轴和保存方式见[手动建模指南](manual-modeling-guide.md)。

<a id="中文"></a>

## 先画一条棱，再圈一个面

启动工作台后进入“轻松建模”，切换到“照片修正”工作区。第一次使用可以选择“试画合成示例”，也可以载入自己的照片；工具、完成按钮和绘制提示就在画布旁。

1. 选择“画棱线”，依次点击两端。指针靠近可拾取位置时会显示目标提示；核对后再点击，按 **Enter** 完成。
2. 选择“圈面”，沿可见边界依次放至少三个点，再完成标注。区域会闭合，不必重复放首点；拾取开启时也可点击首点完成闭合。
3. 需要调整时切到“修正”，拖动圆点。画错的点可退回，已完成的标注可撤销。

外轮廓是照片当前方向看到的物体边界，不包含全部晶棱。阴影、文字和遮挡边界应先核对；没有把握时使用“不确定线”或“遮挡区域”。

## 拾取范围与自由落点

首次使用默认开启“自动拾取”，范围为 **12 个屏幕像素（CSS px）**。在“拾取选项与辅助工具”中可选择 **6 / 12 / 20**，分别适合精细、标准和宽松拾取。范围按屏幕距离判断；保存的点仍使用原图显示坐标。

| 控制 | 作用 |
|---|---|
| 自动拾取 | 总开关；关闭后按指针位置自由落点 |
| 按住 Shift | 临时绕过拾取，松开后恢复原设置 |
| 已有标注端点 | 拾取手工标记的点，便于相邻线或面共用位置 |
| 线段中点 / 线段交点 | 可分别开启或关闭；复杂标注可能只提供部分交点 |
| 照片候选角点 | 独立开关；使用本机图像分析提供未经确认的落点建议 |
| 显示候选点 | 控制辅助点是否显示，不等于关闭拾取 |
| 局部放大镜 | 放大当前指针附近的照片，方便核对落点 |

照片候选角点可能来自文字、背景、阴影或遮挡，不会自动变成“真实晶体角点”。关掉“照片候选角点”后，手工标注端点等拾取仍可使用。如果候选位置不合适，按住 Shift，或直接关闭自动拾取。

“用原图坐标精确放点”可以输入 X、Y 像素；此入口使用填写的坐标，**不自动拾取**。坐标以 EXIF 转正后的照片显示方向为准，不能直接混用未转正图片的坐标。

## 画布快捷键

先点击照片画布取得焦点。输入框中的键盘编辑保持原有行为。

| 按键 | 操作 |
|---|---|
| Enter | 完成当前线或区域；线至少两点，区域至少三点 |
| Backspace | 退回正在绘制的最后一个点 |
| Esc | 取消本次未完成的绘制，保留已完成标注 |
| Ctrl+Z / ⌘Z | 有草稿点时先退一点；没有草稿点时撤销照片标注 |
| Ctrl+Shift+Z / ⌘Shift+Z | 重做已退回的草稿点或照片标注 |

画布旁也提供完成、退点和取消按钮。放大照片与启用局部放大镜只影响查看方式，不改变已保存坐标。

## 入门、学习和课堂演示

“入门练习”以画线、圈面和操作提示为主。“晶体学学习”展开参考轴与参数，方便沿着“观察外形 → 标棱和面 → 定义参考轴 → 查看指数候选”的顺序练习。“课堂演示”提供演示提示，教师可以切换为单个正面、侧面、顶面或三维预览，也可逐步显示面号和参考／候选指数。

这三种方式只调整呈现和提示，不修改模型、参考轴、已有标注或科学解释。图上的“参考”表示已有模型记录；“候选”表示当前参考轴下的解析建议；未知时保留未知。需要比较多个候选及角偏差时查看参数表，不能把显示出来的指数当作实物测定答案。

## 离线与接口范围

手工落点、端点拾取、中点和交点计算在浏览器本地进行。照片候选角点需要本机已有的可选图像依赖；缺少组件或未找到可信点时，界面说明原因，手工拾取仍可继续。工作台不会自动安装组件、下载模型或上传照片。

开发者入口为私有 HTTP `POST /api/photo-guides`，请求形如 `{"image":"<PNG/JPEG data URL 或 base64>"}`，调用 `atlas.photo_guides.photo_guides(image)`。返回原图字节指纹、EXIF 显示尺寸以及有限数量的点线建议，不检索模板、不拟合模型、不返回整张预览图。该入口未增加公共 MCP 工具，公共工具数仍为 14。

照片观察、用户确认与模型参考参数分别保留，使用候选点不会把它们自动认定为同一项证据。

<a id="english"></a>

## Draw an edge, then outline a face

This guide covers software **v1.1.0-dev.4** and skill **v2.1.0-dev.4** on `main`; the latest tagged release archives remain v1.0.1. Start the workbench, open **轻松建模**, and switch to **照片修正**. Use **试画合成示例** for a synthetic practice image, or select your own photograph. Drawing tools, completion controls and point-by-point hints sit next to the canvas.

Choose the edge tool, click two endpoints, and press **Enter**. To mark a face region, place at least three points along its visible boundary and finish; there is no need to repeat the first point. With snapping enabled, clicking the starting point can also close the region. Switch to endpoint editing to drag a saved point.

A silhouette describes the boundary seen from that photograph, not every crystal edge. Check whether a line comes from text, a shadow or an occlusion before treating it as an edge; retain uncertain observations as such.

## Snapping and precise placement

Snapping starts enabled with a **12 CSS-pixel** screen radius. The available radii are **6, 12 and 20**, for fine, standard and loose selection. Zoom affects what you see; saved points remain in the original displayed-image coordinates.

| Control | Behavior |
|---|---|
| Automatic picking | Main snapping switch; disable it for free placement |
| Hold Shift | Temporarily bypass snapping |
| Existing endpoints | Reuse positions from manually marked features |
| Segment midpoints / intersections | Independent optional targets; complex drawings may offer only a subset of intersections |
| Photograph corner suggestions | Separate switch for unconfirmed, locally detected image corners |
| Show suggested points | Display control; hiding points does not disable snapping |
| Local magnifier | Inspect the photograph around the pointer |

Detected corners may belong to text, background, shadows or occlusions. They do not become confirmed crystal vertices automatically. Turning off photograph suggestions preserves snapping to manual endpoints and other enabled manual targets.

For exact placement, enter X and Y under the coordinate controls. This path uses the entered values **without snapping**. Coordinates refer to the EXIF-oriented displayed image, not the unrotated encoded image.

## Canvas shortcuts

Click the photograph canvas first. Text inputs retain their ordinary editing behavior.

| Key | Action |
|---|---|
| Enter | Finish the current line or region; at least two or three points, respectively |
| Backspace | Remove the last unfinished point |
| Esc | Cancel the unfinished drawing, preserving completed annotations |
| Ctrl+Z / ⌘Z | Undo an unfinished point first; otherwise undo a photograph annotation |
| Ctrl+Shift+Z / ⌘Shift+Z | Redo an undone point or photograph annotation |

The nearby buttons provide the same finish, step-back and cancel actions. Photograph zoom and the magnifier do not alter saved coordinates.

## Beginner, study and classroom views

**入门练习** emphasizes drawing and contextual hints. **晶体学学习** expands reference-axis and parameter panels, supporting observation, annotation, axis definition and comparison of index candidates. **课堂演示** adds teaching guidance; a teacher can display one orthogonal view or the 3D preview, then reveal face IDs and reference or candidate indices gradually.

These modes change presentation only. Geometry, axes, annotations and interpretation remain unchanged. “Reference” identifies recorded model assignments; “candidate” identifies a conditional result under the current reference axes. Unknown indices stay unknown. Compare alternative candidates and angular deviations in the parameter table instead of treating an on-screen index as a measured answer.

## Offline behavior and interface scope

Manual placement and endpoint, midpoint and intersection snapping run locally in the browser. Photograph suggestions use existing optional local image dependencies. When a dependency is missing or no suitable point is found, the interface explains the limitation and manual picking remains available. No components or models are installed or downloaded automatically, and no photographs are uploaded.

The private HTTP endpoint `POST /api/photo-guides` accepts an `image` containing PNG/JPEG base64 data and calls `atlas.photo_guides.photo_guides(image)`. It returns the original-byte fingerprint, EXIF display dimensions and bounded point/segment suggestions. It performs no template search or model fitting and returns no full preview image. It does not add a public MCP tool; the public interface remains at 14 tools.

Photograph observations, user confirmation and model reference parameters remain distinct records. For modeling, reference axes and saving, see the [manual modeling guide](manual-modeling-guide.md#english).
