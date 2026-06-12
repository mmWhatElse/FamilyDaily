ARG BUILD_VERSION
FROM ghcr.io/home-assistant/base-python:3.12-alpine3.20

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="addon" \
  io.hass.arch="aarch64|amd64|armv7"

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY app/ ./app/

COPY run.sh /
RUN chmod a+x /run.sh

EXPOSE 8099

CMD ["/run.sh"]
