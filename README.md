# BrightData Scraper

使用 **BrightData 官方 Python SDK** 从 Amazon 和 Temu 爬取商品数据和图片。

## 特点

- 使用 [BrightData 官方 SDK](https://github.com/brightdata/sdk-python)
- SDK 自动处理认证、限流、重试和响应解析
- 支持 Amazon 和 Temu 商品搜索和详情获取
- 批量下载商品图片

## 安装

```bash
# 克隆项目
git clone https://github.com/xsha511/brightdata-scraper.git
cd brightdata-scraper

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -e .
```

## 配置

### 1. 获取 API Token

登录 [BrightData 控制台](https://brightdata.com/cp/zones)，在 **Account Settings -> API Key** 获取你的 API Token。

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```env
BRIGHTDATA_API_TOKEN=your_api_token_here
```

## 使用

### 运行示例

```bash
python main.py
```

### 代码示例

```python
import asyncio
from src.scrapers import AmazonScraper, TemuScraper

async def main():
    # 搜索 Amazon 商品
    async with AmazonScraper() as scraper:
        results = await scraper.search("wireless headphones")
        for product in results.products:
            print(f"{product.title} - ${product.price}")

    # 获取单个商品详情
    async with AmazonScraper() as scraper:
        product = await scraper.get_product("B0CHWRXH8B")
        print(f"Title: {product.title}")

    # 搜索 Temu 商品
    async with TemuScraper() as scraper:
        results = await scraper.search("phone case")
        for product in results.products:
            print(f"{product.title} - ${product.price}")

asyncio.run(main())
```

### 下载商品图片

```python
from src.utils import ImageDownloader

async def download_images():
    async with AmazonScraper() as scraper:
        results = await scraper.search("laptop stand")

        async with ImageDownloader() as downloader:
            updated = await downloader.download_all(results.products[:5])

            for product in updated:
                for image in product.images:
                    if image.local_path:
                        print(f"Downloaded: {image.local_path}")

asyncio.run(download_images())
```

## 项目结构

```
brightdata-scraper/
├── src/
│   ├── client.py          # BrightData SDK 封装
│   ├── config.py          # 配置管理
│   ├── models.py          # Pydantic 数据模型
│   ├── scrapers/
│   │   ├── base.py        # 基础爬虫类
│   │   ├── amazon.py      # Amazon 爬虫
│   │   └── temu.py        # Temu 爬虫
│   └── utils/
│       └── image_downloader.py
├── data/images/           # 下载的图片
├── main.py                # 示例脚本
└── pyproject.toml
```

## 文档

- [BrightData Python SDK](https://docs.brightdata.com/api-reference/SDK)
- [BrightData Web Scraper API](https://docs.brightdata.com/scraping-automation/web-data-apis/web-scraper-api)
- [Scrapers Library](https://docs.brightdata.com/datasets/scrapers/scrapers-library/overview)

## 注意事项

- BrightData 按请求计费，请注意用量
- 请遵守各网站的使用条款

## License

MIT
