# 远端部署说明

## 启动

1. 将 `interconnect-agent-server-*.zip` 上传到 Windows 服务器。
2. 解压到任意目录，建议路径不要太深。
3. 双击 `start_server.bat`。
4. 在服务器本机打开 `http://127.0.0.1:8765/`，其他电脑访问 `http://服务器IP:8765/`。

默认监听 `0.0.0.0:8765`。如果远端电脑无法访问，请在 Windows 防火墙放行 TCP 8765。

## 可选配置

如需接入外部模型，将 `.env.example` 复制为 `.env`，填写：

```text
LLM_BASE_URL=...
LLM_API_KEY=...
LLM_MODEL=...
```

不配置模型时，系统仍可使用本地知识库和离线兜底研判；带模型配置时，模型主导研判会优先调用外部模型。

本交付包按当前打包要求已包含 `.env.local`。该文件内含模型访问密钥，请只在受控服务器和受控渠道分发。

## 修改端口

可在启动前设置环境变量：

```bat
set INTERCONNECT_PORT=9000
start_server.bat
```

也可编辑 `start_server.bat` 中的默认端口。

## 目录说明

- `backend/`：服务端 API。
- `frontend/`：前端页面。
- `data/`：规则、站点、项目、知识库数据。
- `exports/`：运行后生成的报告、快照和评分明细。
- `runtime/python/`：包内 Python 运行时。若构建包未包含该目录，启动脚本会使用系统 Python 并自动创建 `.venv`。

## 停止服务

在启动窗口按 `Ctrl+C`，或直接关闭窗口。
