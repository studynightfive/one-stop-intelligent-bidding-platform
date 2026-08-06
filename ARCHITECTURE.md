# 一站式智能招投标平台 — 架构设计文档

> 版本：v2.0
> 日期：2026-08-05
> 编写：高见远（首席架构师）
> 审核：大湾区靓仔（项目总监）

---

## 0. 版本变更

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-08-04 | 初始版本，做标书8Agent系统 |
| v2.0 | 2026-08-05 | 系统改名；新增评标Agent系统（5个）；新增供应商门户架构；新增评标数据库表（8张）；更新API清单（新增30+端点）；更新成本估算；新增ADR-008~011 |

---

## 1. 架构总览

### 1.1 双业务线架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                     一站式智能招投标平台                               │
│                                                                     │
│  ┌─────────────────────────┐  ┌─────────────────────────────────┐  │
│  │     做标书 (Bid)         │  │       评标书 (Evaluation)        │  │
│  │  7步闭环: 上传→解析→     │  │  6步闭环: 发布→提交→审核→       │  │
│  │  清单→模板→上传→审核→    │  │  评审→公示→关闭                 │  │
│  │  输出                    │  │                                 │  │
│  │  8 Agents                │  │  5 Agents + 供应商门户           │  │
│  └─────────────┬───────────┘  └──────────────┬──────────────────┘  │
│                │                              │                     │
│                └──────────┬───────────────────┘                     │
│                           ▼                                         │
│              共享层: 资质库 / 文档片段库 / 用户权限 / 通知 / 留痕      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    表现层 (Presentation)                      │
│  React 18 + TypeScript + Ant Design 5 + Tailwind CSS       │
│  Lucide React (锁定图标库)                                    │
│  做标书页面 + 评标书页面 + 供应商门户 + 管理后台               │
│  双模式切换导航 (做标书/评标书)                                │
├─────────────────────────────────────────────────────────────┤
│                    API层 (API Gateway)                       │
│  FastAPI + Pydantic + JWT Auth + RBAC + Tenant Middleware  │
│  RESTful API /api/v1/                                       │
│  供应商门户独立认证 (Portal Token)                            │
├─────────────────────────────────────────────────────────────┤
│                    业务层 (Business Services)                 │
│  做标书: TaskService / MaterialService / ReviewService /    │
│          DocumentService / VersionService                   │
│  评标书: EvalTaskService / SupplierService / ScoringService │
│          / BiddingService / AuditTrailService               │
│  共享:   QualificationService / FragmentService /           │
│          NotificationService / UserService                  │
├─────────────────────────────────────────────────────────────┤
│               AI Agent编排层 (Agent Orchestration)            │
│  做标书 LangGraph:                                          │
│    Orchestrator → Parser → Extractor → ListGenerator →     │
│    Matcher → Reviewer → Generator → VersionManager         │
│  评标 LangGraph:                                            │
│    EvalOrchestrator → MaterialChecker → DisqualDetector →  │
│    AIScorer → ScoreAggregator                               │
│  多模型路由 + 熔断降级 + HITL                                  │
├─────────────────────────────────────────────────────────────┤
│                    数据层 (Data Access)                       │
│  SQLAlchemy ORM + Repository Pattern                        │
│  PostgreSQL 16 (关系型) + pgvector (向量搜索)                 │
│  Redis (缓存/队列/会话/倒计时)                                │
│  MinIO (文件存储, S3兼容)                                    │
├─────────────────────────────────────────────────────────────┤
│                  基础设施层 (Infrastructure)                  │
│  Docker / Docker Compose (私有化) / 阿里云ACK (SaaS)        │
│  Celery (异步任务) / Prometheus+Grafana (监控)              │
│  ELK (日志) / WebSocket (实时通知/进度推送)                   │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 核心设计原则

