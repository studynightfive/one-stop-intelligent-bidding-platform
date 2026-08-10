import { createHash, randomUUID } from 'node:crypto';
import type { APIRequestContext } from '@playwright/test';
import { expect, test } from '@playwright/test';
import { ApiClient } from '../helpers/api-client';

interface AuthSession {
  accessToken: string;
  user: { id: string };
}

interface UploadSession {
  id: string;
  totalParts: number;
}

interface UploadPart {
  partNumber: number;
  etag: string;
}

interface FileRef {
  id: string;
  fileName: string;
  mimeType: string;
  scanStatus: string;
}

interface JobRef {
  id: string;
  status: string;
  result?: unknown;
}

interface BidTask {
  id: string;
  status: string;
}

interface BidDocument {
  id: string;
  type: string;
  latestFile: FileRef;
}

interface Evaluation {
  id: string;
  status: string;
  version: number;
}

interface Supplier {
  id: string;
  name: string;
  email: string;
}

interface Invite {
  supplierId: string;
  supplierName: string;
  inviteUrl: string;
}

interface PublishResult {
  evaluation: Evaluation;
  invites: Invite[];
}

interface PortalSession {
  portalAccessToken: string;
  supplier: Supplier;
}

interface PortalContext {
  evaluation: Evaluation;
  supplier: Supplier;
  allowedActions: string[];
}

interface ScoreItem {
  supplierId: string;
  criterionId: string;
  finalScore: string;
  version: number;
}

interface EvaluationReport {
  id: string;
  format: 'docx' | 'pdf';
  file: FileRef;
}

const onePixelPng = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nWQAAAAASUVORK5CYII=',
  'base64',
);

const minimalPdf = Buffer.from(
  '%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
  + '2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n',
  'utf8',
);

async function authenticatedClient(request: APIRequestContext): Promise<{ client: ApiClient; session: AuthSession }> {
  const client = new ApiClient(request);
  const session = await client.data<AuthSession>({
    method: 'POST',
    path: '/api/v1/auth/login',
    data: {
      email: process.env.E2E_ADMIN_EMAIL ?? 'admin@bid-platform.dev',
      password: process.env.E2E_ADMIN_PASSWORD ?? 'DemoAdmin123!',
      remember: false,
    },
  });
  client.setAccessToken(session.accessToken);
  return { client, session };
}

async function uploadFile(
  client: ApiClient,
  file: { name: string; mimeType: string; content: Buffer; purpose: 'tender' | 'bidIllustration'; resourceId?: string },
): Promise<FileRef> {
  const upload = await client.data<UploadSession>({
    method: 'POST',
    path: '/api/v1/files/upload-sessions',
    data: {
      fileName: file.name,
      mimeType: file.mimeType,
      sizeBytes: file.content.length,
      sha256: createHash('sha256').update(file.content).digest('hex'),
      purpose: file.purpose,
      resourceId: file.resourceId,
    },
  });
  expect(upload.totalParts).toBe(1);
  const part = await client.data<UploadPart>({
    method: 'PUT',
    path: `/api/v1/files/upload-sessions/${upload.id}/parts/1`,
    body: file.content,
  });
  const completed = await client.data<FileRef>({
    method: 'POST',
    path: `/api/v1/files/upload-sessions/${upload.id}/complete`,
    headers: { 'Idempotency-Key': `e2e-upload-${randomUUID()}` },
    data: { parts: [part] },
  });
  expect(completed.scanStatus).toBe('clean');
  return completed;
}

