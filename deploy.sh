#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "[deploy] 工作目录: $ROOT_DIR"
echo "[deploy] 拉取最新代码..."
git pull

echo "[deploy] 构建并启动容器..."
docker compose up -d --build

echo "[deploy] 发版完成"
