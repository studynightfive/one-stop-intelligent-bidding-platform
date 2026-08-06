// ===== Evaluation (评标书) mock data =====

// 评标任务状态
export const evalStatusMap: Record<string, { label: string; color: string; step: string }> = {
  collecting: { label: '材料收集中', color: 'blue', step: '供应商提交中' },
  pending: { label: '待评审', color: 'default', step: '等待开始' },
  ai_review: { label: 'AI初审中', color: 'purple', step: 'AI智能初审' },
  human_review: { label: '人工复审', color: 'orange', step: '人工复审' },
  completed: { label: '已完成', color: 'green', step: '评标完成' },
  closed: { label: '已关闭', color: 'default', step: '评标已关闭' },
}

// ===== 评标工作流（6步完整闭环）=====
export const evalWorkflowSteps = [
  { step: 1, title: '发布评标', desc: '创建评标任务，配置材料清单与评分办法，发布供应商提交页面', icon: 'Megaphone' },
  { step: 2, title: '供应商提交', desc: '供应商登录后在截止时间前提交各项材料与报价', icon: 'Upload' },
  { step: 3, title: '材料审核', desc: 'AI审查材料完整性，缺失项通知供应商限时补充', icon: 'ClipboardCheck' },
  { step: 4, title: '评标评审', desc: 'AI初审+人工复审，资格审查、技术评分、商务评分', icon: 'Bot' },
  { step: 5, title: '结果公示', desc: '综合评分排名，生成评标报告与中标候选人', icon: 'FileBarChart' },
  { step: 6, title: '评标关闭', desc: '关闭所有沟通渠道，通知供应商等待最终结果', icon: 'Lock' },
]

export const evaluationTasks = [
  {
    id: 'EVAL-2026-001',
    projectName: '2026年深圳市政务云平台采购项目',
    tenderNo: 'SZGYY-2026-0312',
    tenderEntity: '深圳市政务服务数据管理局',
    budget: '12,800,000.00',
    deadline: '2026-08-25',
    status: 'ai_review',
    currentStep: 4,
    progress: 55,
    assignee: '刘德海',
    bidderCount: 4,
    createdAt: '2026-08-07',
    tags: ['云计算', '政务', '基础设施'],
  },
  {
    id: 'EVAL-2026-002',
    projectName: '华南地区企业数字化转型咨询服务',
    tenderNo: 'HNZX-2026-0089',
    tenderEntity: '广东省工业互联网协会',
    budget: '5,000,000.00',
    deadline: '2026-08-20',
    status: 'human_review',
    currentStep: 4,
    progress: 80,
    assignee: '周天宇',
    bidderCount: 4,
    createdAt: '2026-08-01',
    tags: ['咨询', '数字化转型'],
  },
  {
    id: 'EVAL-2026-003',
    projectName: '某集团ERP系统升级项目',
    tenderNo: 'GRP-ERP-2026-0156',
    tenderEntity: '华润集团',
    budget: '8,500,000.00',
    deadline: '2026-08-10',
    status: 'closed',
    currentStep: 6,
    progress: 100,
    assignee: '刘德海',
    bidderCount: 5,
    createdAt: '2026-07-15',
    tags: ['ERP', '企业信息化', '已关闭'],
  },
  {
    id: 'EVAL-2026-004',
    projectName: '智慧城市数据中台建设项目',
    tenderNo: 'ZHCSSJ-2026-0078',
    tenderEntity: '广州市天河区政务服务中心',
    budget: '15,000,000.00',
    deadline: '2026-09-10',
    status: 'collecting',
    currentStep: 2,
    progress: 15,
    assignee: '刘德海',
    bidderCount: 6,
    createdAt: '2026-08-05',
    tags: ['智慧城市', '数据中台', '材料收集中'],
  },
  {
    id: 'EVAL-2026-005',
    projectName: '公安系统网络安全运维服务',
    tenderNo: 'GAWL-2026-0045',
    tenderEntity: '广州市公安局',
    budget: '3,200,000.00',
    deadline: '2026-08-15',
    status: 'completed',
    currentStep: 5,
    progress: 100,
    assignee: '周天宇',
    bidderCount: 3,
    createdAt: '2026-07-20',
    tags: ['安全', '运维', '已完成'],
  },
]

// ===== 评标任务详情数据 =====

export const evalProjectInfo = {
  projectName: '2026年深圳市政务云平台采购项目',
  tenderNo: 'SZGYY-2026-0312',
  tenderEntity: '深圳市政务服务数据管理局',
  budget: '12,800,000.00',
  deadline: '2026-08-25 17:00',
  duration: '300天',
  scoringMethod: '综合评分法',
  bidderCount: 3,
}

// 投标人列表
export const bidders = [
  { id: 'B01', name: '深圳市智联科技有限公司', quotedPrice: '12,800,000.00', status: 'qualified', score: null },
  { id: 'B02', name: '广州云图信息技术有限公司', quotedPrice: '11,950,000.00', status: 'qualified', score: null },
  { id: 'B03', name: '北京华信科技股份公司', quotedPrice: '13,200,000.00', status: 'disqualified', score: null },
]