async function createPublishedEvaluation(
  client: ApiClient,
  userId: string,
  supplierCount = 2,
): Promise<{ evaluation: Evaluation; suppliers: Supplier[]; published: PublishResult }> {
  const suffix = randomUUID().slice(0, 8);
  const now = Date.now();
  const evaluation = await client.data<Evaluation>({
    method: 'POST',
    path: '/api/v1/evaluations',
    data: {
      projectName: `E2E 评标闭环 ${suffix}`,
      tenderNo: `E2E-EVAL-${suffix}`,
      tenderEntity: 'E2E 建设单位',
      budgetAmount: '5000000.00',
      currency: 'CNY',
      assigneeId: userId,
      supplierDeadline: new Date(now + 3 * 86_400_000).toISOString(),
      evaluationStartAt: new Date(now + 4 * 86_400_000).toISOString(),
      evaluationEndAt: new Date(now + 10 * 86_400_000).toISOString(),
      description: 'Playwright 真实接口评标闭环',
    },
  });
  await client.data({
    method: 'PUT',
    path: `/api/v1/evaluations/${evaluation.id}/materials`,
    data: {
      items: [{
        name: '补充说明（选交）',
        category: 'technical',
        required: false,
        allowedMimeTypes: ['application/pdf'],
        maxSizeBytes: 5_000_000,
        sortOrder: 0,
      }],
    },
  });
  await client.data({
    method: 'PUT',
    path: `/api/v1/evaluations/${evaluation.id}/criteria`,
    data: {
      items: [{
        name: '技术方案完整性',
        category: 'technical',
        maxScore: '100.00',
        weightPercent: '100.00',
        method: 'expert',
        description: '技术方案完整性与可执行性',
        sortOrder: 0,
      }],
    },
  });
  await client.data({
    method: 'PUT',
    path: `/api/v1/evaluations/${evaluation.id}/review-settings`,
    data: {
      multiRoundPricing: true,
      maxRounds: 2,
      supplementDeadlineMinutes: 1440,
      allowModifyBeforeDeadline: true,
      notifyOnMissing: true,
      closeSubmissionAtDeadline: true,
    },
  });
  await client.data({
    method: 'PUT',
    path: `/api/v1/evaluations/${evaluation.id}/reviewers`,
    data: { reviewerIds: [userId] },
  });
  const suppliers = await client.data<Supplier[]>({
    method: 'PUT',
    path: `/api/v1/evaluations/${evaluation.id}/suppliers`,
    data: {
      items: Array.from({ length: supplierCount }, (_, index) => ({
        name: `E2E 供应商 ${index + 1}-${suffix}`,
        contactName: `联系人${index + 1}`,
        email: `e2e-${suffix}-${index + 1}@example.test`,
      })),
    },
  });
  const validation = await client.data<{ valid: boolean }>({
    method: 'POST',
    path: `/api/v1/evaluations/${evaluation.id}/validate`,
  });
  expect(validation.valid).toBe(true);
  const published = await client.data<PublishResult>({
    method: 'POST',
    path: `/api/v1/evaluations/${evaluation.id}/publish`,
    headers: { 'Idempotency-Key': `e2e-publish-${suffix}` },
  });
  return { evaluation, suppliers, published };
}

async function exchangeInvite(request: APIRequestContext, invite: Invite): Promise<ApiClient> {
  const client = new ApiClient(request);
  const session = await client.data<PortalSession>({
    method: 'POST',
    path: '/api/v1/portal/session/exchange',
    data: { inviteCode: invite.inviteUrl.split('/').at(-1) },
  });
  expect(session.supplier.id).toBe(invite.supplierId);
  return client.setAccessToken(session.portalAccessToken);
}

