from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
from bs4 import BeautifulSoup
from bs4.element import Tag
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import requests
import time
import random
import re
import csv
import io
import json
from collections import deque
from typing import Any


app = Flask(__name__)
CORS(app)


APP_NAME = "MarketScraper Pro"

DEFAULT_USER_AGENT = "MarketScraperPro/1.1 (+respectful-public-web-scraper)"
MAX_HARD_LIMIT_PAGES = 50
MAX_HARD_LIMIT_DEPTH = 3
DEFAULT_TIMEOUT = 15

DEFAULT_MIN_DELAY = 1.0
DEFAULT_MAX_DELAY = 3.0
MAX_DELAY_ALLOWED = 15.0
MAX_RETRIES = 3


def normalize_url(url: str) -> str:
    if not url:
        return ""

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)

    if not parsed.netloc:
        return ""

    clean = parsed._replace(fragment="")
    return clean.geturl()


def get_domain(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "")


def is_same_domain(base_url: str, target_url: str) -> bool:
    return get_domain(base_url) == get_domain(target_url)


def is_valid_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def clamp_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except Exception:
        number = default

    return max(minimum, min(number, maximum))


def clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except Exception:
        number = default

    return max(minimum, min(number, maximum))


def human_pause(options: dict[str, Any], page_number: int = 1) -> None:
    """
    Safe human-style pacing:
    - randomized delay between requests
    - optional longer pauses
    - no CAPTCHA bypass
    - no paywall bypass
    - no login bypass
    - no anti-bot evasion
    """
    human_mode = bool(options.get("human_mode", True))

    if not human_mode:
        delay = clamp_float(options.get("delay"), 1.0, 0.0, MAX_DELAY_ALLOWED)
        time.sleep(delay)
        return

    min_delay = clamp_float(
        options.get("min_delay"),
        DEFAULT_MIN_DELAY,
        0.25,
        MAX_DELAY_ALLOWED
    )

    max_delay = clamp_float(
        options.get("max_delay"),
        DEFAULT_MAX_DELAY,
        min_delay,
        MAX_DELAY_ALLOWED
    )

    pause_seconds = random.uniform(min_delay, max_delay)

    long_pause_every = clamp_int(
        options.get("long_pause_every"),
        6,
        0,
        25
    )

    long_pause_min = clamp_float(
        options.get("long_pause_min"),
        4.0,
        0.0,
        MAX_DELAY_ALLOWED
    )

    long_pause_max = clamp_float(
        options.get("long_pause_max"),
        8.0,
        long_pause_min,
        MAX_DELAY_ALLOWED
    )

    if long_pause_every > 0 and page_number > 0 and page_number % long_pause_every == 0:
        pause_seconds += random.uniform(long_pause_min, long_pause_max)

    time.sleep(pause_seconds)


def can_fetch_url(url: str, user_agent: str = DEFAULT_USER_AGENT) -> bool:
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        robot_parser = RobotFileParser()
        robot_parser.set_url(robots_url)
        robot_parser.read()

        return robot_parser.can_fetch(user_agent, url)
    except Exception:
        return True


def make_request(
    url: str,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = MAX_RETRIES
) -> requests.Response:
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "close",
    }

    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True
            )

            if response.status_code in {429, 500, 502, 503, 504}:
                if attempt < retries:
                    backoff = min((2 ** attempt) + random.uniform(0.5, 2.0), 12)
                    time.sleep(backoff)
                    continue

            response.raise_for_status()

            content_type = response.headers.get("content-type", "").lower()

            if (
                "text/html" not in content_type
                and "application/xhtml+xml" not in content_type
            ):
                raise ValueError(f"Unsupported content type: {content_type or 'unknown'}")

            return response

        except Exception as exc:
            last_error = exc

            if attempt < retries:
                backoff = min((2 ** attempt) + random.uniform(0.5, 2.0), 12)
                time.sleep(backoff)

    if last_error is not None:
        raise last_error

    raise RuntimeError("Request failed.")


def clean_text(value: Any) -> str:
    if not value:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def extract_emails(text: str) -> list[str]:
    if not text:
        return []

    pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    return sorted(set(re.findall(pattern, text)))


def extract_phone_like_values(text: str) -> list[str]:
    if not text:
        return []

    pattern = r"(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}"
    values = re.findall(pattern, text)
    return sorted(set(clean_text(value) for value in values if clean_text(value)))