- **双业务线统一架构**：做标书和评标书共享用户体系、资质库、通知系统、留痕系统
- **SaaS+私有化统一代码**：通过配置切换部署模式，不维护两套代码
- **AI与业务解耦**：AI Agent编排层独立于业务层，可独立升级和替换模型
- **多租户隔离**：共享Schema + tenant_id + PostgreSQL Row Level Security
- **供应商门户独立认证**：供应商通过Portal Token访问，与内部用户JWT隔离
- **异步优先**：长耗时操作（文件解析、AI处理、文档生成、评分计算）全部异步+进度推送
- **操作不可篡改**：评标操作日志采用append-only设计，禁止update/delete

---

## 2. 技术选型

### 2.1 完整技术栈

| 层 | 选型 | 备选 | 选择理由 |
|----|------|------|----------|
| 前端框架 | React 18 + TypeScript | Vue 3 | 企业级B2B生态最成熟，Ant Design组件库丰富 |
| UI组件库 | Ant Design 5 | Arco Design | 企业级组件最全，表格/表单/树形控件成熟 |
| CSS框架 | Tailwind CSS 3 | CSS Modules | 与Ant Design配合，快速布局 |
| **SVG图标库(锁定)** | **Lucide React** | Tabler Icons | 1500+图标，tree-shakable，MIT开源，24x24网格2px描边 |
| 后端框架 | FastAPI (Python 3.11+) | NestJS | AI应用标配，async原生，LangGraph同为Python生态 |
| ORM | SQLAlchemy 2.0 + Pydantic | Prisma | Python生态最成熟，异步支持好 |
| 数据库 | PostgreSQL 16 + pgvector | MySQL | 关系型+向量一体化，MVP减少服务数量 |
| 缓存 | Redis 7 | - | 会话/任务队列/限流/倒计时 |
| 文件存储 | MinIO | 阿里云OSS | S3兼容，SaaS+私有化统一代码 |
| 多智能体框架 | LangGraph 0.2+ | CrewAI / Dify | 图结构编排，状态管理，HITL |
| AI模型(主) | Qwen-Plus | - | 1M上下文，Function Calling，性价比高 |
| AI模型(备) | DeepSeek-V3 | - | 推理强，成本极低 |
| AI模型(视觉) | GLM-4.6V | Qwen-VL | 多模态，签字/印章/资质识别 |
| AI模型(免费) | GLM-4-Flash | - | 免费，轻量分类任务 |
| 文档解析 | PyMuPDF + pdfplumber | Apache Tika | 分别处理文本和表格，性能最优 |
| Word生成 | python-docx + docxtpl | Aspose.Words | 模板驱动+程序化构建，开源免费 |
| 任务队列 | Celery + Redis | RQ | Python生态标准，异步任务处理 |
| 实时通信 | WebSocket | SSE | 供应商门户实时通知+评标进度推送 |
| 部署(SaaS) | Docker + 阿里云ACK | AWS EKS | 国内云服务，成本可控 |
| 部署(私有化) | Docker Compose | K8s | 单机部署简单，MVP阶段够用 |
| 监控 | Prometheus + Grafana | Datadog | 开源免费 |
| 日志 | ELK | Loki | 文档处理日志量大，需全文搜索 |

### 2.2 P0规则落实：图标库锁定

**全项目锁定 Lucide React (lucide-react) 作为唯一图标库**

- npm包：`lucide-react@^0.400.0`
- 设计规范：24x24网格，2px默认描边，currentColor继承
- 引入方式：按需import，Tree-shaking自动裁剪
- 尺寸规范：16px（行内）/ 20px（按钮内）/ 24px（独立图标）
- 禁止混用其他图标库，禁止emoji作为功能图标

---

## 3. 多智能体框架选型

### 3.1 框架对比

