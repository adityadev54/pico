FROM python:3.12-slim
WORKDIR /app
COPY relay ./relay
COPY server ./server
COPY website ./website
COPY downloads ./downloads
COPY build/web ./build/web
COPY assets/characters ./assets/characters
RUN useradd --uid 10001 --create-home pico && mkdir -p /data && chown pico:pico /data
EXPOSE 8080
CMD ["python", "-m", "relay.boot", "--host", "0.0.0.0", "--port", "8080", "--state", "/data/relay.sqlite"]
