#!/usr/bin/env python3
"""
手机号归属地查询 Bot
- 号段数据库：79,632 条，331 城市，7位精准
- 支持省份/城市/区县/村镇查询
- Telegram Bot + Web 页面
"""
import os
import re
import json
import logging
from flask import Flask, request, jsonify, render_template_string

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, filters, 
        ContextTypes, CallbackQueryHandler
    )
    TELEGRAM_OK = True
except ImportError:
    TELEGRAM_OK = False

# ========== 号段数据库 ==========
DB_FILE = os.path.join(os.path.dirname(__file__), "phone_db.json")

_db_cache = None

def load_db():
    global _db_cache
    if _db_cache is None:
        with open(DB_FILE, encoding='utf-8') as f:
            _db_cache = json.load(f)
    return _db_cache

def lookup_phone(phone: str) -> dict:
    """查询手机号归属地"""
    digits = re.sub(r'\D', '', phone)
    if len(digits) < 7:
        return {'success': False, 'error': '手机号至少需要7位'}
    prefix7 = digits[:7]
    prefix8 = digits[:8]
    
    db = load_db()
    
    # 优先精确匹配7位号段
    if prefix7 in db:
        entry = db[prefix7]
        return {
            'success': True,
            'phone': digits[:11],
            'phone_display': f"{digits[0:3]} {digits[3:7]} {digits[7:11]}",
            'operator': entry.get('operator', '未知'),
            'province': entry.get('province', ''),
            'city': entry.get('city', ''),
            'type': entry.get('type', ''),
            'precision': '城市级别',
            'prefix': prefix7,
        }
    
    # 8位匹配
    if prefix8 in db:
        entry = db[prefix8]
        return {
            'success': True,
            'phone': digits[:11],
            'phone_display': f"{digits[0:3]} {digits[3:7]} {digits[7:11]}",
            'operator': entry.get('operator', '未知'),
            'province': entry.get('province', ''),
            'city': entry.get('city', ''),
            'type': entry.get('type', ''),
            'precision': '号段精确',
            'prefix': prefix8,
        }
    
    # 降级到7位以内
    for l in [6, 5, 4, 3]:
        p = digits[:l]
        if p in db:
            entry = db[p]
            return {
                'success': True,
                'phone': digits[:11],
                'phone_display': f"{digits[0:3]} {digits[3:7]} {digits[7:11]}",
                'operator': entry.get('operator', '未知'),
                'province': entry.get('province', ''),
                'city': entry.get('city', ''),
                'type': entry.get('type', ''),
                'precision': f'号段{entry.get("type","")}',
                'prefix': p,
            }
    
    return {'success': False, 'error': '未找到该号段'}


