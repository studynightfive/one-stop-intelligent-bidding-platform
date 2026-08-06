# Spec - 一站式智能招投标平台 v2.0

> 生成日期：2026-08-05
> 基于：PRD v2.0 + 架构文档 v2.0 + 前端设计文档 v2.0
> 状态：已确认

---

## 1. 产品定义

- **一句话描述**：覆盖企业采购招投标全流程的一站式平台，通过AI多智能体系统实现做标书（7步闭环：上传→解析→清单→模板→上传→审核→输出）和评标书（6步闭环：发布→提交→审核→评审→公示→关闭）双业务线
- **目标用户**：企业招投标团队（投标专员、商务经理、技术负责人、审核员）+ 外部供应商 + 评标专家
- **核心问题**：做标书周期长/废标率高/经验无法沉淀；评标效率低/材料核查靠人工/评分主观/过程缺乏留痕

---

## 2. MVP范围（锁定——不在此列表的功能一律不做）

### 做标书 P0功能

| 优先级 | 功能 | 验收标准摘要 | RICE评分 |
|--------|------|-------------|-----------|
| P0 | F1 招标文件上传与解析 | 100页以内PDF 3分钟内完成解析 | 4.80 |
| P0 | F2 材料清单展示与匹配 | 清单状态准确标记已有/缺失 | 8.00 |
| P0 | F3 批量上传对应材料 | 拖拽批量上传+自动关联清单项 | 10.00 |
| P0 | F4 AI审核与修改建议 | 5分钟内输出审核报告（4类问题） | 4.00 |
| P0 | F5 Word投标文件输出 | 按招标要求拆分输出3个Word文件 | 7.50 |
| P0 | F6 版本管理与回溯 | 版本树可视化+回滚到任意版本 | 4.00 |
| P0 | F7 资质库管理 | 到期前30/60/90天自动预警 | 3.20 |
| P0 | F8 文档片段库管理 | 全文检索+AI自动匹配引用 | 3.20 |
| P0 | F9 多项目并行管理 | 看板+列表双视图 | 4.27 |
| P0 | F10 多人协作（4角色RBAC） | 4角色权限隔离+任务分配通知 | 3.20 |

### 评标书 P0功能

| 优先级 | 功能 | 验收标准摘要 | RICE评分 |
|--------|------|-------------|-----------|
| P0 | F11 评标任务创建与发布 | 5步向导完成发布，生成供应商入口 | 6.40 |
| P0 | F12 供应商提交门户 | 供应商可完成全部提交操作 | 8.00 |
| P0 | F13 材料完整性检查 | AI检查结果与人工核查一致率>90% | 5.33 |
| P0 | F14 废标条件检测 | 检测结果含详细说明和依据 | 4.80 |
| P0 | F15 AI初步评分 | AI评分与专家评分偏差<15% | 5.33 |
| P0 | F16 人工复审评分 | 人工调整有记录，支持复审 | 6.40 |
| P0 | F17 多轮报价管理 | 多轮报价自动排名+降幅计算 | 4.27 |
| P0 | F18 操作留痕与审计 | 操作日志不可篡改，支持导出 | 4.80 |

---

## 3. 明确不做（Out-of-Scope — 锁定）

| 不做的功能 | 原因 | 何时考虑 |
|------------|------|----------|
| F19 站内通知（邮件渠道） | MVP仅站内消息+WebSocket，邮件渠道P1 | M5阶段 |
| F20 多租户管理（SaaS后台） | MVP先做单租户验证，多租户P1 | M6阶段 |
| F21 私有化部署包 | MVP先验证SaaS模式，私有化P1 | M6阶段 |
| F22 协同编辑（多人实时） | 技术复杂度高（OT/CRDT），P1迭代 | M5阶段 |
| F23 AI模型配置界面 | MVP硬编码模型路由，配置界面P1 | M6阶段 |
| F24 评标报告生成 | MVP先做排名表，自动报告P1 | M6阶段 |
| F25 供应商管理 | MVP仅评标任务内供应商，供应商库P1 | M6阶段 |
| F26 标书查重 | P2远期规划 | v2.0 |
| F27 数据导出与报表 | P2远期规划 | v2.0 |
| F28 模板库管理 | P2远期规划 | v2.0 |
| F29 评标专家库 | P2远期规划 | v2.0 |
| 政府采购/工程招标 | MVP聚焦企业采购，其他类型后续扩展 | v2.0 |
| 国际化（多语言） | MVP仅中文 | v2.0 |
| 移动端App | MVP仅响应式Web | v2.0 |

---

## 4. 技术架构（锁定 — 含版本锚定）

