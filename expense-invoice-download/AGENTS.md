# AGENTS.md — 通用 Agent 接入指南

> 本文件面向任何能运行 Python + 访问邮箱的 Agent 系统。
> 无论你是 OpenClaw、Dify、LangGraph、AutoGen、还是自建 Agent，都可以参考。

## 最小接入要求

1. ✅ 能运行 Python 3.10+
2. ✅ 能访问邮箱（Outlook API / Gmail API / IMAP）
3. ✅ 能下载文件（HTTP GET）
4. ⚡ 可选：浏览器自动化（处理百旺云等 SPA 页面）

## 核心模块

```python
from scripts.extract_invoice_info import (
    extract_invoice_info,    # 提取日期/商户/金额
    build_filename,          # 生成标准文件名
    validate_pdf_header,     # PDF头字节校验
    check_hotel_invoice_type,# 酒店专票校验
    extract_hotel_checkin_date,  # 提取入住日期
)

from scripts.smart_alerts import (
    scan_invoices_from_filenames,  # 从文件名解析发票信息
    check_trip_completeness,       # 出差完整性检查
    check_amount_reasonableness,   # 金额合理性
    check_expiry,                  # 报销时效
    generate_smart_alerts_report,  # 生成完整提醒报告
)
```

## 工作流伪代码

```python
import yaml
from pathlib import Path

# 1. 加载配置
config = yaml.safe_load(open('scripts/config.yaml'))
invoice_dir = config['paths']['invoice_dir']

# 2. 扫描已有文件（去重用）
existing = {f.name.lower() for f in Path(invoice_dir).glob('*.pdf')}

# 3. 获取邮件列表（你的邮箱 API）
emails = your_email_client.list_folder(config['email']['source_folder'])

# 4. 逐封处理
results = []
for email in emails:
    # 4a. 分类（参考 references/platforms.md）
    category = classify_email(email)
    if category == 'SKIP':
        continue
    
    # 4b. 下载 PDF
    pdf_path = download_invoice(email, category)
    
    # 4c. 校验
    is_valid, file_type = validate_pdf_header(pdf_path)
    if not is_valid:
        results.append({'status': 'FAILED', 'reason': f'Not PDF: {file_type}'})
        continue
    
    # 4d. 提取信息 + 重命名
    date, merchant, amount = extract_invoice_info(
        email['subject'], email['body_html']
    )
    new_name = build_filename(date, merchant, amount)
    
    # 4e. 去重检查
    if new_name.lower() in existing:
        results.append({'status': 'DUPLICATE', 'file': new_name})
        continue
    
    # 4f. 保存
    final_path = Path(invoice_dir) / new_name
    shutil.copy(pdf_path, final_path)
    existing.add(new_name.lower())
    
    # 4g. 酒店专票校验
    if '酒店' in merchant:
        pdf_text = extract_pdf_text(final_path)
        invoice_type = check_hotel_invoice_type(pdf_text)
        if invoice_type == 'GENERAL':
            results.append({'status': 'WARNING', 'file': new_name, 
                          'message': '普票，需联系酒店换开专票'})
    
    results.append({'status': 'OK', 'file': new_name})
    
    # 4h. 归档邮件
    your_email_client.move(email['id'], config['email']['archive_folder'])

# 5. 生成智能提醒
report = generate_smart_alerts_report(invoice_dir)
print(report)
```

## 邮件分类规则（简版）

```python
def classify_email(email):
    subject = email['subject']
    sender = email['sender_email']
    
    # 噪音过滤
    skip_keywords = ['Expense report', 'Re:', 'Guidelines', 'Remittance', '用户支付通知']
    if any(k in subject for k in skip_keywords):
        return 'SKIP'
    
    skip_senders = ['cmbchina', 'citiccard', 'amazonaws.com']
    if any(s in sender for s in skip_senders):
        return 'SKIP'
    
    # 有附件
    if email['has_attachments']:
        if '滴滴' in subject or 'didi' in sender:
            return 'DIDI'  # 下载全部附件
        if any(k in subject for k in ['酒店', 'Hotel', 'Marriott', 'Hilton', 'Folio']):
            return 'HOTEL'  # 下载全部附件
        return 'ATTACHMENT'  # 只下载 PDF
    
    # 无附件 → 检查正文链接
    return 'LINK'
```

## 发票平台 URL 处理

详见 `references/platforms.md`。核心逻辑：

```python
import re, html as html_lib

def extract_download_url(body_html, sender):
    """从邮件正文提取PDF下载链接"""
    body = html_lib.unescape(body_html)
    
    # 票点点
    if 'sf-epiaotong' in sender:
        urls = re.findall(r'href=["\']([^"\']*\.pdf[^"\']*)["\']', body)
        return urls[0] if urls else None
    
    # 百旺云预览页 → 构造下载URL
    m = re.search(r'previewInvoiceAllEle\?param=([A-F0-9]+)', body)
    if m:
        param = m.group(1)
        return f"https://pis.baiwang.com/bwmg/mix/bw/downloadFormat?param={param}&formatType=PDF"
    
    # 百旺金穗云
    urls = re.findall(r'href=["\']([^"\']*bwfapiao[^"\']*\.pdf[^"\']*)["\']', body)
    if urls:
        return html_lib.unescape(urls[0])
    
    return None
```

## 配置自定义

复制 `config.yaml` → `config.local.yaml`，修改以下字段适配你的公司：

```yaml
company:
  name: "你的公司全称"
  tax_id: "你的公司税号"

user:
  home_city: "北京"  # 你的常驻城市
  home_city_keywords: ["北京", "Beijing"]

paths:
  invoice_dir: "/path/to/your/invoice/folder"

email:
  provider: "gmail"  # 改成你用的邮箱
```

## 与其他文件的关系

| 文件 | 适用对象 | 内容 |
|------|----------|------|
| `SKILL.md` | Amazon Quick | 完整 workflow，Quick 专属工具调用 |
| `CLAUDE.md` | Kiro / Claude Code | 架构说明 + 编辑规范 |
| `AGENTS.md` | 任何 Agent | 通用接入指南 + 伪代码 |
| `scripts/` | 所有人 | 平台无关的核心逻辑 |
| `config.yaml` | 所有人 | 用户自定义配置 |
