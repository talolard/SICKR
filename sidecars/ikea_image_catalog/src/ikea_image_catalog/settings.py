"""Scrapy settings for the IKEA image catalog sidecar."""

BOT_NAME = "ikea_image_catalog"

SPIDER_MODULES = ["ikea_image_catalog.spiders"]
NEWSPIDER_MODULE = "ikea_image_catalog.spiders"

ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 4
DOWNLOAD_DELAY = 0.25
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.25
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504]
SCHEDULER_DEBUG = True

USER_AGENT = "Mozilla/5.0 (compatible; ikea-image-catalog/0.1; +https://github.com/talolard/SICKR)"
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

FEED_EXPORT_ENCODING = "utf-8"
LOG_LEVEL = "INFO"

EXTENSIONS = {
    "ikea_image_catalog.extensions.RunStatsExtension": 500,
}
