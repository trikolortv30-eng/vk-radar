import os
import requests
import re
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# СПИСОК ВАШИХ ВИДЕО ВК (Вставляйте обычные полные ссылки из браузера!)
MY_VIDEOS = [
    {"id": "1", "url": "https://vkvideo.ru/video-235867873_456239131", "title": "Быстро на пальцах про крипту"},
    {"id": "2", "url": "https://vk.com", "title": "Второе видео ВК"},
    {"id": "3", "url": "https://vk.com", "title": "Третье видео ВК"}
]

cached_data = {v["id"]: {"views": 0, "growth_1hour": 0, "trending": False} for v in MY_VIDEOS}
history = {v["id"]: [] for v in MY_VIDEOS}
current_check_index = 0

def get_vk_views_smart(url):
    if "vk.com" not in url and "vkvideo.ru" not in url:
        return 0
    try:
        # Притворяемся мобильным телефоном, чтобы ВК отдал страницу без авторизации
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
            'Accept-Language': 'ru-RU,ru;q=0.9'
        }
        r = requests.get(url, headers=headers, timeout=4)
        html = r.text
        
        # Способ 1: Ищем в скрытых мета-тегах для поисковиков Яндекса/Гугла
        soup = BeautifulSoup(html, 'html.parser')
        meta = soup.find('meta', {'property': 'ya:ovs:views_total'})
        if meta and meta.get('content'):
            return int(meta['content'])
            
        meta2 = soup.find('meta', {'property': 'video:views'})
        if meta2 and meta2.get('content'):
            return int(meta2['content'])

        # Способ 2: Ищем цифру просмотров в коде страницы через регулярное выражение
        match = re.search(r'"viewsCount"\s*:\s*(\d+)', html)
        if match:
            return int(match.group(1))
            
        match2 = re.search(r'(\d+)\s+просмотр', html)
        if match2:
            return int(match2.group(1))

        return 0
    except:
        return 0

@app.route('/api/stats')
def get_stats():
    global current_check_index
    if not MY_VIDEOS: return jsonify([])
    
    # Проверяем по 1 видео за 3 секунды, чтобы ВК не забанил за скорость
    video = MY_VIDEOS[current_check_index]
    v_id = video["id"]
    
    real_views = get_vk_views_smart(video["url"])
    
    if real_views > 0:
        if v_id not in history: history[v_id] = []
        history[v_id].append(real_views)
        if len(history[v_id]) > 360: history[v_id].pop(0)
            
        growth_10s = history[v_id][-1] - history[v_id][-2] if len(history[v_id]) > 1 else 0
        if growth_10s < 0: growth_10s = 0
            
        growth_1hour = history[v_id][-1] - history[v_id]
        if growth_1hour < 0: growth_1hour = 0
        
        cached_data[v_id] = {
            "views": real_views,
            "growth_1hour": growth_1hour,
            "trending": growth_10s > 0
        }
    
    current_check_index = (current_check_index + 1) % len(MY_VIDEOS)
        
    results = []
    for v in MY_VIDEOS:
        vid = v["id"]
        results.append({
            "id": vid,
            "title": v["title"],
            "views": cached_data[vid]["views"] if cached_data[vid]["views"] > 0 else 0,
            "growth_1hour": cached_data[vid]["growth_1hour"],
            "trending": cached_data[vid]["trending"]
        })
    return jsonify(results)

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>VK Стрим Терминал</title>
    <meta charset="utf-8">
    <style>
        body { font-family: 'Courier New', monospace; background: #0a0b10; color: #8a99ad; padding: 10px; margin: 0; font-size: 12px; }
        h1 { font-size: 14px; color: #0077ff; margin: 0 0 10px 0; text-transform: uppercase; letter-spacing: 1px; }
        .table-header { display: grid; grid-template-columns: 40px 1fr 100px 100px 80px; font-weight: bold; color: #4c586b; border-bottom: 1px solid #1a222d; padding-bottom: 4px; margin-bottom: 4px; }
        .row { display: grid; grid-template-columns: 40px 1fr 100px 100px 80px; padding: 3px 0; border-bottom: 1px solid #111622; transition: all 0.2s; }
        .row.trending { background: #001f4d; color: #0077ff; font-weight: bold; }
        .views-num { color: #0077ff; }
        .growth-num { color: #00ff00; font-weight: bold; }
        .no-growth { color: #343e4f; }
        .alert-tag { color: #ff0055; font-weight: bold; display: none; }
        .row.trending .alert-tag { display: inline; animation: flash 0.8s infinite; }
        @keyframes flash { 0% { opacity: 0; } 50% { opacity: 1; } 100% { opacity: 0; } }
    </style>
</head>
<body>
    <h1>🔷 VK VIDEO REALTIME TERMINAL // MOBILE BYPASS</h1>
    <div class="table-header">
        <div>ID</div><div>НАЗВАНИЕ РОЛИКА</div><div>ВСЕГО</div><div>ЗА ЧАС</div><div>СТАТУС</div>
    </div>
    <div id="terminal"></div>
    <script>
        async function updateTerminal() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                const container = document.getElementById('terminal');
                data.forEach(video => {
                    let row = document.getElementById('row-' + video.id);
                    if (!row) {
                        row = document.createElement('div');
                        row.id = 'row-' + video.id;
                        row.className = 'row';
                        container.appendChild(row);
                    }
                    if (video.trending) row.classList.add('trending');
                    else row.classList.remove('trending');
                    
                    let hourText = video.growth_1hour > 0 ? '<span class="growth-num">+' + video.growth_1hour + '</span>' : '<span class="no-growth">0</span>';
                    let viewsText = video.views > 0 ? video.views : '<span class="no-growth">...</span>';
                    
                    row.innerHTML = `
                        <div style="color: #343e4f;">#` + video.id + `</div>
                        <div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 10px;">` + video.title + `</div>
                        <div class="views-num">` + viewsText + `</div>
                        <div>` + hourText + `</div>
                        <div><span class="alert-tag">▲ BOOM</span></div>
                    `;
                });
            } catch(e) { console.log(e); }
        }
        setInterval(updateTerminal, 3000);
        updateTerminal();
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