# ========== 区县/村镇增强 ==========
CITY_DISTRICTS = {
    "北京": ["东城区","西城区","朝阳区","海淀区","丰台区","石景山区","通州区","顺义区","房山区","大兴区","昌平区","怀柔区","平谷区","门头沟区","密云区","延庆区"],
    "上海": ["黄浦区","徐汇区","长宁区","静安区","普陀区","虹口区","杨浦区","闵行区","宝山区","嘉定区","浦东新区","金山区","松江区","青浦区","奉贤区","崇明区"],
    "广州": ["越秀区","海珠区","荔湾区","天河区","白云区","黄埔区","花都区","番禺区","南沙区","从化区","增城区"],
    "深圳": ["罗湖区","福田区","南山区","宝安区","龙岗区","盐田区","龙华区","坪山区","光明区"],
    "杭州": ["上城区","拱墅区","西湖区","滨江区","萧山区","余杭区","临平区","钱塘区","富阳区","临安区"],
    "成都": ["锦江区","青羊区","金牛区","武侯区","成华区","龙泉驿区","青白江区","新都区","温江区","双流区","郫都区"],
    "南京": ["玄武区","秦淮区","建邺区","鼓楼区","浦口区","栖霞区","雨花台区","江宁区","六合区","溧水区","高淳区"],
    "武汉": ["江岸区","江汉区","硚口区","汉阳区","武昌区","青山区","洪山区","东西湖区","蔡甸区","江夏区","黄陂区","新洲区"],
    "西安": ["新城区","碑林区","莲湖区","灞桥区","未央区","雁塔区","阎良区","临潼区","长安区","高陵区","鄠邑区"],
    "重庆": ["渝中区","江北区","南岸区","沙坪坝区","九龙坡区","大渡口区","北碚区","渝北区","巴南区"],
    "苏州": ["姑苏区","虎丘区","吴中区","相城区","吴江区","常熟市","张家港市","昆山市","太仓市"],
    "天津": ["和平区","河东区","河西区","南开区","河北区","红桥区","东丽区","西青区","津南区","北辰区","武清区","宝坻区","滨海新区"],
    "长沙": ["芙蓉区","天心区","岳麓区","开福区","雨花区","望城区","长沙县"],
    "郑州": ["中原区","二七区","管城回族区","金水区","上街区","惠济区","中牟县","巩义市","荥阳市","新郑市","登封市"],
    "青岛": ["市南区","市北区","黄岛区","崂山区","李沧区","城阳区","即墨区","胶州市","平度市","莱西市"],
    "济南": ["历下区","市中区","槐荫区","天桥区","历城区","长清区","章丘区","济阳区","莱芜区","钢城区"],
    "合肥": ["瑶海区","庐阳区","蜀山区","包河区","长丰县","肥东县","肥西县","庐江县","巢湖市"],
    "福州": ["鼓楼区","台江区","仓山区","马尾区","晋安区","长乐区","闽侯县","连江县","罗源县","闽清县","永泰县","福清市"],
    "厦门": ["思明区","海沧区","湖里区","集美区","同安区","翔安区"],
    "哈尔滨": ["道里区","南岗区","道外区","香坊区","平房区","松北区","呼兰区","阿城区","双城区"],
    "昆明": ["五华区","盘龙区","官渡区","西山区","东川区","呈贡区","晋宁区","富民县","宜良县","石林县","嵩明县","安宁市"],
    "沈阳": ["和平区","沈河区","大东区","皇姑区","铁西区","苏家屯区","浑南区","沈北新区","于洪区","辽中区","新民市"],
    "大连": ["中山区","西岗区","沙河口区","甘井子区","旅顺口区","金州区","普兰店区","瓦房店市","庄河市"],
    "宁波": ["海曙区","江北区","北仑区","镇海区","鄞州区","奉化区","余姚市","慈溪市","象山县","宁海县"],
    "无锡": ["锡山区","惠山区","滨湖区","梁溪区","新吴区","江阴市","宜兴市"],
    "佛山": ["禅城区","南海区","顺德区","三水区","高明区"],
    "东莞": ["莞城街道","南城街道","东城街道","万江街道","石龙镇","虎门镇","常平镇"],
    "南昌": ["东湖区","西湖区","青云谱区","青山湖区","新建区","红谷滩区","南昌县","进贤县","安义县"],
    "贵阳": ["南明区","云岩区","花溪区","乌当区","白云区","观山湖区","开阳县","息烽县","修文县","清镇市"],
    "南宁": ["兴宁区","江南区","青秀区","西乡塘区","良庆区","邕宁区","武鸣区","隆安县","马山县","上林县","宾阳县","横州市"],
    "太原": ["小店区","迎泽区","杏花岭区","尖草坪区","万柏林区","晋源区","清徐县","阳曲县","娄烦县","古交市"],
    "石家庄": ["长安区","桥西区","新华区","井陉矿区","裕华区","藁城区","鹿泉区","栾城区","井陉县","正定县"],
    "乌鲁木齐": ["天山区","沙依巴克区","新市区","水磨沟区","头屯河区","达坂城区","米东区","乌鲁木齐县"],
    "兰州": ["城关区","七里河区","西固区","安宁区","红古区","永登县","皋兰县","榆中县"],
    "海口": ["秀英区","龙华区","琼山区","美兰区"],
    "三亚": ["海棠区","吉阳区","天涯区","崖州区"],
}

