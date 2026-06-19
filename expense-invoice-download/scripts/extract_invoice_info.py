"""
发票信息提取模块
从邮件主题/正文/PDF文本中提取日期、商户名、金额，用于统一命名。
"""
import re
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))


def extract_invoice_info(email_subject: str, email_body_html: str = None, pdf_text: str = None):
    """
    从邮件信息中提取日期、店名、金额，用于重命名。
    
    Args:
        email_subject: 邮件主题
        email_body_html: 邮件正文HTML
        pdf_text: PDF提取的文本（兜底）
    
    Returns:
        tuple: (date_str, merchant, amount) - 如 ('20260520', '上海见面谈', '249.00')
    """
    date = None
    merchant = None
    amount = None
    
    # === 日期提取 ===
    # 优先：邮件正文中的"开票日期"
    date_patterns = [
        r'开票日期[：:\s]*(\d{4})\D*(\d{1,2})\D*(\d{1,2})',
        r'开具.*?(\d{4})\D*(\d{2})\D*(\d{2})',
        r'于(\d{4})\D*(\d{2})\D*(\d{2})日?\D*开',
    ]
    for pat in date_patterns:
        m = re.search(pat, email_body_html or '')
        if m:
            date = f"{m.group(1)}{m.group(2).zfill(2)}{m.group(3).zfill(2)}"
            break
    
    # 次选：主题中的日期
    if not date:
        m = re.search(r'(\d{4})-?(\d{2})-?(\d{2})', email_subject)
        if m:
            date = f"{m.group(1)}{m.group(2)}{m.group(3)}"
    
    # 兜底：PDF文本中的开票日期
    if not date and pdf_text:
        for pat in date_patterns:
            m = re.search(pat, pdf_text)
            if m:
                date = f"{m.group(1)}{m.group(2).zfill(2)}{m.group(3).zfill(2)}"
                break
    
    # === 商户名提取 ===
    merchant_patterns = [
        r'来自[【\[]?(.+?)[】\]]?的[电子]*发票',
        r'【电子发票】(.+?)(?:（|[\(])',
        r'来自\d*\+?(.+?)的电子发票',
        r'【(.+?)】开具的发票',
    ]
    for pat in merchant_patterns:
        m = re.search(pat, email_subject)
        if m:
            merchant = m.group(1).strip()
            break
    
    # 清理商户名
    if merchant:
        cleaned = re.sub(r'[（(].*?[）)].*?(有限公司|餐饮|管理|服务)', '', merchant).strip()
        if cleaned:
            merchant = cleaned
        else:
            merchant = merchant[:15]
    
    # === 金额提取（价税合计）===
    amount_patterns = [
        r'发票金额[：:\s]*[¥￥]?\s*(\d+\.?\d*)',
        r'价税合计.*?[¥￥]?\s*(\d+\.\d{2})',
        r'合计金额[：:\s]*[¥￥]?\s*(\d+\.?\d*)',
        r'金额[：:\s]*[¥￥]?\s*(\d+\.?\d*)',
    ]
    search_text = email_subject + '\n' + (email_body_html or '')
    for pat in amount_patterns:
        m = re.search(pat, search_text)
        if m:
            amount = m.group(1)
            # 确保两位小数
            if '.' not in amount:
                amount += '.00'
            elif len(amount.split('.')[1]) == 1:
                amount += '0'
            break
    
    return date, merchant, amount


def build_filename(date: str, merchant: str, amount: str, suffix: str = '') -> str:
    """
    构造最终文件名 YYYYMMDD_店名_金额.pdf
    
    Args:
        date: 日期字符串 YYYYMMDD
        merchant: 商户名（已清理）
        amount: 金额字符串（如 '249.00'）
        suffix: 可选后缀（如 '水单'、'行程单'）
    
    Returns:
        str: 文件名，如 '20260520_上海见面谈_249.00.pdf'
        None: 如果无法生成有意义的名字
    """
    parts = []
    if date:
        parts.append(date)
    if merchant:
        safe_name = re.sub(r'[/\\:*?"<>|]', '', merchant)
        parts.append(safe_name[:15])
    if amount:
        parts.append(amount)
    
    if not parts:
        return None
    
    filename = '_'.join(parts)
    if suffix:
        filename += f'_{suffix}'
    return filename + '.pdf'


def validate_pdf_header(filepath: str) -> tuple:
    """
    校验PDF文件头字节。
    
    Returns:
        tuple: (is_valid, file_type)
        - (True, 'PDF') - 合法PDF
        - (False, 'HTML') - HTML预览页
        - (False, 'ZIP') - ZIP/OFD
        - (False, 'PNG') - PNG图片
        - (False, 'UNKNOWN') - 未知格式
    """
    with open(filepath, 'rb') as f:
        header = f.read(4)
    
    if header == b'%PDF':
        return True, 'PDF'
    elif header == b'<!DO' or header == b'<!do':
        return False, 'HTML'
    elif header == b'PK\x03\x04':
        return False, 'ZIP'
    elif header == b'\x89PNG':
        return False, 'PNG'
    else:
        return False, 'UNKNOWN'


def check_hotel_invoice_type(pdf_text: str) -> str:
    """
    校验酒店发票类型。
    
    Returns:
        'SPECIAL' - 增值税专用发票 ✅
        'GENERAL' - 增值税普通发票 ⚠️
        'UNKNOWN' - 无法判断
    """
    if '增值税专用发票' in pdf_text or '专用发票' in pdf_text:
        return 'SPECIAL'
    elif '增值税普通发票' in pdf_text or '普通发票' in pdf_text or '电子普通发票' in pdf_text:
        return 'GENERAL'
    elif '全面数字化的电子发票' in pdf_text or '数电发票' in pdf_text:
        if '专用' in pdf_text:
            return 'SPECIAL'
        else:
            return 'GENERAL'
    else:
        return 'UNKNOWN'


def extract_hotel_checkin_date(email_subject: str, email_body: str = '') -> str:
    """
    从酒店水单邮件中提取入住日期。
    
    Patterns:
        "from 30/03/26 to 31/03/26" → 20260330
        "入住日期：2026-03-30" → 20260330
    """
    # Pattern: from DD/MM/YY
    m = re.search(r'from\s+(\d{2})/(\d{2})/(\d{2})', email_subject)
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
        return f"20{year}{month}{day}"
    
    # Pattern: 入住日期
    m = re.search(r'入住[日期]*[：:\s]*(\d{4})\D*(\d{2})\D*(\d{2})', email_body)
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"
    
    return None
