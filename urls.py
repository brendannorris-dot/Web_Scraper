import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth 
from bs4 import BeautifulSoup
import time

async def main(url, target_mode):
    url = str(url).strip() if url else ""
    if not url:
        return "Invalid Data Payload passed to core engine."

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    print("\n" + "="*40)
    print(f"[ SYSTEM ] Booting Playwright Core Engine...")
    print("="*40)
    time.sleep(0.1)
    
    boot_seq = ["Deploying Ninjas...", "Heist Initiated...", "Breaking through Backdoors..."]
    for sequence in boot_seq:
        print(f"[ ✓ ] {sequence} complete...")
        time.sleep(0.1)

    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print(f"\n[ ... ] Intercepting Data Link Handshake: {url}")
            response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)

            # Smart Status Check Handler
            if response and response.status >= 400:
                print(f"[ SYSTEM WARNING ] Server blocked connection channel. HTTP Status: {response.status}")
                return f"HTTP Failure Code {response.status}"

            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            print("[ ✓ ] DOM Content Successfully Mirrored to Cache.\n")

            # --- MODE 1: METADATA & HEADERS ---
            if target_mode == "1":
                title_tag = soup.find('title')
                subtitle_tag = soup.find('h2', class_='subtitle')
                
                title_text = title_tag.text.strip() if title_tag else "None Detected"
                subtitle_text = subtitle_tag.text.strip() if subtitle_tag else "None Detected"
                
                title_components = [text for text in [title_text, subtitle_text] if text and text != "None Detected"]
                combined_title = " | ".join(title_components) if title_components else title_text
                
                print(f"[ ✓ ] Combined Page Title: {combined_title}")
                
                meta_tag = soup.find('meta', attrs={'name': 'description'})
                meta_desc = meta_tag['content'] if meta_tag and 'content' in meta_tag.attrs else "None Detected"
                print(f"[ ✓ ] Meta Description: {meta_desc}")
                return combined_title

            # --- MODE 2: HTML TABLES ---
            elif target_mode == "2":
                table = soup.find('table')
                if table:
                    print("[ SYSTEM ] Data Table Matched. Routing Arrays...\n")
                    headers_list = [th.text.strip() for th in table.find_all('th')]
                    if headers_list:
                        print(f"[ HEADERS ] {' | '.join(headers_list)}")
                        print("-" * 50)
                    
                    for row in table.find_all('tr'):
                        cells = row.find_all('td')
                        if cells:
                            row_data = [cell.text.strip() for cell in cells]
                            print(f"[ DATA ROW ] {' | '.join(row_data)}")
                else:
                    print("[ ERROR ] ❌ Target Layout doesn't contain standard HTML Tables. ❌")
                return "Table Array Complete"

            # --- MODE 3: ANCHOR LINKS ARRAY ---
            elif target_mode == "3":
                links = soup.find_all('a')
                count = 0
                print("[ CAPTURING HIGHWAY ARCHITECTURE MAP ]\n" + "-"*50)
                for link in links:
                    href = link.get('href')
                    text = link.text.strip()[:30]
                    
                    if isinstance(href, list):
                        href = "".join(href)
                    elif href is not None:
                        href = str(href)

                    if href and not href.startswith('#') and not href.startswith('javascript:'):
                        print(f"[ ROUTE ] {text:<32} -> {href}")
                        count += 1
                print(f"\n[ SYSTEM ] Total verified outbound routes mapped: {count}")
                return f"{count} Links Cached"

            # --- MODE 4: MEDIA EXTRACTIONS ---
            elif target_mode == "4":
                images = soup.find_all('img')
                count = 0
                print("[ SCANNING MEDIA FRAME BUFFERS ]\n" + "-"*50)
                for img in images:
                    img_url = img.get('src')
                    alt = (img.get('alt') or 'No Label Attribute')[:30]
                    
                    if isinstance(img_url, list):
                        img_url = "".join(img_url)
                    elif img_url is not None:
                        img_url = str(img_url)

                    if img_url:
                        print(f"[ FRAME ] Alt: {alt:<32} | Src: {img_url}")
                        count += 1
                print(f"\n[ SYSTEM ] Total media assets categorized: {count}")
                return f"{count} Image Strings Logged"

            # --- MODE 5: RAW TEXT PARAGRAPH BLOCKS ---
            elif target_mode == "5":
                paragraphs = soup.find_all('p')
                print("[ CAPTURING PLAIN TEXT PARAGRAPH BUFFER ]\n" + "-"*50)
                for p_tag in paragraphs:
                    text = p_tag.text.strip()
                    if len(text) > 20:
                        print(f">> {text}\n")
                return "Global Text Scan Complete"

        except Exception as e:
            print(f"[ SYSTEM ERROR ] Core Handshake Terminated Natively: {e}")
            return f"Error: {e}"
        finally: 
            await browser.close()