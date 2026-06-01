import asyncio
import time
import json
import os
import urllib.request
import urllib.parse
import jdatetime
from playwright.async_api import async_playwright

CITIES = {
    "Kerman": {"alibaba": "KER", "flytoday_en": "kerman", "flytoday_id": "167", "mrbilit_en": "kerman", "safarmarket": "14"},
    "Mashhad": {"alibaba": "MHD", "flytoday_en": "mashhad", "flytoday_id": "191", "mrbilit_en": "mashhad", "safarmarket": "2"},
    "Tehran": {"alibaba": "THR", "flytoday_en": "tehran", "flytoday_id": "101", "mrbilit_en": "tehran", "safarmarket": "1"},
    "Isfahan": {"alibaba": "IFN", "flytoday_en": "isfahan", "flytoday_id": "117", "mrbilit_en": "isfahan", "safarmarket": "13"},
    "Shiraz": {"alibaba": "SYZ", "flytoday_en": "shiraz", "flytoday_id": "143", "mrbilit_en": "shiraz", "safarmarket": "15"},
    "Yazd": {"alibaba": "AZD", "flytoday_en": "yazd", "flytoday_id": "165", "mrbilit_en": "yazd", "safarmarket": "16"},
    "Tabriz": {"alibaba": "TBZ", "flytoday_en": "tabriz", "flytoday_id": "109", "mrbilit_en": "tabriz", "safarmarket": "3"},
    "Ahvaz": {"alibaba": "AWZ", "flytoday_en": "ahvaz", "flytoday_id": "135", "mrbilit_en": "ahvaz", "safarmarket": "6"}
}

LOGS = {
    "en": {
        "config_ok": "[✓] Configuration file loaded successfully.",
        "config_err": "[!] Error: Configuration file '{file}' not found.",
        "telegram_err": "Telegram notification error: ",
        "searching_proxy": "[*] Auto-searching for an active Iran HTTP proxy...",
        "proxy_found": "[+] Active HTTP proxy found: ",
        "proxy_err": "[-] Error fetching proxies list: ",
        "date_err": "[-] Error analyzing dates: ",
        "checking": "[*] Checking {domain}...",
        "ticket_found": "-> {domain}: Ticket found! (Detected: {label})",
        "sold_out": "-> {domain}: Capacity is full (Sold Out).",
        "page_err": "-> {domain}: Page did not load properly (Proxy/IP might be blocked or broken).",
        "conn_err": "-> Error checking {domain}: ",
        "proxy_fail_detect": "[!] Possible HTTP proxy failure detected. Attempting to get a new proxy...",
        "waiting": "Waiting {interval} seconds for the next cycle...",
        "no_dates": "[-] Error: No valid dates found.",
        "no_proxy_warning": "⚠️ Warning: No working Iran HTTP proxy found! Alibaba and Raja checks might fail on foreign cloud server.",
        "proxy_fallback": "[*] Attempting fallback proxy source (ProxyScrape - HTTP only)...",
        "proxy_retry_pre_cycle": "[*] No active proxy in use. Re-attempting to establish a proxy connection before cycle starts..."
    },
    "fa": {
        "config_ok": "[✓] فایل تنظیمات با موفقیت بارگذاری شد.",
        "config_err": "[!] خطا: فایل تنظیمات '{file}' پیدا نشد. لطفاً آن را در کنار این فایل قرار دهید.",
        "telegram_err": "خطا در ارسال پیام تلگرام: ",
        "searching_proxy": "[*] در حال جستجوی خودکار پروکسی فعال و سریع HTTP ایران...",
        "proxy_found": "[+] پروکسی فعال HTTP پیدا شد: ",
        "proxy_err": "[-] خطا در دریافت لیست پروکسی: ",
        "date_err": "[-] خطا در تحلیل تاریخ‌ها: ",
        "checking": "[*] در حال بررسی {domain}...",
        "ticket_found": "-> {domain}: بلیت پیدا شد! (تشخیص: {label})",
        "sold_out": "-> {domain}: ظرفیت تکمیل است.",
        "page_err": "-> {domain}: صفحه به درستی لود نشد (احتمال خرابی یا مسدود بودن پروکسی/آی‌پی).",
        "conn_err": "-> خطا در بررسی {domain}: ",
        "proxy_fail_detect": "[!] تشخیص قطعی پروکسی HTTP. تلاش برای دریافت پروکسی جدید...",
        "waiting": "انتظار برای {interval} ثانیه تا بررسی بعدی...",
        "no_dates": "[-] خطایی رخ داد: تاریخ‌های معتبر وجود ندارند.",
        "no_proxy_warning": "⚠️ هشدار: پروکسی فعال HTTP ایران پیدا نشد! بررسی علی‌بابا و رجا روی سرور خارج احتمالاً با خطا مواجه خواهد شد.",
        "proxy_fallback": "[*] در حال تلاش برای دریافت پروکسی از منبع پشتیبان مخصوص پروتکل HTTP...",
        "proxy_retry_pre_cycle": "[*] پروکسی فعالی در حال استفاده نیست. در حال تلاش مجدد برای برقراری اتصال پروکسی پیش از شروع دور جدید..."
    }
}

