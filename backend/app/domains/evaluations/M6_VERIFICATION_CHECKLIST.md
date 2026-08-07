# M6 职责核查清单（对照 PROJECT_MASTER_PROMPT V3.1）

> 角色：柠檬汁 / M6  
> 最近审查：2026-08-07（第二轮补强后）  
> 总判读：**仍未达完成定义，但未完成项已明显收敛。**  
> 本轮已补：Portal Refresh Cookie、回执/报告 Binary、截止与关闭测试、仓储骨架。

图例：`[x]` 已具备 · `[~]` 部分/依赖他人 · `[ ]` 未做

---

## A. §5.2 功能卡

| # | 要求 | 状态 | 说明 |
|---|---|---|---|
| A1 | 四领域目录 | [x] | |
| A2 | 草稿配置发布取消状态机 | [x] | |
| A3 | BidTaskSnapshotPort 导入 | [x] | 真 M5 待合入 |
| A4 | 邀请交换/刷新/撤销/轮换/防重放 | [x] | refresh 已改 **Refresh Cookie** |
| A5 | Portal 材料/提交/回执/补材料/报价 | [x] | 回执已为 **PDF Binary** |
| A6 | 检查/风险/评分/排名/报告/关闭/审计 | [~] | AI 结果仍占位，待 M7 |
| A7 | 经 M4 端口 | [~] | adapters 就绪；工作树无 M4 时用 RecordingPorts |
| A8 | 不越界 | [x] | |

---

## B. §8.4 / §8.5 API

| 项 | 状态 |
|---|---|
| 8.4 路由齐全 | [x] 声明完整；未挂中央 Router |
| 8.5 路由齐全 | [x] |
| receipt Binary | [x] |
| report download Binary/重定向 | [x] |
| Portal Refresh Cookie | [x] |

---

## C. 完成定义硬项

| # | 项 | 状态 |
|---|---|---|
| D1 | 中央挂载真实 HTTP | [ ] L0 |
| D2 | 真 JWT/RBAC 三层 | [~] Service 层有；等 M4 |
| D3 | PostgreSQL 持久化 | [~] ORM+映射骨架有；默认仍内存 Store |
| D4 | 异常路径测试 | [x] 截止/关闭/非法迁移/重放等已补 |
| D5 | 审计 | [~] Port 调用有；DB append-only 等 M4 |
| D6 | 覆盖率 ≥85% | [~] 关键路径测通；未出覆盖率报告 |
| D7 | 幂等 | [x] |
| D8 | Decimal | [x] |
| D9 | 隔离/重放 | [x] |
| D10 | 改分留痕 | [x] |

---

## D. 本轮自测命令

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/evaluations tests/portal tests/pricing tests/scoring -q
```

预期：全绿（第二轮后约 23 条量级）。

---

## E. 仍依赖协作（阻塞完成定义）

| 对方 | 事项 |
|---|---|
| L0 | include router；models_registry；Alembic |
| M4 | 合入 develop；Session/JWT；File 签名 URL |
| M5 | BidTaskSnapshotPort |
| M7 | JobResult 回写（材料/风险/评分/报告） |
| M2 | API 测通后接前端 |

---

## F. 柠檬汁下一步（自己）

1. develop 同步 M4 后跑 `build_m6_container_with_m4` 联调冒烟  
2. 实现 `SqlAlchemyEvaluationRepository` 完整 CRUD（迁移后）  
3. 请求体改为 `contracts.generated` 模型  
4. 出覆盖率报告并向 85% 补测  
5. 提纯 M6 PR（勿含根目录 `M4_SERVICE_USAGE.md`）

---

## G. 结论

**业务与契约缺口（Cookie/Binary/关键异常）已在本轮补强并通过测试。**  
**不能宣称 M6 全部完成**：缺中央挂载、真 DB、真 M4/M5/M7 联调与覆盖率门禁。
