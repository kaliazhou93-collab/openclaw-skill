自动从 Outlook "费用报销"文件夹读取发票邮件，下载 PDF 附件到本地 invoice **根目录**，按统一格式重命名（`YYYYMMDD_店名_金额.pdf`），处理完成后将邮件移动到"已提交"子文件夹。

支持**增量模式**（只处理新邮件）和**重复检测**（跳过已存在的同名发票）。

所有发票统一放在根目录，不做子文件夹归类——便于一眼查看全部发票、检查是否重复提交。

覆盖 9 种中国电子发票平台。酒店发票自动校验专票/普票类型。汇总报告含智能提醒和 Concur 提交指引。

**首次使用**：如果用户未配置过公司信息，第一次运行时自动触发 Step 0 引导配置。

**额外触发**：用户说"准备报销"时，生成按类别分好的临时提交包文件夹，便于上传到 Concur 报销助手插件。

## Configuration

<table style="min-width: 50px;"><colgroup><col style="min-width: 25px;"><col style="min-width: 25px;"></colgroup><tbody><tr><th colspan="1" rowspan="1"><p>配置项</p></th><th colspan="1" rowspan="1"><p>值</p></th></tr><tr><td colspan="1" rowspan="1"><p>源文件夹</p></td><td colspan="1" rowspan="1"><p>Outlook 收件箱 → 费用报销</p></td></tr><tr><td colspan="1" rowspan="1"><p>归档文件夹</p></td><td colspan="1" rowspan="1"><p>费用报销 → 已提交</p></td></tr><tr><td colspan="1" rowspan="1"><p><strong>本地保存路径</strong></p></td><td colspan="1" rowspan="1"><p><code>\\WorkDocs\kaliaz-amazon\My Documents\invoice</code>（根目录，不分子文件夹）</p></td></tr><tr><td colspan="1" rowspan="1"><p>下载格式</p></td><td colspan="1" rowspan="1"><p>仅 PDF（不下载 OFD/XML）</p></td></tr><tr><td colspan="1" rowspan="1"><p>酒店发票要求</p></td><td colspan="1" rowspan="1"><p>必须为增值税专用发票</p></td></tr><tr><td colspan="1" rowspan="1"><p>文件命名格式</p></td><td colspan="1" rowspan="1"><p><code>YYYYMMDD_店名_金额.pdf</code></p></td></tr><tr><td colspan="1" rowspan="1"><p>餐饮宴请提醒阈值</p></td><td colspan="1" rowspan="1"><p>单张 &gt; ¥300 提醒备注宴请人数</p></td></tr><tr><td colspan="1" rowspan="1"><p><strong>餐饮与会人提醒</strong></p></td><td colspan="1" rowspan="1"><p><strong>所有餐饮发票 → 必须备注与会人</strong></p></td></tr><tr><td colspan="1" rowspan="1"><p><strong>消费明细小票阈值</strong></p></td><td colspan="1" rowspan="1"><p><strong>单张餐饮 &gt; ¥500 → 须附消费明细小票（2026-07-01 生效）</strong></p></td></tr><tr><td colspan="1" rowspan="1"><p>报销时效警告</p></td><td colspan="1" rowspan="1"><p>开票日期距今 &gt; 45 天</p></td></tr></tbody></table>

## Meal Receipt Policy（餐饮小票新规）

**生效日期**：2026年7月1日

**适用范围**：中国大陆发生的以下四类商务餐饮费用，单笔金额超过 ¥500：

-   出差餐费 / Travel Meals
    
-   出差餐费-团体 / Travel Business Meal (group)
    
-   团体餐费:商务会议活动 / Group Meal: Business Meetings/Events
    
-   招待费-客户 / Entertainment – with Client
    

**要求**：须同时提供有效发票 + 消费明细小票（水单/小票）

**后果**：2026-07-01 后未同时提供两种单据 → 报销将被退回；遗失需申请特殊审批

