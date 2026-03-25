import arxiv
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
import time
from datetime import datetime

# 1. 配置
# SEARCH_QUERY = "cat:cs.AI"  # 例如：搜索人工智能类别


SEARCH_QUERY = "cat:cs.AI OR cat:cs.RO"  
# ID_LIST = ["2603.18004",]  # 直接指定论文ID列表
MAX_RESULTS = 5
OUTPUT_FILE = "result/index.html"
MAX_FETCH_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 5


# 2. 抓取数据
def fetch_papers():
    # Use conservative client settings to reduce chances of hitting arXiv rate limits.
    client = arxiv.Client(
        page_size=min(MAX_RESULTS, 50),
        delay_seconds=5,
        num_retries=5,
    )
    search = arxiv.Search(
        query=SEARCH_QUERY,
        max_results=MAX_RESULTS,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    backoff_seconds = INITIAL_BACKOFF_SECONDS
    results = []
    for attempt in range(1, MAX_FETCH_RETRIES + 1):
        try:
            results = list(client.results(search))
            break
        except arxiv.HTTPError as exc:
            is_rate_limited = "HTTP 429" in str(exc)
            if (not is_rate_limited) or attempt == MAX_FETCH_RETRIES:
                raise
            print(
                f"arXiv API rate limit reached (attempt {attempt}/{MAX_FETCH_RETRIES}). "
                f"Retrying in {backoff_seconds}s..."
            )
            time.sleep(backoff_seconds)
            backoff_seconds *= 2
    
    papers = []
    for r in results:
        papers.append({
            "title": r.title,
            "authors": [a.name for a in r.authors],
            "summary": r.summary.replace('\n', ' '), # 简单清洗换行
            "url": r.entry_id,
            "published": r.published.strftime("%Y-%m-%d"),
            "categories": r.categories,
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
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"成功生成 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

