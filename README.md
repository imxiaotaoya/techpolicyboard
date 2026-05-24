# TechPolicyBoard — 科技政策综合看板

面向政府科技部门（科委、发改委、工信部）和金融市场研究员的交互式综合看板。**5 分钟内理解一个前沿技术的全貌** —— 将"具身智能""脑机接口""量子计算"等政策热词与具体技术、产业实体和市场资本数据关联起来。

## 四大模块

| 模块 | 功能 |
|---|---|
| **技术探索器** | 交互式 SVG 技术图解，悬停展开子技术气泡，点击查看详情卡片 |
| **政策追踪** | 政策时间轴 + 四阶段创新看板（基础研究 → 应用研发 → 试点 → 产业化）+ 同类政策推荐 |
| **产业链** | 区域产业地图，点击城市节点查看产业禀赋、政策和应用场景 |
| **市场趋势** | 资金流热力图，识别过热/低估赛道 + 政策干预目标标记 |

## 技术栈

**前端**：React 19 + TypeScript + Vite + Tailwind CSS 4 + Motion (Framer Motion)

**后端**：Python FastAPI + SQLite + APScheduler + httpx

**数据**：SQLite 数据库 + 多源政策抓取管道

## 快速开始

### 1. 安装依赖

```bash
# 前端
cd frontend
npm install

# 后端
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# LLM Agent（可选）
cp frontend/.env.example frontend/.env.local

# 美国国会 API Key（可选，用于抓取 US Congress 数据）
export CONGRESS_API_KEY="your_api_key"
```

### 3. 初始化数据库

```bash
cd backend
python3 seed_policies.py   # 将手工策展的 JSON 数据导入 SQLite
```

### 4. 启动

```bash
# 终端 1：启动后端（端口 8000）
cd backend && uvicorn main:app --reload --port 8000

# 终端 2：启动前端（端口 3000）
cd frontend && npm run dev
```

浏览器打开 `http://localhost:3000`

## 政策数据管道

项目内置多源政策抓取系统，自动采集并结构化国内外政策文本。

### 数据源

| 来源 | 覆盖 | 更新频率 |
|---|---|---|
| **US Federal Register** | 美国总统行政令、联邦机构法规 | 每 24h |
| **US Congress (Congress.gov)** | 美国国会法案、修正案 | 每 24h |
| **EU EUR-Lex** | 欧盟法规、指令、决定 | 每 48h |
| **手工策展** | 中国科技政策（发改委/科技部/工信部） | 手动 |

### 手动触发抓取

```bash
# 触发 Federal Register 抓取（无需 API Key）
curl -X POST http://localhost:8000/api/scrape/us_federal_register/trigger

# 查看抓取日志
curl http://localhost:8000/api/scrape/logs

# 查看所有数据源状态
curl http://localhost:8000/api/scrape/sources
```

### API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/policies` | 政策列表（分页、过滤、排序） |
| GET | `/api/policies/{id}` | 单条政策详情 |
| GET | `/api/policies/{id}/similar` | 同类政策推荐（含匹配度） |
| POST | `/api/scrape/{source}/trigger` | 手动触发抓取 |
| GET | `/api/scrape/sources` | 数据源列表 |
| GET | `/api/scrape/logs` | 抓取日志 |
| GET | `/api/health` | 健康检查 |
| GET | `/docs` | Swagger API 文档 |

### 同类政策推荐

基于多因子加权相似度算法：技术标签重叠（35%）+ 产业标签重叠（25%）+ 部门匹配（15%）+ 层级匹配（10%）+ 国别匹配（10%）+ 创新阶段邻近（5%）。不依赖向量数据库或嵌入模型。

## LLM 代理集成

底部 Agent 输入框支持通过 LLM 动态生成数据来替换看板静态数据。点击 ⚙ 齿轮图标可配置：

- OpenAI / DeepSeek / 智谱 GLM / 通义千问 / Ollama 本地模型
- API Key + Base URL + 模型名
- 代理模式切换（通过 FastAPI 后端代理 vs 浏览器直连）

也可一键加载 5 组预制演示数据，无需调用任何 LLM。

## 项目结构

```
├── frontend/                    # React 前端
│   └── src/
│       ├── App.tsx              # 主应用（模块路由 + 状态管理）
│       ├── constants.ts         # 硬编码数据 + 派生函数
│       ├── hooks/               # usePolicies / useSimilarPolicies
│       └── components/          # 四大模块组件 + Agent 组件
├── backend/                     # FastAPI 后端
│   ├── main.py                  # 入口（CORS + lifespan + 路由注册）
│   ├── database.py              # SQLite 连接管理 + CRUD
│   ├── data.py                  # 数据访问层（SQLite 优先，JSON 降级）
│   ├── scheduler.py             # APScheduler 定时任务
│   ├── models.py                # Pydantic 响应模型
│   ├── similarity.py            # 多因子加权相似度算法
│   ├── policy_schema.sql        # SQLite schema
│   ├── seed_policies.py         # JSON → SQLite 数据迁移脚本
│   ├── routers/                 # 技术/政策/产业/LLM/抓取 路由
│   ├── scrapers/                # 政策抓取器
│   │   ├── base.py              # 抽象基类 + 工具函数
│   │   ├── us_federal_register.py  # US Federal Register
│   │   ├── us_congress.py       # US Congress.gov
│   │   └── eu_eurlex.py         # EU EUR-Lex SPARQL
│   └── data/                    # JSON 数据 + SQLite 数据库
├── SPEC.md                      # 完整产品规格文档
└── PLAN.md                      # 实现计划
```