**实施逻辑**：

```python
from datetime import date

RECEIPT_POLICY_START = date(2026, 7, 1)
RECEIPT_THRESHOLD = 500.0

def needs_itemized_receipt(invoice_date_str, amount, category):
    """判断是否需要消费明细小票"""
    if category != "餐饮":
        return False
    if amount <= RECEIPT_THRESHOLD:
        return False
    # 开票日期在7/1之后才强制要求
    inv_date = date(int(invoice_date_str[:4]), int(invoice_date_str[4:6]), int(invoice_date_str[6:8]))
    return inv_date >= RECEIPT_POLICY_START
```

## Incremental Mode（增量模式）

```python
LAST_RUN_FILE = f"{WORKSPACE_DIR}/expense_last_run.json"

def save_last_run(latest_datetime):
    import json
    json.dump({"last_processed": latest_datetime}, open(LAST_RUN_FILE, "w"))

def get_last_run():
    import json, os
    if os.path.exists(LAST_RUN_FILE):
        return json.load(open(LAST_RUN_FILE))["last_processed"]
    return None
```

-   首次运行：处理全部邮件
    
-   后续运行：只处理 `receivedDateTime > last_processed` 的新邮件
    
-   用户说"全部重新处理"→ 强制全量
    

## Duplicate Detection（重复检测）

```python
def scan_existing_invoices(invoice_dir):
    import os
    existing = set()
    for f in os.listdir(invoice_dir):
        if f.endswith('.pdf'):
            existing.add(f.lower())
    return existing

def is_duplicate(new_filename, existing_set):
    return new_filename.lower() in existing_set
```

去重规则：同日期+同店名+同金额 → 跳过。

## File Naming Convention

格式：`YYYYMMDD_店名_金额.pdf`

**日期规则**：

<table style="min-width: 50px;"><colgroup><col style="min-width: 25px;"><col style="min-width: 25px;"></colgroup><tbody><tr><th colspan="1" rowspan="1"><p>类别</p></th><th colspan="1" rowspan="1"><p>使用哪个日期</p></th></tr><tr><td colspan="1" rowspan="1"><p>一般发票（餐饮等）</p></td><td colspan="1" rowspan="1"><p>开票日期</p></td></tr><tr><td colspan="1" rowspan="1"><p>酒店发票+水单</p></td><td colspan="1" rowspan="1"><p><strong>入住日期</strong></p></td></tr><tr><td colspan="1" rowspan="1"><p>高铁票</p></td><td colspan="1" rowspan="1"><p><strong>乘车日期</strong></p></td></tr></tbody></table>

**特殊后缀**：

<table style="min-width: 50px;"><colgroup><col style="min-width: 25px;"><col style="min-width: 25px;"></colgroup><tbody><tr><th colspan="1" rowspan="1"><p>类别</p></th><th colspan="1" rowspan="1"><p>示例</p></th></tr><tr><td colspan="1" rowspan="1"><p>酒店水单</p></td><td colspan="1" rowspan="1"><p><code>20260330_万怡酒店_500.00_水单.pdf</code></p></td></tr><tr><td colspan="1" rowspan="1"><p>滴滴行程单</p></td><td colspan="1" rowspan="1"><p><code>20260315_滴滴_45.00_行程单.pdf</code></p></td></tr><tr><td colspan="1" rowspan="1"><p>高铁票</p></td><td colspan="1" rowspan="1"><p><code>20260511_高铁_83.00.pdf</code> 🚄</p></td></tr></tbody></table>

**高铁票标注**：文件名中含"高铁"的发票，在汇总报告中额外标注 `🚄 Train Tab`，提醒用户在 Concur 中使用报销助手的 Train Tab 处理（12306 扫码导入），不走 Agent 模式。

## Workflow

### Step 0: 首次运行引导（仅第一次触发）

-   **Mode**: `agentic`
    
