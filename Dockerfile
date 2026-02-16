FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements_test.txt .
RUN pip install --no-cache-dir -r requirements_test.txt

COPY . .

# 기본은 웹 실행으로 둔다 (워커는 Railway Start Command로 덮어씀)
CMD ["bash", "-lc", "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]