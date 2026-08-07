"""AI 提示词模板集合。

所有模板均为「v1.0.0」基础版，可由 LLM 工程师按 PROMPT_VERSION 协议升级：
1. 新增同名同版本号工厂（抛 ``ValueError`` 提示）；
2. 调整版本号为 ``v1.0.1``；
3. 在 tests/ai/fixtures 新增快照，避免回归。
"""

from __future__ import annotations

from app.ai.prompts.registry import PromptFactory, PromptTemplate

_TENDER_PARSE_SYSTEM = (
    "你是一站式智能招投标平台的招标文件解析助手。" "请将给定文本解析为 Markdown 章节 + 元数据，输出严格 JSON。"
)
_TENDER_PARSE_USER = (
    "## 项目名称\n{projectName}\n\n"
    "## 招标文件原文\n{rawText}\n\n"
    "请输出包含 summary、sections、metadata 字段的 JSON。"
)


def build_tender_parse_template() -> PromptTemplate:
    return PromptTemplate(
        name="tender_parse",
        version="1.0.0",
        system_prompt=_TENDER_PARSE_SYSTEM,
        user_template=_TENDER_PARSE_USER,
        model="qwen-plus",
        temperature=0.1,
        max_output_tokens=2048,
    )


_REQUIREMENT_EXTRACT_SYSTEM = "你是一名评标专家。请从招标文件提取资格要求、技术要求、评分项与废标项。"
_REQUIREMENT_EXTRACT_USER = (
    "## 项目名称\n{projectName}\n\n"
    "## 招标文件\n{tenderText}\n\n"
    "输出 qualificationRequirements / technicalRequirements / scoringItems / disqualificationItems 的 JSON。"
)


def build_requirement_extract_template() -> PromptTemplate:
    return PromptTemplate(
        name="requirement_extract",
        version="1.0.0",
        system_prompt=_REQUIREMENT_EXTRACT_SYSTEM,
        user_template=_REQUIREMENT_EXTRACT_USER,
        model="qwen-plus",
        temperature=0.1,
        max_output_tokens=2048,
    )


_MATERIAL_MATCH_SYSTEM = (
    "你是资质 / 文档片段匹配助手。" "给定「招标文件要求」与「资质库 + 片段库」，输出每个要求的最佳匹配与依据。"
)
_MATERIAL_MATCH_USER = (
    "## 招标文件材料要求\n{requirements}\n\n"
    "## 资质库候选\n{qualifications}\n\n"
    "## 片段库候选\n{fragments}\n\n"
    "请按 materials 顺序返回 matchConfidence 与 matchedSource 的 JSON。"
)


def build_material_match_template() -> PromptTemplate:
    return PromptTemplate(
        name="material_match",
        version="1.0.0",
        system_prompt=_MATERIAL_MATCH_SYSTEM,
        user_template=_MATERIAL_MATCH_USER,
        model="qwen-plus",
        temperature=0.1,
        max_output_tokens=2048,
    )


_BID_REVIEW_SYSTEM = (
    "你是 AI 投标审核助手，必须在结论中保留证据（文件/页码/原文摘要）。"
    "评分与废标结论只能作为「AI 建议，待人工确认」。"
)
_BID_REVIEW_USER = (
    "## 审核类型\n{reviewTypes}\n\n"
    "## 文件版本 ID\n{fileVersionIds}\n\n"
    "## 已绑定材料\n{materials}\n\n"
    "请输出 findings 数组 + summary 字段的 JSON。"
)


def build_bid_review_template() -> PromptTemplate:
    return PromptTemplate(
        name="bid_review",
        version="1.0.0",
        system_prompt=_BID_REVIEW_SYSTEM,
        user_template=_BID_REVIEW_USER,
        model="qwen-plus",
        temperature=0.2,
        max_output_tokens=2048,
    )


_BID_GENERATE_SYSTEM = "你是标书撰写助手，需要根据材料库与历史标书生成结构化大纲。"
_BID_GENERATE_USER = (
    "## 项目信息\n{projectInfo}\n\n"
    "## 资质与片段库\n{library}\n\n"
    "## 生成模式\n{mode}\n\n"
    "请输出 outline 数组（每项含 section 与 estimatedWords）的 JSON。"
)


