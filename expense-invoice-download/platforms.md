# 支持的发票平台

## 直接附件下载

| 平台 | 发件人域名 | 附件格式 | 备注 |
|------|-----------|----------|------|
| 票通 | vpiaotong.com | PDF + OFD + XML | 只取 PDF |
| 美团 | meituan.com / it_fapiao@meituan.com | PDF + OFD + XML | 只取 PDF |
| 51发票 | 51fapiao.cloud / dzfp@51fapiao.cloud | PDF + OFD | 只取 PDF |
| 麦当劳 | mcd.cn / e-invoice@mcd.cn | PDF + OFD | 只取 PDF |
| BCD Travel | bcdtravel.cn / amazon@bcdtravel.cn | PDF (Invoice + Itinerary) | 下载全部 PDF |
| 滴滴出行 | didichuxing.com / didifapiao@mailgate.xiaojukeji.com | PDF (发票 + 行程单) | 下载全部附件 |
| 曹操出行 | didifapiao@mailgate.xiaojukeji.com | PDF (发票 + 行程单) | 第三方网约车，邮件标题含"第三方发票及行程单"，附件名含"曹操出行" |
| 赛百味 | invoice@subway.com.cn | PDF + OFD + ZIP | 只取 PDF；正文含下载链接可备用 |
| 酒店 Folio | marriotthotels.com 等 | PDF (水单) | 下载全部 |

## 邮件正文链接下载

| 平台 | 发件人/域名 | URL 模式 | 下载方式 |
|------|------------|----------|----------|
| 票点点 | sf-epiaotong.com | `https://files.pdd-fapiao.com/invoice/.../pdf/...` | 直接 GET |
| 百旺金穗云 | bwfapiao.com | `https://xz.bwfapiao.com/qdp/.../dzfp_*.pdf?Expires=...` | 直接 GET（⚠️ 注意 HTML unescape，见下方说明） |
| fapiao.com | fapiao.com | `fapiao.com/dzfp-web/pdf/download?...` | 直接 GET |
| xforceplus | xforceplus.com | `s.xforceplus.com/...` 标 (PDF) | 直接 GET |

### 百旺金穗云 HTML unescape 注意事项

邮件 HTML 正文中的 URL 可能包含 HTML 实体编码：
```
原始: https://xz.bwfapiao.com/qdp/...?Expires=1234&amp;Signature=abc&amp;token=xyz
正确: https://xz.bwfapiao.com/qdp/...?Expires=1234&Signature=abc&token=xyz
```

处理方法：
```python
import html
raw_url = "https://xz.bwfapiao.com/qdp/...?Expires=1234&amp;Signature=abc"
clean_url = html.unescape(raw_url)
```

不做 unescape 会导致参数解析错误、下载 403/404。

## 百旺云（3 种模板）

### 模板 1：预览页（最常见）

- **URL 模式**: `https://pis.baiwang.com/smkp-vue/previewInvoiceAllEle?param=...`
- **下载方式**: 浏览器打开 → 等待 Vue SPA 渲染（5秒）→ 点击"下载PDF文件"按钮
- **备注**: 页面是 Vue SPA，直接 curl 只拿到 HTML shell；必须用 `browser_navigate` + `browser_download_file(element_id=下载PDF按钮)`
- **真实下载 URL**: 点击后浏览器会请求 `https://pis.baiwang.com/bwmg/mix/bw/downloadFormat?param=...&formatType=PDF`，该 URL 可用 `download_file` 直接获取 PDF

### 模板 2：短链

- **URL 模式**: `https://u.baiwang.com/xxx`
- **下载方式**: GET 短链 → 跟随 301 → 提取 param → 构造 downloadFormat URL
- **备注**: 短链超 60 天可能过期

### 模板 3：直接下载

- **URL 模式**: 各种 baiwang.com 子域
- **下载方式**: 可能需要浏览器打开

## 需浏览器下载

| 平台 | 场景 | 备注 |
|------|------|------|
| 百旺云 | 上述模板 1 如 downloadFormat URL 失败 | 浏览器打开 → 点击"下载PDF" |
| 诺诺网 | SPA 预览页 | 需浏览器 |

## 不支持 / 需手动处理

| 平台 | 原因 | 建议 |
|------|------|------|
| 数电发票二维码 | 无 QR 解码库，税务局有反爬 | 用户手机扫码后发链接或直接发 PDF |
| 12306 高铁票 | 不主动推送到邮箱 | 用户从 APP 下载后直接发 PDF |
| 浙江省税务局 | dppt.zhejiang.chinatax.gov.cn 反爬 | 用户手机扫码下载 |

## PDF 头字节校验

下载后立即验证文件合法性：
| 头 4 字节 | Hex | 含义 | 处理 |
|-----------|-----|------|------|
| %PDF | 25 50 44 46 | ✅ 合法 PDF | 继续 |
| <!DO | 3C 21 44 4F | ❌ HTML 预览页 | 换浏览器下载 |
| PK.. | 50 4B 03 04 | ❌ ZIP/OFD | 如期望 PDF 则失败 |
| .PNG | 89 50 4E 47 | ❌ PNG 图片 | 失败（拿到二维码） |

## 噪音邮件过滤

以下应自动跳过：

**发件人黑名单**:
- 银行: cmbchina, citiccard, bocomcc, cgbchina, hsbc
- 订阅: amazonaws.com（AWS 账单不走中国报销）

**主题关键词黑名单**:
- 预订确认, 预订取消, 客房升级, 退票, 改签
- 还款, eStatement, 月结单
- "Expense report", "Re:", "Guidelines", "Remittance"
- "用户支付通知"（12306 支付通知无附件）
