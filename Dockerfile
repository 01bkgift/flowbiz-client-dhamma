# Base image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies first to leverage Docker layer caching
COPY requirements.web.txt ./
RUN pip install --no-cache-dir -r requirements.web.txt

# Copy the rest of the project
COPY . .
RUN pip install --no-cache-dir -e .

EXPOSE 8000

ENV APP_NAME="dhamma-automation"
ENV OUTPUT_DIR="./output"

RUN mkdir -p ${OUTPUT_DIR}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
