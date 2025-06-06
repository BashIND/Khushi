FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/

COPY requirements.txt ./ 
RUN pip3 install --no-cache-dir --upgrade -r requirements.txt

COPY . .

CMD ["python", "main.py"]
