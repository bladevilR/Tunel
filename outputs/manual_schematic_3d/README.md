# 群力站通道示意图确定性渲染

这个目录是新分支的最小可行版本：不再继续微调 `outputs/amap_js_3d` 的 hardcoded 高德覆盖层，而是用固定标注数据生成可复查的示意图。

## 文件

- `annotations.json`：底图要素、红线、站体、1 号口、通道、拟建体块、文字标注。
- `index.html`：确定性 SVG 渲染页面。
- `render_manual_schematic.cjs`：生成 `annotations.js` 并导出 PNG。
- `verify_manual_schematic.cjs`：验收空间关系和导出文件。
- `manual_schematic_3d.png`：当前导出的示意图。

## 生成

```powershell
$env:NODE_PATH='C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
node .\render_manual_schematic.cjs
node .\verify_manual_schematic.cjs
```

## 当前设计口径

- 红线沿南侧河道转折，不再遮掉河道关系。
- 通道从群力站 1 号口出发，连接到拟建邻里中心。
- 拟建体块的底面完全位于地块红线内。
- 图面采用近似人工样图的 2.5D 效果，但所有几何来自 `annotations.json`，可继续逐点校准。
