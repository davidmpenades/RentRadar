FROM python:3.13-slim-trixie AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Solo las bibliotecas compartidas que carga GeoDjango, sin -dev ni gdal-bin
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgdal36 libgeos-c1t64 libproj25 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --require-hashes -r /tmp/requirements.txt

# El código queda propiedad de root: el proceso no puede modificarlo
COPY . /app

USER 10001

FROM runtime AS dev

USER root

COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install --require-hashes -r /tmp/requirements-dev.txt

USER 10001