| 维度 | LangGraph | AutoGen | CrewAI | Dify |
|------|-----------|---------|--------|------|
| 编排方式 | 图结构(DAG) | 对话式群聊 | 角色驱动 | 可视化工作流 |
| 国产模型兼容 | 优秀 | 优秀 | 优秀 | 极佳(原生集成) |
| 文档处理 | 强(LangChain生态) | 中等 | 中等 | 强 |
| 状态管理 | 内建StateGraph | 有 | 有 | 有 |
| 人机协作(HITL) | 原生支持 | 支持 | 支持 | 支持 |
| 可观测性 | LangSmith | OpenTelemetry | 内建tracing | 内建监控 |

### 3.2 选型结论：LangGraph

**核心理由：**
1. 图结构编排天然匹配做标书7步和评标书6步流程（每步一个Node，支持条件分支/并行/循环）
2. StateGraph状态管理解决跨步骤共享状态需求
3. 国产模型通过OpenAI兼容API直接接入，零额外成本
4. HITL原生支持（审核步骤暂停/恢复、人工复审评分）
5. 纯Python库，SaaS和私有化环境代码完全一致
6. LangSmith可观测性：每个Agent轨迹全程可追踪

---

## 4. 国产AI模型选型

### 4.1 模型对比

| 模型 | 上下文窗口 | Function Calling | 长文档理解 | 价格(输入/输出) |
|------|-----------|-----------------|-----------|----------------|
| Qwen-Plus | 1M | 支持(增强) | 极佳 | ¥0.8/¥2 |
| DeepSeek-V3 | 128K | 支持 | 优秀 | ~¥1/¥2 |
| GLM-4-Plus | 128K | 支持 | 优秀 | ¥5/¥5 |
| GLM-4-Flash | 128K | 支持 | 好 | 免费 |
| ERNIE 5.0 | 128K | 支持 | 好 | ¥6-10/¥25-42 |

### 4.2 多模型路由策略

```
任务类型 → 模型路由：

做标书：
- 招标文件解析+需求提取 → Qwen-Plus (1M上下文)
- 材料清单生成 → Qwen-Plus 或 DeepSeek-V3
- 内容审核（逻辑推理） → DeepSeek-V3
- 签字/印章检测（视觉） → GLM-4.6V
- 简单分类/标签 → GLM-4-Flash (免费)
- 投标文档生成 → Qwen-Plus

评标书：
- 材料完整性检查 → Qwen-Plus 或 DeepSeek-V3
- 废标条件检测（逻辑推理） → DeepSeek-V3
- 资质真伪识别（视觉） → GLM-4.6V
- 技术标AI评分 → Qwen-Plus (长文档理解)
- 商务标AI评分 → DeepSeek-V3 (推理+计算)
- 评分依据生成 → Qwen-Plus

熔断降级链：
Qwen-Plus → [失败] → DeepSeek-V3 → [失败] → GLM-4-Plus → [连续3次失败] → 熔断10分钟
```

### 4.3 成本估算

| 任务环节 | Token消耗 | 成本(Qwen-Plus) |
|----------|-----------|----------------|
| **做标书** | | |
| 招标文件解析+需求提取 | 50K input + 10K output | ~¥0.06 |
| 材料清单生成 | 20K input + 5K output | ~¥0.03 |
| 内容审核（3-5份材料） | 100K input + 20K output | ~¥0.12 |
| 文档生成 | 30K input + 30K output | ~¥0.09 |
| **做标书单任务** | - | **~¥0.30** |
| **评标书** | | |
| 材料完整性检查（每家） | 30K input + 5K output | ~¥0.03 |
| 废标检测（每家） | 50K input + 10K output | ~¥0.06 |
| AI技术评分（每家） | 80K input + 15K output | ~¥0.09 |
| AI商务评分（每家） | 20K input + 5K output | ~¥0.03 |
| **评标单任务（5家供应商）** | - | **~¥1.05** |
| **月均100做标书+20评标** | - | **~¥51/月** |

---

## 5. 多智能体系统设计

### 5.1 做标书 Agent清单（8个）