// 资格审查 - 材料完整性检查
export const materialCheckResults = [
  { id: 'MC01', bidderId: 'B01', bidderName: '深圳智联科技', material: '营业执照副本', required: true, status: 'provided', note: '有效期内' },
  { id: 'MC02', bidderId: 'B01', bidderName: '深圳智联科技', material: 'ISO 9001认证', required: true, status: 'provided', note: '有效期至2026-09' },
  { id: 'MC03', bidderId: 'B01', bidderName: '深圳智联科技', material: 'ISO 27001认证', required: true, status: 'provided', note: '有效期至2026-12' },
  { id: 'MC04', bidderId: 'B01', bidderName: '深圳智联科技', material: 'CMMI 3级认证', required: true, status: 'missing', note: '未提供CMMI认证' },
  { id: 'MC05', bidderId: 'B01', bidderName: '深圳智联科技', material: 'ITSS证书', required: true, status: 'provided', note: '三级' },
  { id: 'MC06', bidderId: 'B01', bidderName: '深圳智联科技', material: '近三年审计报告', required: true, status: 'provided', note: '2023-2025年度' },
  { id: 'MC07', bidderId: 'B01', bidderName: '深圳智联科技', material: '投标保证金凭证', required: true, status: 'provided', note: '50万元' },
  { id: 'MC08', bidderId: 'B01', bidderName: '深圳智联科技', material: '类似项目业绩证明', required: true, status: 'provided', note: '3个，金额均≥500万' },
  { id: 'MC09', bidderId: 'B01', bidderName: '深圳智联科技', material: '安全生产许可证', required: false, status: 'provided', note: '有效期至2026-08-25（即将过期）' },
  { id: 'MC10', bidderId: 'B01', bidderName: '深圳智联科技', material: '投标函签字盖章', required: true, status: 'provided', note: '签字盖章完整' },

  { id: 'MC11', bidderId: 'B02', bidderName: '广州云图信息', material: '营业执照副本', required: true, status: 'provided', note: '有效期内' },
  { id: 'MC12', bidderId: 'B02', bidderName: '广州云图信息', material: 'ISO 9001认证', required: true, status: 'provided', note: '有效期至2027-03' },
  { id: 'MC13', bidderId: 'B02', bidderName: '广州云图信息', material: 'ISO 27001认证', required: true, status: 'missing', note: '未提供信息安全认证' },
  { id: 'MC14', bidderId: 'B02', bidderName: '广州云图信息', material: 'CMMI 3级认证', required: true, status: 'provided', note: 'CMMI 3级' },
  { id: 'MC15', bidderId: 'B02', bidderName: '广州云图信息', material: 'ITSS证书', required: true, status: 'provided', note: '三级' },
  { id: 'MC16', bidderId: 'B02', bidderName: '广州云图信息', material: '近三年审计报告', required: true, status: 'provided', note: '2023-2025年度' },
  { id: 'MC17', bidderId: 'B02', bidderName: '广州云图信息', material: '投标保证金凭证', required: true, status: 'provided', note: '50万元' },
  { id: 'MC18', bidderId: 'B02', bidderName: '广州云图信息', material: '类似项目业绩证明', required: true, status: 'provided', note: '4个案例' },
  { id: 'MC19', bidderId: 'B02', bidderName: '广州云图信息', material: '投标函签字盖章', required: true, status: 'provided', note: '签字盖章完整' },

  { id: 'MC20', bidderId: 'B03', bidderName: '北京华信科技', material: '营业执照副本', required: true, status: 'provided', note: '有效期内' },
  { id: 'MC21', bidderId: 'B03', bidderName: '北京华信科技', material: 'ISO 9001认证', required: true, status: 'fake', note: 'AI检测到证书编号异常，疑似伪造', risk: 'high' },
  { id: 'MC22', bidderId: 'B03', bidderName: '北京华信科技', material: 'ISO 27001认证', required: true, status: 'missing', note: '未提供' },
  { id: 'MC23', bidderId: 'B03', bidderName: '北京华信科技', material: 'CMMI 3级认证', required: true, status: 'provided', note: 'CMMI 3级' },
  { id: 'MC24', bidderId: 'B03', bidderName: '北京华信科技', material: '投标保证金凭证', required: true, status: 'missing', note: '未提供保证金缴纳凭证' },
  { id: 'MC25', bidderId: 'B03', bidderName: '北京华信科技', material: '类似项目业绩证明', required: true, status: 'fake', note: 'AI检测到2个业绩合同编号重复，疑似虚假业绩', risk: 'high' },
  { id: 'MC26', bidderId: 'B03', bidderName: '北京华信科技', material: '投标函签字盖章', required: true, status: 'provided', note: '仅有盖章，无法定代表人签字' },
]

export const materialCheckStatusMap: Record<string, { label: string; color: string; bg: string }> = {
  provided: { label: '已提供', color: '#16A34A', bg: '#F0FDF4' },
  missing: { label: '缺失', color: '#DC2626', bg: '#FEF2F2' },
  fake: { label: '疑似伪造', color: '#DC2626', bg: '#FEF2F2' },
}

