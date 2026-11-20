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

## 环境准备

本机需要 Git 以外的常规开发工具即可，源码已包含在包内，无需拉取仓库。完整启动需要 Docker 与 Compose v2。手动开发需要 Python 3.13+、uv、Node.js 24+ 和各 `package.json` 中指定的 pnpm 版本。后端与沙箱 Python 的版本要求不同，请以各自配置为准。

推荐至少预留 8 GB 给后端容器，并为浏览器、数据库及沙箱另留余量；镜像和科学计算依赖首次下载较大。不要把源码目录放进自动同步 node_modules 的网盘。

## 一条本地部署路径

以下命令在项目根目录执行。

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
cd web
pnpm typecheck
pnpm build
pnpm test
```

这些命令的全量运行可能需要较多内存和时间。真实 API、数据库和沙箱集成属于独立验证层，不能用单元测试替代。具体交付验证范围见 `VALIDATION.md`。

## 优先改造方向

先完成单市场、单公司、只读研究闭环，再补研究假设的版本历史、证据有效期、指标口径与对照评估。若加入真实交易，须单独测试权限变更、审批绑定、失败恢复和券商对账，不能把研究 Agent 的提示词当作交易授权。

本项目需要持久化后端和执行环境。Supabase 可承担 PostgreSQL 和认证等部分能力，Vercel 可用于适配后的前端托管；后台执行、Redis 和 Docker 沙箱仍需要独立服务。

## 整理说明

已清理项目宣传、原站点与仓库入口、作者联系方式、展示截图和历史版本控制数据，并对显示名及内部标识统一整理。修改文件清单见 `MODIFICATIONS.md`。依法需要保留的许可证、版权与第三方声明保持原文；依赖下载地址、数据服务端点和必要第三方许可链接用于运行或合规，并非原项目宣传入口。
