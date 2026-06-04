import arxiv
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
import time
from datetime import datetime
from pathlib import Path
import requests

# 1. 配置
# SEARCH_QUERY = "cat:cs.AI"  # 例如：搜索人工智能类别


SEARCH_QUERY = "cat:cs.AI OR cat:cs.RO"  
# ID_LIST = ["2603.18004",]  # 直接指定论文ID列表
MAX_RESULTS = 10
OUTPUT_FILE = "result/index_test.html"
MAX_FETCH_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 5


# 2. 抓取数据
def fetch_papers():

    papers = []
    for _ in range(MAX_RESULTS):
        papers.append({
            "title": "Sample Title",
            "authors": ["Sample Author"],
            "summary": "Sample Summary",
            "summary_zh": "示例中文摘要",
            "url": "https://arxiv.org/abs/sample-id",
            "published": "2023-01-01",
            "categories": ["cs.AI", "cs.RO"],
        })
    return papers



# 3. 生成 HTML
def generate_html(papers):
    # 简单的 HTML 模板字符串
    env=Environment(
        loader=FileSystemLoader("./templates"),
        autoescape=select_autoescape(),
    )
    template = env.get_template("main_page.html")
    return template.render(date=datetime.now().strftime("%Y-%m-%d"), papers=papers)

# 4. 主函数
def main():
    print("开始抓取论文...")
    try:
        papers = fetch_papers()
    except arxiv.HTTPError as exc:
        print(f"抓取失败：{exc}")
        print("提示：这是 arXiv 的限流错误（429）。请稍后重试。")
        return
    print(f"抓取到 {len(papers)} 篇论文。")
    
    html_content = generate_html(papers)

    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)  # 确保输出目录存在

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"成功生成 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