| Agent名称 | 职责 | 输入 | 输出 | 使用模型 |
|-----------|------|------|------|----------|
| Orchestrator | 协调7步流程，状态管理，任务路由 | 用户请求+当前状态 | 下一步指令 | Qwen-Plus |
| DocumentParser | 解析招标文件PDF/Word/Excel | 原始文件 | 结构化文档对象 | 无LLM(纯工具) |
| RequirementExtractor | 从解析结果提取投标要求 | 结构化文档 | 需求JSON | Qwen-Plus (1M) |
| MaterialListGenerator | 生成材料清单+模板 | 需求JSON | 材料清单JSON | Qwen-Plus |
| MaterialMatcher | 匹配资质库+文档片段库 | 材料清单 | 匹配结果(已有/缺失) | GLM-4-Flash |
| ContentReviewer | 审核上传材料的完整性/准确性 | 材料+招标要求 | 审核报告+修改建议 | DeepSeek-V3 |
| DocumentGenerator | 生成Word投标文件 | 审核通过的材料+模板 | .docx文件 | Qwen-Plus |
| VersionManager | 记录版本，生成diff | 文件+元数据 | 版本记录 | 无LLM(纯工具) |

### 5.2 做标书 Agent协作流程

```
用户上传招标文件
        │
        ▼
  Orchestrator ← 统一入口，创建任务，初始化状态
        │
        ▼
  DocumentParser ← PyMuPDF/pdfplumber解析文件
        │ 结构化文档
        ▼
  RequirementExtractor ← Qwen-Plus提取投标要求
        │ 需求JSON
        ▼
  MaterialListGenerator ← 生成材料清单
        │ 材料清单
    ┌───┴───┐
    ▼       ▼
  资质库    片段库     ← 并行匹配
  Matcher  Matcher
    └───┬───┘
        │ 匹配结果(已有/缺失)
        ▼
  [HITL: 用户下载清单+上传材料]
        │
        ▼
  ContentReviewer ← DeepSeek审核材料
        │ 审核结果
    ┌───┴───┐
    │ 通过？ │
    ├─否─┐   │
    │   ▼   │
    │ [HITL: 用户修改材料] → 回到审核
    │       │
    └─是─┐  │
        ▼   │
  DocumentGenerator ← 生成Word投标文件
        │ .docx文件
        ▼
  VersionManager ← 保存版本+生成diff
```

### 5.3 做标书 LangGraph图结构映射

```
[Step1: 上传] → Node: file_upload
    → [Step2: 解析] → Node: parse_tender → Node: extract_requirements
    → [Step3: 清单] → Node: generate_material_list
    → [Step4: 匹配] → Parallel: match_qualification_lib + match_fragment_lib
    → [Step5: 上传材料] → Node: upload_materials (HITL暂停)
    → [Step6: 审核] → Node: review_content → Conditional: 通过? → Step7 : 回退Step5
    → [Step7: 生成] → Node: generate_document → Node: save_version
    → [END]
```

### 5.4 评标书 Agent清单（5个）

| Agent名称 | 职责 | 输入 | 输出 | 使用模型 |
|-----------|------|------|------|----------|
| EvalOrchestrator | 协调6步评标流程，状态管理，供应商提交路由 | 评标任务+当前状态 | 下一步指令 | Qwen-Plus |
| MaterialChecker | 检查每家供应商材料完整性，对比必交清单 | 供应商提交文件+材料清单 | 完整性报告(已提供/缺失/疑似伪造) | Qwen-Plus |
| DisqualificationDetector | 检测废标条件（虚假资质/伪造/超预算/缺签字等） | 材料+招标要求+废标条件列表 | 废标检测报告(通过/需关注/废标) | DeepSeek-V3 |
| AIScorer | 按评分办法对技术标和商务标进行AI初步评分 | 投标文件+评分项+评分标准 | AI评分+评分依据 | Qwen-Plus |
| ScoreAggregator | 汇总AI评分+人工复审评分，计算综合排名 | 所有评分数据 | 综合排名表 | 无LLM(纯计算) |

