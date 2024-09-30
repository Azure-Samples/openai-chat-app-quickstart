# ------------------- Stage 0: Base Stage ------------------------------
FROM python:3.11-alpine AS base

WORKDIR /code

# Install tini, a tiny init for containers
RUN apk add --update --no-cache tini

# Install required packages for cryptography package
# https://cryptography.io/en/latest/installation/#building-cryptography-on-linux
RUN apk add gcc musl-dev python3-dev libffi-dev openssl-dev cargo pkgconfig

# ------------------- Stage 1: Build Stage ------------------------------
FROM base AS build

COPY requirements.txt .

RUN pip3 install -r requirements.txt

COPY . .
# ------------------- Stage 2: Final Stage ------------------------------
FROM base AS final

RUN addgroup -S app && adduser -S app -G app

COPY --from=build --chown=app:app /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=build --chown=app:app /usr/local/bin /usr/local/bin
COPY --from=build --chown=app:app /code /code

USER app

EXPOSE 50505

ENTRYPOINT ["tini", "gunicorn", "quartapp:create_app()"]
