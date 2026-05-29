import asyncio
import json
import random
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# --- NETWORK ARCHITECTURE OPTIMIZATION ---
# Block heavy elements and trackers to decrease bandwidth consumption, 
# accelerate script execution, and cut proxy costs.
BLOCKED_RESOURCES = ["font", "media", "image"]
BLOCKED_TRACKERS = ["google-analytics", "doubleclick", "facebook", "hotjar", "tiktok", "bazaarvoice"]

async def optimize_network_routes(route, request):
    """Filters outgoing requests to optimize memory usage and processing speed."""
    url = request.url.lower()
    if request.resource_type in BLOCKED_RESOURCES or any(tracker in url for tracker in BLOCKED_TRACKERS):
        await route.abort()
    else:
        await route.continue_()

# --- REWRIING PARSING ENGINES ---
def get_meta(soup):
    title = soup.find('title').text.strip() if soup.find('title') else "N/A"
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    desc = meta_desc['content'] if meta_desc and 'content' in meta_desc.attrs else "N/A"
    return {"title": title, "description": desc}

def get_tables(soup):
    tables_data = []
    for idx, table in enumerate(soup.find_all('table')[:3]):
        headers = [th.text.strip() for th in table.find_all('th')]
        rows = [[td.text.strip() for td in tr.find_all('td')] for tr in table.find_all('tr') if tr.find_all('td')]
        tables_data.append({"index": idx + 1, "headers": headers, "rows": rows[:5]})
    return tables_data

def get_links(soup):
    return [link.get('href') for link in soup.find_all('a') if link.get('href') and not str(link.get('href')).startswith(('#', 'javascript:'))][:15]

def get_images(soup):
    return [{"src": img.get('src'), "alt": img.get('alt') or "No Alt"} for img in soup.find_all('img') if img.get('src')][:10]

def get_description(soup):
    possible = soup.find_all(['div', 'section', 'article'], class_=lambda x: x and any(w in str(x).lower() for w in ['description', 'detail', 'prod-info', 'about-the']))
    if not possible:
        possible = soup.find_all(['div', 'section', 'article'], id=lambda x: x and any(w in str(x).lower() for w in ['description', 'detail', 'about']))
    
    if possible:
        best = max(possible, key=lambda el: len(el.text))
        return "\n".join([line.strip() for line in best.get_text().splitlines() if line.strip()][:10])
        
    paragraphs = [p.text.strip() for p in soup.find_all('p') if len(p.text.strip()) > 40]
    return "\n\n".join(paragraphs[:4])

