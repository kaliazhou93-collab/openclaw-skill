# CLAUDE.md — Kiro / Claude Code 适配指南

> 本文件供 Kiro、Claude Code、Cursor、Cline 等能运行 shell 的 AI Agent 阅读。
> Agent 读取本文件后即可理解项目架构并执行报销下载任务。

## 项目定位

批量下载中国区 Amazon 员工的报销发票（从 Outlook/Gmail 邮箱），统一命名、校验、生成智能提醒。

**核心价值**：把散落在邮箱里的发票集中到一个文件夹，命名规范化，提交报销时只需全选拖入即可。

## 架构

```
scripts/
├── config.yaml               ← 用户配置（公司信息/路径/规则）
├── extract_invoice_info.py   ← 核心：发票信息提取 + PDF校验 + 专票检查
├── smart_alerts.py           ← 核心：智能提醒（出差完整性/金额/时效）
└── download_invoices.py      ← CLI 入口（可独立运行）
```

**分层设计**：
- `extract_invoice_info.py` 和 `smart_alerts.py` 是**纯逻辑模块**，不依赖任何 Agent 框架
- 邮箱访问层由 Agent 自行实现（Quick 用 Outlook MCP，Kiro 可用 IMAP/Gmail API）
- 浏览器操作层由 Agent 自行实现（Quick 用 browser tools，Kiro 可用 Playwright）

## Agent 执行流程

```
1. 读取 config.yaml（获取公司信息、路径、规则）
2. 连接邮箱 → 读取"费用报销"文件夹邮件列表
3. 分类邮件（参考 SKILL.md § 决策树）
4. 逐封处理：
   a. 有附件 → 下载 PDF
   b. 有链接 → 提取 URL → 下载（参考 references/platforms.md）
   c. 需浏览器 → 打开页面下载
5. 对每个 PDF：
   a. validate_pdf_header() — 校验头字节
   b. extract_invoice_info() — 提取日期/商户/金额
   c. build_filename() — 生成规范文件名
   d. check_hotel_invoice_type() — 酒店专票校验
6. 保存到 invoice_dir，跳过重复
7. 归档邮件到"已提交"
8. 生成汇总报告 + smart_alerts
```

## 编辑规范

### 可以改的
- `config.yaml` — 用户配置
- `scripts/download_invoices.py` — CLI 实现细节
- 新增平台支持（在 `extract_invoice_info.py` 中加正则）

### 不要改的
- `SKILL.md` — 这是 Amazon Quick 的执行契约，改了会影响 Quick 用户
- `build_filename()` 的命名格式 — 已约定为 `YYYYMMDD_店名_金额.pdf`
- 智能提醒的阈值 — 从 `config.yaml` 读取，不要硬编码

### 遇到新平台时
1. 不要盲改代码
2. 运行 `scripts/extract_invoice_info.py` 检查现有正则能否匹配
3. 如不能，在 `references/platforms.md` 记录新平台的 URL 模式
4. 再在代码中添加支持

## 邮箱适配

项目设计时解耦了邮箱访问层。只要你的邮箱能提供以下信息，就能接入：

```python
# 每封邮件需要提供：
email = {
    'id': str,              # 邮件唯一ID
    'subject': str,         # 主题
    'sender_email': str,    # 发件人邮箱
    'received_at': str,     # 接收时间 ISO format
    'body_html': str,       # 正文HTML
    'has_attachments': bool,
    'attachments': [        # 附件列表
        {'name': str, 'id': str, 'size': int}
    ]
}
```

**各平台接入方式**：
| 邮箱 | 接入方式 |
|------|----------|
| Outlook (Amazon) | Quick MCP / Microsoft Graph API |
| Gmail | Gmail API (OAuth2) |
| 飞书/Lark Mail | Lark API |
| 通用 IMAP | imaplib + email 标准库 |

## 依赖

```
pip install pyyaml  # 读取 config.yaml
# 以下按需：
pip install requests        # HTTP下载
pip install playwright      # 浏览器自动化（百旺云等）
pip install google-auth     # Gmail
pip install msal            # Outlook Graph API
```

## 快速测试

```bash
# 1. 复制配置
cp scripts/config.yaml scripts/config.local.yaml
# 编辑 config.local.yaml 填入你的公司信息和路径

# 2. 测试信息提取
python -c "
from scripts.extract_invoice_info import extract_invoice_info
date, merchant, amount = extract_invoice_info(
    '您收到一张来自上海见面谈餐饮管理有限公司的电子发票【发票金额：249.00】',
    '开票日期：2026年05月20日'
)
print(f'{date}_{merchant}_{amount}.pdf')
# 输出: 20260520_上海见面谈_249.00.pdf
"

# 3. 测试智能提醒
python -c "
from scripts.smart_alerts import generate_smart_alerts_report
print(generate_smart_alerts_report('/path/to/your/invoice'))
"
```

## 与 SKILL.md 的关系

- `SKILL.md` 是 Amazon Quick 的 Agent 执行契约，包含完整的 workflow steps
- 本文件（`CLAUDE.md`）是给通用 Agent 的简化版指南
- 两者共享 `scripts/` 里的核心逻辑
- 如果你用 Kiro/Claude Code，读本文件 + `scripts/` 即可，不需要看 SKILL.md