-   **Tool**: `run_python`
    
-   **Input**: 无
    
-   **Output**: 用户配置（公司名称、税号、常驻城市、invoice 路径）
    
-   **触发条件**: workspace 中不存在 `expense_config.json`
    
-   **Process**:
    
    1.  检查 `{WORKSPACE_DIR}/expense_config.json` 是否存在
        
    2.  如果不存在，向用户发送欢迎消息并询问配置信息
        
    3.  用户确认后保存配置
        
    4.  配置完成后自动继续 Step 1
        
-   **Validate**: `expense_config.json` 写入成功
    
-   **On failure**: 使用默认配置继续，但提醒用户稍后补充配置
    

### Step 1-10: 下载流程

1.  定位文件夹 + 增量检查
    
2.  扫描已有文件（重复检测）
    
3.  列出待处理邮件（增量过滤）
    
4.  分类邮件（决策树）
    
5.  批量下载 + 重命名 + 去重（TYPE\_ATTACHMENT）
    
6.  处理链接下载（TYPE\_LINK\_\*）
    
7.  处理百旺云短链
    
8.  浏览器下载（TYPE\_BROWSER）
    
9.  酒店发票类型校验
    
10.  归档邮件 + 保存时间戳
     

### Step 11: 汇总报告 + 智能提醒 + 餐饮自审 + Concur 指引

-   **Mode**: `agentic`
    
-   **Input**: 所有处理结果 + 已有发票列表
    
-   **Output**: 汇总表格 + 智能提醒 + 餐饮自审清单 + Concur 提交指引
    

报告格式：

```
### 发票下载简报
✅ 新下载 N 份，合计 ¥XXX.XX
🔄 跳过 M 份（已存在）

| # | 日期 | 商户 | 金额 | 类别 | 文件名 | 状态 |
|---|------|------|------|------|--------|------|
| 1 | 05-11 | 高铁 | ¥83 | 交通 | 20260511_高铁_83.00.pdf | ✅ 🚄 Train Tab |
| 2 | 03-30 | 万怡酒店 | ¥500 | 酒店 | 20260330_万怡酒店_500.00.pdf | ✅ 专票 |
| 3 | 05-20 | 上海见面谈 | ¥249 | 餐饮 | 20260520_上海见面谈_249.00.pdf | ✅ 🍽️ 备注与会人 |
| 4 | 05-13 | 星巴克 | ¥502 | 餐饮 | 20260513_星巴克_502.20.pdf | ✅ 🍽️ 备注与会人 ⚠️ 需小票 |

---
### 📋 智能提醒

#### 🧳 出差完整性检查
...（按日期聚合，检查缺失凭证）

#### 💰 金额合理性提醒
...（餐饮 > ¥300 提醒备注宴请人数和事由）

#### ⏰ 报销时效提醒
...（> 45天警告）

#### 🏨 酒店线下预订提醒
...（无 BCD 记录的酒店 → 提醒 comment 写 private offer 原因）

---
### 🍽️ 餐饮自审清单

所有餐饮发票提交时须在 Concur comment 中备注与会人信息。

#### ✍️ 与会人备注（所有餐饮必填）
| # | 发票 | 金额 | 需填写 |
|---|------|------|--------|
| 1 | 20260520_上海见面谈_249.00.pdf | ¥249 | 与会人：_____ |
| 2 | 20260513_星巴克_502.20.pdf | ¥502 | 与会人：_____ |

#### 🧾 消费明细小票检查（¥500+ 餐饮，2026-07-01 起强制）
⚠️ 以下发票单笔超过 ¥500，自 2026-07-01 起须同时提供消费明细小票，否则报销将被退回。
即使当前日期在 7/1 之前，也建议提前准备小票以养成习惯。

| # | 发票 | 金额 | 小票状态 |
|---|------|------|----------|
| 1 | 20260513_星巴克_502.20.pdf | ¥502.20 | ❓请确认是否有小票 |

> 💡 小票遗失？需在 Concur 中申请特殊审批（Special Approval）。

---
### 📤 Concur 提交指引
1. 🚄 **高铁票**（N张）→ 报销助手 **Train Tab**，12306 扫码导入
2. 🧾 **其余发票**（M张）→ 报销助手 **Agent 模式**，全选 invoice 根目录文件拖入
3. 📝 **注意事项**：
   - 🍽️ **所有餐饮** → comment 必须备注与会人（姓名/人数/事由）
   - 💰 餐饮 > ¥300 → comment 备注宴请人数和事由
   - 🧾 餐饮 > ¥500（7/1后）→ 须同时上传消费明细小票
   - 🏨 酒店线下预订 → comment 写「酒店提供 private offer 优惠价，故线下直订」
4. 💡 或者说"准备报销"，我帮你生成分类提交包
```