// 废标检测
export const disqualificationChecks = [
  { id: 'DQ01', bidderId: 'B01', bidderName: '深圳智联科技', item: '投标文件签字盖章', result: 'pass', desc: '投标函、授权委托书等关键文件签字盖章完整' },
  { id: 'DQ02', bidderId: 'B01', bidderName: '深圳智联科技', item: '投标报价未超预算', result: 'pass', desc: '报价12,800,000元，未超过预算12,800,000元（等于预算上限，需关注）' },
  { id: 'DQ03', bidderId: 'B01', bidderName: '深圳智联科技', item: '资质文件有效性', result: 'warning', desc: '安全生产许可证将于8月25日到期（评标日当天），建议确认是否在有效期内' },
  { id: 'DQ04', bidderId: 'B01', bidderName: '深圳智联科技', item: '投标保证金', result: 'pass', desc: '已缴纳50万元投标保证金' },
  { id: 'DQ05', bidderId: 'B01', bidderName: '深圳智联科技', item: '工期满足要求', result: 'pass', desc: '承诺工期270天，满足≤300天要求' },
  { id: 'DQ06', bidderId: 'B01', bidderName: '深圳智联科技', item: '商务标与技术标一致性', result: 'warning', desc: '商务标工期270天，技术标工期300天，存在不一致（注：此项目为做标方自查修正后的版本，实际评审中如发现应记录）' },
  { id: 'DQ07', bidderId: 'B01', bidderName: '深圳智联科技', item: '业绩证明数量', result: 'pass', desc: '提供3个类似项目业绩，满足至少3个的要求' },
  { id: 'DQ08', bidderId: 'B01', bidderName: '深圳智联科技', item: '材料真实性', result: 'pass', desc: 'AI未检测到伪造或虚假材料' },

  { id: 'DQ09', bidderId: 'B02', bidderName: '广州云图信息', item: '投标文件签字盖章', result: 'pass', desc: '关键文件签字盖章完整' },
  { id: 'DQ10', bidderId: 'B02', bidderName: '广州云图信息', item: '投标报价未超预算', result: 'pass', desc: '报价11,950,000元，低于预算' },
  { id: 'DQ11', bidderId: 'B02', bidderName: '广州云图信息', item: '资质文件有效性', result: 'warning', desc: '缺少ISO 27001信息安全管理体系认证（招标文件要求项）' },
  { id: 'DQ12', bidderId: 'B02', bidderName: '广州云图信息', item: '投标保证金', result: 'pass', desc: '已缴纳50万元' },
  { id: 'DQ13', bidderId: 'B02', bidderName: '广州云图信息', item: '工期满足要求', result: 'pass', desc: '承诺工期285天，满足要求' },
  { id: 'DQ14', bidderId: 'B02', bidderName: '广州云图信息', item: '商务标与技术标一致性', result: 'pass', desc: '两标工期一致' },
  { id: 'DQ15', bidderId: 'B02', bidderName: '广州云图信息', item: '业绩证明数量', result: 'pass', desc: '提供4个类似项目' },
  { id: 'DQ16', bidderId: 'B02', bidderName: '广州云图信息', item: '材料真实性', result: 'pass', desc: '未检测到伪造材料' },

  { id: 'DQ17', bidderId: 'B03', bidderName: '北京华信科技', item: '投标文件签字盖章', result: 'fail', desc: '投标函缺少法定代表人签字，仅加盖公章' },
  { id: 'DQ18', bidderId: 'B03', bidderName: '北京华信科技', item: '投标报价未超预算', result: 'pass', desc: '报价13,200,000元，超过预算12,800,000元，已超预算（废标）' },
  { id: 'DQ19', bidderId: 'B03', bidderName: '北京华信科技', item: '资质文件有效性', result: 'fail', desc: 'ISO 9001证书编号经AI比对全国认证数据库，编号不存在，疑似伪造' },
  { id: 'DQ20', bidderId: 'B03', bidderName: '北京华信科技', item: '投标保证金', result: 'fail', desc: '未提供投标保证金缴纳凭证' },
  { id: 'DQ21', bidderId: 'B03', bidderName: '北京华信科技', item: '工期满足要求', result: 'pass', desc: '承诺工期260天，满足要求' },
  { id: 'DQ22', bidderId: 'B03', bidderName: '北京华信科技', item: '业绩证明真实性', result: 'fail', desc: 'AI检测到2个业绩合同编号在全国企业信用系统中重复，疑似虚假业绩' },
  { id: 'DQ23', bidderId: 'B03', bidderName: '北京华信科技', item: '材料真实性', result: 'fail', desc: '检测到2项材料疑似伪造，1项业绩虚假' },
]

export const disqualResultMap: Record<string, { label: string; color: string; bg: string }> = {
  pass: { label: '通过', color: '#16A34A', bg: '#F0FDF4' },
  warning: { label: '需关注', color: '#D97706', bg: '#FFFBEB' },
  fail: { label: '废标', color: '#DC2626', bg: '#FEF2F2' },
}

// 评分办法（权重项）
export const scoringCriteria = [
  // 商务标
  { id: 'SC01', category: 'commercial', name: '商务报价', maxScore: 30, weight: 30, method: '最低价得分法', desc: '有效投标中最低价为满分，其他按比例计算：得分 = (最低价 / 投标报价) × 30' },
  { id: 'SC02', category: 'commercial', name: '报价合理性', maxScore: 5, weight: 5, method: '专家打分', desc: '报价明细完整性、价格构成合理性' },

  // 技术标
  { id: 'SC03', category: 'technical', name: '总体架构方案', maxScore: 15, weight: 15, method: '专家打分', desc: '系统架构合理性、技术先进性、扩展性' },
  { id: 'SC04', category: 'technical', name: '安全方案', maxScore: 10, weight: 10, method: '专家打分', desc: '等保三级达标、安全架构完整性' },
  { id: 'SC05', category: 'technical', name: '实施方案', maxScore: 10, weight: 10, method: '专家打分', desc: '实施计划可行性、里程碑合理性' },
  { id: 'SC06', category: 'technical', name: '运维方案', maxScore: 5, weight: 5, method: '专家打分', desc: 'SLA承诺、运维体系完整性' },

  // 资质标
  { id: 'SC07', category: 'qualification', name: '企业资质', maxScore: 15, weight: 15, method: '客观项', desc: 'ISO 9001(5分) + ISO 27001(5分) + CMMI(5分)' },
  { id: 'SC08', category: 'qualification', name: '业绩案例', maxScore: 10, weight: 10, method: '客观项', desc: '每个类似项目3分，最高10分' },

  // 售后
  { id: 'SC09', category: 'service', name: '售后服务', maxScore: 5, weight: 5, method: '专家打分', desc: '服务方案2分 + SLA承诺3分' },
]

