export type EvaluationMaterialTemplate = {
  id: string
  name: string
  category: '资质' | '商务' | '技术'
  required: boolean
  isDefault: boolean
}

export type EvaluationScoringTemplate = {
  id: string
  category: 'commercial' | 'technical' | 'qualification' | 'service'
  name: string
  maxScore: number
  weight: number
  method: string
  desc: string
}

export const DEFAULT_MATERIALS: EvaluationMaterialTemplate[] = [
  { id: 'RM01', name: '营业执照副本', category: '资质', required: true, isDefault: true },
  { id: 'RM02', name: '法定代表人授权委托书', category: '资质', required: true, isDefault: true },
  { id: 'RM03', name: 'ISO 9001质量管理体系认证', category: '资质', required: true, isDefault: true },
  { id: 'RM04', name: 'ISO 27001信息安全管理体系认证', category: '资质', required: false, isDefault: false },
  { id: 'RM05', name: 'CMMI认证', category: '资质', required: false, isDefault: false },
  { id: 'RM06', name: '投标保证金缴纳凭证', category: '商务', required: true, isDefault: true },
  { id: 'RM07', name: '投标函（签字盖章）', category: '商务', required: true, isDefault: true },
  { id: 'RM08', name: '商务报价文件', category: '商务', required: true, isDefault: true },
  { id: 'RM09', name: '技术方案', category: '技术', required: true, isDefault: true },
  { id: 'RM10', name: '实施方案', category: '技术', required: true, isDefault: true },
  { id: 'RM11', name: '运维方案', category: '技术', required: true, isDefault: false },
  { id: 'RM12', name: '类似项目业绩证明', category: '资质', required: true, isDefault: true },
  { id: 'RM13', name: '近三年审计报告', category: '资质', required: false, isDefault: false },
  { id: 'RM14', name: '售后服务承诺书', category: '商务', required: false, isDefault: false },
]

export const DEFAULT_SCORING_ITEMS: EvaluationScoringTemplate[] = [
  { id: 'SC01', category: 'commercial', name: '商务报价', maxScore: 30, weight: 30, method: '最低价得分法', desc: '有效投标中最低价为满分，其他按比例计算：得分 = (最低价 / 投标报价) × 30' },
  { id: 'SC02', category: 'commercial', name: '报价合理性', maxScore: 5, weight: 5, method: '专家打分', desc: '报价明细完整性、价格构成合理性' },
  { id: 'SC03', category: 'technical', name: '总体架构方案', maxScore: 15, weight: 15, method: '专家打分', desc: '系统架构合理性、技术先进性、扩展性' },
  { id: 'SC04', category: 'technical', name: '安全方案', maxScore: 10, weight: 10, method: '专家打分', desc: '等保三级达标、安全架构完整性' },
  { id: 'SC05', category: 'technical', name: '实施方案', maxScore: 10, weight: 10, method: '专家打分', desc: '实施计划可行性、里程碑合理性' },
  { id: 'SC06', category: 'technical', name: '运维方案', maxScore: 5, weight: 5, method: '专家打分', desc: 'SLA承诺、运维体系完整性' },
  { id: 'SC07', category: 'qualification', name: '企业资质', maxScore: 15, weight: 15, method: '客观项', desc: 'ISO 9001(5分) + ISO 27001(5分) + CMMI(5分)' },
  { id: 'SC08', category: 'qualification', name: '业绩案例', maxScore: 10, weight: 10, method: '客观项', desc: '每个类似项目3分，最高10分' },
  { id: 'SC09', category: 'service', name: '售后服务', maxScore: 5, weight: 5, method: '专家打分', desc: '服务方案2分 + SLA承诺3分' },
]

export const EVAL_CATEGORY_LABELS: Record<string, string> = {
  commercial: '商务标',
  technical: '技术标',
  qualification: '资质标',
  service: '售后服务',
}
