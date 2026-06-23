# 🎮 游戏宇宙 GameVerse

> 一个开源的游戏平台 · 免费安装 · 付费解锁精品游戏

**🌐 在线体验：** https://nima54851.github.io/game-platform

---

## ✨ 特色

- 🆓 **4款免费游戏** — 贪吃蛇、2048、井字棋、俄罗斯方块，无需注册直接玩
- 👑 **VIP会员** — ¥18/月 · ¥38/季 · ¥199/年，解锁全部30款游戏
- 👥 **多人游戏** — 同屏双打，和朋友共用键盘对战
- 💳 **PayPal收款** — 扫码支付，自动激活key，无需服务器
- 📦 **本地安装版** — Electron打包，一键安装离线玩
- 🌐 **网页版** — GitHub Pages直接跑，无需安装

---

## 🎮 游戏列表

### 🆓 免费游戏
| 游戏 | 类型 | 操作 |
|---|---|---|
| 🐍 贪吃蛇 | 休闲 | ↑↓←→ 方向键 |
| 🔢 2048 | 益智 | ↑↓←→ 滑动合并 |
| ⭕ 井字棋 | 双人 | 点击落子 |
| 🧱 俄罗斯方块 | 经典 | ←→移动 ↑旋转 ↓加速 |

### 👑 VIP游戏
| 游戏 | 类型 |
|---|---|
| 🐦 Flappy鸟 | 飞行 |
| 💣 扫雷 | 逻辑 |
| ⚫ 五子棋 | 策略 |
| 🦖 跑酷恐龙 | 障碍 |
| 🏓 弹球对战 | 双打 |
| 🔢 数独大师 | 逻辑 |
| ...更多持续更新 |

---

## 💳 订阅价格

| 档位 | 价格 | 内容 |
|---|---|---|
| 🌙 月卡 | ¥18/月 | 解锁全部付费游戏 |
| ☀️ 季卡 | ¥38/季 | 解锁全部 + 多人联机 |
| ⭐ 年卡 | ¥199/年 | 解锁全部 + 未来新增免费送 |

**收款：** PayPal `yinanzo@hotmail.com`

---

## 🛠️ 技术栈

- **前端**：原生 HTML + CSS + JavaScript（零依赖）
- **部署**：GitHub Pages（免费）
- **桌面**：Electron（可选打包本地App）
- **存储**：localStorage（本地持久化）
- **收款**：PayPal.me（扫码 + key激活码）

---

## 📦 部署

**网页版（一键部署）：**

```bash
git clone https://github.com/nima54851/game-platform.git
cd game-platform
# 上传到 GitHub → Settings → Pages → 启用
```

**本地桌面版：**

```bash
npm install -g electron
npx electron .
```

---

## 🔧 自定义游戏

在 `games/` 目录添加 `.html` 文件，即可在平台中显示：

```javascript
// 在 games/your-game.html 中
// 完成后在 index.html 的 GAMES 数组添加：
{id:'your-game', name:'🎮 游戏名', thumb:'#颜色', emoji:'🎮',
 cat:'all vip', free:false, tags:['类型'], desc:'描述'}
```

---

**Built with 💜 by [灵犀 AI](https://github.com/nima54851)**
