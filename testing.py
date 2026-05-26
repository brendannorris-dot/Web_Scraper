import time
import sys
import os
import asyncio
from urls import main as run_scraper


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def loading_screen():
    print("\n" + "="*40)
    print("---INITIALIZING WEB_SCRAPER_OS v2.6---")
    print("="*40 + "\n")
    time.sleep(0.3)

    boot_seq = [
        "Connecting to Matrix server...",
        "Injecting Soup Dependencies...",
        "Bypassing firewalls...",
        "Optimizing scraping protocols..."
    ]
    
    for sequence in boot_seq:
        print(f"[ ✅ ] {sequence}")
        time.sleep(0.3)

    print("\n")
    bar_length = 20
    for i in range(bar_length + 1):
        percent = int((i / bar_length) * 100)
        bar = "■" * i + " " * (bar_length - i)
        sys.stdout.write(f"\rLOADING DATA BUFFER: [{bar}] {percent}%")
        sys.stdout.flush()
        time.sleep(0.03)

    print("\n\n" + "-"*40)
    print("--------SYSTEM READY TO OPERATE--------")
    print("-"*40 + "\n")
    time.sleep(0.4)

    input(">>> PRESS ENTER TO ACCESS MENU <<<")
    clear_screen()


def execute_scraper(url, mode):
    url = str(url).strip() if url else ""
    if not url:
        print("[ ! ] Error: Invalid destination string context.")
        return "Invalid URL"

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    result = asyncio.run(run_scraper(url, mode))
    
    print("\n" + "="*40)
    print(f"[ SYSTEM ] Capture Log Summary: {result}")
    print("="*40)
    return result


if __name__ == "__main__":
    loading_screen()
    
    while True:
        print(f"---> MAIN MENU <---")
        print(f"1. Scan Single URL")
        print(f"2. Load Multi URLs (Batch Matrix Array)")
        print(f"3. Exit Matrix")
        
        selection = input("\nType Selection (1, 2, 3): ").strip()
        
        if selection == "1":
            clear_screen()
            url_input = input("Paste Target URL here: ").strip()
            
            if not url_input:
                print("\n[ ! ] Error: Target routing matrix cannot be blank.")
                time.sleep(1.2)
                clear_screen()
                continue

            clear_screen()
            print(f"--- TARGET DATA PROTOCOLS ({url_input}) ---")
            print("1. Structural Metadata (Title, Subtitles, Meta Descriptions)")
            print("2. Tabular Data Matrices (HTML Tables)")
            print("3. Hyperlink Infrastructure (URLs Map)")
            print("4. Graphical Content Strings (Image Asset Links)")
            print("5. Plain Text Stream (Paragraph Extractions)")
            
            mode_selection = input("\nSelect Data Protocol (1-5): ").strip()
            
            if mode_selection in ["1", "2", "3", "4", "5"]:
                clear_screen()
                execute_scraper(url_input, mode_selection)
                input("\n[ SYSTEM ] Cycle Complete. Press ENTER to return to Main Menu...")
                clear_screen()
            else:
                print("\n[ ! ] Unknown data string protocol. Aborting configuration...")
                time.sleep(1.2)
                clear_screen()
                
        elif selection == "2":
            clear_screen()
            print("--- INITIATING ARRAY QUEUE PROTOCOL ---")
            filename = "targets.txt"
            
            # Auto-create pipeline queue file if it doesn't exist
            if not os.path.exists(filename):
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("https://example.com\nhttps://httpbin.org\n")
                print(f"[ ! ] Pipeline text file '{filename}' was missing.")
                print("      A template has been generated. Paste your target URLs line-by-line inside it.")
                input("\nPress ENTER to return to menu...")
                clear_screen()
                continue
                
            # Read queue
            with open(filename, "r", encoding="utf-8") as f:
                urls_queue = [line.strip() for line in f if line.strip()]
                
            if not urls_queue:
                print(f"[ ! ] Matrix queue empty. Populated entries inside '{filename}' first.")
                input("\nPress ENTER to return...")
                clear_screen()
                continue
                
            print(f"[ SYSTEM ] {len(urls_queue)} destination nodes mapped in current matrix array stream.")
            print("\nSelect Global Extraction Protocol for batch array execution:")
            print("1. Metadata | 2. Tables | 3. Links | 4. Images | 5. Plain Text")
            mode_selection = input("\nSelect Protocol (1-5): ").strip()
            
            if mode_selection not in ["1", "2", "3", "4", "5"]:
                print("\n[ ! ] Invalid Matrix Protocol Selection. Aborting pipeline...")
                time.sleep(1.2)
                clear_screen()
                continue
                
            clear_screen()
            print(f"=== STARTING BATCH BROWSER MATRIX INTERACTION PROCESSING ({len(urls_queue)} TARGETS) ===")
            
            for index, batch_url in enumerate(urls_queue, 1):
                print(f"\n" + "•"*50)
                print(f"[ BATCH QUEUE NODE: {index}/{len(urls_queue)} ] -> {batch_url}")
                print("•"*50)
                
                # Execute node scraping step natively
                execute_scraper(batch_url, mode_selection)
                time.sleep(1.0)  # Safe buffer break cooling period between targets
                
            print("\n" + "="*50)
            print("[ SYSTEM GLOBAL ] Global Batch Execution Frame Chain Finalized.")
            print("="*50)
            input("\nPress ENTER to return to Main Menu...")
            clear_screen()
            
        elif selection == "3":
            clear_screen()
            print("Disconnecting from the Matrix... System Purged. Goodbye.")
            time.sleep(0.8)
            sys.exit()
            
        else:
            print("\n[ ! ] Invalid Selection... Resetting layout configuration...")
            time.sleep(1.2)
            clear_screen()