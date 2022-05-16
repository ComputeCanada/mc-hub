## FRONTEND BUILD STAGE

FROM node:14-bullseye as frontend-build-stage

WORKDIR /frontend
ADD frontend/package*.json ./
RUN npm install
ADD frontend .
RUN npm run build

# BACKEND BUILD STAGE

FROM python:3.10-slim-bullseye as base-server

RUN apt-get update && \
    apt-get install  --no-install-recommends -y curl git gcc linux-libc-dev libc6-dev unzip

## Python requirements
RUN python3 -m venv /venv
ADD poetry.lock pyproject.toml /venv/
WORKDIR /venv
ENV VIRTUAL_ENV=/venv
RUN /venv/bin/pip install poetry && \
    /venv/bin/poetry install
# Install app in venv
ADD mchub /venv/lib/python3.10/site-packages/mchub

RUN apt-get purge -y gcc linux-libc-dev libc6-dev && \
    apt-get -y purge --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    apt-get clean && \
    rm -rf /root/.cache /root/.cargo /tmp/* /var/lib/apt/lists/*

## Magic Castle User
RUN adduser --disabled-password mcu
RUN mkdir -p /home/mcu && chown -R mcu:mcu /home/mcu

USER mcu
WORKDIR /home/mcu
RUN mkdir /home/mcu/database
RUN mkdir /home/mcu/credentials
RUN mkdir /home/mcu/tests
## Python backend src
ADD tests /home/mcu/tests

ENV OS_CLIENT_CONFIG_FILE=/home/mcu/credentials/clouds.yaml


FROM base-server as cleanup-daemon
USER mcu

CMD /venv/bin/python -m mchub.services.cull_expired_cluster

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
    chown -R root:root /magic_castle && \
    mv magic_castle-* ${MAGIC_CASTLE_PATH} && \
    rm magic_castle.tar.gz

USER mcu
RUN mkdir /home/mcu/clusters

ADD .terraformrc /home/mcu
RUN mkdir -p /home/mcu/.terraform.d/plugin-cache

ENV MCH_DIST_PATH=/frontend

CMD /venv/bin/python -m mchub.schema_update --clean && \
    /venv/bin/python -m gunicorn --workers 5 --bind 0.0.0.0:5000 --worker-class gevent "mchub:create_app()"
#CMD /home/mcu/venv/bin/python -m mchub.wsgi