// AI初评分数
export const aiScores = [
  // 深圳智联科技 B01
  { criteriaId: 'SC01', bidderId: 'B01', bidderName: '深圳智联科技', aiScore: 28.5, aiReason: '报价12,800,000元，为3家有效投标人中最高价。按最低价得分法：(11,950,000 / 12,800,000) × 30 = 28.0分。考虑报价等于预算上限，略有风险。' },
  { criteriaId: 'SC02', bidderId: 'B01', bidderName: '深圳智联科技', aiScore: 4.5, aiReason: '报价明细完整，CPU/内存/存储/带宽分项清晰，价格构成合理。扣0.5分因对象存储单价偏高。' },
  { criteriaId: 'SC03', bidderId: 'B01', bidderName: '深圳智联科技', aiScore: 13, aiReason: '架构方案基于K8s容器编排，微服务架构设计合理。技术路线先进，扩展性良好。但多租户隔离方案描述不够详细。' },
  { criteriaId: 'SC04', bidderId: 'B01', bidderName: '深圳智联科技', aiScore: 9, aiReason: '安全方案依据等保三级要求，包含安全架构图。扣1分因备份策略描述不完整。' },
  { criteriaId: 'SC05', bidderId: 'B01', bidderName: '深圳智联科技', aiScore: 9, aiReason: '实施计划分为5阶段，含甘特图和里程碑。扣1分因应急响应方案缺失。' },
  { criteriaId: 'SC06', bidderId: 'B01', bidderName: '深圳智联科技', aiScore: 4.5, aiReason: '运维方案7×24小时，SLA承诺99.99%。但两处SLA不一致（技术标99.9% vs 运维方案99.99%）。' },
  { criteriaId: 'SC07', bidderId: 'B01', bidderName: '深圳智联科技', aiScore: 10, aiReason: 'ISO 9001(5分) + ISO 27001(5分) = 10分。缺少CMMI认证，扣5分。' },
  { criteriaId: 'SC08', bidderId: 'B01', bidderName: '深圳智联科技', aiScore: 9, aiReason: '提供3个类似项目业绩，每个3分 = 9分。' },
  { criteriaId: 'SC09', bidderId: 'B01', bidderName: '深圳智联科技', aiScore: 4.5, aiReason: '服务方案完整，SLA承诺99.99%可用性，故障响应≤15分钟。扣0.5分因未明确升级流程。' },

  // 广州云图信息 B02
  { criteriaId: 'SC01', bidderId: 'B02', bidderName: '广州云图信息', aiScore: 30, aiReason: '报价11,950,000元，为最低价，得满分30分。' },
  { criteriaId: 'SC02', bidderId: 'B02', bidderName: '广州云图信息', aiScore: 4, aiReason: '报价明细基本完整，但部分云资源规格未明确。' },
  { criteriaId: 'SC03', bidderId: 'B02', bidderName: '广州云图信息', aiScore: 12, aiReason: '架构方案基于OpenStack，技术成熟但扩展性稍逊。微服务拆分合理。' },
  { criteriaId: 'SC04', bidderId: 'B02', bidderName: '广州云图信息', aiScore: 7, aiReason: '安全方案缺少ISO 27001认证支撑，等保三级方案描述不够深入。' },
  { criteriaId: 'SC05', bidderId: 'B02', bidderName: '广州云图信息', aiScore: 8.5, aiReason: '实施计划合理，含里程碑。但风险应对措施不够具体。' },
  { criteriaId: 'SC06', bidderId: 'B02', bidderName: '广州云图信息', aiScore: 4, aiReason: '运维方案7×24小时，SLA承诺99.95%。低于智联科技的99.99%。' },
  { criteriaId: 'SC07', bidderId: 'B02', bidderName: '广州云图信息', aiScore: 15, aiReason: 'ISO 9001(5分) + ISO 27001缺失 + CMMI 3级(5分) + ITSS(5分) = 15分。注：ISO 27001缺失，但CMMI和ITSS有额外加分。' },
  { criteriaId: 'SC08', bidderId: 'B02', bidderName: '广州云图信息', aiScore: 10, aiReason: '提供4个类似项目业绩，超过3个上限，得满分10分。' },
  { criteriaId: 'SC09', bidderId: 'B02', bidderName: '广州云图信息', aiScore: 4, aiReason: '服务方案基本完整，SLA承诺99.95%。' },
]