| 层 | 技术 | 实际版本 | 锁定原因 |
|----|------|----------|----------|
| 前端框架 | React | 18.x | 企业级B2B生态最成熟 |
| 前端语言 | TypeScript | 5.x | 类型安全 |
| UI组件库 | Ant Design | 5.x | 企业级组件最全 |
| CSS框架 | Tailwind CSS | 3.x | 快速布局 |
| SVG图标库 | Lucide React | ^0.400.0 | 1500+图标，统一2px描边，MIT开源 |
| 后端框架 | FastAPI | 0.110+ | async原生，LangGraph同为Python |
| 后端语言 | Python | 3.11+ | AI生态标配 |
| ORM | SQLAlchemy | 2.0+ | 异步支持好 |
| 数据校验 | Pydantic | 2.x | FastAPI标配 |
| 数据库 | PostgreSQL | 16 | 关系型+向量一体化 |
| 向量扩展 | pgvector | 0.7+ | 语义搜索 |
| 缓存 | Redis | 7.x | 会话/队列/限流/倒计时 |
| 文件存储 | MinIO | 最新稳定版 | S3兼容，SaaS+私有化统一 |
| 多智能体框架 | LangGraph | 0.2+ | 图结构编排，状态管理，HITL |
| AI模型(主) | Qwen-Plus | 2025版 | 1M上下文，Function Calling |
| AI模型(备) | DeepSeek-V3 | 最新版 | 推理强，成本低 |
| AI模型(视觉) | GLM-4.6V | 最新版 | 多模态，签字/印章/资质识别 |
| AI模型(免费) | GLM-4-Flash | 最新版 | 免费，轻量任务 |
| PDF解析 | PyMuPDF + pdfplumber | 最新版 | 文本+表格分别处理 |
| Word生成 | python-docx + docxtpl | 最新版 | 模板驱动+程序化构建 |
| 任务队列 | Celery | 5.x | Python异步任务标准 |
| 实时通信 | WebSocket | - | 供应商门户实时通知+进度推送 |
| 部署(SaaS) | Docker + 阿里云ACK | - | 国内云服务 |
| 部署(私有化) | Docker Compose | - | 单机部署简单 |
| 认证(内部) | JWT | - | 15min access + 7d refresh |
| 认证(供应商) | Portal Token | - | 与评标任务绑定，关闭后失效 |

---

## 5. API端点清单（锁定——开发时以此为唯一依据）

### 5.1 认证模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| POST | /api/v1/auth/register | 用户注册 | 无 | {email, password, name, company_name} | {user_id, token, refresh_token} |
| POST | /api/v1/auth/login | 用户登录 | 无 | {email, password} | {user_id, token, refresh_token, role} |
| POST | /api/v1/auth/refresh | 刷新Token | refresh_token | {refresh_token} | {token, refresh_token} |
| POST | /api/v1/auth/logout | 登出 | JWT | - | {success: true} |
| GET | /api/v1/auth/me | 获取当前用户 | JWT | - | {user_id, name, email, role, tenant_id} |

### 5.2 投标任务模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| POST | /api/v1/tasks | 创建投标任务 | JWT | {project_name, tender_file_id, deadline} | {task_id, status} |
| GET | /api/v1/tasks | 任务列表 | JWT | query: {status, page, size, keyword} | {tasks[], total, page} |
| GET | /api/v1/tasks/:id | 任务详情 | JWT | - | {task, current_step, progress, materials, versions} |
| PUT | /api/v1/tasks/:id | 更新任务 | JWT | {project_name, deadline, status} | {task} |
| DELETE | /api/v1/tasks/:id | 删除任务 | JWT | - | {success: true} |
| GET | /api/v1/tasks/board | 看板视图 | JWT | query: {view} | {columns: [{status, tasks[]}]} |

### 5.3 招标文件模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| POST | /api/v1/tender-files/upload | 上传招标文件 | JWT | multipart/form-data | {file_id, status: "parsing"} |
| GET | /api/v1/tender-files/:id/status | 解析状态 | JWT | - | {status, progress, result?} |
| GET | /api/v1/tender-files/:id/requirements | 获取解析结果 | JWT | - | {project_info, requirements, scoring_items, disqual_items} |

### 5.4 材料清单模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| GET | /api/v1/tasks/:id/materials | 获取材料清单 | JWT | - | {materials[], total, have, missing} |
| PUT | /api/v1/tasks/:id/materials | 更新清单项 | JWT | {material_id, changes} | {material} |
| POST | /api/v1/tasks/:id/materials | 添加清单项 | JWT | {name, type, requirement, document_part} | {material} |
| DELETE | /api/v1/tasks/:id/materials/:mid | 删除清单项 | JWT | - | {success: true} |
| GET | /api/v1/tasks/:id/materials/export | 导出清单Excel | JWT | - | binary(xlsx) |
| GET | /api/v1/tasks/:id/materials/:mid/template | 下载模板 | JWT | - | binary(docx) |

### 5.5 材料上传模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| POST | /api/v1/tasks/:id/materials/:mid/upload | 上传单个材料 | JWT | multipart/form-data | {material_id, status: "uploaded", file_path} |
| POST | /api/v1/tasks/:id/materials/batch-upload | 批量上传 | JWT | multipart/form-data[] | {results[]} |
| PUT | /api/v1/tasks/:id/materials/:mid/replace | 替换材料 | JWT | multipart/form-data | {material_id, status: "uploaded"} |
| DELETE | /api/v1/tasks/:id/materials/:mid/file | 删除已上传文件 | JWT | - | {success: true} |

