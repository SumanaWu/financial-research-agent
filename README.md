# 金融研究 Agent 工作台

这是用于二次开发的金融研究工作台，展示名称为 FinWorkbench。它把市场资料检索、金融数据处理、沙箱代码执行、子 Agent 分工、跨会话研究记忆和报告交付放在同一套 Web 应用中。当前源码快照整理于 2026 年 11 月 17 日。

建议先阅读随包的项目深度介绍文档，再从 `src/ptc_agent/agent/agent.py` 进入执行核心。本包是完整应用源码，包含前端、后端、MCP 插件、数据协议库、图表库、迁移、测试、CLI、桌面壳和机器连接助手。依赖目录、运行数据与密钥不随包分发。

## 推荐演示业务

为一家公司建立研究 Workspace，拆分行业研究、财务数据整理、估值建模和报告生成任务；保存数据、假设与计算脚本，在新一轮财报到来时更新报告，并展示历史结论变化。个人项目优先做研究与模拟评估，真实交易连接属于需要单独接入和验证的扩展。

## 技术与模块

- 后端：Python 3.13 及以上、FastAPI、LangChain create_agent、LangGraph 持久化、DeepAgents 部分中间件。
- 前端：React 19、Vite、TypeScript、Tailwind、React Query、REST、SSE。
- 数据：PostgreSQL、psycopg 异步连接池、Redis；应用业务数据与 checkpoint 使用分开的连接池。
- 执行：Docker、Daytona、E2B、SSH；本地开发推荐 Docker。
- 金融工具：MCP、Yahoo Finance、FMP、SEC 资料、行情与宏观插件；部分接口需要额外账号或套餐。
- 产物：Python 数据分析、chartkit 图表、研究与文档 Skills、工作区文件。

## 第一阶段优化总结

第一阶段已完成 Mac 本地的单公司 SEC 研究闭环：通过已配置的 DeepSeek，从表单提交公司和截止日，经取数、计算和分析复核，交付带来源的 HTML 报告与 Excel 工作簿。实施与验收记录截至 2026 年 11 月 22 日。

| 方向 | 已完成的能力与修复 |
| --- | --- |
| 公司研究入口 | 支持 ticker／CIK 核对、研究截止日、SEC 请求身份和可选重点；创建专用研究线程，运行 `company-research-v1` 的取数计算、复核交付两阶段流程。 |
| 历史证据与范围 | 保存 SEC 原始申报与数据快照，按申报接受时间筛选证据，排除截止日之后的资料和修订；区分独立季度与累计期间。后端固定研究范围，修复截止时间的时区、精度和比较问题。 |
| 财务计算与校验 | 确定性计算收入增长、自由现金流、净利率、资产负债率及现金流转化率；检查缺失值、币种、资产负债表关系、来源引用和文件哈希。研究工具范围收敛，减少引入当前行情或外部写入操作。 |
| 报告与工作簿 | 生成包含业务、趋势、风险、缺口及来源的报告；标题显示公司名，叙述引用可点击 SEC 来源。工作簿首页通过公式关联核心指标，Checks 汇总失败和缺失项，改善打印分页与长来源文字显示；支持文字更新时保留已复核工作簿。 |
| 研究交互 | 表单改为独立弹窗，结果放入消息滚动区；公司研究与任务入口统一样式和固定顺序，复用收起交互。修复内容遮挡及滚动补偿冲突，并为重新校验增加加载、完成和失败反馈。 |
| 工作流兼容 | 修复空 `focus` 在工作流引擎中的序列化错误，CLI 兼容 `null` 并规范化为空字符串；保留原有运行、取消、历史与收尾机制。 |
| Mac 使用流程 | 提供稳定研究模式的启动、检查和停止命令，关闭后端热重载，避免编辑代码时打断研究；前端更新、后端重启、数据复算及故障排查步骤统一在本 README。 |