def extract_tables(soup: BeautifulSoup) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []

    for table_index, table in enumerate(soup.find_all("table"), start=1):
        if not isinstance(table, Tag):
            continue

        rows: list[list[str]] = []

        for tr in table.find_all("tr"):
            if not isinstance(tr, Tag):
                continue

            cells = tr.find_all(["th", "td"])
            row = [clean_text(cell.get_text(" ", strip=True)) for cell in cells]

            if any(row):
                rows.append(row)

        if rows:
            tables.append({
                "table_number": table_index,
                "rows": rows
            })

    return tables


def get_attr_as_string(tag: Tag, attr_name: str) -> str:
    value = tag.get(attr_name, "")

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return " ".join(str(item) for item in value)

    return ""


def find_canonical_url(soup: BeautifulSoup, page_url: str) -> str:
    for link_tag in soup.find_all("link"):
        if not isinstance(link_tag, Tag):
            continue

        rel_value = link_tag.get("rel")

        if isinstance(rel_value, list):
            rel_values = [str(item).lower() for item in rel_value]

            if "canonical" in rel_values:
                href_value = get_attr_as_string(link_tag, "href")
                return urljoin(page_url, href_value) if href_value else ""

        elif isinstance(rel_value, str):
            if "canonical" in rel_value.lower().split():
                href_value = get_attr_as_string(link_tag, "href")
                return urljoin(page_url, href_value) if href_value else ""

    return ""


def extract_page_data(url: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = clean_text(soup.title.string) if soup.title and soup.title.string else ""

    meta_description = ""
    description_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})

    if isinstance(description_tag, Tag):
        meta_description = clean_text(get_attr_as_string(description_tag, "content"))

    canonical = find_canonical_url(soup, url)

    headings = {
        "h1": [clean_text(h.get_text(" ", strip=True)) for h in soup.find_all("h1")],
        "h2": [clean_text(h.get_text(" ", strip=True)) for h in soup.find_all("h2")],
        "h3": [clean_text(h.get_text(" ", strip=True)) for h in soup.find_all("h3")],
    }

    paragraphs = [
        clean_text(p.get_text(" ", strip=True))
        for p in soup.find_all("p")
        if clean_text(p.get_text(" ", strip=True))
    ]

    links: list[dict[str, Any]] = []
    seen_links: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        if not isinstance(anchor, Tag):
            continue

        href_value = get_attr_as_string(anchor, "href")

        if not href_value:
            continue

        href = urljoin(url, href_value)
        text = clean_text(anchor.get_text(" ", strip=True))

        if not is_valid_http_url(href):
            continue

        if href in seen_links:
            continue

        seen_links.add(href)

        links.append({
            "text": text,
            "url": href,
            "internal": is_same_domain(url, href)
        })

    images: list[dict[str, str]] = []
    seen_images: set[str] = set()

    for image in soup.find_all("img"):
        if not isinstance(image, Tag):
            continue

        src_value = (
            get_attr_as_string(image, "src")
            or get_attr_as_string(image, "data-src")
            or get_attr_as_string(image, "data-lazy-src")
        )

        if not src_value:
            continue

        image_url = urljoin(url, src_value)

        if image_url in seen_images:
            continue

        seen_images.add(image_url)

        images.append({
            "alt": clean_text(get_attr_as_string(image, "alt")),
            "url": image_url
        })

    page_text = clean_text(soup.get_text(" ", strip=True))

    return {
        "url": url,
        "title": title,
        "meta_description": meta_description,
        "canonical": canonical,
        "headings": headings,
        "paragraphs": paragraphs,
        "links": links,
        "images": images,
        "tables": extract_tables(soup),
        "emails": extract_emails(page_text),
        "phone_like_values": extract_phone_like_values(page_text),
        "word_count": len(page_text.split()) if page_text else 0,
        "character_count": len(page_text),
        "text_preview": page_text[:2500]
    }


def scrape_single_page(url: str, options: dict[str, Any]) -> dict[str, Any]:
    normalized_url = normalize_url(url)

    if not normalized_url:
        raise ValueError("Invalid URL.")

    user_agent = str(options.get("user_agent") or DEFAULT_USER_AGENT)
    timeout = clamp_int(options.get("timeout"), DEFAULT_TIMEOUT, 3, 60)
    respect_robots = bool(options.get("respect_robots", True))
    retries = clamp_int(options.get("retries"), MAX_RETRIES, 1, 5)

    if respect_robots and not can_fetch_url(normalized_url, user_agent):
        raise PermissionError("Blocked by robots.txt for this user agent.")

    response = make_request(
        normalized_url,
        user_agent=user_agent,
        timeout=timeout,
        retries=retries
    )

    page_data = extract_page_data(response.url, response.text)
    page_data["status_code"] = response.status_code
    page_data["final_url"] = response.url

    return page_data


