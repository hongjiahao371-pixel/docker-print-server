# Docker Print Server 🖨️

一个支持远程打印的 Web 管理界面，基于 CUPS。

## 功能特点

- 🌐 Web 界面上传文件打印
- 📄 支持多种文件格式：PDF、DOC、DOCX、PPT、PPTX、TXT、图片等
- 👀 文件预览功能（PDF/图片自动预览，Office文档转为PDF预览）
- 📜 打印历史记录，支持重新打印
- ⚙️ 支持设置打印份数、双面打印、页码范围
- 🖨️ 支持多打印机管理

## 快速开始

### 方式一：一键部署（推荐）

```bash
curl -O https://raw.githubusercontent.com/hongjiahao371-pixel/docker-print-server/main/docker-compose.yml
docker-compose up -d
```

访问 http://localhost:5501

### 方式二：手动部署

```bash
# 1. 克隆代码
git clone https://github.com/hongjiahao371-pixel/docker-print-server.git
cd docker-print-server

# 2. 构建镜像
docker build -t print-server .

# 3. 运行
docker run -d --name print-server -p 5501:5000 \
  -v ./uploads:/app/uploads \
  -v ./data:/app/data \
  -e CUPS_HOST=your-cups-ip \
  -e CUPS_PORT=631 \
  print-server
```

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| CUPS_HOST | CUPS 服务器地址 | cups-server |
| CUPS_PORT | CUPS 端口 | 631 |

### Docker Compose 配置

#### 使用自带 CUPS（推荐）

```yaml
version: '3.8'

services:
  print-server:
    image: jvsheng/docker-print-server:latest
    container_name: print-server
    ports:
      - "5501:5000"
    volumes:
      - ./uploads:/app/uploads
      - ./data:/app/data
    environment:
      - CUPS_HOST=cups-server
      - CUPS_PORT=631
    restart: unless-stopped

  cups-server:
    image: ydkn/cups
    container_name: cups-server
    ports:
      - "1631:631"
    environment:
      - CUPS_ADMIN_USER=admin
      - CUPS_ADMIN_PASSWORD=admin
    volumes:
      - cups-config:/etc/cups
      - cups-spool:/var/spool/cups
      - cups-log:/var/log/cups
    devices:
      - /dev/usb:/dev/usb
    restart: unless-stopped

volumes:
  cups-config:
  cups-spool:
  cups-log:
```

#### 使用已有的 CUPS

```yaml
version: '3.8'

services:
  print-server:
    image: jvsheng/docker-print-server:latest
    container_name: print-server
    ports:
      - "5501:5000"
    volumes:
      - ./uploads:/app/uploads
      - ./data:/app/data
    environment:
      # 修改为你的CUPS地址
      - CUPS_HOST=192.168.1.100
      - CUPS_PORT=631
    restart: unless-stopped
```

## 使用说明

### 1. 添加打印机

在 CUPS 管理界面添加打印机：
- 地址：http://你的IP:1631
- 用户名/密码：admin/admin

### 2. 上传打印

1. 打开 Web 界面：http://localhost:5501
2. 选择文件
3. 选择打印机
4. 设置打印选项（份数、双面、页码）
5. 点击"上传并打印"

### 3. 页码范围格式

- 单页：`1`
- 多页：`1,3,5`
- 范围：`1-10`
- 混合：`1,3-5,10`

## 端口说明

| 端口 | 说明 |
|------|------|
| 5501 | Web 界面端口 |
| 1631 | CUPS 端口（可选） |

## 文件结构

```
.
├── app.py              # Flask 主程序
├── Dockerfile         # Docker 镜像构建文件
├── docker-compose.yml # Docker Compose 配置
├── requirements.txt   # Python 依赖
├── static/           # 静态资源
├── templates/        # HTML 模板
├── utils/           # 工具类
│   ├── printer_manager.py   # 打印机管理
│   ├── file_converter.py  # 文件转换
│   └── print_history.py   # 打印历史
├── uploads/         # 上传文件目录
└── data/           # 数据目录
```

## 技术栈

- Python 3.11
- Flask
- CUPS
- LibreOffice（文件转换）
- Pandoc（文档转换）

## 常见问题

### Q: 显示"暂无可用打印机"
A: 检查 CUPS 服务是否正常运行，CUPS_HOST 环境变量是否正确

### Q: Office 文件无法预览
A: 确保容器内已安装 LibreOffice 和 Pandoc

### Q: 打印失败
A: 检查打印机是否连接，检查 CUPS 日志

## 感谢

- [ydkn/cups](https://hub.docker.com/r/ydkn/cups) - CUPS Docker 镜像
