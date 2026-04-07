FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

COPY --chown=user requirements.txt pyproject.toml README.md openenv.yaml /app/
COPY --chown=user supportops_openenv /app/supportops_openenv
COPY --chown=user app.py /app/app.py

RUN python -m pip install --upgrade pip \
	&& pip install --no-cache-dir --retries 5 --timeout 120 -r requirements.txt

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
