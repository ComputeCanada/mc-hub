FROM python:3.8.2-alpine3.11

ENV TERRAFORM_VERSION 0.12.24

WORKDIR /app
COPY ./app .

RUN apk add curl=7.67.0-r0

RUN cd /usr/local/bin && \
    curl https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
    -o terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    rm terraform_${TERRAFORM_VERSION}_linux_amd64.zip

RUN pip install -r requirements.txt

EXPOSE 5000

CMD python server.py