### 5.5 评标书 Agent协作流程

```
管理员发布评标任务
        │
        ▼
  EvalOrchestrator ← 创建评标任务，初始化状态，生成供应商入口
        │
        ▼
  [供应商提交阶段] ← 供应商通过门户提交材料（HITL等待截止）
        │ 提交数据
        ▼
  MaterialChecker ← AI检查每家材料完整性
        │ 完整性报告
        ▼
  DisqualificationDetector ← AI检测废标条件
        │ 废标检测报告
    ┌───┴───┐
    │ 有废标？│
    ├─是─┐   │
    │   ▼   │
    │ [HITL: 管理员确认废标/供应商补材料] → 可回到MaterialChecker
    │       │
    └─否─┐  │
        ▼   │
  AIScorer ← AI按评分办法评分（技术+商务）
        │ AI评分结果
        ▼
  [HITL: 评标专家人工复审，调整分数]
        │ 人工评分
        ▼
  ScoreAggregator ← 汇总计算综合排名
        │ 综合排名表
        ▼
  [评标关闭，操作日志归档]
```

### 5.6 评标书 LangGraph图结构映射

```
[Step1: 发布评标] → Node: create_eval_task → Node: generate_supplier_portal
    → [Step2: 供应商提交] → Node: supplier_submission (HITL等待截止)
    → [Step3: 材料审核] → Node: check_materials → Node: detect_disqualification
        → Conditional: 有废标? → HITL确认 : 继续
        → Conditional: 需补材料? → Node: send_supplement_notice → 等待补充 → 回到check_materials
        → Conditional: 多轮报价? → Node: start_bidding_round → HITL等待 → 回到check_materials
    → [Step4: 评标评审] → Node: ai_scoring → Node: human_review (HITL)
    → [Step5: 结果公示] → Node: aggregate_scores → Node: generate_ranking
    → [Step6: 评标关闭] → Node: close_evaluation → Node: archive_audit_trail
    → [END]
```

- **顺序步骤**：固定Edge连接
- **并行步骤**：fan-out + fan-in模式
- **条件分支**：conditional_edge（废标确认/补材料/多轮报价）
- **人机协作**：interrupt + resume（等待供应商提交、管理员确认废标、专家复审评分）
- **循环**：多轮报价循环 + 补材料循环

### 5.7 权限感知Function Calling

| 角色 | 可调用Agent（做标书） | 可调用Agent（评标书） |
|------|----------------------|----------------------|
| 管理员 | 全部Agent | 全部Agent |
| 项目负责人 | 除系统配置外全部 | 除系统配置外全部 |
| 成员 | DocumentParser、MaterialListGenerator、MaterialMatcher、DocumentGenerator | - |
| 审核员 | ContentReviewer、VersionManager | AIScorer、ScoreAggregator（复审） |
| 供应商 | - | 供应商门户（仅提交，不调用Agent） |

---

## 6. 文档处理技术方案

### 6.1 招标文件解析

```
上传文件 → 文件类型识别 →
  PDF → PyMuPDF提取文本 + pdfplumber提取表格 → 检查是否扫描件 → 是则PaddleOCR
  Word → python-docx提取段落+表格
  Excel → openpyxl提取数据
  PPT → python-pptx提取内容
  图片 → 直接送入多模态模型
  压缩包 → 解压后递归处理
→ 合并为结构化文档对象 → 送入AI模型进行需求提取
```

| 需求 | 方案 | 说明 |
|------|------|------|
| PDF文本提取 | PyMuPDF (fitz) | 性能最优，支持block级别提取+坐标信息 |
| PDF表格提取 | pdfplumber | 布局分析+表格识别 |
| 扫描PDF OCR | PaddleOCR | 中文OCR最佳 |
| Word解析 | python-docx | 段落/表格/样式提取 |
| Excel解析 | openpyxl | 单元格+合并单元格 |
| PPT解析 | python-pptx | 幻灯片+文本框+表格 |
| 图片识别 | GLM-4.6V | 多模态模型直接理解图片内容 |

