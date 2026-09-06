# 牛来：代码包运行说明

本包是 2026-09-06 本地工作区快照，可运行笔记本后端排练页、模拟流程与软件测试。它不包含真实密钥、运行数据库、个人语音数据集、固件镜像或完整小智上游构建树。

## 先运行网页排练（无需云密钥和硬件）

准备 Python 3.13，在解压目录打开 PowerShell：

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r brain/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn brain.app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
~~~

浏览器打开 http://127.0.0.1:8000/ 或 http://127.0.0.1:8000/life 。先在排练页尝试状态切换与模拟互动；页面结果是软件模拟，不代表实机运动或说话。终端 Ctrl+C 停止服务。若端口占用，将命令和浏览器地址的 8000 同时改为 8001。

没有模型密钥时使用既有规则/文字回退，不会变成离线大模型。无需安装 Lua，当前动作脚本是 Python 受限解析器。

## 运行现有测试

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q brain/tests
~~~

本轮原工作区：181 passed，0 failed/error/skipped，1 个弃用警告，14.41 秒。日志位于 outputs/submission-2026-09-06/pytest.txt，元数据在同目录。真实编译器检查需要支持 C++17 的 GCC 兼容 CXX，缺少时相关测试会跳过，应如实记录，不能照抄本机通过数。

本轮用现有 Python 3.13.12 环境验证，未重新安装依赖。本机 uvicorn 0.32.1 与 requirements 的 0.40.0 不同，因此未验证全新依赖安装；其他列出的基础依赖版本一致。

## 若要连接真实板子

1. 配置音频用 FFmpeg（须有 libopus，能从 PATH 找到）。
2. 基础 requirements 未列 WebSocket 运行时，可另安装匹配版本：.\.venv\Scripts\python.exe -m pip install "uvicorn[standard]==0.40.0"。
3. 从 .env.example 复制为本机 .env，填写独立设备密钥 NIULAI_DEVICE_TOKEN；若使用 IM，另设独立 NIULAI_IM_TOKEN。实际语音识别需要云服务配置（如 DASHSCOPE_API_KEY）；模型参数参照示例。不要将真实 .env 发给评委或写进录像。
4. 在受控局域网运行 .\.venv\Scripts\python.exe -m brain.app，默认监听 0.0.0.0:8000；板端地址设为本机局域网地址加 /xiaozhi/v1/，并提供设备 Bearer。当前使用 ws://，没有局域网 TLS。
5. 本包没有完整可复建固件：firmware/xiaozhi-niulai/ 是公开 overlay 和增量补丁，依赖本队已修改的小智 native 基线。其 README 中旧的“未烧录/仅监听本机”段落是历史状态，最新构建与验收边界见 build-evidence.md 和根目录提交说明。不要直接将这些补丁当成对全新上游的一键安装包。

最新项目记录已有 BOOT 问答与一次关键词唤醒后问答正例，用户确认听到回答；重复可靠性、舵机停止时延和连续运行仍待验收。代码包内没有执行烧录、操作实物或上传数据的自动步骤。

## 材料位置

- 根目录“牛来机器人-Submission-2026-09-06.md”：项目说明、分工、架构图、接线、2 分 45 秒视频脚本、安全与隐私。
- outputs/submission-2026-09-06/测试记录.csv：待填实机记录表，NOT_RUN 行不计入成功率。
- outputs/niulai-dialogue-check-2026-09-06/result.json：历史合成输入语音链路样本，不是真机录像。
- PACKAGE-MANIFEST.sha256：包内源文件校验清单；提交目录的 SHA256SUMS.txt：最终 ZIP 校验值。

旧记录引用的 .scratch/、.grok-loop/ 和本机绝对路径不随包提供，属于历史证据位置。固件及语音资源沿用项目现有来源；打包不新增第三方代码或素材的授权声明。

隔离代码包启动检查：3/3 HTTP 请求通过，见 outputs/submission-2026-09-06/package-smoke.json。代码包不含 ≤3 分钟实机录像，视频由用户自行准备，逐次测试表待实测填写；赛事平台提交另行进行。