### 5.6 AI审核模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| POST | /api/v1/tasks/:id/review | 发起AI审核 | JWT | {review_types: ["signature","price","content","consistency"]} | {review_id, status: "processing"} |
| GET | /api/v1/tasks/:id/review/status | 审核状态 | JWT | - | {status, progress, current_step} |
| GET | /api/v1/tasks/:id/review/result | 审核结果 | JWT | - | {summary, suggestions[]} |
| POST | /api/v1/tasks/:id/review/suggestions/:sid/action | 处理建议 | JWT | {action: "accept"/"ignore"/"modify"} | {success: true} |

### 5.7 文档输出模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| POST | /api/v1/tasks/:id/documents/generate | 生成Word文档 | JWT | {split: true/false, format: "tender_requirement"/"standard"} | {document_ids[], status: "generating"} |
| GET | /api/v1/tasks/:id/documents | 文档列表 | JWT | - | {documents[]} |
| GET | /api/v1/tasks/:id/documents/:did/download | 下载文档 | JWT | - | binary(docx) |
| GET | /api/v1/tasks/:id/documents/versions | 版本列表 | JWT | - | {versions[]} |
| GET | /api/v1/tasks/:id/documents/versions/compare | 版本对比 | JWT | query: {v1, v2} | {diff} |
| POST | /api/v1/tasks/:id/documents/versions/:v/rollback | 回滚版本 | JWT | - | {success: true, new_version} |

### 5.8 资质库模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| GET | /api/v1/qualifications | 资质列表 | JWT | query: {category, status, page, size} | {qualifications[], total} |
| POST | /api/v1/qualifications | 上传资质 | JWT | multipart/form-data + {name, category, expiry_date, cert_number} | {qualification} |
| PUT | /api/v1/qualifications/:id | 更新资质 | JWT | {name, category, expiry_date} | {qualification} |
| DELETE | /api/v1/qualifications/:id | 删除资质 | JWT | - | {success: true} |
| GET | /api/v1/qualifications/:id/preview | 预览资质文件 | JWT | - | binary |
| GET | /api/v1/qualifications/expiring | 即将到期列表 | JWT | query: {days: 30/60/90} | {qualifications[]} |
| POST | /api/v1/qualifications/batch-import | 批量导入 | JWT | multipart/form-data(excel) | {results[]} |

### 5.9 文档片段库模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| GET | /api/v1/fragments | 片段列表 | JWT | query: {category, keyword, page, size} | {fragments[], total} |
| POST | /api/v1/fragments | 上传片段 | JWT | multipart/form-data + {title, category, tags[]} | {fragment} |
| PUT | /api/v1/fragments/:id | 更新片段 | JWT | {title, category, tags[]} | {fragment} |
| DELETE | /api/v1/fragments/:id | 删除片段 | JWT | - | {success: true} |
| GET | /api/v1/fragments/search | 全文搜索 | JWT | query: {keyword, category} | {fragments[]} |
| GET | /api/v1/fragments/:id/preview | 预览片段 | JWT | - | {content} |

### 5.10 用户与权限模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| GET | /api/v1/users | 用户列表 | JWT(管理员) | query: {page, size} | {users[], total} |
| POST | /api/v1/users | 邀请用户 | JWT(管理员) | {email, name, role} | {user_id, invite_link} |
| PUT | /api/v1/users/:id/role | 修改角色 | JWT(管理员) | {role} | {user} |
| DELETE | /api/v1/users/:id | 移除用户 | JWT(管理员) | - | {success: true} |

### 5.11 通知模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| GET | /api/v1/notifications | 通知列表 | JWT | query: {page, size, unread_only} | {notifications[], total, unread_count} |
| PUT | /api/v1/notifications/:id/read | 标记已读 | JWT | - | {success: true} |
| PUT | /api/v1/notifications/read-all | 全部已读 | JWT | - | {success: true} |
| WS | /api/v1/ws/notifications | 实时通知推送 | JWT | - | {type, title, content, timestamp} |

### 5.12 评标任务模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| POST | /api/v1/evaluations | 创建评标任务 | JWT(管理员) | {project_name, tender_no, tender_entity, budget, deadline, material_template, scoring_criteria, review_settings} | {eval_id, status: "collecting"} |
| GET | /api/v1/evaluations | 评标任务列表 | JWT | query: {status, page, size, keyword} | {evaluations[], total, page} |
| GET | /api/v1/evaluations/:id | 评标任务详情 | JWT | - | {evaluation, current_step, progress, bidders[], submissions[]} |
| PUT | /api/v1/evaluations/:id | 更新评标任务 | JWT(管理员) | {project_name, deadline, status} | {evaluation} |
| DELETE | /api/v1/evaluations/:id | 删除评标任务 | JWT(管理员) | - | {success: true} |
| POST | /api/v1/evaluations/:id/publish | 发布评标任务 | JWT(管理员) | - | {portal_url, supplier_tokens[]} |
| POST | /api/v1/evaluations/:id/close | 关闭评标 | JWT(管理员) | - | {success: true, closed_at} |
| GET | /api/v1/evaluations/:id/ranking | 综合排名 | JWT | - | {ranking[]} |