test.describe('real business flows @contract', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeEach(({}, testInfo) => {
    test.skip(testInfo.project.name !== 'desktop', 'state-changing contract flows run once on desktop');
  });

  test('create → parse → review → paragraph AI technical document with image', async ({ request }) => {
    const { client, session } = await authenticatedClient(request);
    const tender = await uploadFile(client, {
      name: `e2e-tender-${randomUUID()}.pdf`,
      mimeType: 'application/pdf',
      content: minimalPdf,
      purpose: 'tender',
    });
    const suffix = randomUUID().slice(0, 8);
    const task = await client.data<BidTask>({
      method: 'POST',
      path: '/api/v1/bid-tasks',
      data: {
        projectName: `E2E AI 技术标 ${suffix}`,
        tenderNo: `E2E-BID-${suffix}`,
        tenderEntity: 'E2E 招标单位',
        deadline: new Date(Date.now() + 7 * 86_400_000).toISOString(),
        assigneeId: session.user.id,
        tenderFileId: tender.id,
        tags: ['e2e', 'paragraph-ai'],
      },
    });
    const parsed = await client.data<JobRef>({
      method: 'POST',
      path: `/api/v1/bid-tasks/${task.id}/parse`,
      headers: { 'Idempotency-Key': `e2e-parse-${suffix}` },
    });
    expect(parsed.status).toBe('succeeded');
    const reviewed = await client.data<JobRef>({
      method: 'POST',
      path: `/api/v1/bid-tasks/${task.id}/reviews`,
      headers: { 'Idempotency-Key': `e2e-review-${suffix}` },
      data: { types: ['signature', 'price', 'content', 'consistency'] },
    });
    expect(reviewed.status).toBe('succeeded');

    const illustration = await uploadFile(client, {
      name: `e2e-architecture-${suffix}.png`,
      mimeType: 'image/png',
      content: onePixelPng,
      purpose: 'bidIllustration',
      resourceId: task.id,
    });
    const generated = await client.data<JobRef>({
      method: 'POST',
      path: `/api/v1/bid-tasks/${task.id}/documents`,
      headers: { 'Idempotency-Key': `e2e-document-${suffix}` },
      data: {
        mode: 'split',
        sections: ['technical'],
        templateMode: 'standard',
        includeWatermark: false,
        technicalDocument: {
          strategy: 'paragraph_by_paragraph',
          templateName: 'E2E 技术标标准模板',
          sections: [{
            key: 'overall',
            heading: '1 总体技术方案',
            headingLevel: 1,
            instructions: '按招标要求说明总体架构、实施边界、质量保障与验收方式。',
            targetParagraphs: 3,
            targetWordsPerParagraph: 180,
            required: true,
          }],
          referenceImages: [{
            fileId: illustration.id,
            sectionKey: 'overall',
            caption: '总体技术架构示意图',
            altText: '总体技术架构',
            placement: 'after_paragraph',
            afterParagraphIndex: 1,
          }],
          contextWindowCharacters: 4_000,
          carryForwardParagraphs: 2,
          preserveHeadingNumbering: true,
          requireEvidence: true,
        },
      },
    });
    expect(generated.status).toBe('succeeded');

    const documents = await client.data<BidDocument[]>({
      path: `/api/v1/bid-tasks/${task.id}/documents`,
    });
    const technical = documents.find((item) => item.type === 'technical');
    if (!technical) throw new Error('technical document was not persisted');
    expect(technical.latestFile.mimeType).toContain('wordprocessingml.document');
    const download = await client.raw({
      path: `/api/v1/bid-tasks/${task.id}/documents/${technical.id}/download`,
    });
    const docx = await download.body();
    expect(docx.subarray(0, 2).toString()).toBe('PK');
    expect(docx.includes(Buffer.from('word/media/'))).toBe(true);
  });

  test('invite → submit → AI score → report → close', async ({ request }) => {
    const { client, session } = await authenticatedClient(request);
    const { evaluation, published } = await createPublishedEvaluation(client, session.user.id, 2);
    for (const invite of published.invites) {
      const portal = await exchangeInvite(request, invite);
      const receipt = await portal.data<{ supplierId: string; submittedMaterialCount: number }>({
        method: 'POST',
        path: '/api/v1/portal/submit',
        headers: { 'Idempotency-Key': `e2e-submit-${invite.supplierId}` },
        data: { confirmed: true },
      });
      expect(receipt.supplierId).toBe(invite.supplierId);
      expect(receipt.submittedMaterialCount).toBe(0);
    }

    for (const path of ['material-checks', 'risk-checks', 'ai-scoring']) {
      const job = await client.data<JobRef>({
        method: 'POST',
        path: `/api/v1/evaluations/${evaluation.id}/${path}`,
      });
      expect(job.status).toBe('succeeded');
    }
    const scores = await client.data<ScoreItem[]>({
      path: `/api/v1/evaluations/${evaluation.id}/scores`,
    });
    expect(scores.length).toBeGreaterThanOrEqual(2);
    const first = scores[0];
    await client.data<ScoreItem>({
      method: 'PATCH',
      path: `/api/v1/evaluations/${evaluation.id}/scores/${first.supplierId}/${first.criterionId}`,
      headers: { 'If-Match': String(first.version) },
      data: { humanScore: '88.00', adjustmentReason: 'E2E 人工复核通过' },
    });
    await client.data<{ confirmed: boolean }>({
      method: 'POST',
      path: `/api/v1/evaluations/${evaluation.id}/scores/confirm`,
      data: { comment: 'E2E 评分确认' },
    });
    const reportJob = await client.data<JobRef>({
      method: 'POST',
      path: `/api/v1/evaluations/${evaluation.id}/reports`,
      data: { formats: ['docx', 'pdf'] },
    });
    expect(reportJob.status).toBe('succeeded');
    const reports = await client.data<EvaluationReport[]>({
      path: `/api/v1/evaluations/${evaluation.id}/reports`,
    });
    expect(new Set(reports.map((item) => item.format))).toEqual(new Set(['docx', 'pdf']));
    for (const report of reports) {
      const response = await client.raw({
        path: `/api/v1/evaluations/${evaluation.id}/reports/${report.id}/download`,
      });
      const body = await response.body();
      expect(body.length).toBeGreaterThan(100);
      expect(report.format === 'pdf' ? body.subarray(0, 4).toString() : body.subarray(0, 2).toString())
        .toBe(report.format === 'pdf' ? '%PDF' : 'PK');
    }
    const closed = await client.data<Evaluation>({
      method: 'POST',
      path: `/api/v1/evaluations/${evaluation.id}/close`,
      headers: { 'Idempotency-Key': `e2e-close-${evaluation.id}` },
      data: { resultSummary: 'E2E 评标流程完成' },
    });
    expect(closed.status).toBe('closed');
  });

  test('portal tokens expose only their own supplier', async ({ request }) => {
    const { client, session } = await authenticatedClient(request);
    const { suppliers, published } = await createPublishedEvaluation(client, session.user.id, 2);
    const firstPortal = await exchangeInvite(request, published.invites[0]);
    const secondPortal = await exchangeInvite(request, published.invites[1]);
    const first = await firstPortal.data<PortalContext>({ path: '/api/v1/portal/me' });
    const second = await secondPortal.data<PortalContext>({ path: '/api/v1/portal/me' });

    expect(first.supplier.id).toBe(suppliers[0].id);
    expect(second.supplier.id).toBe(suppliers[1].id);
    expect(JSON.stringify(first)).not.toContain(suppliers[1].email);
    expect(JSON.stringify(second)).not.toContain(suppliers[0].email);
    expect(first.allowedActions).toContain('submit');
    expect(second.allowedActions).toContain('submit');
  });
});