def get_schema(soup):
    script_tags = soup.find_all('script', type='application/ld+json')
    for tag in script_tags:
        try:
            if not tag.string: continue
            data = json.loads(tag.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if 'Product' in str(item.get('@type')):
                    offers = item.get('offers', {})
                    return {
                        "name": item.get('name'),
                        "brand": item.get('brand', {}).get('name') if isinstance(item.get('brand'), dict) else item.get('brand'),
                        "price": f"{offers.get('price')} {offers.get('priceCurrency', '')}" if isinstance(offers, dict) else "N/A",
                        "sku": item.get('sku') or item.get('mpn') or "N/A"
                    }
        except: continue
    return None

# --- ADVANCED HUMAN-INTERACTION ALGORITHMS ---
async def simulate_human_scroll(page):
    """Simulates realistic human scrolling with variable speeds and micro-pauses."""
    total_scrolls = random.randint(3, 5)
    for _ in range(total_scrolls):
        # Human step sizes vary dynamically
        scroll_distance = random.randint(300, 650)
        await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
        # Micro-pauses mirror a user processing visual elements on screen
        await asyncio.sleep(random.uniform(0.6, 1.4))

# --- MAIN BROWSING PIPELINE ---
async def main(url, target_mode, proxy_dict=None):
    url = str(url).strip() if url else ""
    if not url: return "Invalid destination target."
    if not url.startswith(("http://", "https://")): url = "https://" + url

    print("\n" + "═"*70)
    print(f"[ SYSTEM ] Booting Next-Gen Hardened Automation Cluster...")
    print("═"*70)

    async with async_playwright() as p:
        # Launching with specific arguments to dismantle Chromium's automation profiles
        browser = await p.chromium.launch(
            headless=True, # Hardened parameters safely authorize headless operations
            proxy=proxy_dict, # In production, pass high-quality residential rotating proxies here
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled", # Erases basic driver flags
                "--disable-web-security",
                "--disable-infobars",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-runtime-profiling"
            ]
        )
        
        # Configure the environment context to mimic a genuine consumer build
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            device_scale_factor=1,
            has_touch=False,
            is_mobile=False
        )
        
        page = await context.new_page()

        # Route filtering optimization activation
        await page.route("**/*", optimize_network_routes)

        # DEEP RUNTIME PATCHES (Erases structural DevTools artifacts anti-bots probe for)
        await page.add_init_script("""
            // 1. Kill the automated flag
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            
            // 2. Mock authentic Chrome ecosystem variables
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {} };
            
            // 3. Prevent structural prototype leaks used in browser profiling
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ? 
                Promise.resolve({ state: Notification.permission }) : 
                originalQuery(parameters)
            );
        """)

        # Modern HTTP request header mapping matching mainstream desktop architectures
        await page.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Upgrade-Insecure-Requests": "1",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"'
        })
        
        try:
            print(f"[ CONNECTING ] Dispatching network link connection sequence -> {url}")
            # Use 'commit' to immediately grab execution control once the server registers the link handshake
            response = await page.goto(url, wait_until="commit", timeout=30000)

            if response and response.status >= 400:
                print(f"[ EXPORT FAILED ] Server firewall denied access vector. HTTP Status: {response.status}")
                return f"Access Blocked: HTTP {response.status}"

            # Run human emulation module
            print("[ SIMULATING USER ] Triggering asymmetric heuristic browsing paths...")
            await simulate_human_scroll(page)

            # Extract fully rendered page state snapshot
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            print("[ METRICS CACHED ] Target HTML structure successfully mapped to local memory.\n")

            # --- ENGINE ROUTER SWITCH BOARD ---
            if target_mode == "1": return get_meta(soup)
            elif target_mode == "2": return get_tables(soup)
            elif target_mode == "3": return get_links(soup)
            elif target_mode == "4": return get_images(soup)
            elif target_mode == "5": return get_description(soup)
            elif target_mode == "6": return get_schema(soup)
            
            # --- THE "ALL" ENGINE DASHBOARD LAYOUT ---
            elif target_mode == "all":
                meta = get_meta(soup)
                schema = get_schema(soup)
                desc = get_description(soup)
                tables = get_tables(soup)
                links = get_links(soup)
                imgs = get_images(soup)

                print("\n" + "█▓▒░ EXTRACTED PLATFORM CONTENT SNAPSHOT ░▒▓█")
                print("═"*70)
                print(f"• TARGET ADDRESS: {url}")
                print(f"• PAGE TITLE:     {meta['title']}")
                print(f"• META SUMMARY:   {meta['description'][:150]}...")

                if schema:
                    print("\n" + "─── STRUCTURED DATA BLOCK (E-COMMERCE METADATA) ───")
                    print(f"• PRODUCT/ITEM:   {schema['name']}")
                    print(f"• BRAND/VENDOR:   {schema['brand']}")
                    print(f"• VALUE REVENUE:  {schema['price']}")
                    print(f"• IDENTIFIER SKU: {schema['sku']}")

                print("\n" + "─── TEXT CONTENT ARCHITECTURE (HEURISTIC SUMMARY) ───")
                print(desc[:750] if desc else "• Analysis yielded zero non-empty textual layouts.")

                if tables:
                    print(f"\n─── ISOLATED RENDERED ARRAYS ({len(tables)} Matrix Layouts Found) ───")
                    for t in tables:
                        print(f" -> Matrix Layout [{t['index']}] Headers: {', '.join(t['headers'][:5])}")
                        for r in t['rows'][:3]: print(f"    │ {' | '.join(r[:3])}")

                print("\n" + "─── MAPPED NETWORK ARCHITECTURE ROUTES ───")
                print(f"• Extracted Hyperlink Routings (Top {len(links)} Coordinates Mapped):")
                for link in links[:5]: print(f"  [Link Mapping] -> {link}")
                
                print(f"\n• Extracted Image Elements (Top {len(imgs)} Identifiers Registered):")
                for img in imgs[:3]: print(f"  [Media Buffer] {str(img['alt'])[:20]:<20} -> {str(img['src'])[:55]}...")
                print("═"*70 + "\n")

                return "Global Mapping Complete"

        except Exception as e:
            print(f" [ RUNTIME CRASH ] Fatal exception handled in engine workflow loop: {e}")
            return f"Error Trace: {e}"
        finally:
            await context.close()
            await browser.close()