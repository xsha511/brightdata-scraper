# BrightData Scraper

从 Amazon 和 Temu 爬取商品数据和图片的 MVP 项目，使用 BrightData 代理服务。

## 功能

- 支持 Amazon 和 Temu 商品搜索
- 获取商品详情（标题、价格、评分、描述等）
- 批量下载商品图片
- 支持 BrightData 代理（可选）

## 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/brightdata-scraper.git
cd brightdata-scraper

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -e .

# 开发环境
pip install -e ".[dev]"
```

## 配置

复制 `.env.example` 到 `.env` 并填写你的 BrightData 凭据：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
BRIGHTDATA_USERNAME=your_username
BRIGHTDATA_PASSWORD=your_password
BRIGHTDATA_HOST=brd.superproxy.io
BRIGHTDATA_PORT=22225
```

## 使用

### 基本使用

```python
import asyncio
from src.scrapers import AmazonScraper, TemuScraper
from src.utils import ImageDownloader

async def main():
    # 搜索 Amazon
    async with AmazonScraper() as scraper:
        results = await scraper.search("wireless headphones")
        for product in results.products:
            print(f"{product.title} - ${product.price}")

    # 搜索 Temu
    async with TemuScraper() as scraper:
        results = await scraper.search("phone case")
        for product in results.products:
            print(f"{product.title} - ${product.price}")

asyncio.run(main())
```

### 下载图片

```python
async def download_example():
    async with AmazonScraper() as scraper:
        results = await scraper.search("laptop stand")

        async with ImageDownloader() as downloader:
            updated_products = await downloader.download_all(results.products)

            for product in updated_products:
                for image in product.images:
                    if image.local_path:
                        print(f"Downloaded: {image.local_path}")

asyncio.run(download_example())
```

### 运行示例

```bash
python main.py
```

## 项目结构

```
brightdata-scraper/
├── src/
│   ├── __init__.py
│   ├── client.py          # BrightData HTTP 客户端
│   ├── config.py          # 配置管理
│   ├── models.py          # 数据模型
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py        # 基础爬虫类
│   │   ├── amazon.py      # Amazon 爬虫
│   │   └── temu.py        # Temu 爬虫
│   └── utils/
│       ├── __init__.py
│       └── image_downloader.py  # 图片下载器
├── data/
│   └── images/            # 下载的图片
├── tests/
├── main.py                # 示例脚本
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

## 注意事项

- 请遵守各网站的使用条款和爬虫政策
- 建议使用 BrightData 代理以避免 IP 被封
- 控制请求频率，避免对目标网站造成压力

## License

MIT
