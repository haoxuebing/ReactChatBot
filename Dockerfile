# Docker Hub 镜像加速（国内网络可改：docker.1panel.live / docker.xuanyuan.me）
ARG DOCKER_REGISTRY=docker.m.daocloud.io

# Stage 1: 构建前端静态资源
FROM ${DOCKER_REGISTRY}/library/node:20-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com \
    && npm ci

COPY frontend/ ./
ENV VITE_API_BASE_URL=/api
RUN npm run build

# Stage 2: 安装 Python 依赖
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS backend-build

WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

# Stage 3: 运行镜像（复用 ghcr.io uv 镜像，避免再拉 docker.io/python）
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -f /etc/nginx/sites-enabled/default \
    && rm -rf /var/lib/apt/lists/*

COPY backend/ ./backend/
COPY --from=backend-build /app/backend/.venv /app/backend/.venv
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

ENV PATH="/app/backend/.venv/bin:$PATH"
WORKDIR /app/backend

EXPOSE 80

CMD ["/start.sh"]