已验证 DeepSeek 实际调用、代码执行与文件保存、AAPL／MSFT 的 SEC 取数，以及 AAPL 从模型到报告交付的完整链路。选定研究测试 22 项、工作流引擎测试 21 项通过；前端类型检查、生产构建与首屏体积检查通过，多 worker 的启动互斥、取消和请求去重选定检查通过。最新 Apple 工作簿 42 个公式重算无错误、严格审计无发现，8 项明细检查和总检查均为 OK，交付文件哈希匹配。详细记录见 [VALIDATION.md](VALIDATION.md)；这些结果不代表全仓库全量测试或完整故障矩阵已通过。

当前边界：尚未接入可验证历史时点的行情与估值数据，因此报告通常显示“部分完成”，应同时查看具体缺口和校验错误；季度覆盖目前以最近一份合格 10-Q 的可验证字段为主，不保证完整季度趋势。自定义 XBRL 标签和历史资料覆盖仍可能不足，来源 ID 可定位也不等于叙述已获充分支持，分析结论仍需复核。第一阶段完成不代表上述数据能力已经补齐。

## 环境准备

本机需要 Git 以外的常规开发工具即可，源码已包含在包内，无需拉取仓库。完整启动需要 Docker 与 Compose v2。手动开发需要 Python 3.13+、uv、Node.js 24+ 和各 `package.json` 中指定的 pnpm 版本。后端与沙箱 Python 的版本要求不同，请以各自配置为准。

推荐至少预留 8 GB 给后端容器，并为浏览器、数据库及沙箱另留余量；镜像和科学计算依赖首次下载较大。不要把源码目录放进自动同步 node_modules 的网盘。

## 一条本地部署路径

以下命令在项目根目录执行。仅在没有 `.env` 时复制模板；已有配置请保留，不要覆盖。

```bash
cp .env.example .env
```

编辑 `.env`，本地单用户可使用下列设置。密码仅用于本机开发，外网部署须另行设置认证与密钥。

```dotenv
HOST_MODE=oss
AUTH_USER_ID=local-dev-user
VITE_HOST_MODE=oss
VITE_AUTH_USER_ID=local-dev-user
COMPOSE_PROFILES=infra
SANDBOX_PROVIDER=docker
DB_PASSWORD=replace-with-your-local-db-password
REDIS_PASSWORD=replace-with-your-local-redis-password
BYOK_ENCRYPTION_KEY=replace-with-a-long-random-secret
```

模型访问仍然是必要条件。选择一种方案：在 `.env` 中填写模型提供商 API key，再把 `agent_config.yaml` 的 `llm.name` 改成 `src/llms/manifest/models.json` 中存在且账号可用的模型；或在应用内配置支持的个人模型授权。默认模型名称只是配置值，不保证你的账号拥有访问权。搜索服务、FMP 与云沙箱的 key 按需配置。

使用免费行情时，在应用插件页面或配置中启用 Yahoo 对应工具。工具插件的声明在 `plugins/`，主配置 `mcp.servers` 允许按名称覆盖插件默认值；请核对实际启用的服务器，不能只填 key 而不启用工具。

```bash
make up PROVIDER=docker
```

前端默认端口 5173，后端默认端口 8000，后端健康检查路径 `/health`。数据库和 Redis 由 infra profile 启动。`make up` 会准备沙箱镜像并构建应用，首次启动需要联网下载依赖。若启动失败，先看 `docker compose logs backend` 和 `docker compose logs cli`，再检查模型、数据库、Redis 与 Docker socket。

```bash
docker compose ps
curl http://localhost:8000/health
```

停止服务使用 `docker compose down`；不要在需要保留研究数据时随意删除数据库卷。

### Mac 公司研究模式

已接通 DeepSeek 后，可以在 Terminal 中启动关闭后端热重载的本地研究模式：

```bash
cd ~/Desktop/financial-research-agent
open -a Docker
docker info
docker compose version
make research-up
docker compose ps
make research-check
curl http://localhost:8000/health
open http://localhost:5173
```

