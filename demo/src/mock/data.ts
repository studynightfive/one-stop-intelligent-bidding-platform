// Mock data for bid platform demo

export const currentUser = {
  name: '张明远',
  role: '项目负责人',
  email: 'zhangmy@zhilian-tech.com',
  company: '深圳市智联科技有限公司',
  avatar: 'ZM'
}

export const tasks = [
  {
    id: 'TASK-2026-001',
    projectName: '2026年深圳市政务云平台采购项目',
    tenderNo: 'SZGYY-2026-0312',
    deadline: '2026-08-20',
    status: 'material_prep',
    currentStep: 3,
    progress: 45,
    assignee: '张明远',
    materialTotal: 23,
    materialHave: 15,
    materialMissing: 8,
    tenderEntity: '深圳市政务服务数据管理局',
    createdAt: '2026-08-04',
    tags: ['云计算', '政务', '基础设施']
  },
  {
    id: 'TASK-2026-002',
    projectName: '华南地区企业数字化转型咨询服务',
    tenderNo: 'HNZX-2026-0089',
    deadline: '2026-08-15',
    status: 'ai_review',
    currentStep: 6,
    progress: 80,
    assignee: '李雪琴',
    materialTotal: 18,
    materialHave: 18,
    materialMissing: 0,
    tenderEntity: '广东省工业互联网协会',
    createdAt: '2026-07-28',
    tags: ['咨询', '数字化转型']
  },
  {
    id: 'TASK-2026-003',
    projectName: '某集团ERP系统升级项目',
    tenderNo: 'GRP-ERP-2026-0156',
    deadline: '2026-07-30',
    status: 'completed',
    currentStep: 7,
    progress: 100,
    assignee: '王建国',
    materialTotal: 31,
    materialHave: 31,
    materialMissing: 0,
    tenderEntity: '华润集团',
    createdAt: '2026-07-01',
    tags: ['ERP', '企业信息化', '已完成']
  },
  {
    id: 'TASK-2026-004',
    projectName: '智慧城市数据中台建设项目',
    tenderNo: 'ZHCSSJ-2026-0078',
    deadline: '2026-09-05',
    status: 'parsing',
    currentStep: 2,
    progress: 15,
    assignee: '张明远',
    materialTotal: 0,
    materialHave: 0,
    materialMissing: 0,
    tenderEntity: '广州市天河区政务服务中心',
    createdAt: '2026-08-04',
    tags: ['智慧城市', '数据中台']
  },
  {
    id: 'TASK-2026-005',
    projectName: '医疗机构信息化改造工程',
    tenderNo: 'YLXX-2026-0234',
    deadline: '2026-08-28',
    status: 'material_prep',
    currentStep: 5,
    progress: 60,
    assignee: '李雪琴',
    materialTotal: 27,
    materialHave: 20,
    materialMissing: 7,
    tenderEntity: '中山大学附属第一医院',
    createdAt: '2026-07-30',
    tags: ['医疗', '信息化', '改造工程']
  }
]

export const statusMap: Record<string, { label: string; color: string; step: string }> = {
  parsing: { label: 'AI解析中', color: 'blue', step: '解析招标文件' },
  material_prep: { label: '材料准备', color: 'orange', step: '材料清单与上传' },
  ai_review: { label: 'AI审核中', color: 'purple', step: 'AI审核' },
  pending_output: { label: '待输出', color: 'cyan', step: '文档输出' },
  completed: { label: '已完成', color: 'green', step: '完成' }
}

export const workflowSteps = [
  { step: 1, title: '上传招标文件', desc: '上传PDF/Word/Excel等格式招标文件', icon: 'Upload' },
  { step: 2, title: 'AI拆解需求', desc: '智能体解析招标文件，提取评分项、废标项、资质要求', icon: 'FileSearch' },
  { step: 3, title: '材料清单', desc: '展示结构化材料清单，标记已有/缺失', icon: 'ClipboardList' },
  { step: 4, title: '下载模板', desc: '下载清单Excel和缺失材料Word模板', icon: 'Download' },
  { step: 5, title: '批量上传', desc: '拖拽批量上传对应材料文件', icon: 'UploadCloud' },
  { step: 6, title: 'AI审核', desc: '签字提醒/价格检查/内容核对/逻辑一致性', icon: 'ShieldCheck' },
  { step: 7, title: '输出文档', desc: '输出Word投标文件，记录版本', icon: 'FileOutput' }
]

