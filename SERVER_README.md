# 🎮 GameVault 本地后端

## 快速启动

```bash
pip3 install fastapi uvicorn python-multipart
mkdir -p games
python3 game_server.py
```

访问 **http://localhost:18432**

---

## API 文档
打开 **http://localhost:18432/docs** （自动生成 Swagger 文档）

---

## 上架游戏

**方法一：放文件（最简单）**
1. 把你的游戏 `.html` 文件放进 `games/` 目录
2. 重启服务器
3. 游戏自动出现在平台！

**方法二：API 注册**
```bash
curl -X POST "http://localhost:18432/api/games/register" \
  -d "id=my-game" \
  -d "name=我的游戏" \
  -d "description=很好玩" \
  -d "file_path=games/my-game.html" \
  -d "is_vip=0" \
  -d "category=休闲"
```

---

## 多人游戏开发（WebSocket）

```javascript
// 连接房间
const ws = new WebSocket('ws://localhost:18432/ws/ROOMCODE/USERID?username=小明');

// 发送操作
ws.send(JSON.stringify({
  type: 'move',
  x: 100,
  y: 200,
  action: 'shoot'
}));

// 接收其他玩家操作
ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  console.log(data.type, data); // move, shoot, hit, etc.
};
```

**常用消息类型：**
| type | 用途 | 字段 |
|------|------|------|
| `move` | 移动 | x, y |
| `shoot` | 射击 | angle, power |
| `hit` | 命中 | targetId, damage |
| `game_over` | 结束 | score, winner |
| `sync_state` | 状态同步 | state (完整游戏状态) |

---

## 前端对接示例

```javascript
// 登录
const res = await fetch('http://localhost:18432/api/login?username=小明&password=123456');
const user = await res.json();
localStorage.setItem('gv_uid', user.uid);

// 提交分数
await fetch('http://localhost:18432/api/leaderboard/submit?uid=' + uid + '&game_id=my-game&score=9999&username=小明');

// 获取排行榜
const lb = await fetch('http://localhost:18432/api/leaderboard/survivor').then(r=>r.json());

// 创建多人房间
const room = await fetch('http://localhost:18432/api/rooms/create?uid=' + uid + '&username=小明').then(r=>r.json());
console.log('房间码:', room.room_id);
```

---

## 部署到公网（可选）

用 **Cloudflare Tunnel** 暴露本地服务：

```bash
# 安装 cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/download/2024.1.5/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# 启动隧道（免费，不需要服务器）
cloudflared tunnel --url http://localhost:18432
```

这样就能得到一个公网地址，别人也能访问你的后端和游戏！
