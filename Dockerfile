## FRONTEND BUILD STAGE

FROM node:14-bullseye as frontend-build-stage

WORKDIR /frontend
ADD frontend/package*.json ./
RUN npm install
ADD frontend .
RUN npm run build

# BACKEND BUILD STAGE

FROM python:3.9-alpine3.14 as base-server

ENV TERRAFORM_VERSION 1.1.6
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
RUN mkdir /home/mcu/mchub
RUN mkdir /home/mcu/tests
RUN mkdir /home/mcu/clusters

## Terraform plugin caching setup
RUN mkdir -p /home/mcu/.terraform.d/plugin-cache

## Python requirements
ADD requirements.txt .
RUN pip install -r requirements.txt --user

ENV FLASK_APP=mchub

# For storing clouds.yaml configuration
RUN mkdir -p /home/mcu/.config/openstack

## PRODUCTION IMAGE
FROM base-server as production-server

## APPLICATION CODE

## Python backend src
ADD mchub /home/mcu/mchub
ADD tests /home/mcu/tests

## Vue Js frontend src
COPY --from=frontend-build-stage /frontend/dist /home/mcu/dist

CMD python -m gunicorn --workers 5 --bind 0.0.0.0:5000 mchub:app