export const materials = [
  // 资质标
  { id: 'M001', name: '营业执照副本', type: '资质文件', requirement: '有效期内，需加盖公章', status: 'have', source: '资质库', part: 'qualification', libraryRef: 'QUAL-001' },
  { id: 'M002', name: 'ISO 9001质量管理体系认证', type: '资质文件', requirement: '在有效期内，提供原件扫描件', status: 'have', source: '资质库', part: 'qualification', libraryRef: 'QUAL-002' },
  { id: 'M003', name: 'ISO 27001信息安全管理体系认证', type: '资质文件', requirement: '在有效期内', status: 'have', source: '资质库', part: 'qualification', libraryRef: 'QUAL-003' },
  { id: 'M004', name: 'CMMI 3级及以上认证', type: '资质文件', requirement: '软件能力成熟度模型集成', status: 'missing', source: '需上传', part: 'qualification', libraryRef: null },
  { id: 'M005', name: 'ITSS信息技术服务标准符合性证书', type: '资质文件', requirement: '三级及以上', status: 'have', source: '资质库', part: 'qualification', libraryRef: 'QUAL-004' },
  { id: 'M006', name: '近三年财务审计报告', type: '财务文件', requirement: '2023-2025年度，由会计师事务所出具', status: 'have', source: '资质库', part: 'qualification', libraryRef: 'QUAL-005' },
  { id: 'M007', name: '安全生产许可证', type: '资质文件', requirement: '在有效期内', status: 'expiring', source: '资质库', part: 'qualification', libraryRef: 'QUAL-006' },
  { id: 'M008', name: '近三年类似项目业绩证明', type: '业绩文件', requirement: '至少3个合同金额≥500万的政务云项目', status: 'missing', source: '需上传', part: 'qualification', libraryRef: null },

  // 商务标
  { id: 'M009', name: '投标函', type: '商务文件', requirement: '按招标文件格式，法定代表人签字盖章', status: 'template', source: '模板可下载', part: 'commercial', libraryRef: null },
  { id: 'M010', name: '投标报价表', type: '商务文件', requirement: '包含总价和分项报价，大小写一致', status: 'template', source: '模板可下载', part: 'commercial', libraryRef: null },
  { id: 'M011', name: '法定代表人授权委托书', type: '商务文件', requirement: '原件，需公证', status: 'have', source: '文档片段库', part: 'commercial', libraryRef: 'FRAG-001' },
  { id: 'M012', name: '投标保证金缴纳凭证', type: '商务文件', requirement: '银行转账凭证，金额50万元', status: 'missing', source: '需上传', part: 'commercial', libraryRef: null },
  { id: 'M013', name: '履约承诺函', type: '商务文件', requirement: '承诺按合同条款履约', status: 'template', source: '模板可下载', part: 'commercial', libraryRef: null },
  { id: 'M014', name: '供应商诚信承诺书', type: '商务文件', requirement: '按招标文件格式', status: 'have', source: '文档片段库', part: 'commercial', libraryRef: 'FRAG-002' },
  { id: 'M015', name: '报价明细表-云资源', type: '商务文件', requirement: 'CPU/内存/存储/带宽分项报价', status: 'missing', source: '需上传', part: 'commercial', libraryRef: null },

  // 技术标
  { id: 'M016', name: '技术方案-总体架构', type: '技术文件', requirement: '包含系统架构图、网络拓扑图', status: 'have', source: '文档片段库', part: 'technical', libraryRef: 'FRAG-003' },
  { id: 'M017', name: '技术方案-云平台建设方案', type: '技术文件', requirement: 'IaaS/PaaS/SaaS层建设方案', status: 'have', source: '文档片段库', part: 'technical', libraryRef: 'FRAG-004' },
  { id: 'M018', name: '技术方案-安全方案', type: '技术文件', requirement: '等保三级要求，含安全架构图', status: 'have', source: '文档片段库', part: 'technical', libraryRef: 'FRAG-005' },
  { id: 'M019', name: '实施方案-项目实施计划', type: '技术文件', requirement: '甘特图，含里程碑节点', status: 'have', source: '文档片段库', part: 'technical', libraryRef: 'FRAG-006' },
  { id: 'M020', name: '运维方案', type: '技术文件', requirement: '7×24小时运维，含SLA承诺', status: 'have', source: '文档片段库', part: 'technical', libraryRef: 'FRAG-007' },
  { id: 'M021', name: '培训方案', type: '技术文件', requirement: '针对运维人员和业务人员分别制定', status: 'have', source: '文档片段库', part: 'technical', libraryRef: 'FRAG-008' },
  { id: 'M022', name: '应急响应方案', type: '技术文件', requirement: '含故障分级和响应时效', status: 'missing', source: '需上传', part: 'technical', libraryRef: null },
  { id: 'M023', name: '数据迁移方案', type: '技术文件', requirement: '存量数据迁移策略和回退方案', status: 'missing', source: '需上传', part: 'technical', libraryRef: null }
]

