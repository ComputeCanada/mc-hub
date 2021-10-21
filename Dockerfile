## FRONTEND BUILD STAGE

FROM node:14-alpine3.14 as frontend-build-stage

WORKDIR /frontend
ADD frontend/package*.json ./
RUN npm install
ADD frontend .
RUN npm run build

# BACKEND BUILD STAGE

FROM python:3.9-alpine3.14 as base-server

ENV TERRAFORM_VERSION 1.0.9
ENV TERRAFORM_URL https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip

## EXTERNAL DEPENDENCIES

RUN apk --no-cache add git \
    curl \
    build-base \
    libffi-dev \
    openssl-dev \
    cargo

# Terraform
RUN curl ${TERRAFORM_URL} -o terraform_linux_amd64.zip && \
    unzip terraform_linux_amd64.zip -d /usr/local/bin && \
    rm terraform_linux_amd64.zip

## Magic Castle User
RUN adduser -D mcu

# Set mcu as the owner of the SQLite database volume
RUN mkdir -p /home/mcu/database && chown -R mcu:mcu /home/mcu/database

# Set mcu as the owner of the credentials directory
RUN mkdir -p /home/mcu/credentials && chown -R mcu:mcu /home/mcu/credentials

USER mcu
WORKDIR /home/mcu
ADD .terraformrc /home/mcu
RUN mkdir /home/mcu/app
RUN mkdir /home/mcu/clusters

## Terraform plugin caching setup
RUN mkdir -p /home/mcu/.terraform.d/plugin-cache

## Python requirements
ADD app/requirements.txt ./app
RUN pip install -r app/requirements.txt --user

ENV FLASK_APP=app/server.py

# For storing clouds.yaml configuration
RUN mkdir -p /home/mcu/.config/openstack

## PRODUCTION IMAGE
FROM base-server as production-server

## APPLICATION CODE

## Python backend src
ADD app /home/mcu/app
## Vue Js frontend src
COPY --from=frontend-build-stage /frontend/dist /home/mcu/dist

CMD python app/server.py