### 6.2 Word投标文件生成

```
投标文件生成流程：
1. 预制标准模板（资质标/商务标/技术标各一套.docx模板）
2. 模板内嵌Jinja2占位符：{{company_name}}、{% for item in qualifications %}
3. AI生成的内容 → 结构化JSON → docxtpl渲染到模板
4. 复杂表格/图片 → python-docx程序化插入
5. 多章节合并 → docxcompose
6. 最终输出.docx文件
```

### 6.3 文档版本管理

```sql
CREATE TABLE document_versions (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    task_id UUID NOT NULL,
    document_type VARCHAR(50),
    version_number INT NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    change_summary TEXT,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, task_id, document_type, version_number)
);
```

- 每次生成记录hash、版本号、变更摘要、操作人
- 段落级diff（python-docx + difflib），生成可视化对比报告
- 文件快照存储（MinIO），支持回溯下载

### 6.4 供应商提交文件处理

```
供应商上传文件 → 文件类型校验 → 病毒扫描 →
→ 存储到MinIO（按评标任务+供应商分目录）→
→ 记录提交时间戳（精确到秒）→
→ AI解析提取关键信息（资质编号、报价金额、签字页等）→
→ 与材料清单逐项匹配
```

| 需求 | 方案 | 说明 |
|------|------|------|
| 资质真伪识别 | GLM-4.6V | 视觉模型对比资质证书图片，检测篡改痕迹 |
| 报价金额提取 | PyMuPDF + 正则 | 从报价表中提取金额，大小写一致性校验 |
| 签字/印章检测 | GLM-4.6V | 检测投标函等关键页的签字和盖章 |
| 材料比对 | pgvector + 语义匹配 | 供应商提交文件 vs 必交清单的语义匹配 |

---

## 7. 供应商门户架构

### 7.1 认证方案

```
供应商认证流程：
1. 管理员发布评标任务 → 生成供应商入口链接（含Portal Token）
2. 供应商点击链接 → Portal Token验证 → 获取供应商身份和关联的评标任务
3. Portal Token有效期内可多次访问，评标关闭后失效
4. 供应商无需注册账号，通过Token直接访问

认证对比：
├── 内部用户：JWT（15min access + 7d refresh）
└── 供应商：Portal Token（与评标任务绑定，评标关闭后失效）
```

### 7.2 供应商门户数据流

```
供应商门户 ←→ API网关 ←→ SupplierService
                          ├── 提交材料 → MinIO存储 → 记录时间戳
                          ├── 多轮报价 → BiddingService → 记录报价历史
                          ├── 补材料通知 → NotificationService → WebSocket推送
                          └── 提交状态 → Redis缓存实时状态
```

### 7.3 实时通知方案

```
通知渠道：
├── 内部用户：WebSocket + 站内消息
└── 供应商：WebSocket（门户打开时）+ 邮件/短信（门户未打开时）

通知类型：
├── 评标通知：评标任务发布、提交截止提醒
├── 补材料通知：材料缺失需补充（含倒计时）
├── 报价通知：新轮次报价开启
├── 状态通知：提交成功确认、评标结束
└── 结果通知：评标结果公示
```

---

## 8. 评标操作留痕设计

### 8.1 审计日志表设计

```sql
CREATE TABLE eval_audit_trails (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    eval_task_id UUID NOT NULL,
    operator_type VARCHAR(20) NOT NULL, -- 'admin'/'reviewer'/'supplier'/'system'
    operator_id UUID,
    operator_name VARCHAR(100),
    action VARCHAR(50) NOT NULL, -- 'submit'/'replace'/'score_adjust'/'notice_send'/'disqual_confirm'等
    target_type VARCHAR(50), -- 'material'/'bid'/'score'/'notice'
    target_id VARCHAR(100),
    details JSONB NOT NULL, -- 详细操作信息
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- 审计日志禁止UPDATE和DELETE，仅允许INSERT
    CONSTRAINT no_update CHECK (true) -- 应用层强制
);

-- 禁止UPDATE和DELETE（通过数据库触发器）
CREATE OR REPLACE FUNCTION prevent_audit_modify()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit trail records are immutable';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_audit_update BEFORE UPDATE ON eval_audit_trails
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_modify();
CREATE TRIGGER prevent_audit_delete BEFORE DELETE ON eval_audit_trails
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_modify();
```