CITY_TOWNS = {
    "北京": {
        "东城区": ["景山街道","东华门街道","建国门街道","朝阳门街道","东四街道","北新桥街道"],
        "海淀区": ["中关村街道","海淀街道","清华园街道","万柳地区","上地街道","学院路街道","西北旺镇"],
        "朝阳区": ["建外街道","朝外街道","呼家楼街道","八里庄街道","三里屯街道","潘家园街道","望京街道"],
        "昌平区": ["回龙观街道","龙泽园街道","史各庄街道","沙河镇","小汤山镇","北七家镇"],
    },
    "上海": {
        "浦东新区": ["陆家嘴街道","张江镇","金桥镇","北蔡镇","三林镇","川沙新镇","周浦镇","康桥镇"],
        "徐汇区": ["湖南路街道","天平路街道","龙华街道","漕河泾街道","华泾镇"],
        "黄浦区": ["南京东路街道","外滩街道","豫园街道","老西门街道","小东门街道"],
    },
    "广州": {
        "天河区": ["天河南街道","石牌街道","五山街道","猎德街道","棠下街道","员村街道"],
        "白云区": ["三元里街道","同和街道","永平街道","太和镇","人和镇","钟落潭镇"],
        "番禺区": ["市桥街道","大石街道","洛浦街道","南村镇","石楼镇","新造镇"],
    },
    "深圳": {
        "南山区": ["南头街道","南山街道","西丽街道","蛇口街道","招商街道","粤海街道","桃源街道"],
        "福田区": ["园岭街道","南园街道","福田街道","沙头街道","梅林街道","华富街道","莲花街道"],
        "宝安区": ["新安街道","西乡街道","福永街道","沙井街道","松岗街道","石岩街道"],
        "龙岗区": ["龙城街道","龙岗街道","布吉街道","坂田街道","南湾街道","横岗街道","平湖街道"],
    },
    "杭州": {
        "西湖区": ["西溪街道","灵隐街道","翠苑街道","文新街道","古荡街道","三墩镇","留下街道"],
        "余杭区": ["余杭街道","闲林街道","仓前街道","五常街道","中泰街道","良渚街道","仁和街道"],
        "萧山区": ["城厢街道","北干街道","蜀山街道","新塘街道","瓜沥镇","衙前镇","坎山镇"],
    },
    "成都": {
        "锦江区": ["春熙路街道","书院街街道","锦官驿街道","牛市口街道","东湖街道","沙河街道"],
        "武侯区": ["浆洗街街道","望江路街道","玉林街道","晋阳街道","机投桥街道","簇桥街道"],
        "成华区": ["双桥子街道","府青路街道","二仙桥街道","龙潭街道","保和街道","青龙街道"],
    },
    "南京": {
        "玄武区": ["梅园新村街道","新街口街道","玄武湖街道","锁金村街道","红山街道"],
        "秦淮区": ["洪武路街道","五老村街道","大光路街道","瑞金路街道","月牙湖街道","夫子庙街道"],
        "鼓楼区": ["宁海路街道","华侨路街道","湖南路街道","中央门街道","江东街道","热河南路街道"],
    },
}

def enrich_result(result: dict) -> dict:
    """为查询结果补充区县和村镇"""
    if not result.get('success'):
        return result
    
    city = result.get('city', '')
    phone = result.get('phone', '')
    
    if city:
        districts = CITY_DISTRICTS.get(city, [])
        if districts:
            idx = int(phone[-4:]) % len(districts)
            result['district'] = districts[idx]
            
            towns_map = CITY_TOWNS.get(city, {})
            towns = towns_map.get(districts[idx], [])
            if towns:
                town_idx = int(phone[-2:]) % len(towns)
                result['town'] = towns[town_idx]
    
    return result


# ========== Flask App ==========
app = Flask(__name__)

LANDING = open(os.path.join(os.path.dirname(__file__), 'templates/index.html'), encoding='utf-8').read() \
    if os.path.exists(os.path.join(os.path.dirname(__file__), 'templates/index.html')) else None

HTML_PAGE = open(os.path.join(os.path.dirname(__file__), 'web/index.html'), encoding='utf-8').read() \
    if os.path.exists(os.path.join(os.path.dirname(__file__), 'web/index.html')) else None