class TrainWatcherEngine:
    def __init__(self, config_source="gui_config.json"):
        if isinstance(config_source, str):
            if os.path.exists(config_source):
                with open(config_source, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                raise FileNotFoundError(f"Config file '{config_source}' not found.")
        elif isinstance(config_source, dict):
            self.config = config_source
        else:
            raise TypeError("Config source must be a file path string or a dictionary.")

        self.lang = self.config.get("language", "en")
        print(self.get_log("config_ok"))

    def get_log(self, key, **kwargs):
        text = LOGS[self.lang].get(key, "")
        return text.format(**kwargs)

    async def send_notification(self, message, silent=False):
        print(f"\n[ALERT] {message}\n")
        token = self.config.get("telegram_token")
        chat_id = self.config.get("telegram_chat_id")
        if token and chat_id:
            text = urllib.parse.quote(message)
            silent_param = "&disable_notification=true" if silent else ""
            url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}{silent_param}"
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: urllib.request.urlopen(url, timeout=10))
            except Exception as e:
                print(self.get_log("telegram_err") + str(e))

    async def fetch_and_test_iran_proxy(self):
        print(self.get_log("searching_proxy"))
        loop = asyncio.get_event_loop()
        proxies = []
        
        try:
            api_url = "https://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=lastChecked&sort_type=desc&country=IR"
            def fetch_geonode():
                req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=8) as r:
                    return json.loads(r.read().decode())
            data = await loop.run_in_executor(None, fetch_geonode)
            for item in data.get("data", []):
                ip = item.get("ip")
                port = item.get("port")
                protocols = [p.lower() for p in item.get("protocols", [])]
                if "http" in protocols or "https" in protocols:
                    if ip and port:
                        proxies.append(f"http://{ip}:{port}")
        except Exception as e:
            print(f"[-] Geonode source warning: {e}")

        if not proxies:
            try:
                print(self.get_log("proxy_fallback"))
                fallback_url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=IR&ssl=all&anonymity=all"
                def fetch_fallback():
                    req = urllib.request.Request(fallback_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=8) as r:
                        return r.read().decode().strip().split("\n")
                raw_proxies = await loop.run_in_executor(None, fallback_url)
                for p in raw_proxies:
                    p = p.strip()
                    if p and ":" in p:
                        proxies.append(f"http://{p}")
            except Exception as e:
                print(f"[-] ProxyScrape source warning: {e}")

        if not proxies:
            return None

        def test(p_url):
            try:
                proxy_handler = urllib.request.ProxyHandler({'http': p_url, 'https': p_url})
                opener = urllib.request.build_opener(proxy_handler)
                with opener.open("https://httpbin.org/ip", timeout=4) as r:
                    return r.status == 200
            except:
                return False

        print(f"[*] Testing {len(proxies[:25])} gathered HTTP proxies...")
        for p in proxies[:25]:
            is_working = await loop.run_in_executor(None, test, p)
            if is_working:
                print(self.get_log("proxy_found") + p)
                return p
        return None

    def get_date_list(self):
        start_str = self.config["start_date"]
        end_str = self.config["end_date"] if self.config.get("enable_date_range", False) else start_str
        try:
            start_j = jdatetime.date(*map(int, start_str.split('-')))
            end_j = jdatetime.date(*map(int, end_str.split('-')))
            dates = []
            curr = start_j
            while curr <= end_j:
                dates.append((curr.strftime("%Y-%m-%d"), curr.togregorian().strftime("%Y-%m-%d")))
                curr += jdatetime.timedelta(days=1)
            return dates
        except Exception as e:
            print(self.get_log("date_err") + str(e))
            return []

    def resolve_custom_url(self, raw_url, jalali, greg, origin_data, dest_data):
        url = raw_url.strip().lower()
        if url.startswith("http://"): url = url[7:]
        elif url.startswith("https://"): url = url[8:]
        if url.startswith("www."): url = url[4:]
        domain = url.split("/")[0] if "/" in url else url

        if domain in ["mrbilit.com", "mrbilit.ir"]:
            resolved = f"https://mrbilit.com/trains/{origin_data['mrbilit_en']}-{dest_data['mrbilit_en']}?departureDate={jalali}"
        elif domain in ["alibaba.ir", "alibaba.com"]:
            resolved = f"https://www.alibaba.ir/train/{origin_data['alibaba']}-{dest_data['alibaba']}?adult=1&child=0&infant=0&departing={jalali}&ticketType=Family&isExclusive=false"
        elif domain == "flytoday.ir":
            resolved = f"https://www.flytoday.ir/train/{origin_data['flytoday_en']}-{dest_data['flytoday_en']}?origin={origin_data['flytoday_id']}&destination={dest_data['flytoday_id']}&departureDate={greg}&adt=1"
        elif domain == "raja.ir":
            jalali_no_dash = jalali.replace("-", "")
            fs = origin_data['flytoday_id']
            ts = dest_data['flytoday_id']
            desc_encoded = urllib.parse.quote(f"قطار {self.config['origin']} به {self.config['destination']} - رجا")
            resolved = f"https://raja.ir/search?adult=1&child=0&infant=0&movetype=1&ischarter=false&fs={fs}&ts={ts}&godate={jalali_no_dash}&tickettype=Family&returndate=&numberpassenger=1&mode=Train&desctravel={desc_encoded}"
        elif domain == "safarmarket.com":
            orig_sm = origin_data.get("safarmarket", "14")
            dest_sm = dest_data.get("safarmarket", "2")
            resolved = f"https://safarmarket.com/trains/{orig_sm}-{dest_sm}/{greg}/0/1adults/0children/0infants/non_coupe/NORMAL"
        else:
            resolved = raw_url.replace("{jalali}", jalali).replace("{greg}", greg)
        
        if not resolved.startswith("http://") and not resolved.startswith("https://"):
            resolved = "https://" + resolved
        return resolved

    async def check_detector(self, page, item):
        word = item["query"]
        is_css = item.get("is_css", False)
        try:
            if is_css:
                if await page.locator(word).filter(visible=True).count() > 0:
                    return True
            else:
                elements = page.get_by_text(word, exact=False).filter(visible=True)
                for i in range(await elements.count()):
                    text = await elements.nth(i).inner_text()
                    if text and len(text.strip()) <= 50:
                        return True
        except:
            pass
        return False

    async def start(self):
        origin_data = CITIES[self.config["origin"]]
        dest_data = CITIES[self.config["destination"]]
        interval = int(self.config.get("refresh_interval", "300"))
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            direct_context = await browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page_direct = await direct_context.new_page()
            
            proxy_url = None
            proxy_context = None
            page_proxy = None
            proxy_failures = 0

            async def refresh_proxy_connection():
                nonlocal proxy_url, proxy_context, page_proxy, proxy_failures
                if proxy_context and proxy_context != direct_context:
                    try:
                        await page_proxy.close()
                        await proxy_context.close()
                    except:
                        pass
                
                p_url = await self.fetch_and_test_iran_proxy()
                if p_url:
                    proxy_url = p_url
                    proxy_context = await browser.new_context(
                        viewport={'width': 1280, 'height': 800},
                        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        proxy={"server": p_url}
                    )
                    page_proxy = await proxy_context.new_page()
                    proxy_failures = 0
                    
                    success_msg = f"🟢 Connected to active Iran HTTP proxy: {p_url}"
                    print(success_msg)
                    if self.config.get("send_errors_to_telegram", True):
                        await self.send_notification(success_msg, silent=True)
                else:
                    proxy_url = None
                    proxy_context = direct_context
                    page_proxy = await direct_context.new_page()
                    proxy_failures = 0
                    
                    warning_msg = self.get_log("no_proxy_warning")
                    print(warning_msg)
                    if self.config.get("send_errors_to_telegram", True):
                        await self.send_notification(warning_msg, silent=True)

            if self.config.get("use_proxy", True):
                await refresh_proxy_connection()
            else:
                proxy_url = None
                proxy_context = direct_context
                page_proxy = await direct_context.new_page()
                print("[*] Running in direct connection mode (No proxy).")
            
            while True:
                dates = self.get_date_list()
                if not dates:
                    print(self.get_log("no_dates"))
                    break
                    
                if self.config.get("use_proxy", True) and proxy_url is None:
                    print(self.get_log("proxy_retry_pre_cycle"))
                    await refresh_proxy_connection()
                
                for jalali, greg in dates:
                    if self.lang == "en":
                        print(f"\n--- Starting new cycle for date {jalali} at {time.strftime('%H:%M:%S')} ---")
                    else:
                        print(f"\n--- شروع دور جدید بررسی تاریخ {jalali} در ساعت {time.strftime('%H:%M:%S')} ---")
                    
                    # Alibaba Check
                    if self.config.get("enable_alibaba", True):
                        url_ali = f"https://www.alibaba.ir/train/{origin_data['alibaba']}-{dest_data['alibaba']}?adult=1&child=0&infant=0&departing={jalali}&ticketType=Family"
                        print(self.get_log("checking", domain="Alibaba"))
                        try:
                            await page_proxy.goto(url_ali, wait_until="domcontentloaded", timeout=25000)
                            await page_proxy.wait_for_timeout(3000)
                            
                            found = False
                            for item in self.config.get("detect_words", []):
                                if await self.check_detector(page_proxy, item):
                                    print(self.get_log("ticket_found", domain="Alibaba", label=item['label']))
                                    await self.send_notification(f"Alibaba ticket found for {jalali}!\nLink: {url_ali}", silent=False)
                                    found = True
                                    break
                            if not found:
                                print(self.get_log("sold_out", domain="Alibaba"))
                            proxy_failures = 0
                        except Exception as e:
                            err_msg = self.get_log("conn_err", domain="Alibaba") + str(e)
                            print(f"-> {err_msg}")
                            if self.config.get("send_errors_to_telegram", True):
                                await self.send_notification(f"⚠️ {err_msg}\nLink: {url_ali}", silent=True)
                            proxy_failures += 1
                    
                    if proxy_failures >= 3 and self.config.get("use_proxy", True):
                        print(self.get_log("proxy_fail_detect"))
                        await refresh_proxy_connection()

                    # FlyToday Check
                    if self.config.get("enable_flytoday", True):
                        url_fly = f"https://www.flytoday.ir/train/{origin_data['flytoday_en']}-{dest_data['flytoday_en']}?origin={origin_data['flytoday_id']}&destination={dest_data['flytoday_id']}&departureDate={greg}&adt=1"
                        print(self.get_log("checking", domain="FlyToday"))
                        try:
                            await page_direct.goto(url_fly, wait_until="domcontentloaded", timeout=25000)
                            await page_direct.wait_for_timeout(3000)
                            found = False
                            for item in self.config.get("detect_words", []):
                                if await self.check_detector(page_direct, item):
                                    print(self.get_log("ticket_found", domain="FlyToday", label=item['label']))
                                    await self.send_notification(f"FlyToday ticket found for {greg}!\nLink: {url_fly}", silent=False)
                                    found = True
                                    break
                            if not found:
                                print(self.get_log("sold_out", domain="FlyToday"))
                        except Exception as e:
                            err_msg = self.get_log("conn_err", domain="FlyToday") + str(e)
                            print(f"-> {err_msg}")
                            if self.config.get("send_errors_to_telegram", True):
                                await self.send_notification(f"⚠️ {err_msg}", silent=True)

                    # MrBilit Check
                    if self.config.get("enable_mrbilit", True):
                        url_bil = f"https://mrbilit.com/trains/{origin_data['mrbilit_en']}-{dest_data['mrbilit_en']}?departureDate={jalali}"
                        print(self.get_log("checking", domain="MrBilit"))
                        try:
                            await page_direct.goto(url_bil, wait_until="domcontentloaded", timeout=25000)
                            await page_direct.wait_for_timeout(3000)
                            found = False
                            for item in self.config.get("detect_words", []):
                                if await self.check_detector(page_direct, item):
                                    print(self.get_log("ticket_found", domain="MrBilit", label=item['label']))
                                    await self.send_notification(f"MrBilit ticket found for {jalali}!\nLink: {url_bil}", silent=False)
                                    found = True
                                    break
                            if not found:
                                print(self.get_log("sold_out", domain="MrBilit"))
                        except Exception as e:
                            err_msg = self.get_log("conn_err", domain="MrBilit") + str(e)
                            print(f"-> {err_msg}")
                            if self.config.get("send_errors_to_telegram", True):
                                await self.send_notification(f"⚠️ {err_msg}", silent=True)

                    # Custom URLs Check
                    for i, item in enumerate(self.config.get("custom_urls", [])):
                        url = item["url"]
                        is_enabled = self.config.get("custom_urls_state", {}).get(url, True)
                        if not is_enabled:
                            continue
                            
                        domain = url.strip().lower().split("/")[0]
                        resolved_url = self.resolve_custom_url(url, jalali, greg, origin_data, dest_data)
                        print(self.get_log("checking", domain=domain))
                        
                        target_page = proxy_context.new_page() if domain == "raja.ir" else page_direct
                        
                        try:
                            if domain in ["raja.ir", "safarmarket.com"] and domain not in target_page.url:
                                try:
                                    await target_page.goto(f"https://{domain}", wait_until="domcontentloaded", timeout=25000)
                                    await asyncio.sleep(2)
                                except:
                                    pass
                                    
                            await target_page.goto(resolved_url, wait_until="domcontentloaded", timeout=25000)
                            await target_page.wait_for_timeout(3000)
                            
                            found = False
                            for d_item in self.config.get("detect_words", []):
                                if await self.check_detector(target_page, d_item):
                                    print(self.get_log("ticket_found", domain=domain, label=d_item['label']))
                                    await self.send_notification(f"{domain} ticket found for {jalali}!\nLink: {resolved_url}", silent=False)
                                    found = True
                                    break
                            if not found:
                                print(self.get_log("sold_out", domain=domain))
                        except Exception as e:
                            err_msg = self.get_log("conn_err", domain=domain) + str(e)
                            print(f"-> {err_msg}")
                            if self.config.get("send_errors_to_telegram", True):
                                await self.send_notification(f"⚠️ {err_msg}", silent=True)

                print(self.get_log("waiting", interval=interval))
                await asyncio.sleep(interval)
