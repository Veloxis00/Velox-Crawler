import os
import re
import time
import json
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime

# ====================== HARDKODOLT WEBHOOK ======================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1520529578928377886/dJVhNw34V8YYp-IMSOprhx2qQ9MU1lLs7b0BpZKmiMqe-VZclK3EW7bccaZX5Vk6dooZ"  # IDE TEDD A SAJÁT WEBHOOKODAT

FIGYELT_KULCSSZAVAK = [
    "password", "secret", "api_key", "apikey", "access_key", "private_key",
    "credential", "token", "aws_secret", "discord_token", ".env", "config", "backup", "dump", "leak"
]

PRIORITAS_KULCSSZAVAK = ["leak", "breach", "password", "dump", "vulnerability", "exploit", "ransomware"Trump,Magyar Péter,Pénz,Hivatal,Szivárogtatás]

def log(uzenet):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {uzenet}")

def kuld_discordra(content=None, embed=None):
    if not DISCORD_WEBHOOK_URL:
        log("Nincs webhook URL!")
        return
    payload = {"username": "Velox Crawler"}
    if embed:
        payload["embeds"] = [embed]
    else:
        payload["content"] = content
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=15)
        log("Discord üzenet elküldve")
    except Exception as e:
        log(f"Discord hiba: {e}")

def load_sites():
    try:
        with open("sites.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        log("sites.json nem található, alapértelmezett értékeket használom.")
        return ["https://paste.org/archive", "https://index.hu/24ora/rss", "https://telex.hu/rss"]

def teljes_cikk_letoltese(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; VeloxCrawler/2.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        paragraphs = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 50]
        return "\n\n".join(paragraphs[:25])
    except Exception:
        return ""

def is_high_priority(title, content):
    text = (title + " " + content).lower()
    return any(kw in text for kw in PRIORITAS_KULCSSZAVAK)

def main():
    mar_ellenorzott = set()
    log("🚀 Velox Crawler elindult (Hardcoded Webhook)")

    kuld_discordra("✅ **Velox Crawler elindult** - Hardcoded webhook verzió")

    while True:
        try:
            sites = load_sites()

            for site in sites:
                try:
                    if "paste.org" in site:
                        headers = {"User-Agent": "Mozilla/5.0"}
                        resp = requests.get(site, headers=headers, timeout=12)
                        soup = BeautifulSoup(resp.text, "html.parser")
                        linkek = ["https://paste.org" + a["href"] for a in soup.find_all("a", href=True) if a["href"].startswith("/paste/")]

                        for link in linkek[:10]:
                            if link in mar_ellenorzott: continue

                            raw_resp = requests.get(link.replace("/paste/", "/raw/"), timeout=10)
                            if raw_resp.status_code != 200: continue

                            szoveg = raw_resp.text.lower()
                            talalt = [kw for kw in FIGYELT_KULCSSZAVAK if kw in szoveg]

                            if talalt:
                                embed = {
                                    "title": "📋 Paste Találat",
                                    "url": link,
                                    "color": 15158332,
                                    "description": f"**Idő:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n**Kulcsszavak:** {', '.join(talalt)}"
                                }
                                kuld_discordra(embed=embed)
                            mar_ellenorzott.add(link)

                    else:
                        feed = feedparser.parse(site)
                        for entry in feed.entries[:5]:
                            link = entry.link
                            if link in mar_ellenorzott: continue

                            title = entry.get("title", "")
                            full_text = teljes_cikk_letoltese(link)

                            priority = is_high_priority(title, full_text)

                            embed = {
                                "title": f"{'🔴 ' if priority else '📰 '} {title[:160]}",
                                "description": full_text[:3800] + ("..." if len(full_text) > 3800 else ""),
                                "url": link,
                                "color": 15158332 if priority else 3447003,
                                "footer": {"text": f"Idő: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                            }
                            kuld_discordra(embed=embed)

                            mar_ellenorzott.add(link)

                except Exception as e:
                    log(f"Hiba ({site}): {e}")

            if len(mar_ellenorzott) > 6000:
                mar_ellenorzott.clear()
                log("Emlékezet törölve")

            log("Ciklus kész")
            time.sleep(300)

        except Exception as e:
            log(f"KRITIKUS HIBA: {e}")
            time.sleep(120)


if __name__ == "__main__":
    main()