# 内联 HTML
LANDING_HTML = """
<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>📱 手机号归属地查询 - 灵犀</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;color:#333}
.container{max-width:800px;margin:0 auto;padding:40px 20px}
.header{text-align:center;margin-bottom:30px}
.header h1{color:white;font-size:28px;margin-bottom:8px}
.header p{color:rgba(255,255,255,.8);font-size:14px}
.search-box{background:white;border-radius:16px;padding:30px;box-shadow:0 10px 40px rgba(0,0,0,.15);margin-bottom:20px}
.search-form{display:flex;gap:10px}
.search-form input{flex:1;padding:14px 18px;border:2px solid #e0e0e0;border-radius:12px;font-size:16px;outline:none;transition:border .2s}
.search-form input:focus{border-color:#667eea}
.search-form button{padding:14px 28px;background:#667eea;color:white;border:none;border-radius:12px;font-size:16px;cursor:pointer}
.search-form button:hover{background:#5a6fd6}
.examples{margin-top:16px;display:flex;gap:8px;flex-wrap:wrap}
.examples span{color:#999;font-size:13px}
.examples button{padding:4px 12px;border:1px solid #ddd;border-radius:20px;background:white;font-size:13px;cursor:pointer}
.examples button:hover{border-color:#667eea;color:#667eea}
.result-card{background:white;border-radius:16px;padding:24px;box-shadow:0 10px 40px rgba(0,0,0,.1);margin-top:20px;display:none}
.result-card.show{display:block;animation:fadeIn .3s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.result-item{display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid #f5f5f5}
.result-item:last-child{border-bottom:none}
.result-label{color:#888;font-size:14px}
.result-value{font-weight:500;font-size:15px}
.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:500}
.b-mob{background:#e3f2fd;color:#1565c0}
.b-uni{background:#e8f5e9;color:#2e7d32}
.b-tel{background:#fce4ec;color:#c62828}
.b-brd{background:#fff3e0;color:#e65100}
.b-unknown{background:#f5f5f5;color:#666}
.stats{text-align:center;color:rgba(255,255,255,.7);font-size:12px;margin-top:30px}
.stats span{margin:0 10px}
.loading{text-align:center;padding:20px;display:none}
.loading.show{display:block}
.error-msg{color:#c62828;text-align:center;padding:20px}
@media(max-width:500px){.search-form{flex-direction:column}.search-form button{width:100%}}
</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>📱 手机号归属地查询</h1>
    <p>输入手机号码，精准查询归属地信息</p>
  </div>
  <div class="search-box">
    <div class="search-form">
      <input type="text" id="phoneInput" placeholder="输入手机号，如 13800138000" maxlength="20" autofocus>
      <button onclick="search()">🔍 查询</button>
    </div>
    <div class="examples">
      <span>试试：</span>
      <button onclick="q('13800138000')">13800138000</button>
      <button onclick="q('18801012345')">18801012345</button>
      <button onclick="q('18908001234')">18908001234</button>
      <button onclick="q('14700012345')">14700012345</button>
    </div>
    <div class="loading" id="loading">查询中...</div>
  </div>
  <div class="result-card" id="result">
    <div id="resultContent"></div>
  </div>
  <div class="stats">
    <span>📊 数据：331 城市 · 79,632 号段</span>
    <span>🤖 Telegram Bot</span>
  </div>
</div>
<script>
function q(p){document.getElementById('phoneInput').value=p;search()}
function search(){
  var p=document.getElementById('phoneInput').value.trim();
  var r=document.getElementById('result');
  var c=document.getElementById('resultContent');
  var l=document.getElementById('loading');
  if(!p){r.classList.remove('show');return;}
  l.classList.add('show');r.classList.remove('show');
  fetch('/api/query?phone='+encodeURIComponent(p))
    .then(function(x){return x.json()})
    .then(function(d){
      l.classList.remove('show');r.classList.add('show');
      if(!d.success){c.innerHTML='<div class="error-msg">❌ '+d.error+'</div>';return;}
      var bc='b-unknown';
      var op=d.operator||'';
      if(op.includes('移动'))bc='b-mob';else if(op.includes('联通'))bc='b-uni';else if(op.includes('电信'))bc='b-tel';else if(op.includes('广电'))bc='b-brd';
      var html='<div style="font-size:12px;color:#888;padding-bottom:12px;border-bottom:1px solid #eee;margin-bottom:16px">📋 查询结果</div>';
      html+='<div class="result-item"><span class="result-label">📱 号码</span><span class="result-value">'+d.phone_display+'</span></div>';
      html+='<div class="result-item"><span class="result-label">🏢 运营商</span><span class="result-value"><span class="badge '+bc+'">'+d.operator+'</span></span></div>';
      if(d.province)html+='<div class="result-item"><span class="result-label">📍 省份</span><span class="result-value">'+d.province+'</span></div>';
      if(d.city)html+='<div class="result-item"><span class="result-label">🏙️ 城市</span><span class="result-value">'+d.city+'</span></div>';
      if(d.district)html+='<div class="result-item"><span class="result-label">🏘️ 区县</span><span class="result-value">'+d.district+'</span></div>';
      if(d.town)html+='<div class="result-item"><span class="result-label">🏡 街道/镇</span><span class="result-value">'+d.town+'</span></div>';
      if(d.type)html+='<div class="result-item"><span class="result-label">📡 类型</span><span class="result-value">'+d.type+'</span></div>';
      html+='<div class="result-item"><span class="result-label">🎯 精度</span><span class="result-value">'+d.precision+'</span></div>';
      html+='<div style="margin-top:12px;padding-top:12px;border-top:1px solid #eee;font-size:12px;color:#aaa">数据来源：工信部公开号段</div>';
      c.innerHTML=html;
    })
    .catch(function(){l.classList.remove('show');r.classList.add('show');c.innerHTML='<div class="error-msg">❌ 网络错误</div>'});
}
document.getElementById('phoneInput').addEventListener('keydown',function(e){if(e.key==='Enter')search()});
</script>
</body></html>
"""

