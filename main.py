import os
import re
import time
import json
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime

# ====================== HARDKODOLT WEBHOOK ======================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1520529578928377886/dJVhNw34V8YYp-IMSOprhx2qQ9MU1lLs7b0BpZKmiMqe-VZclK3EW7bccaZX5Vk6dooZ"

# ====================== KULCSSZAVAK ======================
TECH_KULCSSZAVAK = [
    "password", "secret", "api_key", "apikey", "access_key", "private_key", "credential",
    "token", "dump", "leak", "breach", "szivárogtatás", "config", "backup", "database", "ssh", "ftp"
]

BELPOLITIKAI_KULCSSZAVAK = [
    "orbán", "magyar péter", "tisza párt", "fidesz", "dk", "momentum", "miép", "kormány", "választás", "korrupció"
]

VILAGPOLITIKAI_KULCSSZAVAK = [
    "trump", "putin", "zelenszkij", "ukrajna", "oroszország", "kína", "izrael", "gáza", "nato", "eu"
]

FIGYELT_KULCSSZAVAK = TECH_KULCSSZAVAK + BELPOLITIKAI_KULCSSZAVAK + VILAGPOLITIKAI_KULCSSZAVAK

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
            img_resp = requests.get(image_url, timeout=15)
            if img_resp.status_code == 200:
                files = {'file': ('image.jpg', img_resp.content, 'image/jpeg')}
                response = requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files, timeout=25)
            else:
                response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=20)
        else:
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=20)

        if response.status_code in (200, 204):
            log("Discordra elküldve" + (" + képpel" if image_url else ""))
        else:
            log(f"Discord hiba: {response.status_code}")
    except Exception as e:
        log(f"Discord hiba: {e}")

def find_and_send_images(url):
    """Oldalról képek keresése és küldése"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(resp.text, "html.parser")
        images = []

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src and src.startswith("http") and len(src) > 15:
                images.append(src)

        for img_url in images[:3]:  # max 3 képet küldünk
            kuld_discordra(image_url=img_url)
    except Exception as e:
        log(f"Kép letöltési hiba: {e}")

def load_sites():
    try:
        with open("sites.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        log("sites.json nem található")
        return ["https://paste.org/archive", "https://index.hu/24ora/rss"]

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

def main():
    mar_ellenorzott = set()
    log("🚀 Velox Crawler elindult - Képekkel + kétnyelvű keresés")

    kuld_discordra("✅ **Velox Crawler elindult** - Képek + teljes kulcsszó készlet")

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

                        for link in linkek[:12]:
                            if link in mar_ellenorzott: continue

                            raw_resp = requests.get(link.replace("/paste/", "/raw/"), timeout=10)
                            if raw_resp.status_code != 200: continue

                            szoveg = raw_resp.text
                            szoveg_low = szoveg.lower()

                            talalt = [kw for kw in FIGYELT_KULCSSZAVAK if kw in szoveg_low]
                            emailek = list(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", szoveg)))

                            if talalt or emailek:
                                description = f"**Forrás:** {link}\n**Idő:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                if talalt: description += f"⚠️ Kulcsszavak: {', '.join(talalt)}\n"
                                if emailek: description += f"📧 E-mailek: {', '.join(emailek[:10])}\n"

                                embed = {
                                    "title": "📋 Paste / Dump Találat",
                                    "url": link,
                                    "color": 15158332,
                                    "description": description[:4000]
                                }
                                kuld_discordra(embed=embed)

                                # Képek küldése
                                find_and_send_images(link)

                            mar_ellenorzott.add(link)

                    else:
                        # Híroldalak
                        feed = feedparser.parse(site)
                        for entry in feed.entries[:5]:
                            link = entry.link
                            if link in mar_ellenorzott: continue

                            title = entry.get("title", "")
                            full_text = teljes_cikk_letoltese(link)

                            embed = {
                                "title": f"📰 {title[:170]}",
                                "description": full_text[:3800] + ("..." if len(full_text) > 3800 else ""),
                                "url": link,
                                "color": 3447003,
                                "footer": {"text": f"Idő: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                            }
                            kuld_discordra(embed=embed)

                            # Képek küldése a cikkből
                            find_and_send_images(link)

                            mar_ellenorzott.add(link)

                except Exception as e:
                    log(f"Hiba ({site}): {e}")

            if len(mar_ellenorzott) > 8000:
                mar_ellenorzott.clear()
                log("Emlékezet törölve")

            log("Ciklus kész")
            time.sleep(300)

        except Exception as e:
            log(f"KRITIKUS HIBA: {e}")
            time.sleep(180)


if __name__ == "__main__":
    main()
