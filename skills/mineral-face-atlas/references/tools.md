# 运行与数据接口

## 三个入口，同一核心

1. 本机界面：完整软件目录内运行`python3 atlas_cli.py serve --open`。选择案例或导入JSON，编辑指数与支持距离，生成后直接查面。原图面号不能确认时先记录未知。
2. CLI：skill目录内`python3 scripts/atlas.py build input.json --out results`。输出为内容寻址目录；相同输入和程序指纹复用完整性检查通过的缓存。不会覆盖已存在但损坏的结果。
3. MCP：`atlas_build(spec)`、`atlas_validate(model)`、`atlas_fit(spec,annotation,image?)`、`atlas_doctor()`、`atlas_inspect_image(image)`、`atlas_ocr(image,language?)`、`atlas_vision(image,model_name)`。图像为PNG/JPEG data URL，最大16MiB。核心工具不调用外网。

如果MCP未连接，用CLI继续；若连Python也没有，可按参考文档完成证据表与参数草案，并明确没有执行几何校验。不要谎称已生成或已验证模型。

## 最小参数例子

```json
{
  "schema_version": 1,
  "id": "cube",
  "title": "立方体参考构形",
  "crystal_system": "等轴",
  "point_group": "m-3m",
  "index_count": 3,
  "basis": [[0,1,0],[0,0,1],[1,0,0]],
  "expected_faces": 6,
  "forms": [{"hkl":[1,0,0],"distance":1}],
  "metadata": {
    "axis_choice":"三条互相垂直的四次轴为a、b、c。",
    "basis_note":"轴比与支持距离为理想示例，非照片测量。"
  },
  "evidence": [{"type":"assumption","status":"assumed","source":"教学参考构形"}]
}
```

`forms`按点群展开。`faces`是显式单面列表，每项可设`id`、`hkl`、`distance`、`expand:false`、`photo_label`、`label`、`evidence`。使用一种列表，不在两者重复定义。ID应为唯一F01形式；模型ID用字母、数字、横线或下划线。

距离是**单位法线**到原点的支持距离，不是未归一化平面方程右端。正面距意味着O在内部；整体乘同一距离因子只改变尺度。指数仅按形态方向约去公因子，不据此合并衍射反射。

四轴：`index_count:4`，示例基底`[[-0.5,1,0],[0,0,2],[0.8660254037844386,0,0]]`，列为a₁、a₂、c。`[1,0,-1,0]`为柱面方向；轴比c/a=2是这里的假设。

机器schema位于完整软件`schema/project.schema.json`；执行期还检查四指数求和、度量、点群、闭合和面数等JSON Schema无法表达的约束。

## 可用点群及设置

支持32类的生成操作：1、−1、2、m、2/m、222、mm2、mmm、4、−4、4/m、422、4mm、−42m、4/mmm、3、−3、32、3m、−3m、6、−6、6/m、622、6mm、−6m2、6/mmm、23、m−3、432、−43m、m−3m。

这不是“32类全部经过实物验证”。单斜唯一轴b；其他非等轴高阶轴c。程序把第二独立轴投影到水平正向，c直立。在三方/六方只接受六方四轴设置；不自动把菱方原胞三指数混进来。其他设置（例如−62m）需明确转换基底/指标后使用，不能只改文本群名。

## 可选工具

- NumPy/SciPy：原始像素相机拟合；无它们核心仍运行。
- Pillow：尺寸、EXIF方向和格式检查；不据此猜镜像或实物轴向。
- Tesseract：可见文字候选与框。负号、上划线、手写红字必须复核；缺语言包如实报错。
- Ollama：用户已有的本机视觉模型，固定127.0.0.1:11434；固定seed与temperature仅减少随机性，不保证语义判读跨硬件相同。候选观察绝不自动应用到模型。没有服务/模型时不自动下载。

图像处理工具是辅助观察。没有一个工具能够从缺少标定的单张照片唯一求出真实晶面指数。