### 8.2 留痕覆盖范围

| 操作类型 | 记录内容 | 操作人 |
|----------|----------|--------|
| 评标任务发布 | 任务信息、配置、供应商列表 | 管理员 |
| 供应商材料提交 | 文件名、大小、时间戳、IP | 供应商 |
| 材料替换 | 原文件、新文件、替换时间 | 供应商 |
| 补材料通知发送 | 通知内容、接收方、时限 | 管理员 |
| 补材料提交 | 补充文件、提交时间、是否超时 | 供应商 |
| 多轮报价发起 | 轮次、截止时间 | 管理员 |
| 报价提交 | 报价金额、轮次、时间戳 | 供应商 |
| AI评分完成 | 评分项、AI分数、评分依据 | 系统 |
| 人工评分调整 | 原分、调整后分、调整原因 | 审核员 |
| 废标确认/撤销 | 废标原因、确认/撤销时间 | 管理员 |
| 评标关闭 | 关闭时间、最终结果 | 管理员 |

---

## 9. 核心功能可行性验证

| 功能 | 可行性 | 方案 | 风险 |
|------|--------|------|------|
| **做标书** | | | |
| AI拆解招标文件 | 高 | Qwen-Plus 1M上下文覆盖50-200页招标文件 | 扫描件需OCR预处理 |
| 材料清单自动生成 | 高 | Function Calling调用清单生成工具 | - |
| 签字提醒 | 中高 | GLM-4.6V视觉模型检测签字区域 | 扫描件质量影响识别率 |
| 价格填充检查 | 高 | 结构化提取价格字段 | 格式多样需规则+AI结合 |
| 内容核对 | 高 | AI对比招标要求 vs 投标内容 | 长文档需分段审核 |
| 逻辑一致性检查 | 中 | AI跨章节交叉验证 | 需全文档上下文 |
| Word投标文件生成 | 高 | docxtpl模板渲染 | 特殊格式需自定义 |
| **评标书** | | | |
| 材料完整性检查 | 高 | AI逐项比对提交文件与必交清单 | 非标准文件名需语义匹配 |
| 废标条件检测 | 中高 | DeepSeek-V3逻辑推理+GLM-4.6V视觉检测 | 资质真伪识别准确率约85% |
| AI技术评分 | 中高 | Qwen-Plus理解技术方案，按评分标准打分 | 评分主观性，需人工复审 |
| AI商务评分 | 高 | 报价对比+公式计算 | 规则明确，准确率高 |
| 多轮报价管理 | 高 | 数据库记录+状态机管理 | 并发提交需锁机制 |
| 操作留痕 | 高 | Append-only审计日志+触发器保护 | 性能需索引优化 |

---

## 10. 多租户架构

### 10.1 隔离策略

- **数据库层**：共享Schema + tenant_id + PostgreSQL Row Level Security
- **文件存储层**：MinIO按租户分Bucket
- **缓存层**：Redis key前缀加tenant_id
- **AI模型层**：租户级API Key配置（私有化部署可配置本地模型）
- **供应商数据**：评标任务级隔离，不同评标任务的供应商数据互不可见

### 10.2 部署模式

| 模式 | 数据库 | 文件存储 | AI模型 | 部署方式 |
|------|--------|----------|--------|----------|
| SaaS多租户 | 共享PostgreSQL | 共享MinIO(分Bucket) | 共享API Key | Docker + 阿里云ACK |
| 私有化部署 | 独立PostgreSQL | 独立MinIO | 本地模型/独立API Key | Docker Compose |