export const materialStatusMap: Record<string, { label: string; color: string; bg: string }> = {
  have: { label: '已有', color: '#16A34A', bg: '#F0FDF4' },
  missing: { label: '缺失', color: '#DC2626', bg: '#FEF2F2' },
  template: { label: '模板可下载', color: '#2563EB', bg: '#EFF6FF' },
  expiring: { label: '即将过期', color: '#D97706', bg: '#FFFBEB' }
}

export const reviewSuggestions = [
  {
    id: 'S001',
    type: 'signature',
    severity: 'error',
    title: '投标函缺少法定代表人签字',
    description: '投标函第1页标注位置未检测到签字。招标文件要求"投标函须由法定代表人或其授权代表签字并加盖单位公章"。',
    location: '商务标 - 投标函 - 第1页',
    suggestion: '请在签字处添加法定代表人手写签字，并加盖单位公章后重新上传。'
  },
  {
    id: 'S002',
    type: 'price',
    severity: 'error',
    title: '投标报价表-云资源存储单价未填充',
    description: '报价明细表中"对象存储"行单价为空。招标文件要求所有分项必须填写报价。',
    location: '商务标 - 报价明细表 - 第3行',
    suggestion: '请填写对象存储单价（元/GB/月），并确保总价=单价×数量计算正确。'
  },
  {
    id: 'S003',
    type: 'price',
    severity: 'warning',
    title: '报价大小写金额不一致',
    description: '投标报价表总价大写"壹仟贰佰捌拾万元整"，小写"12,800,000.00"，差异为80,000元。',
    location: '商务标 - 投标报价表 - 总价行',
    suggestion: '请核实实际报价金额，确保大小写完全一致。'
  },
  {
    id: 'S004',
    type: 'consistency',
    severity: 'error',
    title: '商务标与技术标工期不一致',
    description: '商务标承诺工期为270天，技术标实施计划中工期为300天。两处工期不一致可能导致废标。',
    location: '商务标-投标函 vs 技术标-实施计划',
    suggestion: '请统一工期口径，建议以技术标的300天为准，同步修改商务标中的工期描述。'
  },
  {
    id: 'S005',
    type: 'content',
    severity: 'warning',
    title: '技术方案未响应招标文件第5.3条要求',
    description: '招标文件5.3条要求"提供多租户隔离方案"，技术方案中未找到相关内容。',
    location: '技术标 - 技术方案 - 第4章',
    suggestion: '请在技术方案中补充多租户隔离方案章节，包括VPC隔离、数据隔离、网络隔离等内容。'
  },
  {
    id: 'S006',
    type: 'content',
    severity: 'info',
    title: '建议补充数据备份策略',
    description: '技术方案中提到了数据安全但未详细说明备份策略。虽然非废标条款，但评分项中有"数据安全保障"（5分）。',
    location: '技术标 - 安全方案 - 第3节',
    suggestion: '建议补充：全量备份周期、增量备份频率、备份保留策略、异地容灾方案等内容，有助于提高评分。'
  },
  {
    id: 'S007',
    type: 'signature',
    severity: 'warning',
    title: '授权委托书需公证',
    description: '招标文件要求法定代表人授权委托书需提供公证原件。当前上传的为复印件扫描件。',
    location: '商务标 - 授权委托书',
    suggestion: '请上传公证后的授权委托书原件扫描件。'
  },
  {
    id: 'S008',
    type: 'consistency',
    severity: 'info',
    title: 'SLA承诺不一致',
    description: '技术方案中承诺"99.9%可用性"，运维方案中承诺"99.99%可用性"。建议统一为更高标准。',
    location: '技术标-技术方案 vs 技术标-运维方案',
    suggestion: '建议统一为99.99%可用性，并在技术方案中同步修改。'
  }
]

