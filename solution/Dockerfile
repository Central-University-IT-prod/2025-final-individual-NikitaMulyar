FROM python:3.12-bullseye

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:server_app", "--host", "REDACTED", "--port", "8080", "--reload"]
