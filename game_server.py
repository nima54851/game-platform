"""
GameVault 本地后端服务器
运行方式: python3 game_server.py
访问: http://localhost:18432
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, os, json, sqlite3, hashlib, time, uuid, asyncio
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import threading

# ──────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────
PORT = 18432
DB_PATH = "./gamevault.db"
STATIC_DIR = "./games"  # 游戏文件放这里

# ──────────────────────────────────────────────
#  DATABASE
# ──────────────────────────────────────────────
def init_db():
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            uid TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            coins INTEGER DEFAULT 0,
            is_vip INTEGER DEFAULT 0,
            created_at INTEGER
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT, item TEXT, amount INTEGER,
            type TEXT, ts INTEGER
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT, uid TEXT, username TEXT,
            score INTEGER, ts INTEGER
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS game_sessions (
            id TEXT PRIMARY KEY,
            game_id TEXT, host_uid TEXT,
            status TEXT, players TEXT,
            created_at INTEGER, data TEXT
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id TEXT PRIMARY KEY,
            name TEXT, description TEXT,
            file_path TEXT, thumbnail TEXT,
            is_vip INTEGER DEFAULT 0, category TEXT,
            plays INTEGER DEFAULT 0, created_at INTEGER
        )
    """)
    db.commit()
    db.close()

def db_get():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

init_db()

# ──────────────────────────────────────────────
#  WEBSOCKET MANAGER
# ──────────────────────────────────────────────
class WSManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
        self.user_sockets: Dict[str, WebSocket] = {}

    async def connect(self, ws: WebSocket, room_id: str, uid: str):
        await ws.accept()
        if room_id not in self.connections:
            self.connections[room_id] = []
        self.connections[room_id].append(ws)
        self.user_sockets[uid] = ws

    def disconnect(self, ws: WebSocket, room_id: str, uid: str):
        if room_id in self.connections:
            self.connections[room_id] = [w for w in self.connections[room_id] if w != ws]
            if not self.connections[room_id]:
                del self.connections[room_id]
        if uid in self.user_sockets:
            del self.user_sockets[uid]

    async def broadcast(self, room_id: str, msg: dict, exclude: Optional[WebSocket] = None):
        if room_id not in self.connections:
            return
        dead = []
        for ws in self.connections[room_id]:
            try:
                if ws != exclude:
                    await ws.send_json(msg)
            except:
                dead.append(ws)
        for ws in dead:
            self.connections[room_id].discard(ws)

    async def send_to(self, uid: str, msg: dict):
        if uid in self.user_sockets:
            try:
                await self.user_sockets[uid].send_json(msg)
            except: pass

ws_manager = WSManager()

# ──────────────────────────────────────────────
#  FASTAPI APP
# ──────────────────────────────────────────────
app = FastAPI(title="GameVault API", version="1.0")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

# ──────────────────────────────────────────────
#  AUTH
# ──────────────────────────────────────────────
def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

@app.get("/api/me")
def get_me(uid: str):
    db = db_get()
    row = db.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()
    db.close()
    if not row:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {
        "uid": row[0], "username": row[1], "coins": row[3],
        "is_vip": bool(row[4]), "created_at": row[5]
    }

@app.post("/api/register")
def register(username: str, password: str):
    db = db_get()
    existing = db.execute("SELECT uid FROM users WHERE username=?", (username,)).fetchone()
    if existing:
        db.close(); raise HTTPException(400, "用户名已存在")
    uid = uuid.uuid4().hex[:12]
    db.execute("INSERT INTO users VALUES (?,?,?,0,0,?)",
               (uid, username, hash_pw(password), int(time.time())))
    db.commit()
    db.close()
    return {"uid": uid, "username": username, "coins": 0, "is_vip": False}

@app.post("/api/login")
def login(username: str, password: str):
    db = db_get()
    row = db.execute("SELECT uid,username,coins,is_vip FROM users WHERE username=? AND password_hash=?",
                     (username, hash_pw(password))).fetchone()
    db.close()
    if not row:
        raise HTTPException(401, "用户名或密码错误")
    return {"uid": row[0], "username": row[1], "coins": row[2], "is_vip": bool(row[3])}

