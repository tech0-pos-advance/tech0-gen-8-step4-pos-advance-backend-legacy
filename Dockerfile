# Python 3.8 イメージをベースにする
FROM python:3.9

# 作業ディレクトリを指定
WORKDIR /app

# 必要な依存関係をインストール
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# アプリケーションコードをコピー
COPY . /app

# アプリケーションを実行
CMD ["python", "main.py"]
