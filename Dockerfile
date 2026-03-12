FROM python:3.11-slim

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=zh_CN.UTF-8

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-impress \
    libreoffice-calc \
    pandoc \
    cups-client \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制应用代码
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir Flask==2.3.3 Werkzeug==2.3.7 requests==2.31.0 python-docx python-pptx Pillow

# 创建必要的目录
RUN mkdir -p /app/uploads /app/static /app/templates

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python3", "app.py"]