# ──────────────────────────────────────────────
#  COINS & VIP
# ──────────────────────────────────────────────
@app.post("/api/coins/add")
def add_coins(uid: str, amount: int, item: str = ""):
    db = db_get()
    db.execute("UPDATE users SET coins = coins + ? WHERE uid=?", (amount, uid))
    db.execute("INSERT INTO transactions VALUES (NULL,?,?,?,'recharge',?)",
               (uid, item, amount, int(time.time())))
    db.commit()
    new = db.execute("SELECT coins FROM users WHERE uid=?", (uid,)).fetchone()[0]
    db.close()
    return {"coins": new}

@app.post("/api/coins/spend")
def spend_coins(uid: str, amount: int, item: str = ""):
    db = db_get()
    cur = db.execute("SELECT coins FROM users WHERE uid=?", (uid,)).fetchone()
    if not cur or cur[0] < amount:
        db.close(); raise HTTPException(400, "金币不足")
    db.execute("UPDATE users SET coins = coins - ? WHERE uid=?", (amount, uid))
    db.execute("INSERT INTO transactions VALUES (NULL,?,?,?,'spend',?)",
               (uid, item, amount, int(time.time())))
    db.commit()
    new = db.execute("SELECT coins FROM users WHERE uid=?", (uid,)).fetchone()[0]
    db.close()
    return {"coins": new}

@app.post("/api/vip/activate")
def activate_vip(uid: str):
    db = db_get()
    db.execute("UPDATE users SET is_vip=1 WHERE uid=?", (uid,))
    db.execute("INSERT INTO transactions VALUES (NULL,?,'VIP永久会员',0,'vip',?)",
               (uid, int(time.time())))
    db.commit()
    db.close()
    return {"is_vip": True}

@app.get("/api/transactions")
def get_transactions(uid: str, limit: int = 20):
    db = db_get()
    rows = db.execute(
        "SELECT item,amount,type,ts FROM transactions WHERE uid=? ORDER BY ts DESC LIMIT ?",
        (uid, limit)
    ).fetchall()
    db.close()
    return [{"item": r[0], "amount": r[1], "type": r[2], "ts": r[3]} for r in rows]

# ──────────────────────────────────────────────
#  LEADERBOARD
# ──────────────────────────────────────────────
@app.get("/api/leaderboard/{game_id}")
def get_leaderboard(game_id: str, limit: int = 10):
    db = db_get()
    rows = db.execute(
        "SELECT uid,username,score,ts FROM leaderboard WHERE game_id=? ORDER BY score DESC LIMIT ?",
        (game_id, limit)
    ).fetchall()
    db.close()
    return [{"uid": r[0], "username": r[1], "score": r[2], "ts": r[3]} for r in rows]

@app.post("/api/leaderboard/submit")
def submit_score(uid: str, game_id: str, score: int, username: str = ""):
    db = db_get()
    db.execute("INSERT INTO leaderboard VALUES (NULL,?,?,?,?,?)",
               (game_id, uid, username, score, int(time.time())))
    db.commit()
    db.close()
    return {"ok": True}

# ──────────────────────────────────────────────
#  GAME CATALOG
# ──────────────────────────────────────────────
@app.get("/api/games")
def list_games(category: str = "", is_vip: int = -1):
    db = db_get()
    sql = "SELECT id,name,description,file_path,is_vip,category,plays FROM games WHERE 1=1"
    args = []
    if category: sql += " AND category=?"; args.append(category)
    if is_vip >= 0: sql += " AND is_vip=?"; args.append(is_vip)
    sql += " ORDER BY plays DESC"
    rows = db.execute(sql, args).fetchall()
    db.close()
    return [{"id": r[0], "name": r[1], "description": r[2], "file_path": r[3],
             "is_vip": bool(r[4]), "category": r[5], "plays": r[6]} for r in rows]

