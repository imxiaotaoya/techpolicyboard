# TechPolicyBoard — 科技政策综合看板

面向政府科技部门（科委、发改委、工信部）和金融市场研究员的交互式综合看板。**5 分钟内理解一个前沿技术的全貌** —— 将"具身智能""脑机接口""量子计算""核聚变"等政策热词与具体技术、产业实体和市场资本数据关联起来。

## 四大模块

| 模块 | 功能 |
|---|---|
| **技术探索器** | 交互式技术图解，悬停展开子技术，点击查看能力边界和近期成果 |
| **政策追踪** | 按技术领域过滤的政策看板 + 四阶段创新看板 + 同类政策推荐 |
| **产业链** | 区域产业地图，点击城市节点查看产业禀赋、政策和应用场景 |
| **市场趋势** | 一级市场动态滚动 Feed + 政策-市场反应延迟分析 + 产业链热力图 |

## 技术栈

**前端**：React 19 + TypeScript + Vite + Tailwind CSS 4 + Motion

**后端**：Python FastAPI + SQLite + APScheduler + httpx

**数据**：SQLite 数据库 + 多源政策抓取管道 + 一级市场动态采集

## 快速开始

### 1. 安装依赖

```bash
# 前端
cd frontend && npm install

# 后端
cd backend && pip install -r requirements.txt
```

### 2. 配置

```bash
# 后端环境变量（可选）
cp backend/.env.example backend/.env

# LLM Agent（可选）
cp frontend/.env.example frontend/.env.local
```

### 3. 初始化数据库

```bash
cd backend
python3 seed_policies.py     # 手工策展数据 → SQLite
python3 seed_external.py     # 外部数据集导入（AI Legislation Tracker）
python3 tag_policies.py      # 自动标注政策的关联技术和产业
```

### 4. 启动

```bash
# 终端 1：后端（端口 8000）
cd backend && uvicorn main:app --reload --port 8000

# 终端 2：前端（端口 3000）
cd frontend && npm run dev
```

浏览器打开 `http://localhost:3000`

## 数据管道

### 政策采集

| 来源 | 覆盖 | 频率 |
|---|---|---|
| US Federal Register | 总统行政令、联邦机构法规 | 每 24h |
| US Congress (Congress.gov) | 国会法案、修正案 | 每 24h |
| EU EUR-Lex | 欧盟法规、指令、决定 | 每 48h |
| RSS 多源订阅 | Federal Register / EU Parliament / NIST / 科技部等 13 个源 | 每 12h |
| 搜索引擎发现 | DuckDuckGo 搜索权威域名 | 每 24h |
| 外部数据集 | AI Legislation Tracker（28 条全球 AI 法律） | 手动 |

### 一级市场动态

| 来源 | 内容 |
|---|---|
| TechCrunch / VentureBeat / Sifted / 36Kr RSS | 科技融资新闻 |
| SEC EDGAR Form D | 美国 VC 融资备案 |
| 36Kr / IT桔子 | 中国一级市场 |

每条动态通过 `tech_mapper` 引擎自动关联到系统内的 4 大技术领域和 6 个产业方向。

### 技术-产业映射

150+ 关键词映射引擎，自动将政策文本和融资新闻归类到：

| 技术领域 | 产业方向 |
|---|---|
| 具身智能 (embodied-ai) | 人形机器人 |
| 脑机接口 (bci) | 神经假肢/BCI医疗 |
| 量子计算 (quantum) | 量子计算产业链 |
| 核聚变 (fusion) | 聚变能源产业链 |
| | 算力网 |
| | 生物医药 |

### 同类政策推荐

多因子加权相似度：技术标签重叠（35%）+ 产业标签重叠（25%）+ 部门匹配（15%）+ 层级匹配（10%）+ 国别匹配（10%）+ 创新阶段邻近（5%）。不依赖向量数据库。

## API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/policies` | 政策列表（分页、技术/产业/国家/部门过滤、排序） |
| GET | `/api/policies/{id}` | 单条政策 |
| GET | `/api/policies/{id}/similar` | 同类政策推荐（含匹配度） |
| GET | `/api/policies/{id}/trail` | 数据来源追溯链 |
| GET | `/api/market-events` | 一级市场动态（按技术/产业过滤） |
| GET | `/api/market-events/stats` | 融资统计（按技术/产业/事件类型） |
| POST | `/api/market-events/fetch` | 手动触发市场数据采集 |
| POST | `/api/scrape/{source}/trigger` | 手动触发政策抓取 |
| GET | `/api/scrape/sources` | 数据源状态 |
| GET | `/api/scrape/logs` | 抓取日志 |
| GET | `/api/health` | 健康检查 |
| GET | `/docs` | Swagger API 文档 |

## LLM Agent

底部输入框支持 LLM 动态生成看板数据。⚙️ 配置支持：

- OpenAI / DeepSeek / 智谱 GLM / 通义千问 / Ollama
- 通过 FastAPI 代理绕过 CORS
- 5 组预制演示数据（无需 API Key）

## 项目结构

```
├── frontend/                          # React 前端
│   └── src/
│       ├── App.tsx                    # 主应用
│       ├── constants.ts               # 数据 + 派生函数
│       ├── types.ts                   # TypeScript 类型
│       ├── hooks/                     # usePolicies / useMarketEvents / useSimilarPolicies
│       ├── components/                # 四大模块 + Settings + AgentStatusBar
│       └── lib/                       # LLM 客户端 / 演示预设
├── backend/                           # FastAPI 后端
│   ├── main.py                        # 入口（lifespan + CORS + 路由）
│   ├── config.py                      # 环境变量配置
│   ├── database.py                    # SQLite CRUD
│   ├── data.py                        # 数据访问层（DB 优先，JSON 降级）
│   ├── scheduler.py                   # APScheduler 定时调度
│   ├── models.py                      # Pydantic 模型
│   ├── similarity.py                  # 相似度算法
│   ├── routers/                       # API 路由（tech/policy/industry/llm/scrape/market）
│   ├── scrapers/                      # 数据采集
│   │   ├── base.py                    # 抽象基类
│   │   ├── us_federal_register.py     # US Federal Register API
│   │   ├── us_congress.py             # US Congress.gov API
│   │   ├── eu_eurlex.py               # EU EUR-Lex SPARQL
│   │   ├── rss_feeds.py               # RSS 多源订阅（13 源）
│   │   ├── search_discovery.py        # 搜索引擎发现 + 来源核查
│   │   ├── market_events.py           # 一级市场动态
│   │   ├── tech_mapper.py             # 技术-产业关键词映射
│   │   └── cleaner.py                 # 数据清洗去重管道
│   ├── seed_policies.py               # JSON → SQLite
│   ├── seed_external.py               # 外部数据集导入
│   ├── tag_policies.py                # 自动标注政策关联
│   └── data/                          # JSON 数据文件
├── SPEC.md                            # 产品规格文档
└── PLAN.md                            # 实现计划
```
