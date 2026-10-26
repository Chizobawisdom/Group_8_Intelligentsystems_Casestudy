FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Run as a non-root user
RUN useradd --create-home --uid 1000 appuser

# Copy requirements first (Docker layer caching)
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=appuser:appuser . .
USER appuser

# Default: run the evaluation (no web server needed)
CMD ["python", "-m", "src.evaluation.run_eval"]

# Only if you build a Streamlit demo:
# EXPOSE 8501
# CMD ["streamlit", "run", "src/app.py", "--server.address=0.0.0.0", "--server.port=8501"]