export const reviewSummary = {
  total: 8,
  errors: 3,
  warnings: 3,
  info: 2,
  passed: ['资质文件完整性检查', '营业执照有效期', 'ISO认证有效性', '安全生产许可证有效性', '投标保证金金额核对', '业绩证明格式']
}

export const qualifications = [
  { id: 'QUAL-001', name: '营业执照副本', category: '营业执照', certNumber: '91440300MA5FXXXX5K', expiryDate: '2030-06-15', status: 'valid', fileName: '营业执照_2025.pdf' },
  { id: 'QUAL-002', name: 'ISO 9001质量管理体系认证', category: 'ISO证书', certNumber: 'ISO-9001-2023-CN-XXXX', expiryDate: '2026-09-20', status: 'valid', fileName: 'ISO9001_2023.pdf' },
  { id: 'QUAL-003', name: 'ISO 27001信息安全管理体系认证', category: 'ISO证书', certNumber: 'ISO-27001-2023-CN-XXXX', expiryDate: '2026-12-10', status: 'valid', fileName: 'ISO27001_2023.pdf' },
  { id: 'QUAL-004', name: 'ITSS三级证书', category: '行业资质', certNumber: 'ITSS-3-2024-XXXX', expiryDate: '2027-03-25', status: 'valid', fileName: 'ITSS_2024.pdf' },
  { id: 'QUAL-005', name: '2024年度财务审计报告', category: '财务文件', certNumber: 'AUDIT-2024-XXXX', expiryDate: '-', status: 'valid', fileName: '审计报告_2024.pdf' },
  { id: 'QUAL-006', name: '安全生产许可证', category: '安全资质', certNumber: 'AQ-2023-XXXX', expiryDate: '2026-08-25', status: 'expiring', fileName: '安全生产许可证.pdf' },
  { id: 'QUAL-007', name: '高新技术企业证书', category: '行业资质', certNumber: 'GR-2023-XXXX', expiryDate: '2025-12-31', status: 'expired', fileName: '高新技术企业证书.pdf' },
  { id: 'QUAL-008', name: '软件企业认定证书', category: '行业资质', certNumber: 'RJ-2022-XXXX', expiryDate: '2026-10-18', status: 'valid', fileName: '软件企业证书.pdf' },
  { id: 'QUAL-009', name: '增值电信业务经营许可证', category: '行业资质', certNumber: 'B1-2023-XXXX', expiryDate: '2028-05-30', status: 'valid', fileName: 'ICP许可证.pdf' },
  { id: 'QUAL-010', name: '信息系统集成及服务资质（三级）', category: '行业资质', certNumber: 'CIC-3-2024-XXXX', expiryDate: '2026-08-28', status: 'expiring', fileName: '系统集成资质.pdf' }
]

export const qualStatusMap: Record<string, { label: string; color: string; bg: string }> = {
  valid: { label: '有效', color: '#16A34A', bg: '#F0FDF4' },
  expiring: { label: '即将过期', color: '#D97706', bg: '#FFFBEB' },
  expired: { label: '已失效', color: '#DC2626', bg: '#FEF2F2' }
}