### 5.13 供应商门户模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| GET | /api/v1/portal/:token | 供应商门户首页 | Portal Token | - | {project_info, deadline, materials[], status} |
| POST | /api/v1/portal/:token/materials/:mid/upload | 供应商上传材料 | Portal Token | multipart/form-data | {material_id, status: "submitted", submitted_at} |
| PUT | /api/v1/portal/:token/materials/:mid/replace | 供应商替换材料 | Portal Token | multipart/form-data | {material_id, status: "submitted", replaced_at} |
| GET | /api/v1/portal/:token/submissions | 提交记录 | Portal Token | - | {submissions[]} |
| GET | /api/v1/portal/:token/notices | 补材料通知 | Portal Token | - | {notices[]} |
| POST | /api/v1/portal/:token/notices/:nid/respond | 响应补材料通知 | Portal Token | multipart/form-data | {notice_id, status: "responded"} |
| WS | /api/v1/portal/:token/ws | 供应商实时通知 | Portal Token | - | {type, content, timestamp} |

### 5.14 多轮报价模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| POST | /api/v1/evaluations/:id/bidding/rounds | 发起新一轮报价 | JWT(管理员) | {deadline} | {round_id, round_number, deadline} |
| GET | /api/v1/evaluations/:id/bidding/rounds | 报价轮次列表 | JWT | - | {rounds[]} |
| POST | /api/v1/portal/:token/bidding/:round_id/submit | 供应商提交报价 | Portal Token | {amount, currency} | {round_id, amount, submitted_at} |
| GET | /api/v1/evaluations/:id/bidding/compare | 报价对比 | JWT | - | {comparison[]} |

### 5.15 评分模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| POST | /api/v1/evaluations/:id/check-materials | 发起材料完整性检查 | JWT | - | {check_id, status: "processing"} |
| GET | /api/v1/evaluations/:id/check-materials/result | 材料检查结果 | JWT | - | {results: [{bidder_id, materials[], missing[], suspicious[]}]} |
| POST | /api/v1/evaluations/:id/detect-disqualification | 发起废标检测 | JWT | - | {detect_id, status: "processing"} |
| GET | /api/v1/evaluations/:id/disqualification/result | 废标检测结果 | JWT | - | {results: [{bidder_id, items: [{condition, result, explanation}]}]} |
| POST | /api/v1/evaluations/:id/disqualification/:bidder_id/confirm | 确认/撤销废标 | JWT(管理员) | {confirmed: true/false, reason} | {success: true} |
| POST | /api/v1/evaluations/:id/ai-scoring | 发起AI评分 | JWT | - | {scoring_id, status: "processing"} |
| GET | /api/v1/evaluations/:id/ai-scoring/result | AI评分结果 | JWT | - | {results: [{bidder_id, scores: [{item_id, ai_score, basis}]}]} |
| PUT | /api/v1/evaluations/:id/scores/:bidder_id/:item_id | 人工调整评分 | JWT(审核员) | {adjusted_score, reason} | {success: true, old_score, new_score} |
| GET | /api/v1/evaluations/:id/scores | 全部评分 | JWT | - | {scores: [{bidder_id, items: [{item_id, ai_score, human_score, final_score}]}]} |

### 5.16 补材料通知模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| POST | /api/v1/evaluations/:id/supplement-notices | 发送补材料通知 | JWT(管理员) | {bidder_id, material_ids[], deadline_minutes} | {notice_id, status: "sent"} |
| GET | /api/v1/evaluations/:id/supplement-notices | 通知列表 | JWT | - | {notices[]} |
| GET | /api/v1/evaluations/:id/supplement-notices/:nid | 通知详情 | JWT | - | {notice, status, responded_at?} |

### 5.17 操作留痕模块

| Method | Path | 功能 | 认证 | 请求体 | 响应体 |
|--------|------|------|------|--------|--------|
| GET | /api/v1/evaluations/:id/audit-trail | 操作日志列表 | JWT | query: {action_type, operator, start_date, end_date, page, size} | {logs[], total, page} |
| GET | /api/v1/evaluations/:id/audit-trail/export | 导出操作日志 | JWT | - | binary(xlsx) |

---

## 6. 数据库表清单（锁定）

### 6.1 做标书相关表（18张）

