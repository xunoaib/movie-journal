FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

EXPOSE 40000

CMD ["streamlit", "run", "movies.py", "--server.port=40000", "--server.address=0.0.0.0"]
