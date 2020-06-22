## FRONTEND BUILD STAGE

FROM node:12.16.3-alpine3.11 as frontend-build-stage

WORKDIR /frontend
ADD frontend/package*.json ./
RUN npm install
ADD frontend .
RUN npm run build

## PRODUCTION STAGE

FROM python:3.8.2-alpine3.11 as base-server

ENV TERRAFORM_VERSION 0.12.24
ENV MAGIC_CASTLE_VERSION 7.3
ENV TERRAFORM_URL https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip
ENV MAGIC_CASTLE_URL https://github.com/ComputeCanada/magic_castle/releases/download/${MAGIC_CASTLE_VERSION}/magic_castle-openstack-${MAGIC_CASTLE_VERSION}.zip

## EXTERNAL DEPENDENCIES

RUN apk --no-cache add curl=7.67.0-r0 \
                       build-base=0.5-r1 \
                       libffi-dev=3.2.1-r6 \
                       openssl-dev=1.1.1g-r0

# Terraform
RUN curl ${TERRAFORM_URL} -o terraform_linux_amd64.zip && \
    unzip terraform_linux_amd64.zip -d /usr/local/bin && \
    rm terraform_linux_amd64.zip

## Magic Castle User
RUN adduser -D mcu
USER mcu
WORKDIR /home/mcu
ADD .terraformrc /home/mcu
RUN mkdir /home/mcu/app
RUN mkdir /home/mcu/clusters

## Download Magic Castle Open Stack release
RUN curl -L ${MAGIC_CASTLE_URL} -o magic_castle-openstack.zip && \
    unzip magic_castle-openstack.zip && \
    rm magic_castle-openstack.zip

## Terraform plugin caching setup
RUN mkdir -p /home/mcu/.terraform.d/plugin-cache

## Terraform init for Magic Castle
RUN terraform init magic_castle-openstack-${MAGIC_CASTLE_VERSION}

## Python requirements
ADD app/requirements.txt ./app
RUN pip install -r app/requirements.txt --user

## APPLICATION CODE

## Python backend src
ADD app /home/mcu/app

## Vue Js frontend src
COPY --from=frontend-build-stage /frontend/dist /home/mcu/dist

ENV FLASK_APP=app/server.py


## DEVELOPMENT IMAGE - For debugging with vscode
FROM base-server as development-server

USER root

RUN apk add git=2.24.3-r0 \
            npm=12.15.0-r1
RUN pip install ptvsd==4.3.2 \
                pylint==2.5.3 \
                black

USER mcu

RUN mkdir -p /home/mcu/.vscode-server/extensions

# For flask hot reloading
ENV FLASK_ENV=development

# for npm serve hot reloading inside docker
ENV CHOKIDAR_USEPOLLING=true

CMD python -m ptvsd --host 0.0.0.0 --port 5678 --wait --multiprocess -m flask run -h 0.0.0 -p 5000

## PRODUCTION IMAGE
FROM base-server as production-server

CMD python app/server.py