### Step 12: 一键生成提交包（按需触发）

-   **Mode**: `agentic`
    
-   **Tool**: `folder_create` + `file_copy`
    
-   **Input**: 用户说"准备报销"
    
-   **Output**: 临时分类文件夹
    

**触发条件**：用户明确说"准备报销"/"生成提交包"/"帮我分类好"

**Process**:

1.  在 invoice 根目录下创建 `_提交包_{YYYYMMDD}/` 临时文件夹
    
2.  按类别创建子文件夹并复制对应发票：
    

```
_提交包_20260521/
├── 餐饮/          ← 所有餐饮发票（供 Concur 餐饮 Tab）
│   ├── 20260513_星巴克_502.20.pdf
│   ├── 20260513_达凡特_484.20.pdf
│   └── ...
├── 网约车/         ← 滴滴等（供网约车 Tab）
│   ├── 20260315_滴滴_45.00.pdf
│   └── 20260315_滴滴_45.00_行程单.pdf
├── 酒店/          ← 酒店发票+水单（供酒店 Tab）
│   ├── 20260330_万怡酒店_500.00.pdf
│   └── 20260330_万怡酒店_500.00_水单.pdf
├── 话费/          ← 话费（供话费 Tab）
└── 高铁/          ← 仅供参考（实际用 Train Tab 扫码）
    └── 🚄 请用报销助手 Train Tab 处理，无需上传此文件夹
```

3.  告知用户：
    
    -   高铁票 → 用 Train Tab 12306 扫码
        
    -   其余文件夹 → 可按 Tab 逐个上传，也可全选拖入 Agent 模式
        

**注意**：

-   只复制（不移动）— 根目录原件保留
    
-   高铁票文件夹只是提示作用，实际应该用 Train Tab 扫码
    
-   提交包是临时产物，报销完成后可删除
    

## Smart Alerts（智能提醒逻辑）

### 1\. 出差完整性检查

按日期聚合，检查一次出差是否凭证齐全（交通+住宿+餐饮）。

### 2\. 金额合理性提醒

餐饮发票单张 > ¥300 → 提醒备注宴请人数和事由。

### 3\. 报销时效提醒

-   45-55 天：⚠️ 黄色警告
    
-   55+ 天：🔴 红色紧急
    

### 4\. 酒店线下预订提醒

无对应 BCD Invoice → 提醒 comment 写「private offer 优惠价，线下直订」。

### 5\. 餐饮与会人提醒（NEW）

**所有餐饮发票**（不限金额）→ 在汇总表格和 Concur 指引中提醒用户在 comment 中填写与会人信息（姓名、人数、事由）。这是公司政策强制要求，非可选。

### 6\. 消费明细小票检查（NEW - 2026-07-01 生效）

**餐饮发票单笔 > ¥500**：

-   2026-07-01 前：⚠️ 建议提醒（即将生效，建议提前养成习惯）
    
-   2026-07-01 起：🔴 强制要求，必须同时提供发票 + 消费明细小票
    

