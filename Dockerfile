FROM python:3.12-slim-bookworm
ARG GIT_SHA=unknown
ENV DEPLOYMENT_SHA=$GIT_SHA
LABEL org.opencontainers.image.revision=$GIT_SHA

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Cache dependencies separately from frequently changed application files.
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip check

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY main.py smoke_test.py ./
COPY dist/ ./dist/

USER 10001:10001

# Bonchorok has no ML model: verify its actual data and FastAPI entry point.
# A broken catalog or a missing runtime asset must fail the image build.
RUN python -c "import main; from pathlib import Path; assert main.health()['herb_count'] == 601; assert main.health()['deployment_sha'] == main.DEPLOYMENT_SHA; assert len({r['id'] for r in main.catalog}) == 601; assert any(r['id'] == 'sophorae-flos' for r in main.catalog); assert all((Path('dist') / f).is_file() for f in ['index.html', 'app-v2.js', 'details.js', 'style.css', 'sophora-plant.jpg']); print('PASS: FastAPI import, version, 601 unique herbs and runtime assets')"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import json, urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3); d=json.load(r); assert d['status']=='ok' and d['herb_count']>0"

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
