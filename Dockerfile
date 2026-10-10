FROM python:3.12-slim
WORKDIR /app
COPY tarot /app/tarot
COPY registry.json theme.json /app/
COPY web /app/web
COPY art /app/art
RUN useradd --uid 10001 --create-home tarot && mkdir /data && chown tarot /data
USER tarot
ENV DATABASE_PATH=/data/tarot.sqlite3
EXPOSE 8080
CMD ["python", "-m", "tarot.server"]