export const fragments = [
  { id: 'FRAG-001', title: '法定代表人授权委托书模板', category: '商务文件', preview: '兹授权______同志（身份证号：______）为本公司授权代表，参加______项目的投标活动...', useCount: 23, updatedAt: '2026-07-15', tags: ['商务', '授权', '模板'] },
  { id: 'FRAG-002', title: '供应商诚信承诺书', category: '商务文件', preview: '本公司作为______项目的投标人，郑重承诺如下：一、严格遵守国家法律法规...', useCount: 31, updatedAt: '2026-06-20', tags: ['商务', '承诺', '合规'] },
  { id: 'FRAG-003', title: '云平台总体架构方案', category: '解决方案', preview: '本方案采用"一朵云、两层架构、三大平台"的总体设计思路，基于Kubernetes容器编排...', useCount: 15, updatedAt: '2026-07-30', tags: ['云计算', '架构', 'K8s'] },
  { id: 'FRAG-004', title: '云平台建设方案-标准版', category: '解决方案', preview: '本方案基于OpenStack+Kubernetes双引擎架构，提供IaaS层计算、存储、网络资源池化服务...', useCount: 18, updatedAt: '2026-08-01', tags: ['云计算', 'IaaS', 'PaaS'] },
  { id: 'FRAG-005', title: '信息安全方案-等保三级', category: '解决方案', preview: '本安全方案依据《信息安全技术 网络安全等级保护基本要求》（GB/T 22239-2019）三级要求...', useCount: 22, updatedAt: '2026-07-22', tags: ['安全', '等保', '三级'] },
  { id: 'FRAG-006', title: '项目实施计划模板', category: '实施方案', preview: '本项目实施周期为____天，分为需求调研、方案设计、系统部署、测试验收、上线运行五个阶段...', useCount: 27, updatedAt: '2026-07-10', tags: ['实施', '计划', '项目管理'] },
  { id: 'FRAG-007', title: '运维服务方案-7×24', category: '解决方案', preview: '本公司提供7×24小时不间断运维服务，SLA承诺：核心系统可用性≥99.99%，故障响应≤15分钟...', useCount: 19, updatedAt: '2026-07-25', tags: ['运维', 'SLA', '7x24'] },
  { id: 'FRAG-008', title: '培训方案-标准版', category: '培训方案', preview: '本培训方案针对系统管理员、运维人员、业务人员三类角色，分别制定培训计划...', useCount: 14, updatedAt: '2026-06-28', tags: ['培训', '运维', '业务'] },
  { id: 'FRAG-009', title: '产品手册-云管理平台', category: '产品手册', preview: '云管理平台提供统一资源管理、监控告警、计费计量、服务目录等功能，支持多租户隔离...', useCount: 8, updatedAt: '2026-06-15', tags: ['产品', '云管理'] },
  { id: 'FRAG-010', title: '功能手册-资源调度系统', category: '功能手册', preview: '资源调度系统基于Kubernetes Scheduler扩展开发，支持亲和性/反亲和性调度、优先级调度...', useCount: 5, updatedAt: '2026-05-20', tags: ['功能', '调度', 'K8s'] },
  { id: 'FRAG-011', title: '应急响应方案模板', category: '实施方案', preview: '本方案建立四级应急响应机制：P0级（核心服务中断）、P1级（重要功能异常）、P2级（一般功能异常）...', useCount: 11, updatedAt: '2026-07-05', tags: ['应急', '响应', '运维'] },
  { id: 'FRAG-012', title: '数据迁移方案-标准版', category: '解决方案', preview: '本方案采用"分批迁移+增量同步+验证切换"策略，确保数据迁移过程中业务零中断...', useCount: 9, updatedAt: '2026-06-30', tags: ['数据', '迁移'] }
]

export const fragmentCategories = ['全部', '产品手册', '功能手册', '实施方案', '培训方案', '解决方案', '商务文件']

export const documentVersions = [
  { version: 'v3.2', createdAt: '2026-08-04 14:30', createdBy: '张明远', changeSummary: '根据AI审核建议修正工期不一致、补充多租户方案', status: 'latest' },
  { version: 'v3.1', createdAt: '2026-08-03 16:45', createdBy: '张明远', changeSummary: '更新报价表，修正对象存储单价', status: 'history' },
  { version: 'v3.0', createdAt: '2026-08-02 10:15', createdBy: '李雪琴', changeSummary: '完成全部材料上传，生成完整投标文件', status: 'history' },
  { version: 'v2.0', createdAt: '2026-08-01 09:30', createdBy: '张明远', changeSummary: '技术标补充安全方案和运维方案', status: 'history' },
  { version: 'v1.0', createdAt: '2026-07-31 15:20', createdBy: '系统', changeSummary: 'AI自动生成投标文件初稿', status: 'history' }
]

export const notifications = [
  { id: 'N001', type: 'task', title: '新任务分配', content: '张明远将"智慧城市数据中台建设项目"分配给你', time: '5分钟前', isRead: false },
  { id: 'N002', type: 'review', title: 'AI审核完成', content: '"政务云平台采购项目"AI审核发现3处错误，5处警告', time: '1小时前', isRead: false },
  { id: 'N003', type: 'qualification', title: '资质即将过期', content: '安全生产许可证将于8月25日到期，请及时更新', time: '3小时前', isRead: false },
  { id: 'N004', type: 'version', title: '新版本生成', content: '"政务云平台采购项目"生成了v3.2版本', time: '5小时前', isRead: true },
  { id: 'N005', type: 'qualification', title: '资质已失效', content: '高新技术企业证书已于2025年12月31日失效', time: '1天前', isRead: true }
]