def build_bid_generate_template() -> PromptTemplate:
    return PromptTemplate(
        name="bid_generate",
        version="1.0.0",
        system_prompt=_BID_GENERATE_SYSTEM,
        user_template=_BID_GENERATE_USER,
        model="qwen-plus",
        temperature=0.3,
        max_output_tokens=4096,
    )


_RISK_CHECK_SYSTEM = (
    "你是评标风险识别助手，需要识别串标、异常报价、围标等高风险行为。"
    "所有结论必须附带证据 + 置信度，并由人工最终裁决。"
)
_RISK_CHECK_USER = (
    "## 评标任务\n{evaluationId}\n\n"
    "## 供应商报价明细\n{suppliers}\n\n"
    "## 历史报价\n{history}\n\n"
    "请输出 findings 数组（含 type/severity/evidence/confidence）的 JSON。"
)


def build_risk_check_template() -> PromptTemplate:
    return PromptTemplate(
        name="risk_check",
        version="1.0.0",
        system_prompt=_RISK_CHECK_SYSTEM,
        user_template=_RISK_CHECK_USER,
        model="deepseek-v3",
        temperature=0.1,
        max_output_tokens=2048,
    )


_EVALUATION_CHECK_SYSTEM = "你是评标材料完整性检查助手，负责判断必填项与缺失项。"
_EVALUATION_CHECK_USER = (
    "## 评标任务\n{evaluationId}\n\n"
    "## 必填材料\n{requiredMaterials}\n\n"
    "## 供应商提交\n{submissions}\n\n"
    "请输出 completeness（0-1）、missing 数组 的 JSON。"
)


def build_evaluation_check_template() -> PromptTemplate:
    return PromptTemplate(
        name="evaluation_check",
        version="1.0.0",
        system_prompt=_EVALUATION_CHECK_SYSTEM,
        user_template=_EVALUATION_CHECK_USER,
        model="qwen-plus",
        temperature=0.0,
        max_output_tokens=1024,
    )


_EVALUATION_SCORE_SYSTEM = "你是 AI 辅助评分助手，必须为每个评分项提供置信度与依据。" "最终得分仍由人工调整。"
_EVALUATION_SCORE_USER = (
    "## 评分标准\n{scoringCriteria}\n\n"
    "## 供应商响应\n{supplierResponse}\n\n"
    "请输出 scores 数组（含 criterionName / score / confidence / basis）与 overall 的 JSON。"
)


def build_evaluation_score_template() -> PromptTemplate:
    return PromptTemplate(
        name="evaluation_score",
        version="1.0.0",
        system_prompt=_EVALUATION_SCORE_SYSTEM,
        user_template=_EVALUATION_SCORE_USER,
        model="deepseek-v3",
        temperature=0.1,
        max_output_tokens=2048,
    )


_REPORT_GENERATE_SYSTEM = "你是评标报告生成助手，按章节输出 Markdown 报告。"
_REPORT_GENERATE_USER = (
    "## 评标任务\n{evaluationId}\n\n"
    "## 评分汇总\n{ranking}\n\n"
    "## 风险结论\n{risks}\n\n"
    "请输出 reportTitle 与 sections 数组（含 heading / body）的 JSON。"
)


def build_report_generate_template() -> PromptTemplate:
    return PromptTemplate(
        name="report_generate",
        version="1.0.0",
        system_prompt=_REPORT_GENERATE_SYSTEM,
        user_template=_REPORT_GENERATE_USER,
        model="qwen-plus",
        temperature=0.2,
        max_output_tokens=4096,
    )


def all_template_factories() -> list[PromptFactory]:
    return [
        build_tender_parse_template,
        build_requirement_extract_template,
        build_material_match_template,
        build_bid_review_template,
        build_bid_generate_template,
        build_risk_check_template,
        build_evaluation_check_template,
        build_evaluation_score_template,
        build_report_generate_template,
    ]


__all__ = [
    "all_template_factories",
    "build_bid_generate_template",
    "build_bid_review_template",
    "build_evaluation_check_template",
    "build_evaluation_score_template",
    "build_material_match_template",
    "build_report_generate_template",
    "build_requirement_extract_template",
    "build_risk_check_template",
    "build_tender_parse_template",
]