// 人工复审分数
export const humanScores = [
  { criteriaId: 'SC01', bidderId: 'B01', aiScore: 28.5, humanScore: 28.5, comment: 'AI计算正确，维持原评', reviewer: '刘德海', reviewedAt: '2026-08-05 10:30' },
  { criteriaId: 'SC02', bidderId: 'B01', aiScore: 4.5, humanScore: 4, comment: '对象存储单价确实偏高，调整为4分', reviewer: '刘德海', reviewedAt: '2026-08-05 10:35' },
  { criteriaId: 'SC03', bidderId: 'B01', aiScore: 13, humanScore: 14, comment: '架构方案整体优秀，多租户方案在答辩中补充说明充分，上调至14分', reviewer: '刘德海', reviewedAt: '2026-08-05 10:42' },
  { criteriaId: 'SC04', bidderId: 'B01', aiScore: 9, humanScore: 9, comment: '维持AI评分', reviewer: '刘德海', reviewedAt: '2026-08-05 10:45' },
  { criteriaId: 'SC05', bidderId: 'B01', aiScore: 9, humanScore: 9, comment: '维持AI评分', reviewer: '刘德海', reviewedAt: '2026-08-05 10:48' },
  { criteriaId: 'SC06', bidderId: 'B01', aiScore: 4.5, humanScore: 5, comment: '运维方案整体完善，SLA不一致为笔误，以99.99%为准，给满分', reviewer: '刘德海', reviewedAt: '2026-08-05 10:52' },
  { criteriaId: 'SC07', bidderId: 'B01', aiScore: 10, humanScore: 10, comment: '维持AI评分', reviewer: '刘德海', reviewedAt: '2026-08-05 10:55' },
  { criteriaId: 'SC08', bidderId: 'B01', aiScore: 9, humanScore: 9, comment: '维持AI评分', reviewer: '刘德海', reviewedAt: '2026-08-05 10:58' },
  { criteriaId: 'SC09', bidderId: 'B01', aiScore: 4.5, humanScore: 4.5, comment: '维持AI评分', reviewer: '刘德海', reviewedAt: '2026-08-05 11:00' },

  { criteriaId: 'SC01', bidderId: 'B02', aiScore: 30, humanScore: 30, comment: '最低价满分，维持', reviewer: '周天宇', reviewedAt: '2026-08-04 15:20' },
  { criteriaId: 'SC02', bidderId: 'B02', aiScore: 4, humanScore: 4, comment: '维持AI评分', reviewer: '周天宇', reviewedAt: '2026-08-04 15:25' },
  { criteriaId: 'SC03', bidderId: 'B02', aiScore: 12, humanScore: 12.5, comment: '架构方案有亮点，微调至12.5', reviewer: '周天宇', reviewedAt: '2026-08-04 15:30' },
  { criteriaId: 'SC04', bidderId: 'B02', aiScore: 7, humanScore: 7, comment: '缺少ISO 27001是硬伤，维持7分', reviewer: '周天宇', reviewedAt: '2026-08-04 15:35' },
  { criteriaId: 'SC05', bidderId: 'B02', aiScore: 8.5, humanScore: 8.5, comment: '维持AI评分', reviewer: '周天宇', reviewedAt: '2026-08-04 15:38' },
  { criteriaId: 'SC06', bidderId: 'B02', aiScore: 4, humanScore: 4, comment: '维持AI评分', reviewer: '周天宇', reviewedAt: '2026-08-04 15:40' },
  { criteriaId: 'SC07', bidderId: 'B02', aiScore: 15, humanScore: 15, comment: '维持AI评分', reviewer: '周天宇', reviewedAt: '2026-08-04 15:42' },
  { criteriaId: 'SC08', bidderId: 'B02', aiScore: 10, humanScore: 10, comment: '维持AI评分', reviewer: '周天宇', reviewedAt: '2026-08-04 15:45' },
  { criteriaId: 'SC09', bidderId: 'B02', aiScore: 4, humanScore: 4, comment: '维持AI评分', reviewer: '周天宇', reviewedAt: '2026-08-04 15:48' },
]

// 综合评标结果
export const finalResults = [
  {
    bidderId: 'B01',
    bidderName: '深圳市智联科技有限公司',
    quotedPrice: '12,800,000.00',
    priceScore: 28.5,
    technicalScore: 37,
    qualificationScore: 19,
    serviceScore: 4.5,
    totalScore: 89,
    aiTotalScore: 87.5,
    ranking: 1,
    status: 'recommended',
    conclusion: '综合评分排名第一，推荐为中标候选人。技术方案优秀，资质齐全（缺CMMI），报价等于预算上限需关注。',
  },
  {
    bidderId: 'B02',
    bidderName: '广州云图信息技术有限公司',
    quotedPrice: '11,950,000.00',
    priceScore: 30,
    technicalScore: 32,
    qualificationScore: 25,
    serviceScore: 4,
    totalScore: 91,
    aiTotalScore: 90.5,
    ranking: 2,
    status: 'candidate',
    conclusion: '综合评分排名第二。报价最低，资质最全（含CMMI），但缺少ISO 27001认证且技术方案略逊。',
  },
  {
    bidderId: 'B03',
    bidderName: '北京华信科技股份公司',
    quotedPrice: '13,200,000.00',
    priceScore: 0,
    technicalScore: 0,
    qualificationScore: 0,
    serviceScore: 0,
    totalScore: 0,
    aiTotalScore: 0,
    ranking: 3,
    status: 'disqualified',
    conclusion: '废标。触发废标条件：1)投标报价超过预算；2)ISO 9001证书疑似伪造；3)未提供投标保证金；4)业绩证明疑似虚假；5)投标函缺少法定代表人签字。',
  },
]

export const evalCategoryLabels: Record<string, string> = {
  commercial: '商务标',
  technical: '技术标',
  qualification: '资质标',
  service: '售后服务',
}

// 评标通知
export const evalNotifications = [
  { id: 'EN001', type: 'task', title: '新评标任务', content: '"政务云平台采购项目"已收到3家投标人标书，开始AI初审', time: '10分钟前', isRead: false },
  { id: 'EN002', type: 'alert', title: '废标预警', content: '北京华信科技检测到4项废标风险，请人工确认', time: '30分钟前', isRead: false },
  { id: 'EN003', type: 'review', title: 'AI初审完成', content: '"政务云平台采购项目"AI初审完成，2家通过资格审查，1家触发废标', time: '1小时前', isRead: false },
  { id: 'EN004', type: 'score', title: '评分待复审', content: '"数字化转型咨询服务"AI评分已完成，等待专家复审', time: '3小时前', isRead: true },
  { id: 'EN005', type: 'complete', title: '评标完成', content: '"ERP系统升级项目"评标已完成，推荐中标候选人：浪潮软件', time: '1天前', isRead: true },
]

// ===== 供应商提交门户数据 =====

