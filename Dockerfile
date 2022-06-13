## FRONTEND BUILD STAGE

FROM node:18-bullseye as frontend-build-stage

WORKDIR /frontend
ADD frontend .
RUN npm install && npm run build

# BACKEND BUILD STAGE

FROM python:3.10-slim-bullseye as backend-build-stage

RUN apt-get update && \
    apt-get install --no-install-recommends -y curl git gcc linux-libc-dev libc6-dev unzip && \
    pip install poetry

ENV MAGIC_CASTLE_PATH=/magic_castle
ENV MAGIC_CASTLE_VERSION=11.9.3
RUN curl -L https://github.com/ComputeCanada/magic_castle/releases/download/${MAGIC_CASTLE_VERSION}/magic_castle-openstack-${MAGIC_CASTLE_VERSION}.tar.gz -o magic_castle.tar.gz && \
    tar xvf magic_castle.tar.gz && \
    mv magic_castle-* ${MAGIC_CASTLE_PATH} && \
    chown -R root:root ${MAGIC_CASTLE_PATH}

ENV TERRAFORM_VERSION 1.1.9
RUN TERRAFORM_URL="https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_$(dpkg --print-architecture).zip" && \
    curl -L ${TERRAFORM_URL} -o terraform.zip && \
    unzip terraform.zip -d /usr/local/bin

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR='/var/cache/pypoetry' \
    POETRY_HOME='/usr/local'

WORKDIR /code
ADD poetry.lock pyproject.toml /code/
COPY mchub /code/mchub

RUN poetry install --no-dev --no-ansi && \
    pip uninstall -y poetry

FROM python:3.10-slim-bullseye as base-server

COPY --from=backend-build-stage /code /code
COPY --from=backend-build-stage /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

## Magic Castle User
RUN adduser --disabled-password mcu && \
    mkdir -p /home/mcu && \
    chown -R mcu:mcu /home/mcu

FROM base-server as cleanup-daemon
USER mcu
WORKDIR /home/mcu
CMD python3 -m mchub.services.cull_expired_cluster

## PRODUCTION IMAGE
FROM base-server as production-server

USER root
COPY --from=backend-build-stage /magic_castle /magic_castle
COPY --from=backend-build-stage /usr/local/bin/terraform /usr/local/bin/terraform
COPY --from=frontend-build-stage /frontend/dist /code/frontend

USER mcu
WORKDIR /home/mcu

RUN mkdir -p /home/mcu/clusters /home/mcu/database /home/mcu/credentials /home/mcu/.terraform.d/plugin-cache

ADD .terraformrc /home/mcu

ENV MAGIC_CASTLE_PATH=/magic_castle
ENV MAGIC_CASTLE_VERSION=11.9.3
ENV MCH_DIST_PATH=/code/frontend

CMD python3 -m mchub.schema_update --clean && \
    python3 -m gunicorn --workers 5 --bind 0.0.0.0:5000 --worker-class gevent "mchub:create_app()"
#CMD python3 -m mchub.wsgi
