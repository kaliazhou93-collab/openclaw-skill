# Lessons Learned（实战经验）

> 从多次实际执行中积累的踩坑和最佳实践，补充到 SKILL.md 的 Lessons Learned 章节。

## Do

- **所有发票统一放 invoice 根目录** — 便于查重，报销打款前不动
- **高铁票在报告中标注 🚄 Train Tab** — 提醒走 12306 扫码或直接上传 PDF
- **所有餐饮发票标注 🍽️ 备注与会人** — 公司政策强制要求，不限金额
- **餐饮 > ¥500 标注 ⚠️ 需小票** — 7/1 后强制，之前建议提前准备
- **"准备报销"时生成临时分类提交包** — 便于按 Tab 上传
- 下载前扫描根目录做去重
- 保存 last_processed 时间戳做增量
- 金额使用价税合计，保留两位小数
- 酒店发票用入住日期、高铁票用乘车日期
- 下载后做 PDF 头字节校验
- 酒店发票校验专票/普票
- 百旺云预览页用 `browser_navigate` + `browser_download_file(element_id=下载PDF按钮)`
- 百旺云下载成功后记录真实 URL（`https://pis.baiwang.com/bwmg/mix/bw/downloadFormat?param=...&formatType=PDF`），后续相同模板可直接 `download_file`
- `email_move` 做顶层工具调用，**不要放在 `run_python` 里**（会超时）
- 百旺金穗云 URL 带 `&amp;` 时先 `html.unescape()` 再请求
- 酒店水单若邮件中找不到，让用户直接拖 PDF 附件发给 agent
- 发票 PDF 文本乱码时用 `file_get_page_raster` + 视觉 OCR 兜底
- 高铁票日期从 PDF 正文中提取乘车日期（非开票日期），格式如"2026年06月02日 16:58开"

## Don't

- **不要自动归类到子文件夹** — 收到 Remittance Advice 打款邮件前，所有发票保持根目录
- **不要对已有文件做任何操作**
- **不要把高铁票放入 Agent 模式上传**（应提醒用 Train Tab 或直接上传 PDF）
- **不要遗漏餐饮与会人提醒**（即使金额很小也要提醒）
- **不要猜 attachmentId** — 必须从 `email_read` 返回的 JSON 中取 `attachments[].id`
- **不要用 `browser_download_file` 保存到目标文件夹** — 浏览器下载保存路径不在 allowed folders，改用 `download_file(url=真实下载URL)` 保存到 workspace/downloads/，再 `file_copy` 到 invoice 目录
- 不要假设所有邮件都有附件
- 不要用邮件接收时间作为发票日期
- 智能提醒只提示不阻止
- **不要生成"_提交包_"分类文件夹** — Concur 报销助手不支持按文件夹上传，直接全选根目录 PDF 拖入 Agent 模式

## Common Failures

| 故障 | 原因 | 解决 |
|------|------|------|
| 重复文件名 | 同一商户同日多笔 | 追加序号 `_2`、`_3` |
| 商户名提取失败 | PDF 文本结构不规则 | `file_read_pdf` 全文搜索兜底 |
| 日期提取失败 | 非标准格式 | receivedDateTime（UTC+8）兜底 |
| BCD 邮件 404 | 附件 ID 过期 | `email_search` 重新获取 |
| 百旺云 downloadFormat 直接 curl 返回 HTML | Vue SPA 页面 | 必须用浏览器打开预览页点击下载按钮 |
| 百旺云短链过期 | 超 60 天 | 提示用户联系商户重发 |
| attachmentId 404 | 使用了错误的 ID | 从 `email_read` 最新返回值中取 |
| `email_move` 在 run_python 中超时 | 工具调用链路限制 | 改为顶层直接调用 `email_move` |
| 高铁票 PDF 文本乱码 | 字体未嵌入 | `file_get_page_raster` 渲染后视觉推断 |
| 浙江税务局二维码发票 | 网站有反爬 | 让用户手机扫码下载后直接发 PDF |

## When to Ask the User

- 发现重复发票时
- 邮件分类不确定时
- 下载失败时
- 酒店发票为普票时（需换开专票）
- 用户说"全部重新处理"时
- 用户说"准备报销"时确认要包含哪些发票
- **餐饮 > ¥500 时确认是否有消费明细小票**
- **发票抬头/税号不匹配时**（非"亚马逊信息服务（北京）有限公司上海分公司" / 913100005903918561）
- 二维码发票无法自动下载时（让用户手机扫码）
- 酒店水单在邮箱中找不到时（让用户直接拖文件发来）

## 归档触发规则

**何时从根目录归类到子文件夹：**

仅当收到以下邮件时才触发归档：
- Subject 含: `Remittance Advice - KALIA ZHOU(205735013) Payment#`
- 正文含: `The following payment has been made by Amazon.cn`

收到此邮件表示上次提交的发票已完成报销打款。此时才执行：
```
滴滴/曹操出行 → 打车/
酒店发票+水单 → 酒店/
话费 → phone bill/
火车票 → 火车票/
```

**在收到 Remittance Advice 之前，所有发票保持在 invoice 根目录不动。**
