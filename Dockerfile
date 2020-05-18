FROM python:3.8.2-alpine3.11

ENV TERRAFORM_VERSION 0.12.24
ENV MAGIC_CASTLE_VERSION 6.4
ENV TERRAFORM_URL https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip
ENV MAGIC_CASTLE_URL https://github.com/ComputeCanada/magic_castle/releases/download/${MAGIC_CASTLE_VERSION}/magic_castle-openstack-${MAGIC_CASTLE_VERSION}.zip

## EXTERNAL DEPENDENCIES

# Curl
RUN apk add curl=7.67.0-r0

# Terraform
RUN curl ${TERRAFORM_URL} -o terraform_linux_amd64.zip && \
    unzip terraform_linux_amd64.zip -d /usr/local/bin && \
    rm terraform_linux_amd64.zip

## Magic Castle User
RUN adduser -D mcu
USER mcu
WORKDIR /home/mcu
ADD app /home/mcu/app
ADD .terraformrc /home/mcu

## Download Magic Castle Open Stack release
RUN curl -L ${MAGIC_CASTLE_URL} -o magic_castle-openstack.zip && \
    unzip magic_castle-openstack.zip && \
    rm magic_castle-openstack.zip

## Terraform plugin caching setup
RUN mkdir -p /home/mcu/.terraform.d/plugin-cache

## Terraform init for Magic Castle
RUN mkdir clusters
RUN terraform init magic_castle-openstack-${MAGIC_CASTLE_VERSION}

## Python requirements
RUN pip install -r app/requirements.txt --user

EXPOSE 5000

CMD python app/server.py
