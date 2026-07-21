#!/usr/bin/env python3
"""
中国手机号段精准数据库
覆盖全国 31 省、331 个城市
7位精准 → 精确到城市级别
运营商 → 移动/联通/电信/广电
数据来源：工信部公开号段
"""

import json
import os
import re

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(__file__), "phone_db.json")

# 全局缓存
_db_cache = None


def _load_db() -> dict:
    """延迟加载数据库"""
    global _db_cache
    if _db_cache is not None:
        return _db_cache

    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, 'r', encoding='utf-8') as f:
                _db_cache = json.load(f)
                return _db_cache
        except (json.JSONDecodeError, IOError):
            pass

    # 回退到内嵌数据
    return _get_fallback_db()


def _get_fallback_db() -> dict:
    """内嵌备用数据库（精简版）"""
    return {
        # ===== 运营商级别号段（4位精度） =====
        **{
            p: {"operator": "中国移动", "province": "全国", "type": "2G/4G"}
            for p in ["134","135","136","137","138","139","144","147","148",
                      "150","151","152","157","158","159","170","172","178",
                      "182","183","184","187","188","195","197","198"]
        },
        **{
            p: {"operator": "中国联通", "province": "全国", "type": "2G"}
            for p in ["130","131","132","145","146","155","156","166","167",
                      "171","175","176","185","186","196"]
        },
        **{
            p: {"operator": "中国电信", "province": "全国", "type": "2G/3G"}
            for p in ["133","149","153","173","177","180","181","189","191","193","199"]
        },
        **{
            p: {"operator": "中国广电", "province": "全国", "type": "5G"}
            for p in ["192"]
        },
    }


# ===== 4位运营商数据库 =====
PREFIX4_DB = {
    **{p: {"operator": "中国移动", "province": "全国", "type": "2G/3G/4G/5G/物联网"}
       for p in ["134","135","136","137","138","139","144","147","148",
                 "150","151","152","157","158","159","170","172","178",
                 "182","183","184","187","188","195","197","198"]},
    **{p: {"operator": "中国联通", "province": "全国", "type": "2G/3G/4G/5G"}
       for p in ["130","131","132","145","146","155","156","166","167",
                 "171","175","176","185","186","196"]},
    **{p: {"operator": "中国电信", "province": "全国", "type": "2G/3G/4G/5G"}
       for p in ["133","149","153","173","177","180","181","189","191","193","199"]},
    **{p: {"operator": "中国广电", "province": "全国", "type": "5G(700MHz)"}
       for p in ["192"]},
}


def lookup(phone: str) -> dict:
    """
    查询手机号归属地
    :param phone: 手机号（字符串，可含+86）
    :return: 结果字典
    """
    # 清理输入
    phone = phone.strip().replace(' ', '').replace('-', '').replace('_', '')

    # 处理 +86 国际前缀
    if phone.startswith('+86'):
        phone = phone[3:]
    elif phone.startswith('86') and len(phone) > 11:
        phone = phone[2:]

    # 基础验证
    if not phone.isdigit():
        return {'success': False, 'error': '请输入正确的手机号码（仅数字）', 'phone': phone}

    if len(phone) < 3:
        return {'success': False, 'error': '号码太短，至少需要3位', 'phone': phone}

    if len(phone) > 15:
        return {'success': False, 'error': '号码格式不正确', 'phone': phone}

    # ===== 查询 7 位精准数据 =====
    if len(phone) >= 7:
        prefix7 = phone[:7]
        db = _load_db()
        if prefix7 in db:
            info = db[prefix7]
            return {
                'success': True,
                'phone': phone,
                'prefix': prefix7,
                'operator': info['operator'],
                'province': info['province'],
                'city': info['city'],
                'precision': '城市级别',
            }

    # ===== 查询 4 位运营商数据 =====
    prefix4 = phone[:4]
    if prefix4 in PREFIX4_DB:
        info = PREFIX4_DB[prefix4]
        return {
            'success': True,
            'phone': phone,
            'prefix': prefix4,
            'operator': info['operator'],
            'province': '全国（需7位以上精确到省/市）',
            'city': None,
            'precision': '运营商级别',
            'type': info.get('type', ''),
        }

    # ===== 查询 3 位号段 =====
    prefix3 = phone[:3]
    if prefix3 in ['134','135','136','137','138','139',
                    '145','146','147','148',
                    '150','151','152','155','156',
                    '157','158','159','166','167',
                    '170','171','172','173','175','176','177','178',
                    '180','181','182','183','184','185','186','187','188','189',
                    '191','192','193','195','197','198','199']:
        return {
            'success': True,
            'phone': phone,
            'prefix': prefix3,
            'operator': _get_operator_from_prefix3(prefix3),
            'province': '全国（需7位以上精确到省/市）',
            'city': None,
            'precision': '运营商级别',
        }

    return {
        'success': False,
        'error': '未找到该号段信息，可能是新发放号段或卫星/特服号',
        'phone': phone,
        'prefix': phone[:4] if len(phone) >= 4 else phone,
    }