// ===== User & Permissions mock data =====

export const roleMap: Record<string, { label: string; color: string; bg: string }> = {
  admin: { label: '管理员', color: '#7C3AED', bg: '#F5F3FF' },
  project_lead: { label: '项目负责人', color: '#2563EB', bg: '#EFF6FF' },
  member: { label: '成员', color: '#475569', bg: '#F1F5F9' },
  reviewer: { label: '审核人', color: '#D97706', bg: '#FFFBEB' },
}

export const users = [
  { id: 'U001', name: '陈志强', email: 'chenzq@zhilian-tech.com', phone: '138****6789', role: 'admin', department: '管理部', projects: 5, status: 'active', lastLogin: '2026-08-04 22:15', avatar: 'CZ' },
  { id: 'U002', name: '张明远', email: 'zhangmy@zhilian-tech.com', phone: '139****2341', role: 'project_lead', department: '投标部', projects: 3, status: 'active', lastLogin: '2026-08-04 21:48', avatar: 'ZM' },
  { id: 'U003', name: '李雪琴', email: 'lixq@zhilian-tech.com', phone: '137****8852', role: 'project_lead', department: '投标部', projects: 2, status: 'active', lastLogin: '2026-08-04 20:33', avatar: 'LX' },
  { id: 'U004', name: '王建国', email: 'wangjg@zhilian-tech.com', phone: '135****4412', role: 'member', department: '技术部', projects: 4, status: 'active', lastLogin: '2026-08-04 19:20', avatar: 'WJ' },
  { id: 'U005', name: '赵雅婷', email: 'zhaoyt@zhilian-tech.com', phone: '136****7733', role: 'member', department: '商务部', projects: 3, status: 'active', lastLogin: '2026-08-04 16:05', avatar: 'ZY' },
  { id: 'U006', name: '刘德海', email: 'liudh@zhilian-tech.com', phone: '138****1290', role: 'reviewer', department: '质量部', projects: 5, status: 'active', lastLogin: '2026-08-04 14:22', avatar: 'LD' },
  { id: 'U007', name: '孙小美', email: 'sunxm@zhilian-tech.com', phone: '139****5566', role: 'member', department: '技术部', projects: 2, status: 'active', lastLogin: '2026-08-03 18:40', avatar: 'SX' },
  { id: 'U008', name: '周天宇', email: 'zhouty@zhilian-tech.com', phone: '137****2299', role: 'reviewer', department: '质量部', projects: 3, status: 'inactive', lastLogin: '2026-07-28 10:15', avatar: 'ZT' },
  { id: 'U009', name: '吴敏华', email: 'wumh@zhilian-tech.com', phone: '135****8844', role: 'member', department: '行政部', projects: 1, status: 'active', lastLogin: '2026-08-02 09:30', avatar: 'WM' },
]

export const permissionMatrix = [
  { module: '投标任务', actions: { admin: '全部权限', project_lead: '创建/管理自己的', member: '查看/上传材料', reviewer: '查看/审核' } },
  { module: '材料管理', actions: { admin: '全部权限', project_lead: '上传/下载/删除', member: '上传/下载', reviewer: '下载' } },
  { module: 'AI审核', actions: { admin: '全部权限', project_lead: '触发/查看/处理', member: '查看', reviewer: '触发/查看/处理' } },
  { module: '文档输出', actions: { admin: '全部权限', project_lead: '生成/下载/版本管理', member: '下载', reviewer: '下载' } },
  { module: '资质库', actions: { admin: '增删改查', project_lead: '查看/上传', member: '查看', reviewer: '查看' } },
  { module: '文档片段库', actions: { admin: '增删改查', project_lead: '增删改查', member: '查看', reviewer: '查看' } },
  { module: '用户管理', actions: { admin: '全部权限', project_lead: '无', member: '无', reviewer: '无' } },
  { module: '系统设置', actions: { admin: '全部权限', project_lead: '无', member: '无', reviewer: '无' } },
]

// ===== System settings mock data =====

