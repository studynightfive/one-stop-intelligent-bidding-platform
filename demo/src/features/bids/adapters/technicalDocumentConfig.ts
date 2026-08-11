import type {
  TechnicalDocumentGenerationOptions,
  TechnicalDocumentImage,
  TechnicalDocumentSectionTemplate,
} from './schemaTypes'

export type TechnicalDocumentDraft = TechnicalDocumentGenerationOptions

export function createDefaultTechnicalDocument(): TechnicalDocumentDraft {
  return {
    strategy: 'paragraph_by_paragraph',
    templateName: '招标文件技术响应格式',
    sections: [
      {
        key: 'project_understanding',
        heading: '项目理解与总体技术路线',
        headingLevel: 1,
        instructions: '结合招标需求说明建设背景、现状痛点、目标理解、总体原则与技术路线，逐条对应关键要求。',
        targetParagraphs: 4,
        targetWordsPerParagraph: 350,
        required: true,
      },
      {
        key: 'architecture_solution',
        heading: '系统架构与关键技术方案',
        headingLevel: 1,
        instructions: '从业务、数据、应用和技术架构展开，说明关键组件、接口、部署、安全及可扩展性设计。',
        targetParagraphs: 6,
        targetWordsPerParagraph: 450,
        required: true,
      },
      {
        key: 'implementation_plan',
        heading: '实施组织与进度保障',
        headingLevel: 1,
        instructions: '说明项目组织、阶段任务、里程碑、交付物、资源投入、沟通机制和进度纠偏措施。',
        targetParagraphs: 4,
        targetWordsPerParagraph: 350,
        required: true,
      },
      {
        key: 'quality_service',
        heading: '质量、安全与服务保障',
        headingLevel: 1,
        instructions: '说明质量控制、信息安全、风险管理、验收、培训、运维与售后服务机制。',
        targetParagraphs: 4,
        targetWordsPerParagraph: 320,
        required: true,
      },
    ],
    referenceImages: [],
    contextWindowCharacters: 48_000,
    carryForwardParagraphs: 2,
    preserveHeadingNumbering: true,
    requireEvidence: true,
  }
}

export function createTechnicalSection(index: number): TechnicalDocumentSectionTemplate {
  return {
    key: `custom_section_${index}`,
    heading: `自定义技术章节 ${index}`,
    headingLevel: 1,
    instructions: '请说明本章节需要覆盖的招标要求、技术方案和可验证依据。',
    targetParagraphs: 3,
    targetWordsPerParagraph: 300,
    required: true,
  }
}

export function validateTechnicalDocument(value: TechnicalDocumentDraft): string[] {
  const errors: string[] = []
  if (!value.templateName.trim()) errors.push('请填写技术文档格式或模板名称')
  if (!value.sections.length) errors.push('至少需要一个技术章节')
  const keys = new Set<string>()
  value.sections.forEach((section, index) => {
    const label = `第 ${index + 1} 章`
    if (!/^[a-zA-Z][a-zA-Z0-9_-]{0,63}$/.test(section.key)) errors.push(`${label}的章节标识格式不正确`)
    if (keys.has(section.key)) errors.push(`${label}的章节标识重复`)
    keys.add(section.key)
    if (!section.heading.trim()) errors.push(`${label}缺少标题`)
    if (!section.instructions.trim()) errors.push(`${label}缺少生成要求`)
    if (section.targetParagraphs < 1 || section.targetParagraphs > 30) errors.push(`${label}段落数应为 1–30`)
    if (section.targetWordsPerParagraph < 80 || section.targetWordsPerParagraph > 1500) {
      errors.push(`${label}每段目标字数应为 80–1500`)
    }
  })
  value.referenceImages.forEach((image, index) => {
    const section = value.sections.find(item => item.key === image.sectionKey)
    if (!section) errors.push(`第 ${index + 1} 张图片未关联有效章节`)
    if (!image.caption.trim()) errors.push(`第 ${index + 1} 张图片缺少图注`)
    if (image.placement === 'after_paragraph') {
      const paragraph = image.afterParagraphIndex
      if (!paragraph || !section || paragraph > section.targetParagraphs) {
        errors.push(`第 ${index + 1} 张图片的段落锚点超出章节范围`)
      }
    }
  })
  return errors
}

function normalizeImage(image: TechnicalDocumentImage): TechnicalDocumentImage {
  const normalized = {
    ...image,
    caption: image.caption.trim(),
    altText: image.altText?.trim() || undefined,
  }
  if (normalized.placement !== 'after_paragraph') delete normalized.afterParagraphIndex
  return normalized
}

export function normalizeTechnicalDocument(value: TechnicalDocumentDraft): TechnicalDocumentGenerationOptions {
  return {
    ...value,
    strategy: 'paragraph_by_paragraph',
    templateName: value.templateName.trim(),
    sections: value.sections.map(section => ({
      ...section,
      heading: section.heading.trim(),
      instructions: section.instructions.trim(),
    })),
    referenceImages: value.referenceImages.map(normalizeImage),
  }
}
