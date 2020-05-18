FROM python:3.8.2-alpine3.11

ENV TERRAFORM_VERSION 0.12.24
ENV MAGIC_CASTLE_VERSION 6.4

WORKDIR /app

#
# EXTERNAL DEPENDENCIES
#

# Terraform
RUN apk add curl=7.67.0-r0
RUN cd /usr/local/bin && \
    curl https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
    -o terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    rm terraform_${TERRAFORM_VERSION}_linux_amd64.zip

# Terraform plugin caching setup
RUN mkdir ~/.terraform.d && mkdir ~/.terraform.d/plugin-cache
COPY ./.terraformrc /root/.terraformrc

# Download Magic Castle Open Stack release
RUN curl -L \
 https://github.com/ComputeCanada/magic_castle/releases/download/${MAGIC_CASTLE_VERSION}/magic_castle-openstack-${MAGIC_CASTLE_VERSION}.zip \
 -o magic_castle-openstack-${MAGIC_CASTLE_VERSION}.zip && \
 unzip magic_castle-openstack-${MAGIC_CASTLE_VERSION}.zip && \
 rm magic_castle-openstack-${MAGIC_CASTLE_VERSION}.zip

# Terraform init for Magic Castle
RUN (cd magic_castle-openstack-${MAGIC_CASTLE_VERSION} && terraform init)

# Python requirements
COPY ./app/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

#
# APPLICATION
#

COPY ./app .

EXPOSE 5000

CMD python server.py
