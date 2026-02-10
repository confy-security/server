FROM python:3.14.3-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHON_COLORS=0

WORKDIR /code

COPY . /code/

RUN pip install --no-cache-dir --root-user-action ignore --upgrade pip \
    && pip install --no-cache-dir --root-user-action ignore -r requirements.txt

EXPOSE 8000

ENTRYPOINT ["uvicorn", "--reload", "--host", "0.0.0.0", "server.main:app", "--workers", "4"]