| 表名 | 核心字段 | 索引 | 关联 |
|------|----------|------|------|
| tenants | id, name, plan, max_storage, created_at | id | - |
| users | id, tenant_id, email, password_hash, name, role, created_at | (tenant_id, email) UNIQUE | tenants |
| projects | id, tenant_id, name, status, deadline, created_by, created_at | (tenant_id, status) | users |
| tasks | id, tenant_id, project_id, name, status, current_step, tender_file_id, created_by, created_at | (tenant_id, project_id, status) | projects, users |
| tender_files | id, task_id, original_name, file_path, file_type, file_size, parse_status, parse_result(jsonb), uploaded_at | (task_id) | tasks |
| material_lists | id, task_id, total_count, have_count, missing_count, created_at | (task_id) | tasks |
| material_items | id, list_id, name, type, requirement, status(have/missing/template), source(library/upload/manual), library_ref_id, sort_order, document_part, created_at | (list_id, sort_order) | material_lists |
| uploaded_materials | id, material_id, file_path, file_name, file_type, file_size, uploaded_by, uploaded_at | (material_id) | material_items |
| review_reports | id, task_id, status, summary, total_issues, error_count, warning_count, suggestion_count, started_at, completed_at | (task_id) | tasks |
| review_suggestions | id, review_id, type, severity, title, description, location, action_taken, created_at | (review_id, severity) | review_reports |
| documents | id, task_id, type, current_version, created_at | (task_id, type) | tasks |
| document_versions | id, document_id, version_number, file_hash, file_path, change_summary, created_by, created_at | (document_id, version_number) UNIQUE | documents, users |
| qualifications | id, tenant_id, name, category, cert_number, expiry_date, status, file_path, tags(jsonb), created_at, updated_at | (tenant_id, status, expiry_date) | tenants |
| document_fragments | id, tenant_id, title, category, content, file_path, tags(jsonb), use_count, embedding(vector), created_at, updated_at | (tenant_id, category) + embedding(ivfflat) | tenants |
| notifications | id, tenant_id, user_id, type, title, content, is_read, created_at | (user_id, is_read, created_at) | users |
| audit_logs | id, tenant_id, user_id, action, resource_type, resource_id, details(jsonb), created_at | (tenant_id, user_id, created_at) | users |
| ai_model_configs | id, tenant_id, provider, model_name, api_key_encrypted, is_active, created_at | (tenant_id, is_active) | tenants |
| task_assignments | id, task_id, user_id, role_in_task, assigned_by, assigned_at | (task_id, user_id) UNIQUE | tasks, users |

### 6.2 评标书相关表（10张）

| 表名 | 核心字段 | 索引 | 关联 |
|------|----------|------|------|
| evaluation_tasks | id, tenant_id, project_name, tender_no, tender_entity, budget, deadline, status(collecting/pending/ai_review/human_review/completed/closed), current_step, created_by, created_at | (tenant_id, status) | tenants, users |
| evaluation_materials | id, eval_task_id, name, type, is_required, sort_order, created_at | (eval_task_id, sort_order) | evaluation_tasks |
| evaluation_scoring_criteria | id, eval_task_id, item_name, category(technical/commercial/qualification), max_score, weight, sort_order | (eval_task_id, category) | evaluation_tasks |
| evaluation_review_settings | id, eval_task_id, multi_round_bidding(bool), max_rounds, supplement_notice_minutes, allow_modify, auto_close | (eval_task_id) | evaluation_tasks |
| bidders | id, eval_task_id, name, portal_token, contact_email, status(invited/submitted/qualified/disqualified), created_at | (eval_task_id, portal_token) UNIQUE | evaluation_tasks |
| bidder_submissions | id, bidder_id, material_id, file_path, file_name, file_size, submitted_at, replaced_at | (bidder_id, material_id) | bidders, evaluation_materials |
| bidding_rounds | id, eval_task_id, round_number, deadline, status(open/closed), created_at | (eval_task_id, round_number) | evaluation_tasks |
| bidding_submissions | id, round_id, bidder_id, amount, currency, submitted_at | (round_id, bidder_id) UNIQUE | bidding_rounds, bidders |
| material_check_results | id, eval_task_id, bidder_id, material_id, status(provided/missing/suspicious), ai_analysis, checked_at | (eval_task_id, bidder_id) | evaluation_tasks, bidders, evaluation_materials |
| disqualification_checks | id, eval_task_id, bidder_id, condition_name, result(pass/attention/disqualified), explanation, confirmed_by, confirmed_at | (eval_task_id, bidder_id) | evaluation_tasks, bidders |

### 6.3 评分与留痕相关表（4张）

| 表名 | 核心字段 | 索引 | 关联 |
|------|----------|------|------|
| ai_scores | id, eval_task_id, bidder_id, criteria_id, ai_score, score_basis, created_at | (eval_task_id, bidder_id, criteria_id) | evaluation_tasks, bidders, evaluation_scoring_criteria |
| human_scores | id, eval_task_id, bidder_id, criteria_id, ai_score_id, adjusted_score, original_ai_score, adjustment_reason, adjusted_by, adjusted_at | (eval_task_id, bidder_id, criteria_id) | ai_scores, users |
| supplement_notices | id, eval_task_id, bidder_id, material_ids(jsonb), deadline, status(sent/responded/expired), sent_at, responded_at | (eval_task_id, bidder_id) | evaluation_tasks, bidders |
| eval_audit_trails | id, tenant_id, eval_task_id, operator_type, operator_id, operator_name, action, target_type, target_id, details(jsonb), ip_address, created_at | (eval_task_id, created_at) + (tenant_id, operator_id) | evaluation_tasks |

**注**：eval_audit_trails 表设置触发器禁止UPDATE和DELETE，实现append-only。

---

## 7. 页面清单（锁定）

### 做标书页面（10个）