// 供应商提交状态
export const supplierSubmissionStatusMap: Record<string, { label: string; color: string; bg: string }> = {
  submitted: { label: '已提交', color: '#16A34A', bg: '#F0FDF4' },
  partial: { label: '部分提交', color: '#D97706', bg: '#FFFBEB' },
  missing: { label: '未提交', color: '#DC2626', bg: '#FEF2F2' },
  overdue: { label: '逾期未交', color: '#991B1B', bg: '#FEE2E2' },
  supplementing: { label: '补充中', color: '#2563EB', bg: '#EFF6FF' },
}

// 供应商提交记录
export const supplierSubmissions = [
  {
    supplierId: 'S01',
    supplierName: '深圳市智联科技有限公司',
    contact: '张明',
    phone: '138****8888',
    email: 'zhangming@zhilian.com',
    status: 'submitted',
    submitTime: '2026-08-08 14:32:18',
    materialCount: 10,
    requiredCount: 10,
    missingCount: 0,
    priceRound: 2,
    currentPrice: '12,500,000.00',
    isQualified: true,
  },
  {
    supplierId: 'S02',
    supplierName: '广州云图信息技术有限公司',
    contact: '李芳',
    phone: '139****6666',
    email: 'lifang@yuntu.com',
    status: 'submitted',
    submitTime: '2026-08-08 15:10:45',
    materialCount: 9,
    requiredCount: 10,
    missingCount: 1,
    priceRound: 2,
    currentPrice: '11,800,000.00',
    isQualified: true,
  },
  {
    supplierId: 'S03',
    supplierName: '北京华信科技股份公司',
    contact: '王强',
    phone: '137****3333',
    email: 'wangqiang@huaxin.com',
    status: 'partial',
    submitTime: '2026-08-08 16:45:02',
    materialCount: 7,
    requiredCount: 10,
    missingCount: 3,
    priceRound: 1,
    currentPrice: '13,200,000.00',
    isQualified: false,
  },
  {
    supplierId: 'S04',
    supplierName: '上海数擎科技有限公司',
    contact: '陈丽',
    phone: '136****5555',
    email: 'chenli@shuqing.com',
    status: 'supplementing',
    submitTime: '2026-08-08 11:20:33',
    materialCount: 8,
    requiredCount: 10,
    missingCount: 2,
    priceRound: 2,
    currentPrice: '12,000,000.00',
    isQualified: true,
  },
]

// 供应商提交的材料明细（含时间戳和留痕）
export const supplierMaterialRecords = [
  { id: 'SMR01', supplierId: 'S01', supplierName: '深圳智联科技', material: '营业执照副本', fileName: '营业执照_2026.pdf', fileSize: '2.3MB', submitTime: '2026-08-08 14:05:12', status: 'submitted', round: 1 },
  { id: 'SMR02', supplierId: 'S01', supplierName: '深圳智联科技', material: 'ISO 9001认证', fileName: 'ISO9001_智联.pdf', fileSize: '1.1MB', submitTime: '2026-08-08 14:08:33', status: 'submitted', round: 1 },
  { id: 'SMR03', supplierId: 'S01', supplierName: '深圳智联科技', material: 'ISO 27001认证', fileName: 'ISO27001_智联.pdf', fileSize: '0.9MB', submitTime: '2026-08-08 14:10:05', status: 'submitted', round: 1 },
  { id: 'SMR04', supplierId: 'S01', supplierName: '深圳智联科技', material: '投标函', fileName: '投标函_智联.pdf', fileSize: '0.5MB', submitTime: '2026-08-08 14:15:22', status: 'submitted', round: 1 },
  { id: 'SMR05', supplierId: 'S01', supplierName: '深圳智联科技', material: '商务报价文件', fileName: '商务报价_智联_v1.xlsx', fileSize: '0.3MB', submitTime: '2026-08-08 14:20:18', status: 'submitted', round: 1 },
  { id: 'SMR06', supplierId: 'S01', supplierName: '深圳智联科技', material: '商务报价文件（第二轮）', fileName: '商务报价_智联_v2.xlsx', fileSize: '0.3MB', submitTime: '2026-08-09 10:30:15', status: 'submitted', round: 2, note: '二次报价：12,800,000 → 12,500,000' },

  { id: 'SMR07', supplierId: 'S02', supplierName: '广州云图信息', material: '营业执照副本', fileName: '营业执照_云图.pdf', fileSize: '2.1MB', submitTime: '2026-08-08 14:45:00', status: 'submitted', round: 1 },
  { id: 'SMR08', supplierId: 'S02', supplierName: '广州云图信息', material: 'ISO 27001认证', fileName: '', fileSize: '', submitTime: '', status: 'missing', round: 1, note: '未提交，已发补充通知' },
  { id: 'SMR09', supplierId: 'S02', supplierName: '广州云图信息', material: '商务报价文件', fileName: '商务报价_云图_v1.xlsx', fileSize: '0.3MB', submitTime: '2026-08-08 15:00:12', status: 'submitted', round: 1 },
  { id: 'SMR10', supplierId: 'S02', supplierName: '广州云图信息', material: '商务报价文件（第二轮）', fileName: '商务报价_云图_v2.xlsx', fileSize: '0.3MB', submitTime: '2026-08-09 10:35:20', status: 'submitted', round: 2, note: '二次报价：11,950,000 → 11,800,000' },

  { id: 'SMR11', supplierId: 'S03', supplierName: '北京华信科技', material: '营业执照副本', fileName: '营业执照_华信.pdf', fileSize: '2.5MB', submitTime: '2026-08-08 16:20:00', status: 'submitted', round: 1 },
  { id: 'SMR12', supplierId: 'S03', supplierName: '北京华信科技', material: 'ISO 9001认证', fileName: 'ISO9001_华信.pdf', fileSize: '1.2MB', submitTime: '2026-08-08 16:25:30', status: 'submitted', round: 1, note: 'AI标记：证书编号异常，疑似伪造' },
  { id: 'SMR13', supplierId: 'S03', supplierName: '北京华信科技', material: '投标保证金凭证', fileName: '', fileSize: '', submitTime: '', status: 'missing', round: 1, note: '未提交，已发补充通知（未响应）' },
  { id: 'SMR14', supplierId: 'S03', supplierName: '北京华信科技', material: '商务报价文件', fileName: '商务报价_华信_v1.xlsx', fileSize: '0.3MB', submitTime: '2026-08-08 16:45:02', status: 'submitted', round: 1, note: '未参与二次报价' },

  { id: 'SMR15', supplierId: 'S04', supplierName: '上海数擎科技', material: '营业执照副本', fileName: '营业执照_数擎.pdf', fileSize: '2.0MB', submitTime: '2026-08-08 11:00:15', status: 'submitted', round: 1 },
  { id: 'SMR16', supplierId: 'S04', supplierName: '上海数擎科技', material: 'CMMI 3级认证', fileName: '', fileSize: '', submitTime: '', status: 'missing', round: 1, note: '未提交，已发补充通知，供应商补充中' },
  { id: 'SMR17', supplierId: 'S04', supplierName: '上海数擎科技', material: '商务报价文件', fileName: '商务报价_数擎_v1.xlsx', fileSize: '0.3MB', submitTime: '2026-08-08 11:15:30', status: 'submitted', round: 1 },
  { id: 'SMR18', supplierId: 'S04', supplierName: '上海数擎科技', material: '商务报价文件（第二轮）', fileName: '商务报价_数擎_v2.xlsx', fileSize: '0.3MB', submitTime: '2026-08-09 10:40:00', status: 'submitted', round: 2, note: '二次报价：12,300,000 → 12,000,000' },
]