首次下载依赖可能较慢。若 `make` 不可用，可先运行 `xcode-select --install`。检查脚本不打印密钥；启动期间若显示 FAIL，等待初始化后重试。健康检查通过仅表示服务可访问，模型和研究流程仍需单独验证。确认 `.env` 的本地模式、Docker 沙箱和 DeepSeek 配置可用；`agent_config.yaml` 的模型名为 `llm.name`，不要重复嵌套 `llm`。

#### 验证聊天和公司研究

1. 在网页中选择或创建 Docker 计算机和工作区，新建普通对话，发送“只回答 OK，不调用工具”，确认 DeepSeek 能回复。再让它执行 `print(2 + 2)` 并保存测试文件，检查代码执行、文件面板和刷新后的历史记录。
2. 在工作区对话输入框附近点击“公司研究”。例如输入 `AAPL` 或 CIK `320193`，选择 `2024-12-31`，填写真实 SEC 请求身份（项目名和联系邮箱，可使用 `financial-research-agent sumanaocean@gmail.com`），按需填写研究重点。
3. 点击“核对公司”，确认 Apple 和 CIK `0000320193`，再点击“开始研究”。等待 `company-research-v1` 的取数和复核阶段及交付完成；主 Agent 回复结束不一定代表后台任务已结束。
4. 在研究结果区点击“重新校验”，并打开或下载报告与工作簿。公司或截止日改变时请创建新的研究线程；普通追问可复用原有快照。仅更新文字时，可更新 `analysis.json` 后运行 `company_research.cli render`，保留已复核的工作簿。

研究文件位于工作区 `research/<线程 ID>/`：`report.html` 和 `research.xlsx` 是报告与工作簿；`request.json` 保存研究范围；`sources.json` 和 `raw/` 保存 SEC 来源与原始材料；`observations.json`、`quarterly.json` 和 `metrics.json` 保存数据及计算结果；`analysis.json` 保存分析与引用；`validation.json` 和 `manifest.json` 用于校验；`calculate.py`、`research_core.py` 和 `requirements.txt` 可用于复算。

选取资料依据 SEC 接受时间，而非仅看报告期。历史行情和估值时点无法核实时会留作缺口，状态可能显示“部分完成”；这不等于研究运行失败，也不代表缺失数据已经补齐。交付状态与运行状态是两回事。

如需离线复算，先下载整个研究目录，在该目录的 Terminal 中执行以下命令，再将输出与 `metrics.json` 对照。复算不需要再次访问 SEC 或调用模型。

```bash
python3 -m venv .research-venv
source .research-venv/bin/activate
python -m pip install -r requirements.txt
python calculate.py
```

进一步验收时，可在运行中刷新页面、在独立测试线程中停止任务、用较早截止日检查资料缺口，并对 MSFT（CIK `789019`）创建另一份研究，确认目录隔离。校验截止时间、来源、计算和文件指纹时，不应通过改写状态或重新生成指纹掩盖内容错误。服务端结果也可通过 `GET /api/v1/threads/<线程 ID>/company-research` 查看。

关闭浏览器页面不会停止后台服务。停止本地研究服务时，在 Terminal 中执行：

```bash
cd ~/Desktop/financial-research-agent
make research-down
```

该命令保留数据库和 Redis 数据卷。不要使用 `docker compose down -v`，以免删除需要保留的数据。如果另行在 Terminal 中手动运行了前端 `pnpm dev` 或后端开发服务器，请回到对应窗口按 **Control + C** 停止。

#### 日常启动与代码更新

首次启动或镜像不存在时，使用上面的 `make research-up` 构建镜像。日常停止后，如果代码和依赖没有变化，可以使用已有镜像启动，跳过显式构建：

```bash
cd ~/Desktop/financial-research-agent
docker compose -f docker-compose.yml -f deploy/compose.research.yml up -d
make research-check
```

代码更新后，根据改动范围处理：

- **前端页面代码**：Vite 通常会自动更新，必要时刷新浏览器。
- **后端 Python 代码**：研究模式关闭了后端热重载，以免中断正在进行的研究。确认没有研究任务运行后，只重启后端：

  ```bash
  docker compose -f docker-compose.yml -f deploy/compose.research.yml restart backend
  make research-check
  ```