@app.post("/api/games/register")
def register_game(id: str, name: str, description: str, file_path: str,
                  category: str = "休闲", is_vip: int = 0):
    db = db_get()
    db.execute("INSERT OR REPLACE INTO games VALUES (?,?,?,?,'',?,?,0,?)",
               (id, name, description, file_path, is_vip, category, int(time.time())))
    db.commit()
    db.close()
    return {"ok": True}

# ──────────────────────────────────────────────
#  MULTIPLAYER SESSIONS
# ──────────────────────────────────────────────
@app.get("/api/rooms")
def list_rooms(status: str = "waiting"):
    db = db_get()
    rows = db.execute(
        "SELECT id,game_id,host_uid,status,players,created_at FROM game_sessions WHERE status=? ORDER BY created_at DESC",
        (status,)
    ).fetchall()
    db.close()
    return [{"id": r[0], "game_id": r[1], "host_uid": r[2], "status": r[3],
             "players": json.loads(r[4]), "created_at": r[5]} for r in rows]

@app.post("/api/rooms/create")
def create_room(uid: str, username: str, game_id: str = "connect4"):
    room_id = uuid.uuid4().hex[:8].upper()
    db = db_get()
    db.execute("INSERT INTO game_sessions VALUES (?,?,?,?,?,?,'')",
               (room_id, game_id, uid, "waiting",
                json.dumps([{"uid": uid, "username": username, "ready": True}]),
                int(time.time())))
    db.commit()
    db.close()
    return {"room_id": room_id}

@app.post("/api/rooms/join")
def join_room(room_id: str, uid: str, username: str):
    db = db_get()
    row = db.execute("SELECT * FROM game_sessions WHERE id=?", (room_id,)).fetchone()
    if not row: db.close(); raise HTTPException(404, "房间不存在")
    players = json.loads(row[4])
    if len(players) >= 4: db.close(); raise HTTPException(400, "房间已满")
    if any(p["uid"] == uid for p in players): db.close(); raise HTTPException(400, "已在房间中")
    players.append({"uid": uid, "username": username, "ready": True})
    db.execute("UPDATE game_sessions SET players=? WHERE id=?", (json.dumps(players), room_id))
    db.commit()
    db.close()
    return {"ok": True, "players": players}

@app.post("/api/rooms/leave")
def leave_room(room_id: str, uid: str):
    db = db_get()
    row = db.execute("SELECT players FROM game_sessions WHERE id=?", (room_id,)).fetchone()
    if row:
        players = [p for p in json.loads(row[0]) if p["uid"] != uid]
        if len(players) == 0:
            db.execute("DELETE FROM game_sessions WHERE id=?", (room_id,))
        else:
            db.execute("UPDATE game_sessions SET players=? WHERE id=?", (json.dumps(players), room_id))
        db.commit()
    db.close()
    return {"ok": True}

# ──────────────────────────────────────────────
#  WEBSOCKET - 多人游戏实时同步
# ──────────────────────────────────────────────
@app.websocket("/ws/{room_id}/{uid}")
async def websocket_endpoint(ws: WebSocket, room_id: str, uid: str):
    username = ws.query_params.get("username", uid)
    await ws_manager.connect(ws, room_id, uid)
    # Notify room
    await ws_manager.broadcast(room_id, {
        "type": "player_joined", "uid": uid, "username": username,
        "count": len(ws_manager.connections.get(room_id, []))
    })
    try:
        while True:
            data = await ws.receive_json()
            # Broadcast to all other players in room
            await ws_manager.broadcast(room_id, data, exclude=ws)
    except WebSocketDisconnect:
        ws_manager.disconnect(ws, room_id, uid)
        await ws_manager.broadcast(room_id, {
            "type": "player_left", "uid": uid, "username": username
        })

# ──────────────────────────────────────────────
#  HEALTH CHECK
# ──────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "GameVault API", "time": datetime.now().isoformat()}