// 多轮报价记录
export const priceRounds = [
  {
    round: 1,
    title: '首轮报价',
    startTime: '2026-08-08 09:00',
    deadline: '2026-08-08 17:00',
    status: 'completed',
    suppliers: [
      { supplierId: 'S01', supplierName: '深圳智联科技', price: '12,800,000.00', submitTime: '2026-08-08 14:20:18', isLowest: false },
      { supplierId: 'S02', supplierName: '广州云图信息', price: '11,950,000.00', submitTime: '2026-08-08 15:00:12', isLowest: true },
      { supplierId: 'S03', supplierName: '北京华信科技', price: '13,200,000.00', submitTime: '2026-08-08 16:45:02', isLowest: false },
      { supplierId: 'S04', supplierName: '上海数擎科技', price: '12,300,000.00', submitTime: '2026-08-08 11:15:30', isLowest: false },
    ],
  },
  {
    round: 2,
    title: '二次报价（竞争性谈判）',
    startTime: '2026-08-09 10:00',
    deadline: '2026-08-09 11:00',
    status: 'completed',
    suppliers: [
      { supplierId: 'S01', supplierName: '深圳智联科技', price: '12,500,000.00', submitTime: '2026-08-09 10:30:15', isLowest: false },
      { supplierId: 'S02', supplierName: '广州云图信息', price: '11,800,000.00', submitTime: '2026-08-09 10:35:20', isLowest: true },
      { supplierId: 'S03', supplierName: '北京华信科技', price: '—', submitTime: '', isLowest: false, note: '未参与（已触发废标条件）' },
      { supplierId: 'S04', supplierName: '上海数擎科技', price: '12,000,000.00', submitTime: '2026-08-09 10:40:00', isLowest: false },
    ],
  },
]

// 补材料通知记录
export const supplementNotifications = [
  {
    id: 'SN01',
    supplierId: 'S02',
    supplierName: '广州云图信息',
    missingMaterials: ['ISO 27001认证'],
    sentTime: '2026-08-08 16:00:00',
    deadline: '2026-08-08 17:30:00',
    remainingMinutes: 90,
    status: 'sent',
    responseTime: null,
    responseStatus: 'pending',
    note: '请在1.5小时内补充提交ISO 27001信息安全管理体系认证文件',
  },
  {
    id: 'SN02',
    supplierId: 'S03',
    supplierName: '北京华信科技',
    missingMaterials: ['投标保证金凭证', 'ISO 27001认证', '类似项目业绩证明'],
    sentTime: '2026-08-08 17:00:00',
    deadline: '2026-08-08 18:30:00',
    remainingMinutes: 0,
    status: 'expired',
    responseTime: null,
    responseStatus: 'no_response',
    note: '供应商未在规定时间内响应补充通知',
  },
  {
    id: 'SN03',
    supplierId: 'S04',
    supplierName: '上海数擎科技',
    missingMaterials: ['CMMI 3级认证', '安全生产许可证'],
    sentTime: '2026-08-08 15:30:00',
    deadline: '2026-08-08 17:00:00',
    remainingMinutes: 0,
    status: 'responded',
    responseTime: '2026-08-08 16:45:00',
    responseStatus: 'supplementing',
    note: '供应商正在补充提交CMMI认证文件，安全生产许可证已提交',
  },
]

