import requests
import pandas as pd
import time
import random
from datetime import datetime

def crawl_bunjang_women(keywords: list, pages: int = 5, title_filters: list = None) -> pd.DataFrame:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://m.bunjang.co.kr",
        "Referer": "https://m.bunjang.co.kr/"
    }

    all_items = {}
    
    for keyword in keywords:
        print(f"\n [{keyword}] 크롤링 시작")
        for page in range(1, pages + 1):
            try:
                resp = requests.get(
                    "https://api.bunjang.co.kr/api/1/find_v2.json",
                    headers=headers,
                    params={
                        "q": keyword,
                        "order": "score",
                        "page": page,
                        "f_category_id": "310"
                    },
                    timeout=5
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"[{keyword}] 페이지 {page} 에러: {e} → 스킵")
                time.sleep(delay)
                continue

            items = data.get("list", [])
            if not items:
                print(f"[{keyword}] 페이지 {page} 결과 없음 → 중단")
                break

            for it in items:
                title = it.get("name", "")
                if title_filters and not any(k.lower() in title.lower() for k in title_filters):
                    continue

                pid = it.get("pid")
                if pid in all_items:
                    continue  # 중복 제거

                try:
                    ts = it.get("update_time")
                    date = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S") if ts else ""
                except:
                    date = ""

                try:
                    det = requests.get(
                        f"https://api.bunjang.co.kr/api/pms/v3/products-detail/{pid}?viewerUid=-1",
                        headers=headers,
                        timeout=5
                    )
                    det.raise_for_status()
                    product = det.json().get("data", {}).get("product", {})
                    if not product:
                        continue

                    categories = product.get("categories", [])
                    category_names = [cat.get("name", "") for cat in categories]
                    full_category_path = " > ".join(category_names)


                    if title_filters and any(k.lower() in ["코스", "cos"] for k in title_filters):
                        bad_categories = {"코스튬/코스프레", "한복", "기타 테마/이벤트"}
                        if any(cat in bad_categories for cat in category_names):
                            continue
                            
                    item = {
                        "pid": product.get("pid"),
                        "상품 이름": product.get("name", ""),
                        "가격": product.get("price", ""),
                        "설명": product.get("description", "").replace("\n", " ").strip(),
                        "상품상태": product.get("condition", ""),
                        "판매상태": product.get("saleStatus", ""),
                        "찜 수": product.get("metrics", {}).get("favoriteCount", 0),
                        "조회수": product.get("metrics", {}).get("viewCount", 0),
                        "배송비": product.get("trade", {}).get("shippingSpecs", {}).get("DEFAULT", {}).get("fee", 0),
                        "사진": ";".join([
                            product.get("imageUrl", "").replace("{cnt}", str(i + 1)).replace("{res}", "600")
                            for i in range(product.get("imageCount", 0))
                        ]),
                        "카테고리": full_category_path,
                        "직거래지역": product.get("geo", {}).get("address", ""),
                        "상품태그": ", ".join([
                            kw.get("keyword", "") for kw in product.get("keywords", [])
                        ]),
                        "검수가능": product.get("care", False),
                        "링크": f"https://m.bunjang.co.kr/products/{pid}",
                        "업데이트일": date
                    }

                    all_items[pid] = item

                except Exception as e:
                    print(f"🔁 [상세 실패] pid={pid}: {e}")
                    continue

            print(f"[{keyword}] 페이지 {page} 완료 → 누적 수집 {len(all_items)}개")
            time.sleep(random.uniform(0.2, 0.6))

    return pd.DataFrame(list(all_items.values()))

if __name__ == "__main__":
    search_keywords = ["폴로"]
    title_filters = ["폴로","polo","랄프로렌"]
    pages = 166

    df = crawl_bunjang_women(search_keywords, pages=pages, title_filters=title_filters)
    fname = "bunjang_폴로_여성의류_최종.csv"
    df.to_csv(fname, index=False, encoding="utf-8-sig")
    print(f"\n 저장 완료: {fname} (총 {len(df)}개 상품)")