def crawl_site(start_url: str, options: dict[str, Any]) -> dict[str, Any]:
    normalized_start_url = normalize_url(start_url)

    if not normalized_start_url:
        raise ValueError("Invalid start URL.")

    max_pages = clamp_int(
        options.get("max_pages"),
        10,
        1,
        MAX_HARD_LIMIT_PAGES
    )

    max_depth = clamp_int(
        options.get("max_depth"),
        1,
        0,
        MAX_HARD_LIMIT_DEPTH
    )

    user_agent = str(options.get("user_agent") or DEFAULT_USER_AGENT)
    respect_robots = bool(options.get("respect_robots", True))

    queue: deque[tuple[str, int]] = deque([(normalized_start_url, 0)])
    visited: set[str] = set()
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    while queue and len(results) < max_pages:
        current_url, depth = queue.popleft()

        if current_url in visited:
            continue

        visited.add(current_url)

        try:
            if respect_robots and not can_fetch_url(current_url, user_agent):
                errors.append({
                    "url": current_url,
                    "error": "Blocked by robots.txt"
                })
                continue

            page_number = len(results) + 1

            if page_number > 1:
                human_pause(options, page_number=page_number)

            data = scrape_single_page(current_url, options)
            results.append(data)

            if depth < max_depth:
                for link in data.get("links", []):
                    next_url = normalize_url(str(link.get("url", "")))

                    if (
                        next_url
                        and next_url not in visited
                        and is_same_domain(normalized_start_url, next_url)
                    ):
                        queue.append((next_url, depth + 1))

        except Exception as exc:
            errors.append({
                "url": current_url,
                "error": str(exc)
            })

    return {
        "start_url": normalized_start_url,
        "pages_scraped": len(results),
        "pages_attempted": len(visited),
        "max_pages": max_pages,
        "max_depth": max_depth,
        "human_mode": bool(options.get("human_mode", True)),
        "results": results,
        "errors": errors
    }


def iter_scrape(url: str, mode: str, options: dict[str, Any]):
    """Generator that yields SSE-compatible dicts for streaming scrape progress."""
    import json as _json

    if mode == "crawl":
        normalized_start_url = normalize_url(url)

        if not normalized_start_url:
            yield {"event": "log", "message": "Invalid start URL."}
            return

        max_pages = clamp_int(options.get("max_pages"), 10, 1, MAX_HARD_LIMIT_PAGES)
        max_depth = clamp_int(options.get("max_depth"), 1, 0, MAX_HARD_LIMIT_DEPTH)
        user_agent = str(options.get("user_agent") or DEFAULT_USER_AGENT)
        respect_robots = bool(options.get("respect_robots", True))

        yield {"event": "log", "message": f"Starting crawl of {normalized_start_url} (max_pages={max_pages}, max_depth={max_depth})"}

        queue: deque[tuple[str, int]] = deque([(normalized_start_url, 0)])
        visited: set[str] = set()
        results: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []

        while queue and len(results) < max_pages:
            current_url, depth = queue.popleft()

            if current_url in visited:
                continue

            visited.add(current_url)
            page_num = len(results) + 1

            yield {"event": "page_start", "url": current_url, "page_num": page_num}

            try:
                if respect_robots and not can_fetch_url(current_url, user_agent):
                    err = "Blocked by robots.txt"
                    errors.append({"url": current_url, "error": err})
                    yield {"event": "page_error", "url": current_url, "error": err}
                    continue

                if page_num > 1:
                    human_pause(options, page_number=page_num)

                data = scrape_single_page(current_url, options)
                results.append(data)

                yield {
                    "event": "page_done",
                    "url": current_url,
                    "page_num": page_num,
                    "title": data.get("title", ""),
                    "word_count": data.get("word_count", 0)
                }

                if depth < max_depth:
                    for link in data.get("links", []):
                        next_url = normalize_url(str(link.get("url", "")))
                        if (
                            next_url
                            and next_url not in visited
                            and is_same_domain(normalized_start_url, next_url)
                        ):
                            queue.append((next_url, depth + 1))

            except Exception as exc:
                errors.append({"url": current_url, "error": str(exc)})
                yield {"event": "page_error", "url": current_url, "error": str(exc)}

        result = {
            "start_url": normalized_start_url,
            "pages_scraped": len(results),
            "pages_attempted": len(visited),
            "max_pages": max_pages,
            "max_depth": max_depth,
            "human_mode": bool(options.get("human_mode", True)),
            "results": results,
            "errors": errors
        }

        yield {"event": "log", "message": f"Crawl complete. {len(results)} page(s) scraped."}
        yield {"event": "complete", "data": result}

    else:
        # single page mode
        normalized_url = normalize_url(url)

        if not normalized_url:
            yield {"event": "log", "message": "Invalid URL."}
            return

        yield {"event": "log", "message": f"Scraping single page: {normalized_url}"}
        yield {"event": "page_start", "url": normalized_url, "page_num": 1}

        try:
            page = scrape_single_page(normalized_url, options)

            yield {
                "event": "page_done",
                "url": normalized_url,
                "page_num": 1,
                "title": page.get("title", ""),
                "word_count": page.get("word_count", 0)
            }

            result = {
                "start_url": normalized_url,
                "pages_scraped": 1,
                "pages_attempted": 1,
                "max_pages": 1,
                "max_depth": 0,
                "human_mode": bool(options.get("human_mode", True)),
                "results": [page],
                "errors": []
            }

            yield {"event": "log", "message": "Scrape complete. 1 page scraped."}
            yield {"event": "complete", "data": result}

        except Exception as exc:
            yield {"event": "page_error", "url": normalized_url, "error": str(exc)}


