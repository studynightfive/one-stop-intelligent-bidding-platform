# 一站式智能招投标平台

面向企业投标与采购评标的一站式平台。仓库当前包含经过浏览器回归的 React 前端 Demo、产品/架构/设计文档，以及供 8 人小组继续完成全栈项目的统一开发提示词。

## 首先阅读

- [`PROJECT_MASTER_PROMPT.md`](PROJECT_MASTER_PROMPT.md)：唯一权威的功能范围、7 名组员分工、接口契约、环境版本和合并规则。
- [`Demo优化实施汇总_V1.1.md`](Demo优化实施汇总_V1.1.md)：当前 Demo 已完成的优化。
- `PRD.md`、`ARCHITECTURE.md`、`DESIGN.md`、`SPEC.md`：背景资料；冲突时以总提示词为准。

## 运行当前前端 Demo

要求 Node.js `24.16.0`、npm `11.13.0`。

```bash
cd demo
npm ci
npm run dev
```

浏览器打开：<http://127.0.0.1:3210>

生产构建：

```bash
cd demo
npm run build
```

## 小组协作

组长先在 GitHub 建立 `main`、`develop` 保护规则；成员按 `PROJECT_MASTER_PROMPT.md` 的 M1-M7 文件所有权和分支规则开发。任何接口变化必须先走 CONTRACT-CHANGE，不允许口头约定或成员自行创建同义接口。

## 当前状态

- 前端 Demo：可运行、可构建、主要流程可交互。
- 全栈后端、AI、基础设施与 E2E：按总提示词分阶段实现。
- 仓库默认不包含任何真实密钥、供应商文件或生产数据。