---

## 11. 技术约束与风险

### 11.1 技术约束

1. Qwen-Plus RPM限制120次/分钟，需请求队列和重试
2. 超过1M token的招标文件需分段处理（极少见，需兜底）
3. docxtpl不支持复杂的Word样式继承
4. 多章节合并时页眉页脚可能丢失
5. 供应商门户需兼容低版本浏览器（供应商设备不可控）
6. 多轮报价并发提交需防重复提交和锁机制
7. 审计日志数据量大，需定期归档（>3年转冷存储）

### 11.2 风险与缓解

| 风险 | 等级 | 缓解方案 |
|------|------|----------|
| AI模型API不稳定 | 高 | 多模型路由+熔断降级 |
| 招标文件格式多样 | 中 | 混合解析策略+人工fallback |
| 审核准确率不达标 | 中 | MVP先做价格检查+内容核对，逐步迭代 |
| Word模板覆盖不全 | 中 | 模板编辑器+标准模板持续扩充 |
| 长流程超时 | 中 | 异步处理+WebSocket进度推送+断点续传 |
| 私有化部署模型API缺失 | 中 | 支持本地部署GLM/Qwen开源模型 |
| 资质真伪识别误判 | 中高 | AI检测+人工确认双保险，不自动废标 |
| 供应商并发提交压力 | 中 | Redis限流+队列处理+CDN加速 |
| 审计日志性能瓶颈 | 低 | 分区表+异步写入+定期归档 |

---

## 12. 开发成本评估

| 模块 | 预估人周 | 说明 |
|------|----------|------|
| **做标书** | | |
| 前端 | 4-5周 | React+Ant Design，10页面 |
| 后端 | 3-4周 | FastAPI+PostgreSQL+Redis |
| AI Agent系统 | 4-5周 | LangGraph编排+8个Agent |
| 文档处理 | 2-3周 | PDF解析+Word生成+版本管理 |
| **评标书** | | |
| 前端 | 3-4周 | 评标工作台+详情+创建+供应商门户 |
| 后端 | 3-4周 | 评标API+供应商门户+多轮报价+留痕 |
| AI Agent系统 | 3-4周 | LangGraph编排+5个Agent |
| **共享** | | |
| 资质库+文档片段库 | 2周 | CRUD+搜索+匹配 |
| 用户权限+通知 | 2周 | 4+1角色RBAC+WebSocket通知 |
| 部署+测试 | 3周 | Docker+CI/CD+集成测试 |
| **总计** | **29-36周** | 约7-9个月（3人团队） |

AI辅助开发可提速2-3倍，预计实际周期10-14周（3人团队）。

---

## 13. ADR决策清单

| ADR编号 | 决策 | 状态 |
|---------|------|------|
| ADR-001 | 使用LangGraph作为多智能体编排框架 | Accepted |
| ADR-002 | 使用Qwen-Plus作为主AI模型 | Accepted |
| ADR-003 | 使用PostgreSQL+pgvector作为统一数据存储 | Accepted |
| ADR-004 | 使用MinIO作为文件存储(SaaS+私有化统一) | Accepted |
| ADR-005 | 使用Lucide React作为锁定SVG图标库 | Accepted |
| ADR-006 | 使用docxtpl+python-docx进行Word文档生成 | Accepted |
| ADR-007 | 使用共享Schema+tenant_id实现多租户隔离 | Accepted |
| ADR-008 | 做标书和评标书共享Agent编排框架(LangGraph)但独立Graph | Accepted |
| ADR-009 | 供应商门户使用Portal Token认证而非注册账号 | Accepted |
| ADR-010 | 评标审计日志采用Append-only设计+数据库触发器保护 | Accepted |
| ADR-011 | 评标Agent与做标书Agent独立部署，共享模型路由层 | Accepted |
