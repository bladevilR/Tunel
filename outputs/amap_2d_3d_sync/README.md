# 高德 2D/3D 框线同源校准

这个版本用于解决“2D 框线准、3D 出图漂”的问题。

## 核心做法

- `geometry.js` 是唯一几何来源，红线、地下轮廓、通道、站体、1 号口、拟建体块都从这里读。
- 左侧 `map2d` 是高德 2D 正视图，用于校准红线与河道、道路、站口的关系。
- 右侧 `map3d` 是高德 3D 环境图，使用同一份经纬度生成 AMap 矢量框线和 Canvas 轻 3D 覆盖层。
- 两个地图会同步中心和缩放；3D 保留 pitch/rotation 用于出图。
- 用户可在 2D 地图上手动画红线、地下轮廓、通道线、建筑、站体和 1 号口。
- `保存草图` 会写入 `user_geometry.json`；`导出PNG` 会保存当前草图并生成 3D 截图到 `exports/`。

## 启动

```powershell
$env:AMAP_JS_KEY='你的高德JS Key'
$env:AMAP_SECURITY_CODE='你的安全密钥'
cd E:\ai\苏州轨道交通站点周边互联互通智能体开发工作提资\outputs\amap_2d_3d_sync
.\run_amap_sync.ps1
```

打开：

```text
http://127.0.0.1:8898/index.html
```

## 验收

静态验收不需要高德 Key：

```powershell
node .\verify_sync_static.cjs
```

浏览器验收需要先启动本地服务：

```powershell
$env:NODE_PATH='C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
node .\verify_amap_sync.cjs
```

导出验收：

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8898/api/export-png' -Method Post
```