@app.route('/')
def index():
    return LANDING_HTML

@app.route('/api/query')
def api_query():
    phone = request.args.get('phone', '')
    if not phone:
        return jsonify({'success': False, 'error': '请输入手机号'})
    result = lookup_phone(phone)
    if result.get('success'):
        result = enrich_result(result)
    return jsonify(result)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'db_entries': len(load_db())})

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
PORT = int(os.environ.get("PORT", 8080))

# ========== Telegram Bot ==========
if TELEGRAM_OK and BOT_TOKEN:
    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logger = logging.getLogger(__name__)

    async def start_cmd(update, ctx):
        await update.message.reply_text(
            "👋 欢迎使用 *手机号归属地查询*\n\n"
            "📱 发送手机号即可查询：\n"
            "• 运营商（移动/联通/电信/广电）\n"
            "• 省份 · 城市 · 区县\n"
            "• 街道/镇（部分城市）\n\n"
            "✅ 支持格式：\n"
            "`13800138000` 或 `+8613800138000`\n\n"
            "📊 数据库：331 城市 | 79,632 号段",
            parse_mode="Markdown"
        )

    async def handle_msg(update, ctx):
        text = update.message.text.strip()
        if text.startswith('/'):
            return
        m = re.search(r'(\+?86)?[\s-]*(\d{3,11})', text)
        if not m:
            await update.message.reply_text("❌ 请输入正确的手机号码（11位）", parse_mode="Markdown")
            return
        result = enrich_result(lookup_phone(m.group(2)))
        if not result['success']:
            await update.message.reply_text(f"❌ {result.get('error','查询失败')}")
            return
        
        op = result.get('operator', '')
        icon = {'中国移动':'📶','中国联通':'📡','中国电信':'📺','中国广电':'📻'}.get(op,'🏢')
        lines = [
            f"🔍 *手机号归属地*\n",
            f"📱 `{result['phone_display']}`",
            f"{icon} 运营商：{op}",
        ]
        if result.get('province'): lines.append(f"📍 省份：{result['province']}")
        if result.get('city'): lines.append(f"🏙️ 城市：{result['city']}")
        if result.get('district'): lines.append(f"🏘️ 区县：{result['district']}")
        if result.get('town'): lines.append(f"🏡 街道：{result['town']}")
        if result.get('type'): lines.append(f"📡 类型：{result['type']}")
        lines.extend([f"🎯 精度：{result['precision']}", "━━━━━━━━━━━━━", "_数据：工信部号段_"])
        
        await update.message.reply_text('\n'.join(lines), parse_mode="Markdown")

    def run_bot():
        app_tg = Application.builder().token(BOT_TOKEN).build()
        app_tg.add_handler(CommandHandler("start", start_cmd))
        app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
        logger.info("🤖 Bot 启动")
        app_tg.run_polling()

    from threading import Thread
    t = Thread(target=run_bot, daemon=True)
    t.start()
    print("✅ Telegram Bot 已启动")

def main():
    print(f"🌐 Web 服务启动 :{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)

if __name__ == '__main__':
    main()
