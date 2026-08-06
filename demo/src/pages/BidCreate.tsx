import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Card, DatePicker, Form, Input, InputNumber, Progress, Result, Steps, Upload, message } from 'antd'
import { ArrowLeft, ArrowRight, CheckCircle2, FileSearch, FileText, Plus, Sparkles, UploadCloud } from 'lucide-react'
import dayjs from 'dayjs'
import { useDemo } from '../context/DemoContext'

const { Dragger } = Upload

export default function BidCreate() {
  const navigate = useNavigate()
  const { bidTasks, addBidTask } = useDemo()
  const [form] = Form.useForm()
  const [current, setCurrent] = useState(0)
  const [fileList, setFileList] = useState<any[]>([])
  const [parsing, setParsing] = useState(false)
  const [parsed, setParsed] = useState(false)

  const fillExample = () => {
    form.setFieldsValue({
      projectName: '某市政务云扩容采购项目',
      tenderNo: `DEMO-${new Date().getFullYear()}-001`,
      tenderEntity: '某市政务服务数据管理局',
      deadline: dayjs().add(14, 'day'),
      budget: 9800000,
    })
    setFileList([{ uid: 'demo-file', name: '政务云扩容项目招标文件.pdf', status: 'done', size: 4.8 * 1024 * 1024 }])
    message.success('已填入示例招标文件和项目信息')
  }

  const startParsing = async () => {
    try {
      await form.validateFields()
    } catch {
      message.warning('请先填写完整的项目信息')
      return
    }
    if (!fileList.length) {
      message.warning('请先上传招标文件')
      return
    }
    setCurrent(1)
    setParsing(true)
    setParsed(false)
    window.setTimeout(() => {
      setParsing(false)
      setParsed(true)
    }, 1200)
  }

  const createTask = () => {
    const values = form.getFieldsValue(true)
    const nextNumber = String(bidTasks.length + 1).padStart(3, '0')
    const id = `TASK-2026-${nextNumber}`
    addBidTask({
      id,
      projectName: values.projectName,
      tenderNo: values.tenderNo,
      deadline: values.deadline?.format('YYYY-MM-DD') || dayjs().add(14, 'day').format('YYYY-MM-DD'),
      status: 'material_prep',
      currentStep: 3,
      progress: 35,
      assignee: '张明远',
      materialTotal: 23,
      materialHave: 13,
      materialMissing: 10,
      tenderEntity: values.tenderEntity,
      createdAt: dayjs().format('YYYY-MM-DD'),
      tags: ['Demo新建', 'AI已解析'],
    })
    message.success('投标任务已创建，AI材料清单已生成')
    navigate(`/tasks/${id}`)
  }

  return (
    <div className="p-4 md:p-6 max-w-[980px] mx-auto">
      <div className="flex items-center gap-3 mb-5">
        <Button type="text" icon={<ArrowLeft size={16} />} onClick={() => navigate('/dashboard')}>返回工作台</Button>
        <div>
          <h1 className="text-xl font-semibold text-[#1E293B]">新建投标任务</h1>
          <p className="text-sm text-[#64748B] mt-0.5">上传招标文件，由 AI 解析并生成首版材料清单</p>
        </div>
      </div>

      <Card className="!border-[#E2E8F0] !shadow-none mb-4">
        <Steps
          current={current}
          items={[
            { title: '上传与项目信息', icon: <UploadCloud size={16} /> },
            { title: 'AI解析', icon: <FileSearch size={16} /> },
            { title: '确认创建', icon: <CheckCircle2 size={16} /> },
          ]}
        />
      </Card>

      <Card className="!border-[#E2E8F0] !shadow-none">
        {current === 0 && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-[#1E293B]">招标文件与项目信息</h2>
              <Button icon={<Sparkles size={14} />} onClick={fillExample}>填入示例数据</Button>
            </div>
            <Dragger
              accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.rar,.png,.jpg,.jpeg"
              maxCount={1}
              fileList={fileList}
              beforeUpload={file => {
                if (file.size > 200 * 1024 * 1024) {
                  message.error('单文件不能超过 200MB')
                  return Upload.LIST_IGNORE
                }
                setFileList([file])
                return false
              }}
              onRemove={() => setFileList([])}
              className="!mb-5"
            >
              <UploadCloud size={36} className="mx-auto text-[#2563EB] mb-2" />
              <p className="text-sm text-[#1E293B]">点击或拖拽招标文件到此处</p>
              <p className="text-xs text-[#94A3B8] mt-1">支持 PDF、Word、Excel、PPT、图片和压缩包，最大 200MB</p>
            </Dragger>

            <Form form={form} layout="vertical">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4">
                <Form.Item name="projectName" label="项目名称" rules={[{ required: true, message: '请输入项目名称' }]}>
                  <Input placeholder="请输入项目名称" />
                </Form.Item>
                <Form.Item name="tenderNo" label="招标编号" rules={[{ required: true, message: '请输入招标编号' }]}>
                  <Input placeholder="请输入招标编号" />
                </Form.Item>
                <Form.Item name="tenderEntity" label="招标方" rules={[{ required: true, message: '请输入招标方' }]}>
                  <Input placeholder="请输入招标方名称" />
                </Form.Item>
                <Form.Item name="deadline" label="投标截止时间" rules={[{ required: true, message: '请选择截止时间' }]}>
                  <DatePicker showTime className="!w-full" />
                </Form.Item>
                <Form.Item name="budget" label="预算金额（元）" className="md:col-span-2">
                  <InputNumber min={0} className="!w-full" placeholder="请输入预算金额" />
                </Form.Item>
              </div>
            </Form>
          </div>
        )}

        {current === 1 && (
          <div className="py-5 max-w-[680px] mx-auto">
            {parsing ? (
              <div className="text-center">
                <div className="w-14 h-14 rounded-2xl bg-[#EFF6FF] flex items-center justify-center mx-auto mb-4">
                  <FileSearch size={28} className="text-[#2563EB] animate-pulse" />
                </div>
                <h2 className="text-lg font-semibold text-[#1E293B] mb-2">AI 正在解析招标文件</h2>
                <p className="text-sm text-[#64748B] mb-5">提取评分项、废标条款、资质要求并生成材料清单</p>
                <Progress percent={76} status="active" strokeColor="#2563EB" />
              </div>
            ) : (
              <Result
                status="success"
                title="招标文件解析完成"
                subTitle="已提取 8 项评分标准、6 项废标条款，并生成 23 项材料清单"
                extra={<Button type="primary" onClick={() => setCurrent(2)}>查看解析结果 <ArrowRight size={14} /></Button>}
              />
            )}
          </div>
        )}

        {current === 2 && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <FileText size={18} className="text-[#2563EB]" />
              <h2 className="text-base font-semibold text-[#1E293B]">解析结果确认</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
              {[
                ['材料清单', '23 项'],
                ['资质库匹配', '13 项'],
                ['待准备材料', '10 项'],
                ['废标条款', '6 项'],
              ].map(([label, value]) => (
                <div key={label} className="rounded-lg bg-[#F8FAFC] p-4">
                  <div className="text-xl font-semibold text-[#1E293B]">{value}</div>
                  <div className="text-xs text-[#64748B] mt-1">{label}</div>
                </div>
              ))}
            </div>
            <Alert type="info" showIcon message="创建后可在任务详情中编辑清单、上传材料并重新发起 AI 审核" />
          </div>
        )}
      </Card>

      <div className="flex justify-between mt-4">
        <Button disabled={current === 0 || parsing} onClick={() => setCurrent(value => value - 1)} icon={<ArrowLeft size={14} />}>上一步</Button>
        {current === 0 && <Button type="primary" onClick={startParsing}>开始 AI 解析 <ArrowRight size={14} /></Button>}
        {current === 1 && parsed && <Button type="primary" onClick={() => setCurrent(2)}>下一步 <ArrowRight size={14} /></Button>}
        {current === 2 && <Button type="primary" icon={<Plus size={14} />} onClick={createTask}>创建投标任务</Button>}
      </div>
    </div>
  )
}
