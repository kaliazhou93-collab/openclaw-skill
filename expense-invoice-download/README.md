# 🧾 expense-invoice-download

批量下载中国区报销发票，自动重命名、去重、校验，配合 Concur 报销助手一键提交。

面向 AWS 中国区员工，解决每月报销发票管理痛点。

> **多平台支持**：Amazon Quick / Kiro / Claude Code / 任何能跑 Python 的 Agent / 独立 CLI。
>
> 选择你的平台 → 读对应文档 → 开始使用。

## 功能一览

| 功能 | 说明 |
|------|------|
| 📥 批量下载 | 从 Outlook "费用报销"文件夹自动下载发票 PDF |
| 📛 统一命名 | `YYYYMMDD_店名_金额.pdf`（按日期排序、方便查重） |
| ⚡ 增量模式 | 记录上次处理时间，只处理新邮件 |
| 🔍 重复检测 | 下载前扫描已有文件，同名跳过 |
| ✅ 专票校验 | 酒店发票自动检查是否为增值税专用发票 |
| 📋 智能提醒 | 出差完整性 / 金额合理性 / 报销时效 |
| 📤 Concur 指引 | Train Tab + Agent 模式提交建议 |
| 📁 提交包 | 说"准备报销"生成分类文件夹，按 Tab 上传 |

## 选择你的平台

| 你用什么 | 读哪个文档 | 怎么开始 |
|----------|-----------|----------|
| **Amazon Quick** | `SKILL.md` | 说"下载报销发票"自动执行 |
| **Kiro / Claude Code** | `CLAUDE.md` | Agent 读文档 + 调 `scripts/` |
| **其他 Agent**（小龙虾/Dify/LangGraph 等） | `AGENTS.md` | 按通用指南接入 |
| **不用 Agent，手动跑** | `scripts/download_invoices.py` | CLI 直接运行 |

**核心设计**：业务逻辑（分类规则/命名/校验/提醒）全在 `scripts/` 里，平台无关。各 Agent 按各自方式调用邮箱和浏览器，共享同一套核心逻辑。

```
scripts/config.yaml  ← 先改这个（填你的公司信息、路径、邮箱类型）
scripts/*.py         ← 核心逻辑，直接 import 使用
```

## 支持的发票来源

### 邮件附件直接下载
- 票通（vpiaotong.com）
- 美团（meituan.com）
- 51发票（51fapiao.cloud）
- 麦当劳（mcd.cn）
- BCD Travel（bcdtravel.cn）
- 滴滴出行（发票+行程单）
- 酒店（万豪/希尔顿等，发票+水单）

### 邮件正文链接下载
- 票点点（sf-epiaotong.com）— 正文含 PDF URL
- 百旺金穗云（bwfapiao.com）— 正文含 PDF URL
- fapiao.com — 直接 curl

### 需浏览器下载
- 百旺云预览页（pis.baiwang.com）— 自动构造下载 URL 或浏览器打开

### 手动处理
- 数电发票二维码 — 用户手机扫码后发链接给 Agent
- 12306 高铁票 — 用户从 APP 下载后直接发 PDF 给 Agent

## 快速开始

### 通用前置条件（所有平台都需要）
1. 在 Outlook 收件箱下创建"费用报销"文件夹和"已提交"子文件夹
2. 本地创建一个 invoice 文件夹存放发票
3. 复制 `scripts/config.yaml` → `scripts/config.local.yaml`，填入你的公司信息和路径

### 按平台额外配置

