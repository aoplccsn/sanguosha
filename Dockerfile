FROM python:3.12-slim AS assets
WORKDIR /build
COPY assets ./assets
COPY scripts/sync_web_assets.py ./scripts/
RUN pip install --no-cache-dir Pillow && python scripts/sync_web_assets.py --production

FROM node:22-bookworm-slim AS frontend
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
COPY --from=assets /build/web/public/assets ./public/assets
COPY --from=assets /build/assets/idle_portraits.json /build/assets/idle_portraits.json
ARG APP_VERSION=0.3.0
ARG BUILD_COMMIT=unknown
ARG RENDER_GIT_COMMIT
ENV APP_VERSION=${APP_VERSION} BUILD_COMMIT=${BUILD_COMMIT}
RUN if [ "$BUILD_COMMIT" = unknown ] && [ -n "$RENDER_GIT_COMMIT" ]; then export BUILD_COMMIT="$RENDER_GIT_COMMIT"; fi; \
    ./node_modules/.bin/tsc -b && ./node_modules/.bin/vite build && \
    ! grep -R -E 'localhost|127\.0\.0\.1|:5173|ws://' dist/assets --include='*.js'

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 APP_ENV=production WEB_DIST_DIR=/app/web/dist
COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts/start_production_web.sh ./start_production_web.sh
RUN pip install --no-cache-dir 'fastapi>=0.115,<1' 'uvicorn[standard]>=0.32,<1' 'websockets>=12,<16' && pip install --no-cache-dir --no-deps .
COPY --from=frontend /build/web/dist ./web/dist
RUN useradd --system --uid 10001 --home /app app && chown -R app:app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "import os, urllib.request; host=os.getenv('DOMAIN') or os.getenv('RENDER_EXTERNAL_HOSTNAME') or os.getenv('ZEABUR_WEB_DOMAIN'); port=os.getenv('PORT', '10000' if os.getenv('RENDER') == 'true' else '8000'); urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:' + port + '/health', headers={'Host': host or ''}), timeout=3)"
CMD ["sh", "/app/start_production_web.sh"]
