FROM python:3.8.2-alpine3.11

ENV TERRAFORM_VERSION 0.12.24
ENV MAGIC_CASTLE_VERSION 6.4

WORKDIR /app

# External dependencies

RUN apk add curl=7.67.0-r0

RUN cd /usr/local/bin && \
    curl https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
    -o terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    rm terraform_${TERRAFORM_VERSION}_linux_amd64.zip

RUN mkdir ~/.terraform.d && mkdir ~/.terraform.d/plugin-cache
COPY ./.terraformrc /root/.terraformrc

COPY ./app/magic_castle-openstack-${MAGIC_CASTLE_VERSION} ./magic_castle-openstack-${MAGIC_CASTLE_VERSION}

RUN (cd magic_castle-openstack-${MAGIC_CASTLE_VERSION} && terraform init)

# Application

RUN mkdir clusters
COPY ./app .
RUN pip install -r requirements.txt

EXPOSE 5000

CMD python server.py
