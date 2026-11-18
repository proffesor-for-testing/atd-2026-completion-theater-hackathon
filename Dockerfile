# Runs the optional starter-python scaffold (stdlib only, no pip install).
FROM python:3.12-slim
WORKDIR /app
COPY starter-python/ /app/
ENV HOST=0.0.0.0 PORT=8765 DATA_DIR=/data PYTHONUNBUFFERED=1
VOLUME /data
EXPOSE 8765
# Reset the fixture only on first run (no marker yet), then serve.
CMD ["sh", "-c", "[ -f /data/.fixture-owner ] || python app.py --reset; exec python app.py"]
