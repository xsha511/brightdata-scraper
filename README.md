# BrightData Scraper

使用 BrightData Web Scraper API 从 Amazon 和 Temu 爬取商品数据和图片的 MVP 项目。

## 特点

- 使用 **BrightData Web Scraper API**（不是自己写解析逻辑）
- BrightData 负责处理反爬虫、页面解析、数据结构化
- 支持 Amazon 和 Temu 商品搜索和详情获取
- 批量下载商品图片

## 为什么用 Web Scraper API？

| 方案 | 优点 | 缺点 |
|------|------|------|
| **Web Scraper API** ✅ | 稳定、无需维护解析逻辑、处理反爬虫 | 按请求计费 |
| 代理 + 自己解析 | 灵活 | 页面结构变化需要维护 |
| Scraping Browser | 支持复杂JS | 资源消耗大 |

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

# 开发环境
pip install -e ".[dev]"
```

## 配置

1. 获取 BrightData API Token：https://brightdata.com/cp/api_tokens

2. 复制并编辑配置文件：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
BRIGHTDATA_API_TOKEN=your_api_token_here
```

3. （可选）配置 Dataset ID：

BrightData 为不同平台提供预构建的 Dataset，可以在 [Dataset Marketplace](https://brightdata.com/cp/datasets) 找到。

```env
# 默认值已在代码中配置，如需更改：
BRIGHTDATA_AMAZON_DATASET_ID=gd_l7q7dkf244hwjntr0
BRIGHTDATA_TEMU_DATASET_ID=gd_lz6e6n1k2pgo51vy9d
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
from src.utils import ImageDownloader

async def main():
    # 搜索 Amazon 商品
    async with AmazonScraper() as scraper:
        results = await scraper.search("wireless headphones", pages=1)
        for product in results.products:
            print(f"{product.title} - ${product.price}")
            print(f"  Images: {[img.url for img in product.images]}")

    # 获取单个商品详情（通过 ASIN）
    async with AmazonScraper() as scraper:
        product = await scraper.get_product("B0CHWRXH8B")
        print(f"Title: {product.title}")
        print(f"Price: ${product.price}")

    # 搜索 Temu 商品
    async with TemuScraper() as scraper:
        results = await scraper.search("phone case")
        for product in results.products:
            print(f"{product.title} - ${product.price}")

asyncio.run(main())
```

### 下载商品图片

```python
async def download_images():
    async with AmazonScraper() as scraper:
        results = await scraper.search("laptop stand")

        async with ImageDownloader() as downloader:
            # 下载前5个商品的图片
            updated = await downloader.download_all(results.products[:5])

            for product in updated:
                for image in product.images:
                    if image.local_path:
                        print(f"Downloaded: {image.local_path}")

asyncio.run(download_images())
```

### 批量获取商品（通过 URL 列表）

```python
async def batch_scrape():
    urls = [
        "https://www.amazon.com/dp/B0CHWRXH8B",
        "https://www.amazon.com/dp/B09V3KXJPB",
    ]

    async with AmazonScraper() as scraper:
        products = await scraper.get_products_by_urls(urls)
        for p in products:
            print(f"{p.title}: ${p.price}")

asyncio.run(batch_scrape())
```

## 项目结构

```
brightdata-scraper/
├── src/
│   ├── client.py          # BrightData API 客户端
│   ├── config.py          # 配置管理
│   ├── models.py          # Pydantic 数据模型
│   ├── scrapers/
│   │   ├── base.py        # 基础爬虫类
│   │   ├── amazon.py      # Amazon 爬虫
│   │   └── temu.py        # Temu 爬虫
│   └── utils/
│       └── image_downloader.py  # 图片下载器
├── data/
│   └── images/            # 下载的图片
├── tests/
├── main.py                # 示例脚本
├── pyproject.toml
├── .env.example
└── README.md
```

## API 参考

### AmazonScraper

```python
# 搜索
results = await scraper.search(
    query="keyword",
    pages=1,           # 搜索页数
    country="us"       # 国家代码
)

# 获取商品详情
product = await scraper.get_product("B0CHWRXH8B")  # ASIN
product = await scraper.get_product("https://amazon.com/dp/...")  # URL

# 批量获取
products = await scraper.get_products_by_urls([url1, url2, ...])
```

### TemuScraper

```python
# 搜索
results = await scraper.search(query="keyword")

# 获取商品详情
product = await scraper.get_product("12345")  # 商品ID
product = await scraper.get_product("https://temu.com/...")  # URL
```

### ImageDownloader

```python
async with ImageDownloader(output_dir="data/images") as downloader:
    # 下载单个图片
    path = await downloader.download_image(url, product_id, index)

    # 下载商品所有图片
    product = await downloader.download_product_images(product, max_images=5)

    # 批量下载
    products = await downloader.download_all(products, max_images_per_product=5)
```

## BrightData 文档

- [Web Scraper API 文档](https://docs.brightdata.com/scraping-automation/web-data-apis/web-scraper-api)
- [Amazon Dataset](https://docs.brightdata.com/scraping-automation/web-data-apis/web-scraper-api/datasets/amazon)
- [API Token 管理](https://brightdata.com/cp/api_tokens)

## 注意事项

- BrightData API 按请求计费，请注意用量
- 首次请求可能需要几十秒完成（API 异步处理）
- 请遵守各网站的使用条款

## License

MIT
