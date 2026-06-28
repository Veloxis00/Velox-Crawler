import os
import re
import time
import json
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
import random

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1520529578928377886/dJVhNw34V8YYp-IMSOprhx2qQ9MU1lLs7b0BpZKmiMqe-VZclK3EW7bccaZX5Vk6dooZ"

# User-Agent rotáció
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0"
]

def get_headers():
    return {"User-Agent": random.choice(USER_AGENTS)}

# Kulcsszavak (bővítve)
KULCSSZAVAK = [
    "password", "secret", "api_key", "dump", "leak", "breach", "szivárogtatás",
    "config", "backup", "database", "admin", "root", "token", "credential",
    "orbán", "magyar péter", "fidesz", "kormány", "választás", "korrupció",
    "trump", "putin", "ukrajna", "oroszország"
]

def log(uzenet):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {uzenet}")

def kuld_discordra(content=None, embed=None, image_url=None):
    if not DISCORD_WEBHOOK_URL: return
    payload = {"username": "Velox Crawler"}
    files = None

    if embed:
        payload["embeds"] = [embed]
    elif content:
        payload["content"] = content

    try:
        if image_url:
            img_resp = requests.get(image_url, timeout=12)
            if img_resp.status_code == 200:
                files = {'file': ('image.jpg', img_resp.content, 'image/jpeg')}
                requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files, timeout=20)
            else:
                requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=20)
        else:
            requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=20)
        log("Discordra elküldve")
    except Exception as e:
        log(f"Discord hiba: {e}")

def find_and_send_images(url):
    try:
        resp = requests.get(url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        for img in soup.find_all("img")[:3]:
            src = img.get("src") or img.get("data-src")
            if src and src.startswith("http"):
                kuld_discordra(image_url=src)
                time.sleep(1)
    except:
        pass

def load_sites():
    try:
        with open("sites.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return ["https://paste.org/archive"]

def main():
    mar_ellenorzott = set()
    log("🚀 Velox Crawler elindult - Egyszerűsített keresés")

    kuld_discordra("✅ **Velox Crawler elindult** - Egyszerűsített mód")

    while True:
        try:
            sites = load_sites()

            for site in sites:
                try:
                    headers = get_headers()
                    resp = requests.get(site, headers=headers, timeout=12)
                    soup = BeautifulSoup(resp.text, "html.parser")

                    if "paste.org" in site:
                        linkek = ["https://paste.org" + a["href"] for a in soup.find_all("a", href=True) if a["href"].startswith("/paste/")]
                        for link in linkek[:15]:
                            if link in mar_ellenorzott: continue

                            raw_resp = requests.get(link.replace("/paste/", "/raw/"), headers=headers, timeout=10)
                            if raw_resp.status_code != 200: continue

                            szoveg = raw_resp.text
                            talalt = [kw for kw in KULCSSZAVAK if kw in szoveg.lower()]

                            if talalt or len(szoveg) > 600:
                                embed = {
                                    "title": "📋 Találat",
                                    "url": link,
                                    "color": 15158332,
                                    "description": f"**Idő:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n**Kulcsszavak:** {', '.join(talalt)}"
                                }
                                kuld_discordra(embed=embed)
                                find_and_send_images(link)

                            mar_ellenorzott.add(link)

                    else:
                        # RSS
                        feed = feedparser.parse(site)
                        for entry in feed.entries[:5]:
                            link = entry.link
                            if link in mar_ellenorzott: continue

                            title = entry.get("title", "")
                            embed = {
                                "title": f"📰 {title[:160]}",
                                "url": link,
                                "color": 3447003,
                                "footer": {"text": f"Idő: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                            }
                            kuld_discordra(embed=embed)
                            find_and_send_images(link)

                            mar_ellenorzott.add(link)

                except Exception as e:
                    log(f"Hiba ({site}): {e}")

            if len(mar_ellenorzott) > 10000:
                mar_ellenorzott.clear()

            log("Ciklus kész")
            time.sleep(240)

        except Exception as e:
            log(f"KRITIKUS HIBA: {e}")
            time.sleep(120)


if __name__ == "__main__":
    main()