export const aiModelConfig = {
  primaryModel: 'qwen-plus',
  fallbackModel: 'deepseek-v3',
  thirdModel: 'glm-4-plus',
  apiKey: 'sk-••••••••••••••••••••••••',
  maxTokens: 8192,
  temperature: 0.3,
  enableCircuitBreaker: true,
  retryCount: 3,
  timeout: 60,
}

export const modelOptions = [
  { value: 'qwen-plus', label: '通义千问 Qwen-Plus', desc: '阿里云，支持100万token上下文', provider: '阿里云' },
  { value: 'deepseek-v3', label: 'DeepSeek-V3', desc: '深度求索，推理能力强', provider: '深度求索' },
  { value: 'glm-4-plus', label: 'GLM-4-Plus', desc: '智谱AI，多模态支持', provider: '智谱AI' },
  { value: 'qwen-max', label: '通义千问 Qwen-Max', desc: '阿里云，最强版本', provider: '阿里云' },
  { value: 'deepseek-r1', label: 'DeepSeek-R1', desc: '深度求索，深度推理', provider: '深度求索' },
]

export const systemConfig = {
  deploymentMode: 'saas',
  companyName: '深圳市智联科技有限公司',
  maxProjects: 50,
  maxUsers: 30,
  storageQuota: 500,
  storageUsed: 187,
  enableVersionControl: true,
  enableAutoBackup: true,
  backupFrequency: 'daily',
  enableNotification: true,
  enableEmailNotify: true,
  enableExpiryWarning: true,
  expiryWarningDays: 30,
}

export const docTemplateConfig = {
  defaultFormat: 'standard',
  enableAutoSplit: true,
  splitMode: 'three_part',
  watermark: true,
  watermarkText: '深圳市智联科技有限公司',
  fontFamily: '宋体',
  fontSize: '12pt',
  lineHeight: '1.5',
  pageSize: 'A4',
  margin: '标准',
}

export const operationLogs = [
  { id: 'L001', user: '张明远', action: '生成投标文件', target: 'TASK-2026-001', time: '2026-08-04 14:30', ip: '10.0.1.35' },
  { id: 'L002', user: '李雪琴', action: '上传材料', target: 'TASK-2026-002', time: '2026-08-04 13:15', ip: '10.0.1.48' },
  { id: 'L003', user: '陈志强', action: '修改系统设置', target: 'AI模型配置', time: '2026-08-04 11:20', ip: '10.0.1.12' },
  { id: 'L004', user: '刘德海', action: 'AI审核', target: 'TASK-2026-002', time: '2026-08-04 10:45', ip: '10.0.1.67' },
  { id: 'L005', user: '王建国', action: '下载文档', target: 'TASK-2026-003 v3.2', time: '2026-08-04 09:30', ip: '10.0.1.52' },
  { id: 'L006', user: '陈志强', action: '添加用户', target: '吴敏华', time: '2026-08-03 16:20', ip: '10.0.1.12' },
  { id: 'L007', user: '赵雅婷', action: '更新资质', target: '安全生产许可证', time: '2026-08-03 14:05', ip: '10.0.1.78' },
]

export const tenderRequirements = {
  projectName: '2026年深圳市政务云平台采购项目',
  tenderNo: 'SZGYY-2026-0312',
  tenderEntity: '深圳市政务服务数据管理局',
  deadline: '2026-08-20 17:00',
  budget: '12,800,000.00',
  duration: '300天',
  scoringItems: [
    { item: '商务报价', maxScore: 30, desc: '最低价得分法' },
    { item: '技术方案', maxScore: 40, desc: '架构方案15分 + 安全方案10分 + 实施方案10分 + 运维方案5分' },
    { item: '企业资质', maxScore: 15, desc: 'ISO证书5分 + CMMI 5分 + ITSS 5分' },
    { item: '业绩案例', maxScore: 10, desc: '近三年类似项目，每个3分，最高10分' },
    { item: '售后服务', maxScore: 5, desc: '服务方案2分 + SLA承诺3分' }
  ],
  disqualItems: [
    '投标文件未按招标文件要求签字盖章',
    '投标报价超过预算金额',
    '资质文件不在有效期内',
    '未提供投标保证金缴纳凭证',
    '工期不满足招标文件要求（≤300天）',
    '商务标与技术标工期不一致',
    '未按要求提供类似项目业绩证明（至少3个）'
  ]
}
