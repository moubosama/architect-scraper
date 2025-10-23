FROM python:3.11-slim

# 必要パッケージをインストール
RUN apt-get update && apt-get install -y \
    wget unzip curl gnupg \
    && rm -rf /var/lib/apt/lists/*

# Google Chrome の追加（新方式）
RUN mkdir -p /etc/apt/keyrings \
    && wget -q -O /etc/apt/keyrings/google-linux-signing-key.gpg https://dl.google.com/linux/linux_signing_key.pub \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-linux-signing-key.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Python環境
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src ./src

# Selenium 実行時に必要な shared memory を増やす
ENV TZ=Asia/Tokyo
CMD ["python", "src/scraper.py"]
