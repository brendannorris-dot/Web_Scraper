#!/usr/bin/env python3
"""
MarketScraper Pro - CLI
A standalone command-line interface for the web scraper.
"""
import argparse
import json
import sys
from typing import Any

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
GRAY = "\033[90m"


def color(text: str, code: str) -> str:
    return f"{code}{text}{RESET}"


def print_header() -> None:
    print(color("╔══════════════════════════════════════╗", CYAN))
    print(color("║      MarketScraper Pro - CLI         ║", CYAN))
    print(color("╚══════════════════════════════════════╝", CYAN))
    print()


def format_summary(result: dict[str, Any], mode: str) -> None:
    pages = result.get("results", [])
    errors = result.get("errors", [])
    total = len(pages)

    for index, page in enumerate(pages, start=1):
        print(color(f"━━━ Page {index}/{total} ━━━", CYAN))

        title = page.get("title") or "Untitled"
        url = page.get("url", "")
        word_count = page.get("word_count", 0)

        links = page.get("links", [])
        internal_links = sum(1 for link in links if link.get("internal"))
        external_links = len(links) - internal_links

        headings = page.get("headings", {})
        h1_list = headings.get("h1", [])
        h1_text = h1_list[0] if h1_list else ""

        print(f"Title: {color(title, BOLD)}")
        print(f"URL:   {color(url, CYAN)}")
        print(f"Words: {color(str(word_count), GREEN)}")
        print(f"Links: {len(links)} ({internal_links} internal, {external_links} external)")

        if h1_text:
            print(f"H1:    {h1_text}")

        emails = page.get("emails", [])
        phones = page.get("phone_like_values", [])

        if emails:
            print(f"Emails: {', '.join(emails)}")

        if phones:
            print(f"Phones: {', '.join(phones)}")

        print()

    if errors:
        print(color("Errors:", RED))
        for error in errors:
            print(color(f"  - {error.get('url')}: {error.get('error')}", RED))
        print()

    pages_scraped = result.get("pages_scraped", total)
    print(color(f"[✓] Scrape complete. {pages_scraped} page(s) scraped.", GREEN))


def build_options(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "max_pages": args.max_pages,
        "max_depth": args.max_depth,
        "timeout": args.timeout,
        "retries": args.retries,
        "respect_robots": not args.no_robots,
        "human_mode": not args.no_human_mode,
        "min_delay": args.min_delay,
        "max_delay": args.max_delay,
        "user_agent": args.user_agent,
    }


def main() -> None:
    from app import scrape_single_page, crawl_site, normalize_url, DEFAULT_USER_AGENT

    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="MarketScraper Pro - CLI scraping tool"
    )

    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--mode", choices=["single", "crawl"], default="single",
                        help="Scrape mode (default: single)")
    parser.add_argument("--max-pages", type=int, default=10, metavar="N",
                        help="Max pages to crawl (default: 10)")
    parser.add_argument("--max-depth", type=int, default=1, metavar="N",
                        help="Max crawl depth (default: 1)")
    parser.add_argument("--timeout", type=int, default=15, metavar="N",
                        help="Request timeout in seconds (default: 15)")
    parser.add_argument("--retries", type=int, default=3, metavar="N",
                        help="Number of retries (default: 3)")
    parser.add_argument("--no-robots", action="store_true",
                        help="Disable robots.txt checking")
    parser.add_argument("--no-human-mode", action="store_true",
                        help="Disable human pacing")
    parser.add_argument("--min-delay", type=float, default=1.0, metavar="F",
                        help="Minimum delay between requests in seconds (default: 1.0)")
    parser.add_argument("--max-delay", type=float, default=3.0, metavar="F",
                        help="Maximum delay between requests in seconds (default: 3.0)")
    parser.add_argument("--user-agent", type=str, default=DEFAULT_USER_AGENT, metavar="STR",
                        help="Custom user agent string")
    parser.add_argument("--output", choices=["summary", "json"], default="summary",
                        help="Output format (default: summary)")
    parser.add_argument("--output-file", type=str, default=None, metavar="PATH",
                        help="Save JSON output to file")

    args = parser.parse_args()

    print_header()

    options = build_options(args)

    robots_str = "no" if args.no_robots else "yes"
    human_str = "no" if args.no_human_mode else "yes"
    print(color(f"[*] Scraping: {args.url}", CYAN))
    print(color(f"[*] Mode: {args.mode} | Robots: {robots_str} | Human mode: {human_str}", CYAN))
    print()

    try:
        if args.mode == "crawl":
            print(color(f"[*] Starting crawl (max_pages={args.max_pages}, max_depth={args.max_depth})...", YELLOW))
            result = crawl_site(args.url, options)
        else:
            print(color("[*] Fetching single page...", YELLOW))
            page = scrape_single_page(args.url, options)
            normalized = normalize_url(args.url)
            result = {
                "start_url": normalized,
                "pages_scraped": 1,
                "pages_attempted": 1,
                "max_pages": 1,
                "max_depth": 0,
                "human_mode": not args.no_human_mode,
                "results": [page],
                "errors": []
            }

    except PermissionError as exc:
        print(color(f"[!] Permission denied: {exc}", RED), file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(color(f"[!] Error: {exc}", RED), file=sys.stderr)
        sys.exit(1)

    if args.output == "json" or args.output_file:
        json_output = json.dumps(result, indent=2, ensure_ascii=False)

        if args.output_file:
            try:
                with open(args.output_file, "w", encoding="utf-8") as fh:
                    fh.write(json_output)
                print(color(f"[✓] JSON saved to {args.output_file}", GREEN))
            except OSError as exc:
                print(color(f"[!] Could not write file: {exc}", RED), file=sys.stderr)
                sys.exit(1)

        if args.output == "json":
            print(json_output)
        else:
            format_summary(result, args.mode)
    else:
        format_summary(result, args.mode)


if __name__ == "__main__":
    main()