@app.route("/api/scrape/stream", methods=["POST"])
def api_scrape_stream():
    payload = request.get_json(force=True)

    url = payload.get("url", "")
    mode = payload.get("mode", "single")

    options = {
        "max_pages": payload.get("max_pages", 10),
        "max_depth": payload.get("max_depth", 1),
        "delay": payload.get("delay", 1),
        "min_delay": payload.get("min_delay", DEFAULT_MIN_DELAY),
        "max_delay": payload.get("max_delay", DEFAULT_MAX_DELAY),
        "long_pause_every": payload.get("long_pause_every", 6),
        "long_pause_min": payload.get("long_pause_min", 4),
        "long_pause_max": payload.get("long_pause_max", 8),
        "timeout": payload.get("timeout", DEFAULT_TIMEOUT),
        "retries": payload.get("retries", MAX_RETRIES),
        "user_agent": payload.get("user_agent", DEFAULT_USER_AGENT),
        "respect_robots": payload.get("respect_robots", True),
        "human_mode": payload.get("human_mode", True),
    }

    def generate():
        try:
            for event_dict in iter_scrape(url, mode, options):
                yield f"data: {json.dumps(event_dict)}\n\n"
        except Exception as exc:
            error_dict = {"event": "page_error", "url": url, "error": str(exc)}
            yield f"data: {json.dumps(error_dict)}\n\n"

    response = Response(generate(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


def flatten_for_csv(crawl_result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    pages = crawl_result.get("results", [])

    for page in pages:
        headings = page.get("headings", {})

        h1 = " | ".join(headings.get("h1", []))
        h2 = " | ".join(headings.get("h2", []))
        emails = " | ".join(page.get("emails", []))
        phones = " | ".join(page.get("phone_like_values", []))
        links = " | ".join(link.get("url", "") for link in page.get("links", [])[:50])
        images = " | ".join(img.get("url", "") for img in page.get("images", [])[:50])

        rows.append({
            "url": page.get("url", ""),
            "final_url": page.get("final_url", ""),
            "status_code": page.get("status_code", ""),
            "title": page.get("title", ""),
            "meta_description": page.get("meta_description", ""),
            "h1": h1,
            "h2": h2,
            "word_count": page.get("word_count", 0),
            "character_count": page.get("character_count", 0),
            "emails": emails,
            "phone_like_values": phones,
            "links_sample": links,
            "images_sample": images,
            "text_preview": page.get("text_preview", "")
        })

    return rows


def build_markdown(crawl_result: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append(f"# {APP_NAME} Export")
    lines.append("")
    lines.append(f"Start URL: {crawl_result.get('start_url', '')}")
    lines.append(f"Pages scraped: {crawl_result.get('pages_scraped', 0)}")
    lines.append(f"Human mode: {crawl_result.get('human_mode', True)}")
    lines.append("")

    for index, page in enumerate(crawl_result.get("results", []), start=1):
        lines.append(f"## {index}. {page.get('title') or page.get('url')}")
        lines.append("")
        lines.append(f"- URL: {page.get('url', '')}")
        lines.append(f"- Final URL: {page.get('final_url', '')}")
        lines.append(f"- Status: {page.get('status_code', '')}")
        lines.append(f"- Words: {page.get('word_count', 0)}")
        lines.append("")

        if page.get("meta_description"):
            lines.append("### Description")
            lines.append(str(page["meta_description"]))
            lines.append("")

        h1_values = page.get("headings", {}).get("h1", [])
        h2_values = page.get("headings", {}).get("h2", [])

        if h1_values:
            lines.append("### H1")
            for heading in h1_values:
                lines.append(f"- {heading}")
            lines.append("")

        if h2_values:
            lines.append("### H2")
            for heading in h2_values[:20]:
                lines.append(f"- {heading}")
            lines.append("")

        if page.get("paragraphs"):
            lines.append("### Paragraph Samples")
            for paragraph in page["paragraphs"][:8]:
                lines.append(f"- {paragraph}")
            lines.append("")

        if page.get("emails"):
            lines.append("### Emails")
            for email in page["emails"]:
                lines.append(f"- {email}")
            lines.append("")

        if page.get("phone_like_values"):
            lines.append("### Phone-like Values")
            for phone in page["phone_like_values"]:
                lines.append(f"- {phone}")
            lines.append("")

        lines.append("---")
        lines.append("")

    if crawl_result.get("errors"):
        lines.append("## Errors")
        for error in crawl_result["errors"]:
            lines.append(f"- {error.get('url')}: {error.get('error')}")
        lines.append("")

    return "\n".join(lines)


@app.route("/")
def home():
    return render_template("index.html", app_name=APP_NAME)


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    try:
        payload = request.get_json(force=True)

        url = payload.get("url", "")
        mode = payload.get("mode", "single")

        options = {
            "max_pages": payload.get("max_pages", 10),
            "max_depth": payload.get("max_depth", 1),
            "delay": payload.get("delay", 1),
            "min_delay": payload.get("min_delay", DEFAULT_MIN_DELAY),
            "max_delay": payload.get("max_delay", DEFAULT_MAX_DELAY),
            "long_pause_every": payload.get("long_pause_every", 6),
            "long_pause_min": payload.get("long_pause_min", 4),
            "long_pause_max": payload.get("long_pause_max", 8),
            "timeout": payload.get("timeout", DEFAULT_TIMEOUT),
            "retries": payload.get("retries", MAX_RETRIES),
            "user_agent": payload.get("user_agent", DEFAULT_USER_AGENT),
            "respect_robots": payload.get("respect_robots", True),
            "human_mode": payload.get("human_mode", True),
        }

        if mode == "crawl":
            result = crawl_site(url, options)
        else:
            page = scrape_single_page(url, options)

            result = {
                "start_url": normalize_url(url),
                "pages_scraped": 1,
                "pages_attempted": 1,
                "max_pages": 1,
                "max_depth": 0,
                "human_mode": bool(options.get("human_mode", True)),
                "results": [page],
                "errors": []
            }

        return jsonify({
            "ok": True,
            "data": result
        })

    except PermissionError as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
            "error_type": "permission"
        }), 403

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
            "error_type": "general"
        }), 400