| 页面 | 路由 | 核心组件 | 对应API | 设计Token主题 |
|------|------|----------|---------|---------------|
| 登录/注册 | /login | 登录表单、注册向导 | auth/* | 浅色居中卡片 |
| 工作台 | /dashboard | 任务看板/表格、筛选栏、空状态引导 | GET /tasks, GET /tasks/board | 主色#2563EB |
| 任务详情 | /tasks/:id | 7步流程指示器、Tab内容区、AI建议面板、Sticky操作栏 | GET /tasks/:id | 主色+语义色 |
| 材料清单 | /tasks/:id (Tab) | 进度摘要卡、清单表格、拖拽上传区、模板下载 | GET /materials, POST /upload | 成功#16A34A/危险#DC2626 |
| AI审核中心 | /tasks/:id (Tab) | 文档标注、AI建议卡片、审核摘要、多步加载 | POST /review, GET /result | 语义色（Error红/Warning橙/Info蓝） |
| 文档输出 | /tasks/:id (Tab) | 输出配置、版本历史、版本对比、下载 | POST /generate, GET /versions | 主色+版本Tag |
| 资质库管理 | /admin/qualifications | 资质表格、失效预警Banner、分类筛选、批量导入 | GET /qualifications, POST /batch-import | 预警色阶（绿/橙/红） |
| 文档片段库 | /admin/fragments | 卡片网格、分类Tab、全文搜索、AI匹配标识 | GET /fragments, GET /search | 主色+卡片表面 |
| 用户与权限 | /admin/users | 角色矩阵、用户列表、邀请 | GET /users, POST /users | 主色+角色Badge |
| 系统设置 | /admin/settings | AI模型配置、存储配额、通知设置、操作日志 | GET/PUT /settings | 浅色表单 |

### 评标书页面（4个）

| 页面 | 路由 | 核心组件 | 对应API | 设计Token主题 |
|------|------|----------|---------|---------------|
| 评标工作台 | /evaluation | 统计卡片、任务表格/看板、筛选栏、创建按钮 | GET /evaluations | 评标色#7C3AED标识 |
| 创建评标任务 | /evaluation/create | 5步向导（项目信息→材料清单→评分办法→评审设置→发布） | POST /evaluations, POST /publish | 主色+步骤条 |
| 评标任务详情 | /evaluation/:id | 6步流程指示器、7个Tab、三栏布局 | GET /evaluations/:id | 主色+语义色 |
| 供应商门户 | /evaluation/portal/:id | 截止倒计时、材料上传、多轮报价、补材料通知、提交记录、评标结束 | GET /portal/:token, POST /upload | 简洁单栏 |

---

## 8. 设计Token（锁定）

### 配色
- **主色**：#2563EB（品牌蓝，选中态/关键链接）
- **CTA色**：#EA580C（行动橙，关键操作按钮）
- **评标标识色**：#7C3AED（纯色，仅用于模式切换标识，非渐变）
- **背景**：#F8FAFC / **表面**：#FFFFFF
- **前景**：#1E293B / **次级**：#334155 / **弱化**：#64748B
- **成功**：#16A34A / **警告**：#D97706 / **危险**：#DC2626 / **信息**：#2563EB
- **边框**：#E2E8F0

### 字体
- **Display**：Inter (400/500/600/700)
- **Body**：Inter + Noto Sans SC (400/500)
- **Mono**：JetBrains Mono (400/500)
- 字号：36/30/24/20/18/16/14/12px（8级）

### 图标库
- **Lucide React (lucide-react@^0.400.0)** — 全项目唯一锁定
- 尺寸：16px（行内）/ 20px（按钮）/ 24px（独立）
- 描边：2px，currentColor继承

### 主题
- 浅色为主，支持深色模式（--bg: #0F172A / --surface: #1E293B / --fg: #F8FAFC）

### 对标品牌
- Linear（信息密度/键盘优先）+ Stripe Dashboard（信任感/数据表格）

---

## 9. 验收标准（锁定——QA测试时以此为唯一依据）

### 做标书验收标准

| 编号 | 功能 | EARS格式验收标准 | 优先级 |
|------|------|-----------------|--------|
| AC-01 | 招标文件解析 | While 用户上传100页以内PDF招标文件，系统**必须**在3分钟内完成解析并生成材料清单 | P0 |
| AC-02 | 文件格式校验 | If 用户上传不支持的格式，系统**必须**提示"不支持的文件格式，请上传PDF/Word/Excel/PPT/图片/压缩包" | P0 |
| AC-03 | 材料清单匹配 | While 系统自动匹配资质库，匹配到的材料**必须**标绿色"已有"并标注来源 | P0 |
| AC-04 | AI审核 | When 用户发起AI审核，系统**必须**在5分钟内输出审核报告，包含4类问题 | P0 |
| AC-05 | 签字审核 | If 标书某页需要签字但未签字，AI审核报告**必须**标注位置和修改建议 | P0 |
| AC-06 | 价格审核 | If 报价表某项未填充，AI审核报告**必须**标注"单价为空，请填充" | P0 |
| AC-07 | 一致性审核 | If 商务标工期与技术标工期不一致，AI审核报告**必须**标注差异 | P0 |
| AC-08 | Word输出 | When 用户选择"按招标要求拆分"，系统**必须**输出资质标/商务标/技术标三个Word | P0 |
| AC-09 | 版本管理 | When 用户修改后再次输出，系统**必须**生成新版本并保留历史版本 | P0 |
| AC-10 | 资质预警 | If 资质30天后到期，系统**必须**自动发送通知并标橙色预警 | P0 |
| AC-11 | 资质失效 | If 资质已过期，系统**必须**标红色"已失效"并禁止引用 | P0 |
| AC-12 | 权限控制 | If 成员尝试修改任务设置，系统**必须**拒绝并提示"权限不足" | P0 |

### 评标书验收标准

| 编号 | 功能 | EARS格式验收标准 | 优先级 |
|------|------|-----------------|--------|
| AC-13 | 评标任务发布 | When 管理员完成5步向导并点击发布，系统**必须**生成供应商入口链接并通知受邀供应商 | P0 |
| AC-14 | 供应商提交截止 | If 当前时间超过提交截止时间，系统**必须**禁止供应商继续提交并显示"已截止" | P0 |
| AC-15 | 材料完整性检查 | When 所有供应商提交截止后，系统**必须**在10分钟内完成AI材料完整性检查 | P0 |
| AC-16 | 废标检测 | If 供应商提交了伪造的ISO证书，系统**必须**标记"疑似伪造"并触发废标预警 | P0 |
| AC-17 | AI初步评分 | When 资格审查通过后，系统**必须**按评分办法对每家供应商进行AI初步评分并输出评分依据 | P0 |
| AC-18 | 人工复审评分 | While 评标专家进行复审，系统**必须**显示AI初评分并允许调整，调整时**必须**记录调整原因 | P0 |
| AC-19 | 多轮报价 | When 管理员发起二次报价，系统**必须**通知所有通过资格审查的供应商并在门户开启新一轮报价入口 | P0 |
| AC-20 | 补材料通知 | When 管理员发送补材料通知，供应商门户**必须**显示通知和倒计时，超时后标记"已超时" | P0 |
| AC-21 | 评标关闭 | When 管理员关闭评标，系统**必须**关闭所有供应商沟通渠道并在门户显示"评标已结束，请等待最终结果" | P0 |
| AC-22 | 操作留痕 | While 评标全过程进行中，系统**必须**记录所有操作（提交/变更/评分调整/通知），日志不可篡改 | P0 |
| AC-23 | 综合排名 | When 所有评分完成后，系统**必须**生成综合排名表含各家总分/技术分/商务分/排名/推荐中标人 | P0 |
| AC-24 | 供应商门户状态 | If 供应商已提交全部必交材料，门户**必须**显示"已提交，等待审核"状态 | P0 |

### 通用验收标准

| 编号 | 功能 | EARS格式验收标准 | 优先级 |
|------|------|-----------------|--------|
| AC-25 | 多项目并行 | While 用户有多个投标/评标任务，系统**必须**在看板和列表中同时展示所有任务 | P0 |
| AC-26 | 批量上传 | When 用户拖拽多个文件到上传区，系统**必须**批量上传并自动关联清单项 | P0 |
| AC-27 | 版本回滚 | When 用户选择回滚到历史版本，系统**必须**恢复该版本内容并生成新版本号 | P0 |
| AC-28 | 清单导出 | When 用户点击导出清单，系统**必须**生成Excel格式清单文件 | P0 |
| AC-29 | 模板下载 | When 用户点击下载模板，系统**必须**生成对应材料的Word模板 | P0 |
| AC-30 | 文档片段搜索 | When 用户输入关键词搜索文档片段，系统**必须**返回全文匹配结果 | P0 |
| AC-31 | AI降级 | If 主AI模型不可用，系统**必须**自动切换到备用模型并继续处理 | P0 |
| AC-32 | 任务分配通知 | When 项目负责人分配任务给成员，成员**必须**收到站内通知 | P0 |

---

## 10. 边界与约束

- 不支持IE浏览器
- 响应式断点：移动端<768px / 平板768-1024px / 桌面>1024px
- 性能目标：招标文件解析（100页）< 3分钟；标书生成（10万字）< 10分钟；AI评标初审 < 10分钟；API p95 < 500ms；首屏 < 3s
- 单文件上传限制：200MB
- 单任务版本上限：100个（超过提示归档，保留最近20个可回滚）
- AI模型RPM限制：Qwen-Plus 120次/分钟（需请求队列）
- AI熔断策略：连续3次失败熔断10分钟
- 浏览器兼容：Chrome/Safari/Firefox最新2版 + Edge最新版
- 供应商门户兼容：Chrome/Safari/Firefox/Edge（支持低2版本）
- 并发：单任务支持10人并发；单评标任务支持50家供应商同时提交
- 文件格式：上传PDF/Word/Excel/PPT/图片/压缩包；输出Word(.docx)
- 评标审计日志：append-only，禁止UPDATE/DELETE，保留≥3年
- 供应商Portal Token：与评标任务绑定，评标关闭后失效

---

## 11. 内嵌已知坑

> 首次开发，暂无历史坑记录。开发过程中踩坑后将追加到此表。

| 坑 | 技术栈指纹 | 根因 | 修法 |
|----|------------|------|------|
| （暂无） | - | - | - |

**预防性提醒**（基于技术栈常见问题）：
1. LangGraph状态序列化：自定义对象需支持序列化，否则检查点恢复失败
2. docxtpl模板渲染：Jinja2语法与Word XML交互时可能产生格式错乱，需预留模板测试
3. PyMuPDF表格提取：合并单元格表格提取不完整，需pdfplumber补充
4. MinIO大文件上传：超过100MB需分片上传，注意超时配置
5. Celery任务追踪：长耗时AI任务需配置任务进度上报，否则前端无法展示进度
6. WebSocket连接管理：供应商门户WebSocket需处理断线重连和Token过期
7. 多轮报价并发提交：需Redis分布式锁防止重复提交
8. 审计日志触发器：PostgreSQL触发器阻止UPDATE/DELETE，测试时需注意mock

---

## 12. 端到端验证步骤

### 做标书核心流程

```bash
# 1. 构建
cd frontend && npm run build
cd backend && pip install -r requirements.txt

# 2. 启动
docker-compose up -d  # PostgreSQL + Redis + MinIO
cd backend && uvicorn main:app --reload
cd frontend && npm run dev

# 3. 核心成功流
# 3.1 注册登录
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test1234","name":"测试用户","company_name":"测试公司"}'
# 断言：返回200 + JWT token

# 3.2 上传招标文件
curl -X POST http://localhost:8000/api/v1/tender-files/upload \
  -H "Authorization: Bearer {token}" \
  -F "file=@tender_sample.pdf"
# 断言：返回 file_id + status: "parsing"

# 3.3 查询解析状态（轮询直到completed）
curl http://localhost:8000/api/v1/tender-files/{file_id}/status \
  -H "Authorization: Bearer {token}"
# 断言：status: "completed" + requirements非空

# 3.4 上传材料 + AI审核 + 生成Word（同v1.0流程）
```

### 评标书核心流程

```bash
# 4. 评标核心成功流
# 4.1 创建评标任务
curl -X POST http://localhost:8000/api/v1/evaluations \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{"project_name":"测试评标项目","tender_no":"TEST-001","tender_entity":"测试单位","budget":"1000000","deadline":"2026-09-01T23:59:59","material_template":[...],"scoring_criteria":[...],"review_settings":{"multi_round_bidding":true,"max_rounds":2,"supplement_notice_minutes":120}}'
# 断言：返回 eval_id + status: "collecting"

# 4.2 发布评标任务
curl -X POST http://localhost:8000/api/v1/evaluations/{eval_id}/publish \
  -H "Authorization: Bearer {admin_token}"
# 断言：返回 portal_url + supplier_tokens[]

# 4.3 供应商提交材料
curl -X POST http://localhost:8000/api/v1/portal/{portal_token}/materials/{mid}/upload \
  -F "file=@bidder_qualification.pdf"
# 断言：返回 status: "submitted" + submitted_at

# 4.4 发起材料完整性检查
curl -X POST http://localhost:8000/api/v1/evaluations/{eval_id}/check-materials \
  -H "Authorization: Bearer {admin_token}"
# 断言：返回 check_id + status: "processing"

# 4.5 发起废标检测
curl -X POST http://localhost:8000/api/v1/evaluations/{eval_id}/detect-disqualification \
  -H "Authorization: Bearer {admin_token}"
# 断言：返回 detect_id + status: "processing"

# 4.6 发起AI评分
curl -X POST http://localhost:8000/api/v1/evaluations/{eval_id}/ai-scoring \
  -H "Authorization: Bearer {admin_token}"
# 断言：返回 scoring_id + status: "processing"

# 4.7 人工调整评分
curl -X PUT http://localhost:8000/api/v1/evaluations/{eval_id}/scores/{bidder_id}/{item_id} \
  -H "Authorization: Bearer {reviewer_token}" \
  -d '{"adjusted_score":14,"reason":"答辩表现优秀，技术上调1分"}'
# 断言：返回 success: true + old_score + new_score

# 4.8 查看综合排名
curl http://localhost:8000/api/v1/evaluations/{eval_id}/ranking \
  -H "Authorization: Bearer {admin_token}"
# 断言：返回 ranking[] 含总分/排名/推荐中标人

# 4.9 关闭评标
curl -X POST http://localhost:8000/api/v1/evaluations/{eval_id}/close \
  -H "Authorization: Bearer {admin_token}"
# 断言：返回 success: true + closed_at

# 5. 关键错误流
# 5.1 供应商逾期提交
curl -X POST http://localhost:8000/api/v1/portal/{expired_token}/materials/{mid}/upload \
  -F "file=@late_submission.pdf"
# 断言：返回403 + "提交已截止"

# 5.2 审计日志不可修改
curl -X PUT http://localhost:8000/api/v1/evaluations/{eval_id}/audit-trail/{log_id} \
  -H "Authorization: Bearer {admin_token}" \
  -d '{"action":"modified"}'
# 断言：返回403 + "Audit trail records are immutable"
```

---

## 13. 变更记录

| 日期 | 变更内容 | 原因 | 影响范围 |
|------|----------|------|----------|
| 2026-08-04 | Spec v1.0 初始版本 | 基于PRD+架构+设计三文档生成 | 做标书全部 |
| 2026-08-05 | Spec v2.0 升级 | 新增评标书业务线（F11-F18）；系统改名"一站式智能招投标平台"；新增评标API 30+端点；新增评标DB表14张；新增评标页面4个；新增评标验收标准12条 | 全部 |