适用费用类型：

-   出差餐费 / Travel Meals
    
-   出差餐费-团体 / Travel Business Meal (group)
    
-   团体餐费:商务会议活动 / Group Meal: Business Meetings/Events
    
-   招待费-客户 / Entertainment – with Client
    

未提供小票 → 报销退回。小票遗失 → 需申请特殊审批。

在汇总报告中：

-   列出所有 > ¥500 的餐饮发票
    
-   标注 ⚠️ 提醒用户确认是否有对应小票
    
-   如果用户回复"没有小票"→ 提示走特殊审批流程
    

## PDF Header Validation

<table style="min-width: 75px;"><colgroup><col style="min-width: 25px;"><col style="min-width: 25px;"><col style="min-width: 25px;"></colgroup><tbody><tr><th colspan="1" rowspan="1"><p>头字节</p></th><th colspan="1" rowspan="1"><p>含义</p></th><th colspan="1" rowspan="1"><p>处理</p></th></tr><tr><td colspan="1" rowspan="1"><p><code>%PDF</code></p></td><td colspan="1" rowspan="1"><p>✅ 合法 PDF</p></td><td colspan="1" rowspan="1"><p>继续</p></td></tr><tr><td colspan="1" rowspan="1"><p><code>&lt;!DO</code></p></td><td colspan="1" rowspan="1"><p>HTML 预览页</p></td><td colspan="1" rowspan="1"><p>换浏览器方式</p></td></tr><tr><td colspan="1" rowspan="1"><p><code>PK..</code></p></td><td colspan="1" rowspan="1"><p>ZIP/OFD</p></td><td colspan="1" rowspan="1"><p>标记失败</p></td></tr><tr><td colspan="1" rowspan="1"><p><code>.PNG</code></p></td><td colspan="1" rowspan="1"><p>PNG 图片</p></td><td colspan="1" rowspan="1"><p>标记失败</p></td></tr></tbody></table>

## Hotel Invoice Type Validation

<table style="min-width: 75px;"><colgroup><col style="min-width: 25px;"><col style="min-width: 25px;"><col style="min-width: 25px;"></colgroup><tbody><tr><th colspan="1" rowspan="1"><p>类型</p></th><th colspan="1" rowspan="1"><p>关键词</p></th><th colspan="1" rowspan="1"><p>处理</p></th></tr><tr><td colspan="1" rowspan="1"><p>SPECIAL</p></td><td colspan="1" rowspan="1"><p><code>增值税专用发票</code></p></td><td colspan="1" rowspan="1"><p>✅ 合规</p></td></tr><tr><td colspan="1" rowspan="1"><p>GENERAL</p></td><td colspan="1" rowspan="1"><p><code>增值税普通发票</code></p></td><td colspan="1" rowspan="1"><p>⚠️ 提醒换开</p></td></tr><tr><td colspan="1" rowspan="1"><p>数电票</p></td><td colspan="1" rowspan="1"><p><code>全面数字化的电子发票</code> + "专用"</p></td><td colspan="1" rowspan="1"><p>✅ / ⚠️</p></td></tr><tr><td colspan="1" rowspan="1"><p>UNKNOWN</p></td><td colspan="1" rowspan="1"><p>无法提取文本</p></td><td colspan="1" rowspan="1"><p>⚠️ 人工确认</p></td></tr></tbody></table>

## Platform URL Patterns