@app.route("/api/export/json", methods=["POST"])
def export_json():
    payload = request.get_json(force=True)
    data = payload.get("data", {})

    content = json.dumps(data, indent=2, ensure_ascii=False)

    return Response(
        content,
        mimetype="application/json",
        headers={
            "Content-Disposition": "attachment; filename=scrape-export.json"
        }
    )


@app.route("/api/export/csv", methods=["POST"])
def export_csv():
    payload = request.get_json(force=True)
    data = payload.get("data", {})

    rows = flatten_for_csv(data)

    output = io.StringIO()

    fieldnames = [
        "url",
        "final_url",
        "status_code",
        "title",
        "meta_description",
        "h1",
        "h2",
        "word_count",
        "character_count",
        "emails",
        "phone_like_values",
        "links_sample",
        "images_sample",
        "text_preview"
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for row in rows:
        writer.writerow(row)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=scrape-export.csv"
        }
    )


@app.route("/api/export/markdown", methods=["POST"])
def export_markdown():
    payload = request.get_json(force=True)
    data = payload.get("data", {})

    markdown = build_markdown(data)

    return Response(
        markdown,
        mimetype="text/markdown",
        headers={
            "Content-Disposition": "attachment; filename=scrape-export.md"
        }
    )


@app.errorhandler(404)
def not_found(_):
    return jsonify({
        "ok": False,
        "error": "Endpoint not found."
    }), 404


if __name__ == "__main__":
    app.run(debug=True)