- **依赖、Dockerfile 或图表构建资源**：可能需要重新构建，在项目根目录执行 `make research-up`。构建期间如需重建服务，先确认没有正在运行的研究任务。

当前后端镜像构建会在安装依赖之前复制 `README.md`；修改该文件也可能使后续构建缓存失效，导致依赖和浏览器重新安装。

#### 日志与排查

```bash
docker compose logs --tail=100 backend
docker compose logs --tail=100 cli
docker compose logs --tail=100 frontend
```

聊天失败时检查模型配置；代码执行失败时检查 Docker 和计算机状态；SEC 取数失败时检查请求身份、网络和限流；报告校验失败时检查研究范围、来源、计算及 manifest。重启或进程恢复后，应检查任务记录，不能假定它会从任意代码行继续执行。

## 手动开发

数据库、Redis 与沙箱服务仍需可用。服务端在根目录运行：

```bash
uv sync --frozen --extra test --python 3.13
uv run python server.py --reload
```

前端与 CLI 分别在自己的目录安装依赖：

```bash
cd web
pnpm install --frozen-lockfile
pnpm dev
```

```bash
cd cli
pnpm install --frozen-lockfile
pnpm build
```

本地手动后端需把 `.env` 的数据库主机改成可达地址，不能使用只有 Compose 网络内可见的 postgres 主机名。前端开发代理默认指向后端 8000；跨主机部署时另外检查代理、CORS 与公开应用地址。

## 代码阅读顺序

1. `agent_config.yaml`、`config.yaml`：模型、沙箱、MCP、上下文与服务行为。
2. `src/ptc_agent/agent/agent.py`：工具集合、角色、中间件与 create_agent 装配。
3. `src/ptc_agent/core/tool_generator.py`：MCP Schema 生成 Python wrapper。
4. `src/ptc_agent/agent/tools/code_execution.py` 与 `core/sandbox/`：代码执行和 provider 抽象。
5. `src/ptc_agent/agent/subagents/` 与 `middleware/background_subagent/`：子任务编译、后台执行与回报。
6. `src/ptc_agent/agent/backends/langgraph_store.py`、`filesystem_routes.py`：用户与工作区记忆。
7. `src/ptc_agent/agent/middleware/compaction/`：上下文压缩、笔记与历史窗口。
8. `src/server/services/runs/`、`database/runs/`：运行账本、流式传输与恢复。
9. `web/src/pages/ChatAgent/`：消息流、任务卡片、文件与报告展示。

## 验证命令

```bash
uv run pytest tests/unit/ -q --tb=short
uv run pytest tests/research/ -q --confcutdir=tests/research
cd web
pnpm typecheck
pnpm exec vitest run src/pages/ChatAgent/components/__tests__/CompanyResearchForm.test.tsx src/locales/__tests__/keys.test.ts
pnpm build
pnpm test
```

这些命令的全量运行可能需要较多内存和时间。真实 API、数据库和沙箱集成属于独立验证层，不能用单元测试替代。具体交付验证范围见 `VALIDATION.md`。

## 优先改造方向

在第一阶段单公司研究闭环基础上，后续可补充历史行情与估值、季度覆盖、研究假设的版本历史、证据有效期、指标口径与对照评估。若加入真实交易，须单独测试权限变更、审批绑定、失败恢复和券商对账，不能把研究 Agent 的提示词当作交易授权。

本项目需要持久化后端和执行环境。Supabase 可承担 PostgreSQL 和认证等部分能力，Vercel 可用于适配后的前端托管；后台执行、Redis 和 Docker 沙箱仍需要独立服务。

## 整理说明

已清理项目宣传、原站点与仓库入口、作者联系方式、展示截图和历史版本控制数据，并对显示名及内部标识统一整理。修改文件清单见 `MODIFICATIONS.md`。依法需要保留的许可证、版权与第三方声明保持原文；依赖下载地址、数据服务端点和必要第三方许可链接用于运行或合规，并非原项目宣传入口。