<table style="min-width: 75px;"><colgroup><col style="min-width: 25px;"><col style="min-width: 25px;"><col style="min-width: 25px;"></colgroup><tbody><tr><th colspan="1" rowspan="1"><p>平台</p></th><th colspan="1" rowspan="1"><p>URL 模式</p></th><th colspan="1" rowspan="1"><p>下载方式</p></th></tr><tr><td colspan="1" rowspan="1"><p>fapiao.com</p></td><td colspan="1" rowspan="1"><p><code>fapiao.com/dzfp-web/pdf/download?...</code></p></td><td colspan="1" rowspan="1"><p>直接 curl</p></td></tr><tr><td colspan="1" rowspan="1"><p>百旺云预览</p></td><td colspan="1" rowspan="1"><p><code>pis.baiwang.com/smkp-vue/previewInvoice*</code></p></td><td colspan="1" rowspan="1"><p>浏览器点击"下载PDF文件"按钮</p></td></tr><tr><td colspan="1" rowspan="1"><p>百旺云短链</p></td><td colspan="1" rowspan="1"><p><code>u.baiwang.com/xxx</code></p></td><td colspan="1" rowspan="1"><p>301→构造 URL</p></td></tr><tr><td colspan="1" rowspan="1"><p>xforceplus</p></td><td colspan="1" rowspan="1"><p><code>s.xforceplus.com/...</code></p></td><td colspan="1" rowspan="1"><p>直接下载</p></td></tr><tr><td colspan="1" rowspan="1"><p>票点点</p></td><td colspan="1" rowspan="1"><p><code>sf-epiaotong.com</code></p></td><td colspan="1" rowspan="1"><p>正文 PDF URL</p></td></tr><tr><td colspan="1" rowspan="1"><p>百旺金穗云</p></td><td colspan="1" rowspan="1"><p><code>bwfapiao.com</code></p></td><td colspan="1" rowspan="1"><p>类似百旺云</p></td></tr><tr><td colspan="1" rowspan="1"><p>诺诺网</p></td><td colspan="1" rowspan="1"><p>SPA 预览页</p></td><td colspan="1" rowspan="1"><p>浏览器</p></td></tr></tbody></table>

## Lessons Learned

### Do

-   **所有发票统一放 invoice 根目录** — 便于查重
    
-   **高铁票在报告中标注 🚄 Train Tab** — 提醒走 12306 扫码
    
-   **所有餐饮发票标注 🍽️ 备注与会人** — 公司政策强制要求
    
-   **餐饮 > ¥500 标注 ⚠️ 需小票** — 7/1 后强制，之前建议
    
-   **"准备报销"时生成临时分类提交包** — 便于按 Tab 上传
    
-   下载前扫描根目录做去重
    
-   保存 last\_processed 时间戳做增量
    
-   金额使用价税合计，保留两位小数
    
-   酒店发票用入住日期、高铁票用乘车日期
    
-   下载后做 PDF 头字节校验
    
-   酒店发票校验专票/普票
    
-   百旺云预览页用 browser\_navigate + browser\_download\_file(element\_id=下载PDF按钮)
    

### Don't

-   **不要自动归类到子文件夹**（报销打款前保持根目录）
    
-   **不要对已有文件做任何操作**
    
-   **不要把高铁票放入 Agent 模式上传**（应提醒用 Train Tab）
    
-   **不要遗漏餐饮与会人提醒**（即使金额很小也要提醒）
    
-   不要假设所有邮件都有附件
    
-   不要用邮件接收时间作为发票日期
    
-   智能提醒只提示不阻止
    

### Common Failures

-   重复文件名 → 追加序号 `_2`
    
-   商户名提取失败 → `file_read_pdf` 兜底
    
-   日期提取失败 → receivedDateTime（UTC+8）兜底
    
-   BCD 邮件 404 → `email_search` 代替
    
-   百旺云链接过期 → 超60天失败
    
-   百旺云 downloadFormat URL 直接 curl 返回 HTML（非 PDF）→ 必须用浏览器
    

### When to Ask the User

-   发现重复发票时
    
-   邮件分类不确定时
    
-   下载失败时
    
-   酒店发票为普票时
    
-   用户说"全部重新处理"时
    
-   用户说"准备报销"时确认要包含哪些发票
    
-   **餐饮 > ¥500 时确认是否有消费明细小票**
