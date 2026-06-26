#!/bin/bash
# GameVault 后端启动脚本
# 运行方式: bash run_server.sh

echo "🎮 启动 GameVault 本地后端..."

# 检查 Python
if ! command -v python3 &>/dev/null; then
    echo "❌ 需要 Python3，请先安装"
    exit 1
fi

# 安装依赖
echo "📦 安装依赖 (fastapi, uvicorn)..."
pip3 install fastapi uvicorn python-multipart --quiet 2>/dev/null

# 创建 games 目录
mkdir -p games

# 启动
echo "🚀 启动服务器..."
python3 game_server.py