**Amazon Quick 用户：**
1. 安装 [Amazon Quick](https://quick.aws.dev)
2. 连接 Outlook（Settings → Capabilities → Connections）
3. 添加本地文件夹（Settings → My Computer → Local Folders）

**Kiro / Claude Code 用户：**
1. 确保 Agent 能访问 Outlook API（Microsoft Graph）
2. 把本 repo 的路径告诉 Agent，它会读 `CLAUDE.md`

**其他 Agent / CLI 用户：**
1. `pip install pyyaml requests`
2. 配置邮箱 API 凭证（Outlook Graph / Gmail OAuth / IMAP）
3. 参考 `AGENTS.md` 接入

### 安装 Skill
将 `SKILL.md` 放到 `~/.quickwork/skills/expense-invoice-download/SKILL.md`

或者直接在 Amazon Quick 中说："帮我安装这个 skill"，把本仓库链接发给它。

### 使用

```
你: 下载报销发票
Quick: [自动处理：增量检查 → 分类 → 下载 → 重命名 → 去重 → 校验 → 归档 → 汇总报告]

你: 准备报销
Quick: [生成分类提交包 → Concur 提交指引]

你: (拖入高铁票 PDF)
Quick: [提取乘车日期+金额 → 命名为 20260511_高铁_83.00.pdf → 保存]
```

## 文件命名规则

| 类别 | 日期来源 | 示例 |
|------|----------|------|
| 餐饮 | 开票日期 | `20260520_上海见面谈_249.00.pdf` |
| 酒店发票 | **入住日期** | `20260330_万怡酒店_500.00.pdf` |
| 酒店水单 | **入住日期** | `20260330_万怡酒店_500.00_水单.pdf` |
| 高铁票 | **乘车日期** | `20260511_高铁_83.00.pdf` |
| 滴滴发票 | 开票日期 | `20260315_滴滴_45.00.pdf` |
| 滴滴行程单 | 同上 | `20260315_滴滴_45.00_行程单.pdf` |

## 智能提醒

### 🧳 出差完整性检查
按日期聚合发票，检查是否有遗漏：
- 有酒店但无交通票 → 提醒
- 有交通票但无酒店 → 提醒

### 💰 金额合理性
- 餐饮单张 > ¥300 → 提醒备注宴请人数

### ⏰ 报销时效
- 开票 > 45 天 → ⚠️ 警告
- 开票 > 55 天 → 🔴 紧急（接近 60 天硬限制）

### 🏨 酒店线下预订提醒
- 无 BCD Invoice 对应 → 提醒 comment 写"private offer 优惠价，线下直订"

## 报销生命周期

```
发票下载 → invoice 根目录平铺（查重/对账）
  → 提交报销 → 继续留根目录
  → 收到 Remittance Advice → 归类到子文件夹（归档完成）
```

## 配合 Concur 报销助手使用

本 Skill 负责**下载整理**，报销助手插件负责**提交到 Concur**：

| 发票类型 | 提交方式 |
|----------|----------|
| 高铁票 | 报销助手 **Train Tab**（12306 扫码）或直接上传 PDF |
| 其余发票 | 报销助手 **Agent 模式**（全选拖入） |
| 或按分类 | "准备报销" → 按文件夹上传到对应 Tab |

> 💡 高铁票两种方式：(1) Train Tab 扫码（推荐，自动导入票据信息）；(2) 直接上传 PDF 文件（适合12306已开具电子发票的情况）。说"准备报销"时会询问你选哪种。

报销助手安装：[Quip 文档](https://quip-amazon.com/tqnMAA6bMZlP)

## 目录说明

```
├── README.md              本文件
├── SKILL.md               Amazon Quick Skill 执行契约
├── CLAUDE.md              Kiro / Claude Code 适配指南
├── AGENTS.md              通用 Agent 接入指南（含伪代码）
├── scripts/
│   ├── config.yaml               用户配置（公司/路径/规则）
│   ├── extract_invoice_info.py   核心：发票信息提取 + PDF校验
│   └── smart_alerts.py           核心：智能提醒逻辑
└── references/
    └── platforms.md              支持的 9 种发票平台详情
└── LICENSE
```

## 已知限制

- 数电发票二维码无法直接解码（需用户手机扫码后发链接）
- 浙江省税务局 dppt.zhejiang.chinatax.gov.cn 有反爬保护
- 百旺云链接超过 60 天会过期
- 图片版 PDF（扫描件）无法提取文本做专票校验
- 12306 邮箱收不到发票，需从 APP 手动下载

## 贡献

欢迎 AWS 同事提 Issue 或 PR：
- 新的发票平台支持
- Concur 报销流程优化
- 更多智能提醒规则

## License

MIT - 仅供 Amazon 内部使用参考