@app.get("/api/info")
def info():
    return {
        "name": "GameVault API",
        "version": "1.0",
        "port": PORT,
        "docs": f"http://localhost:{PORT}/docs",
        "ws": f"ws://localhost:{PORT}/ws/<room_id>/<uid>",
        "features": [
            "用户系统 (注册/登录)",
            "金币系统 (充值/消费)",
            "VIP会员",
            "排行榜",
            "游戏目录",
            "多人房间",
            "WebSocket实时同步"
        ]
    }

# ──────────────────────────────────────────────
#  STATIC GAMES (serve game files)
# ──────────────────────────────────────────────
if os.path.exists(STATIC_DIR):
    app.mount("/games", StaticFiles(directory=STATIC_DIR), name="games")

# ──────────────────────────────────────────────
#  SERVE GAMES INDEX
# ──────────────────────────────────────────────
@app.get("/games/")
def games_index():
    if not os.path.exists(STATIC_DIR):
        return JSONResponse({"games": [], "hint": f"在 {STATIC_DIR}/ 目录放入游戏HTML文件"})
    files = []
    for f in os.listdir(STATIC_DIR):
        if f.endswith('.html'):
            files.append({
                "name": f.replace('.html', '').replace('-', ' ').title(),
                "file": f"/games/{f}",
                "size": os.path.getsize(os.path.join(STATIC_DIR, f))
            })
    return {"games": files}

# ──────────────────────────────────────────────
#  BOOTSTRAP - 创建示例游戏
# ──────────────────────────────────────────────
def bootstrap():
    db = db_get()
    # Seed some leaderboard data
    sample_scores = [
        ("survivor","U001","冰魂",9800),
        ("survivor","U002","火神",8500),
        ("survivor","U003","雷帝",7200),
        ("basketball","U001","冰魂",88),
        ("basketball","U002","风行者",75),
        ("space-shooter","U001","冰魂",15000),
        ("space-shooter","U002","火神",12300),
        ("pinball","U001","冰魂",250000),
        ("pinball","U002","雷帝",198000),
    ]
    for game_id, uid, username, score in sample_scores:
        db.execute("INSERT OR IGNORE INTO leaderboard VALUES (NULL,?,?,?,?,?)",
                   (game_id, uid, username, score, int(time.time())))
    # Seed game list
    games = [
        ("survivor","太空生存战","在太空中生存到最后，躲避陨石和外星敌人","games/survivor.html",0,"射击"),
        ("basketball","篮球投篮","测试你的投篮精准度","games/basketball.html",0,"体育"),
        ("space-shooter","太空射击战","驾驶飞船击败UFO和敌人","games/space-shooter.html",0,"射击"),
        ("pinball","霓虹弹珠台","经典弹珠台玩法","games/pinball.html",0,"休闲"),
        ("connect4","四子棋","双人联机对战，先4连者胜","games/connect4.html",0,"棋牌"),
        ("tictactoe","井字棋","经典双人游戏","games/tictactoe.html",0,"棋牌"),
    ]
    for gid, name, desc, path, vip, cat in games:
        db.execute("INSERT OR REPLACE INTO games VALUES (?,?,?,?,'',?,?,0,?)",
                   (gid, name, desc, path, vip, cat, int(time.time())))
    db.commit()
    db.close()
    print("[GameVault] 示例数据已初始化 ✓")

# ──────────────────────────────────────────────
#  RUN
# ──────────────────────────────────────────────
if __name__ == "__main__":
    bootstrap()
    print(f"""
╔══════════════════════════════════════════════╗
║       🎮 GameVault 本地后端                  ║
╠══════════════════════════════════════════════╣
║  API 地址:   http://localhost:{PORT}           ║
║  文档:       http://localhost:{PORT}/docs      ║
║  WebSocket: ws://localhost:{PORT}/ws/<room>/<uid> ║
║  游戏目录:   {STATIC_DIR}/                     ║
╠══════════════════════════════════════════════╣
║  把 .html 游戏文件放进 {STATIC_DIR}/ 目录        ║
║  自动注册到平台，刷新即显示！                 ║
╚══════════════════════════════════════════════╝
""")
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=True)
