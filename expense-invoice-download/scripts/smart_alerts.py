"""
智能提醒模块
报销汇总报告中的三项检查：出差完整性、金额合理性、报销时效。
"""
import re
import os
from datetime import datetime, timedelta
from collections import defaultdict


def scan_invoices_from_filenames(invoice_dir: str) -> list:
    """
    扫描 invoice 根目录，从文件名解析发票信息。
    
    Returns:
        list of dict: [{file, date, merchant, amount, suffix, category}]
    """
    invoices = []
    for f in os.listdir(invoice_dir):
        if not f.endswith('.pdf'):
            continue
        m = re.match(r'^(\d{8})_(.+?)_(\d+\.\d+)(?:_(.+))?\.pdf$', f)
        if m:
            date_str = m.group(1)
            merchant = m.group(2)
            amount = float(m.group(3))
            suffix = m.group(4) or ''
            
            # Categorize
            if '高铁' in merchant:
                category = '交通'
            elif any(k in merchant for k in ['酒店', '万怡', '希尔顿', '洲际', 'Marriott', 'Hilton']):
                category = '酒店'
            elif '滴滴' in merchant or 'DiDi' in merchant:
                category = '交通'
            elif 'BCD' in merchant:
                category = '交通'
            elif any(k in merchant for k in ['话费', '移动', '联通', '电信']):
                category = '话费'
            else:
                category = '餐饮'
            
            invoices.append({
                'file': f,
                'date': date_str,
                'merchant': merchant,
                'amount': amount,
                'suffix': suffix,
                'category': category
            })
    
    return sorted(invoices, key=lambda x: x['date'])


def check_trip_completeness(invoices: list) -> list:
    """
    出差完整性检查：按日期聚合，检查是否缺少凭证。
    
    识别出差的信号：有酒店发票 或 有外地交通票。
    
    Returns:
        list of dict: [{range, city, hotel, transport, meals, missing}]
    """
    alerts = []
    
    # 找出酒店发票（不含水单）
    hotels = [i for i in invoices if i['category'] == '酒店' and i['suffix'] != '水单']
    transports = [i for i in invoices if i['category'] == '交通']
    
    # 对每个酒店入住，检查前后2天内是否有交通票
    for hotel in hotels:
        hotel_date = datetime.strptime(hotel['date'], '%Y%m%d')
        nearby_transport = [
            t for t in transports
            if abs((datetime.strptime(t['date'], '%Y%m%d') - hotel_date).days) <= 2
        ]
        nearby_meals = [
            i for i in invoices
            if i['category'] == '餐饮'
            and abs((datetime.strptime(i['date'], '%Y%m%d') - hotel_date).days) <= 1
        ]
        
        if not nearby_transport:
            alerts.append({
                'range': hotel['date'],
                'hotel': hotel['merchant'],
                'missing': '交通票（高铁/机票）',
                'transport': [],
                'meals': nearby_meals
            })
    
    # 对交通票往返组合，检查中间是否有酒店
    # Group transports by nearby dates
    if len(transports) >= 2:
        for i, t1 in enumerate(transports):
            for t2 in transports[i+1:]:
                d1 = datetime.strptime(t1['date'], '%Y%m%d')
                d2 = datetime.strptime(t2['date'], '%Y%m%d')
                gap = (d2 - d1).days
                if 1 <= gap <= 5:  # Likely a round trip
                    nearby_hotel = [
                        h for h in hotels
                        if d1 <= datetime.strptime(h['date'], '%Y%m%d') <= d2
                    ]
                    if not nearby_hotel:
                        alerts.append({
                            'range': f"{t1['date']}~{t2['date']}",
                            'hotel': None,
                            'missing': '酒店发票',
                            'transport': [t1, t2],
                            'meals': []
                        })
    
    return alerts


def check_amount_reasonableness(invoices: list, threshold: float = 300.0) -> list:
    """
    金额合理性提醒：餐饮发票单张超过阈值。
    
    Args:
        invoices: 发票列表
        threshold: 提醒阈值（默认 ¥300）
    
    Returns:
        list of dict: [{file, amount, message}]
    """
    alerts = []
    for inv in invoices:
        if inv['category'] == '餐饮' and inv['amount'] > threshold:
            alerts.append({
                'file': inv['file'],
                'amount': inv['amount'],
                'message': f'餐饮超¥{threshold:.0f}，请确认是否需备注宴请人数'
            })
    return alerts


def check_expiry(invoices: list, today: datetime = None, warn_days: int = 45, urgent_days: int = 55) -> list:
    """
    报销时效提醒：发票开票日期距今超过指定天数。
    
    Args:
        invoices: 发票列表
        today: 当前日期（默认 now）
        warn_days: 警告天数（默认 45）
        urgent_days: 紧急天数（默认 55）
    
    Returns:
        list of dict: [{file, date, days, urgency, message}]
    """
    if today is None:
        today = datetime.now()
    
    alerts = []
    for inv in invoices:
        try:
            inv_date = datetime.strptime(inv['date'], '%Y%m%d')
            days_elapsed = (today - inv_date).days
            if days_elapsed > warn_days:
                urgency = '🔴 紧急' if days_elapsed > urgent_days else '⚠️ 警告'
                alerts.append({
                    'file': inv['file'],
                    'date': inv['date'],
                    'days': days_elapsed,
                    'urgency': urgency,
                    'message': f'已过{days_elapsed}天，建议尽快提交！'
                })
        except ValueError:
            continue
    
    return sorted(alerts, key=lambda x: -x['days'])


def generate_smart_alerts_report(invoice_dir: str, today: datetime = None) -> str:
    """
    生成完整的智能提醒报告（Markdown格式）。
    """
    invoices = scan_invoices_from_filenames(invoice_dir)
    
    if not invoices:
        return "### 📋 智能提醒\n\n✅ invoice 根目录无待报销发票。\n"
    
    report = "### 📋 智能提醒\n\n"
    
    # 1. 出差完整性
    trip_alerts = check_trip_completeness(invoices)
    report += "#### 🧳 出差完整性检查\n"
    if trip_alerts:
        for alert in trip_alerts:
            report += f"- ⚠️ **{alert['range']}** {alert.get('hotel', '未知')}: 缺少{alert['missing']}\n"
    else:
        report += "- ✅ 所有出差凭证齐全\n"
    report += "\n"
    
    # 2. 金额合理性
    amount_alerts = check_amount_reasonableness(invoices)
    report += "#### 💰 金额合理性提醒\n"
    if amount_alerts:
        for alert in amount_alerts:
            report += f"- ⚠️ `{alert['file']}` ¥{alert['amount']:.2f} — {alert['message']}\n"
    else:
        report += "- ✅ 无异常\n"
    report += "\n"
    
    # 3. 报销时效
    expiry_alerts = check_expiry(invoices, today)
    report += "#### ⏰ 报销时效提醒\n"
    if expiry_alerts:
        for alert in expiry_alerts:
            report += f"- {alert['urgency']} `{alert['file']}` — {alert['message']}\n"
    else:
        report += "- ✅ 所有发票均在时效内\n"
    
    return report
