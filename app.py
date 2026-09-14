import os
import requests
import re
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# 🔑 ВСТАВЬТЕ СЮДА ВАШ СЕРВИСНЫЙ КЛЮЧ ИЗ НАСТРОЕК ПРИЛОЖЕНИЯ VK
VK_SERVICE_TOKEN = "87db805c87db805c87db805c4584983e01887db87db805ced739b3542812221181b8430"

# СПИСОК ВАШИХ ВИДЕО ВК (Вставляйте обычные полные ссылки из адресной строки!)
MY_VIDEOS = [
    {"id": "1", "url": "https://vkvideo.ru/video-235867873_456239131", "title": "Быстро на пальцах про крипту"},
    {"id": "2", "url": "-235867873_456239131", "title": "Второе видео ВК"},
    {"id": "3", "url": "235867873_456239131", "title": "Третье видео ВК"}
]

cached_data = {v["id"]: {"views": 0, "growth_1hour": 0, "trending": False} for v in MY_VIDEOS}
history = {v["id"]: [] for v in MY_VIDEOS}
current_check_index = 0

def get_vk_views_ultimate(url):
    if "video-" not in url and "video" not in url:
        return 0
    
    match = re.search(r'video(-?\d+_\d+)', url)
    if not match:
        return 0
    video_id = match.group(1) # Получаем формат ownerId_videoId
    
    # Разделяем на ID владельца и ID видео для альтернативных методов
    parts = video_id.split('_')
    owner_id = parts[0]
    vid_id = parts[1]
    
    # --- МЕТОД 1: Стандартный запрос видео через API ---
    try:
        api_url = f"https://vk.com{video_id}&access_token={VK_SERVICE_TOKEN}&v=5.131"
        r = requests.get(api_url, timeout=3).json()
        if 'response' in r and r['response']['items']:
            views = int(r['response']['items'][0].get('views', 0))
            if views > 0: return views
    except:
        pass

    # --- МЕТОД 2: Если видео в группе, запрашиваем через стену сообщества ---
    try:
        # Убираем минус из ID владельца, если он есть, для запроса к стене
        g_id = owner_id.replace('-', '')
        api_url_wall = f"https://vk.com{g_id}_{vid_id}&access_token={VK_SERVICE_TOKEN}&v=5.131"
        r_wall = requests.get(api_url_wall, timeout=3).json()
        if 'response' in r_wall and r_wall['response']:
            # Ищем блок просмотров самого поста, где прикреплено видео
            views = int(r_wall['response'][0].get('views', {}).get('count', 0))
            if views > 0: return views
    except:
        pass

    # --- МЕТОД 3: Запасной официальный сбор статистики видео ---
    try:
        api_url_stats = f"https://vk.com{owner_id}&video_id={vid_id}&access_token={VK_SERVICE_TOKEN}&v=5.131"
        r_stats = requests.get(api_url_stats, timeout=3).json()
        if 'response' in r_stats and r_stats['response']:
            views = int(r_stats['response'][0].get('view_video', 0))
            if views > 0: return views
    except:
        pass
        
    return 0

@app.route('/api/stats')
def get_stats():
    global current_check_index
    if not MY_VIDEOS: return jsonify([])
    
    video = MY_VIDEOS[current_check_index]
    v_id = video["id"]
    
    real_views = get_vk_views_ultimate(video["url"])
    
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
        # Превращаем число просмотров в красивый формат (например, 15300 -> 15.3k)
        raw_views = cached_data[vid]["views"]
        if isinstance(raw_views, int) and raw_views > 1000:
            formatted_views = f"{raw_views/1000:.1f}k"
        else:
            formatted_views = raw_views if raw_views > 0 else "загрузка..."

        results.append({
            "id": vid,
            "title": v["title"],
            "views": formatted_views,
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
    <h1>🔷 VK VIDEO REALTIME TERMINAL // MULTI-API SYSTEM</h1>
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
                    
                    row.innerHTML = `
                        <div style="color: #343e4f;">#` + video.id + `</div>
                        <div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 10px;">` + video.title + `</div>
                        <div class="views-num">` + video.views + `</div>
                        <div>` + hourText + `</div>
                        <div><span class="alert-tag">▲ BOOM</span></div>
                    `;
                });
            } catch(e) { console.log(e); }
        }
        setInterval(updateTerminal, 2000);
        updateTerminal();
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