def _get_operator_from_prefix3(p3: str) -> str:
    """根据3位号段判断运营商"""
    cmcc = ['134','135','136','137','138','139','144','147','148',
            '150','151','152','157','158','159','170','172','178',
            '182','183','184','187','188','195','197','198']
    cucc = ['130','131','132','145','146','155','156','166','167',
            '171','175','176','185','186','196']
    ctcc = ['133','149','153','173','177','180','181','189','191','193','199']
    cgtv = ['192']
    if p3 in cmcc: return '中国移动'
    if p3 in cucc: return '中国联通'
    if p3 in ctcc: return '中国电信'
    if p3 in cgtv: return '中国广电'
    return '未知运营商'


def format_result(result: dict) -> str:
    """格式化查询结果为 Telegram 消息"""
    if not result['success']:
        return (f"❌ *查询失败*\n\n"
                f"原因：{result.get('error', '未知错误')}\n"
                f"📱 输入号码：`{result.get('phone', '')}`\n\n"
                f"_提示：11位手机号可精确到城市_")

    phone = result['phone']
    prefix = result.get('prefix', '')
    operator = result['operator']
    province = result.get('province', '全国')
    city = result.get('city')
    precision = result.get('precision', '未知')
    num_type = result.get('type', '')

    # 运营商图标
    op_icon = {'中国移动': '📶', '中国联通': '📡', '中国电信': '📺',
               '中国广电': '📻'}.get(operator, '🏢')

    # 精确度图标
    precision_icon = {'城市级别': '🎯', '运营商级别': '📍'}.get(precision, '📍')

    lines = [
        f"🔍 *手机号归属地查询*",
        f"",
        f"📱 *手机号：* `{phone}`",
        f"🔢 *号段：* `{prefix}`",
        f"",
        f"{op_icon} *运营商：* {operator}",
    ]

    if city:
        lines.append(f"🏙️ *城市：* {province} · {city}")
    else:
        lines.append(f"📍 *省份：* {province}")

    lines.extend([
        f"",
        f"{precision_icon} *查询精度：* {precision}",
    ])

    if num_type:
        lines.append(f"📡 *号段类型：* {num_type}")

    lines.extend([
        f"",
        f"━━━━━━━━━━━━━━━",
        f"_数据基于工信部公开号段_",
        f"_全国 31 省 331 城市覆盖_",
    ])

    return '\n'.join(lines)


def get_db_stats() -> dict:
    """获取数据库统计信息"""
    db = _load_db()
    provinces = set(v['province'] for v in db.values() if 'province' in v)
    cities = set(v['city'] for v in db.values() if 'city' in v)
    operators = {}
    for v in db.values():
        op = v.get('operator', '未知')
        operators[op] = operators.get(op, 0) + 1

    return {
        'total_7digit': len(db),
        'covered_provinces': len(provinces),
        'covered_cities': len(cities),
        'operators': operators,
    }


# 命令行测试
if __name__ == '__main__':
    import sys
    test_phones = sys.argv[1:] or [
        '13800138000',   # 测试11位
        '18801012345',   # 北京
        '18908001234',   # 成都
        '13805711234',   # 杭州
        '138',           # 测试3位
        '13800',         # 测试4位
    ]
    print("=== 手机号归属地查询测试 ===\n")
    for p in test_phones:
        r = lookup(p)
        print(f"📱 {p} → {r}")
        print()
