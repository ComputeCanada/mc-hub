# BACKEND BUILD STAGE
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS backend-build-stage
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

RUN apt-get update && \
    apt-get install --no-install-recommends -y gcc linux-libc-dev libc6-dev

WORKDIR /code
COPY mchub /code/mchub
COPY migrations /code/migrations
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev

FROM python:3.14-slim as base-server

COPY --from=backend-build-stage /code /code

## Magic Castle User
RUN adduser --disabled-password mcu && \
    mkdir -p /home/mcu && \
    chown -R mcu:mcu /home/mcu

ENV PATH="/code/.venv/bin:$PATH"

FROM base-server as cleanup-daemon
USER mcu
WORKDIR /home/mcu
CMD python -m mchub.services.cull_expired_cluster

## PRODUCTION IMAGE
FROM base-server as production-server

USER mcu
WORKDIR /home/mcu

RUN mkdir -p /home/mcu/clusters /home/mcu/database /home/mcu/credentials

ENV FLASK_APP="mchub:create_app"

CMD flask db upgrade && \
    python -m mchub.schema_update && \
    python -m mchub.init_clusters && \
    python -m gunicorn --workers 5 --bind 0.0.0.0:5000 --worker-class gevent "mchub:create_app()"