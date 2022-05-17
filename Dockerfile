## FRONTEND BUILD STAGE

FROM node:14-bullseye as frontend-build-stage

WORKDIR /frontend
ADD frontend/package*.json ./
RUN npm install
ADD frontend .
RUN npm run build

# BACKEND BUILD STAGE

FROM python:3.10-slim-bullseye as base-server

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR='/var/cache/pypoetry' \
    POETRY_HOME='/usr/local'

## Python requirements
WORKDIR /code
ADD poetry.lock pyproject.toml /code/
COPY mchub /code/mchub

RUN apt-get update && \
    apt-get install --no-install-recommends -y curl git gcc linux-libc-dev libc6-dev unzip && \
    pip install poetry && \
    poetry install --no-dev --no-ansi && \
    pip uninstall -y poetry && \
    rm -rf /var/cache/pypoetry && \
    apt-get purge -y gcc linux-libc-dev libc6-dev && \
    apt-get -y purge --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    apt-get clean && \
    rm -rf /root/.cache /root/.cargo /tmp/* /var/lib/apt/lists/*

## Magic Castle User
RUN adduser --disabled-password mcu && \
    mkdir -p /home/mcu && \
    chown -R mcu:mcu /home/mcu

ENV OS_CLIENT_CONFIG_FILE=/home/mcu/credentials/clouds.yaml

FROM base-server as cleanup-daemon
USER mcu

CMD python3 -m mchub.services.cull_expired_cluster

## PRODUCTION IMAGE
FROM base-server as production-server

ENV TERRAFORM_VERSION 1.1.6

## EXTERNAL DEPENDENCIES

# Terraform
USER root
RUN TERRAFORM_URL="https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_$(dpkg --print-architecture).zip" && \
    curl -L ${TERRAFORM_URL} -o terraform.zip && \
    unzip terraform.zip -d /usr/local/bin && \
    rm terraform.zip

## Vue Js frontend src
COPY --from=frontend-build-stage /frontend/dist /frontend

ENV MAGIC_CASTLE_PATH=/magic_castle
ENV MAGIC_CASTLE_VERSION=11.9.3
RUN curl -L https://github.com/ComputeCanada/magic_castle/releases/download/${MAGIC_CASTLE_VERSION}/magic_castle-openstack-${MAGIC_CASTLE_VERSION}.tar.gz -o magic_castle.tar.gz && \
    tar xvf magic_castle.tar.gz && \
    mv magic_castle-* ${MAGIC_CASTLE_PATH} && \
    chown -R root:root ${MAGIC_CASTLE_PATH} && \
    rm magic_castle.tar.gz

USER mcu
WORKDIR /home/mcu
RUN mkdir /home/mcu/clusters /home/mcu/database /home/mcu/credentials

ADD .terraformrc /home/mcu
RUN mkdir -p /home/mcu/.terraform.d/plugin-cache

ENV MCH_DIST_PATH=/frontend

CMD python3 -m mchub.schema_update --clean && \
    python3 -m gunicorn --workers 5 --bind 0.0.0.0:5000 --worker-class gevent "mchub:create_app()"
#CMD python3 -m mchub.wsgi