// 操作留痕记录（全程审计日志）
export const auditTrail = [
  { id: 'AT01', time: '2026-08-07 09:00:00', operator: '刘德海', role: '评标管理员', action: '创建评标任务', target: '2026年深圳市政务云平台采购项目', detail: '设置截止时间2026-08-08 17:00，4家供应商受邀', ip: '10.1.2.33' },
  { id: 'AT02', time: '2026-08-07 09:05:00', operator: '刘德海', role: '评标管理员', action: '发布评标页面', target: '供应商提交门户', detail: '生成供应商入口链接，发送邀请通知至4家供应商', ip: '10.1.2.33' },
  { id: 'AT03', time: '2026-08-08 11:00:15', operator: '上海数擎科技', role: '供应商', action: '提交材料', target: '营业执照副本', detail: '上传文件 营业执照_数擎.pdf (2.0MB)', ip: '114.85.*.12' },
  { id: 'AT04', time: '2026-08-08 11:15:30', operator: '上海数擎科技', role: '供应商', action: '提交报价', target: '首轮报价', detail: '商务报价 12,300,000.00元', ip: '114.85.*.12' },
  { id: 'AT05', time: '2026-08-08 14:05:12', operator: '深圳智联科技', role: '供应商', action: '提交材料', target: '营业执照副本', detail: '上传文件 营业执照_2026.pdf (2.3MB)', ip: '120.77.*.88' },
  { id: 'AT06', time: '2026-08-08 14:20:18', operator: '深圳智联科技', role: '供应商', action: '提交报价', target: '首轮报价', detail: '商务报价 12,800,000.00元', ip: '120.77.*.88' },
  { id: 'AT07', time: '2026-08-08 15:00:12', operator: '广州云图信息', role: '供应商', action: '提交报价', target: '首轮报价', detail: '商务报价 11,950,000.00元', ip: '59.110.*.45' },
  { id: 'AT08', time: '2026-08-08 16:00:00', operator: '系统', role: 'AI', action: '发送补充通知', target: '广州云图信息', detail: '检测到缺失材料：ISO 27001认证，已发送限时补充通知（90分钟内）', ip: 'system' },
  { id: 'AT09', time: '2026-08-08 16:25:30', operator: '北京华信科技', role: '供应商', action: '提交材料', target: 'ISO 9001认证', detail: '上传文件 ISO9001_华信.pdf (1.2MB) — AI标记异常', ip: '123.59.*.77' },
  { id: 'AT10', time: '2026-08-08 16:45:02', operator: '北京华信科技', role: '供应商', action: '提交报价', target: '首轮报价', detail: '商务报价 13,200,000.00元（超预算）', ip: '123.59.*.77' },
  { id: 'AT11', time: '2026-08-08 17:00:00', operator: '系统', role: 'AI', action: '提交截止', target: '材料提交通道', detail: '到达截止时间，关闭材料提交通道，3家已提交，1家部分提交', ip: 'system' },
  { id: 'AT12', time: '2026-08-08 17:00:00', operator: '系统', role: 'AI', action: '发送补充通知', target: '北京华信科技', detail: '检测到缺失材料3项，已发送限时补充通知（90分钟内）', ip: 'system' },
  { id: 'AT13', time: '2026-08-08 17:30:00', operator: '系统', role: 'AI', action: 'AI材料审查', target: '全部供应商材料', detail: 'AI完成材料完整性检查，检测到1项疑似伪造（华信ISO 9001）', ip: 'system' },
  { id: 'AT14', time: '2026-08-08 18:30:00', operator: '系统', role: 'AI', action: '补充通知过期', target: '北京华信科技', detail: '补充通知已超时，供应商未响应', ip: 'system' },
  { id: 'AT15', time: '2026-08-09 10:00:00', operator: '刘德海', role: '评标管理员', action: '发起二次报价', target: '竞争性谈判', detail: '开启第二轮报价通道，截止时间11:00', ip: '10.1.2.33' },
  { id: 'AT16', time: '2026-08-09 10:30:15', operator: '深圳智联科技', role: '供应商', action: '提交报价', target: '二次报价', detail: '商务报价 12,500,000.00元（降300,000）', ip: '120.77.*.88' },
  { id: 'AT17', time: '2026-08-09 10:35:20', operator: '广州云图信息', role: '供应商', action: '提交报价', target: '二次报价', detail: '商务报价 11,800,000.00元（降150,000）', ip: '59.110.*.45' },
  { id: 'AT18', time: '2026-08-09 10:40:00', operator: '上海数擎科技', role: '供应商', action: '提交报价', target: '二次报价', detail: '商务报价 12,000,000.00元（降300,000）', ip: '114.85.*.12' },
  { id: 'AT19', time: '2026-08-09 11:00:00', operator: '系统', role: 'AI', action: '报价截止', target: '二次报价通道', detail: '3家提交二次报价，1家未参与（华信已触发废标）', ip: 'system' },
  { id: 'AT20', time: '2026-08-09 11:05:00', operator: '系统', role: 'AI', action: 'AI初审启动', target: '全部有效标书', detail: '开始AI材料审查、废标检测、初步评分', ip: 'system' },
]

// 评标创建表单 - 必交材料模板
export const requiredMaterialTemplates = [
  { id: 'RM01', name: '营业执照副本', category: '资质', required: true, isDefault: true },
  { id: 'RM02', name: '法定代表人授权委托书', category: '资质', required: true, isDefault: true },
  { id: 'RM03', name: 'ISO 9001质量管理体系认证', category: '资质', required: true, isDefault: true },
  { id: 'RM04', name: 'ISO 27001信息安全管理体系认证', category: '资质', required: true, isDefault: false },
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

// 已关闭的评标任务示例
export const closedEvaluationExample = {
  projectName: '某集团ERP系统升级项目',
  closedAt: '2026-08-03 17:00:00',
  result: '中标候选人：浪潮软件（综合评分93.5分）',
  message: '评标已结束，所有提交通道已关闭。请等待采购人发布最终结果通知。',
}
