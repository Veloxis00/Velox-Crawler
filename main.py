import os
import re
import time
import json
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, date
import matplotlib.pyplot as plt
import io

# ====================== HARDKODOLT WEBHOOK ======================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1520529578928377886/dJVhNw34V8YYp-IMSOprhx2qQ9MU1lLs7b0BpZKmiMqe-VZclK3EW7bccaZX5Vk6dooZ"

# ====================== KULCSSZAVAK ======================
TECH_KULCSSZAVAK = [
    "password", "secret", "api_key", "apikey", "access_key", "private_key", "credential",
    "token", "dump", "leak", "breach", "szivárogtatás", "config", "backup", "database"
]

BELPOLITIKAI_KULCSSZAVAK = [
    "orbán", "magyar péter", "tisza párt", "fidesz", "dk", "momentum", "kormány", "választás","hivatal","ukrajna","elszámoltatás","ügyézség"
]

VILAGPOLITIKAI_KULCSSZAVAK = [
    "trump", "putin", "zelenszkij", "ukrajna", "oroszország", "kína", "izrael", "gáza","war"
]

FIGYELT_KULCSSZAVAK = TECH_KULCSSZAVAK + BELPOLITIKAI_KULCSSZAVAK + VILAGPOLITIKAI_KULCSSZAVAK

# Statisztika
stats = {"total": 0}
site_stats = {}

def log(uzenet):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {uzenet}")

def kuld_discordra(content=None, embed=None, file=None):
    if not DISCORD_WEBHOOK_URL: return
    payload = {"username": "Velox Crawler"}
    files = {}
    if content:
        payload["content"] = content
    if embed:
        payload["embeds"] = [embed]
    if file:
        files = {'file': file}
    try:
        requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files, timeout=20)
    except Exception as e:
        log(f"Discord hiba: {e}")

def send_daily_report():
    global site_stats, stats
    if not site_stats:
        kuld_discordra("📊 Napi jelentés: Ma nem volt találat.")
        return

    # Pie chart készítése
    labels = list(site_stats.keys())
    sizes = list(site_stats.values())

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    ax.set_title(f"Napi Crawler Jelentés - {date.today()}")

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)

    embed = {
        "title": "📊 Napi Összefoglaló",
        "description": f"**Dátum:** {date.today()}\n**Összes találat:** {stats['total']}",
        "color": 3447003
    }

    kuld_discordra(embed=embed, file=("daily_report.png", buf, "image/png"))

    # Reset
    site_stats.clear()
    stats["total"] = 0

def load_sites():
    try:
        with open("sites.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        log("sites.json nem található")
        return ["https://paste.org/archive"]

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
    last_report_date = date.today()

    log("🚀 Velox Crawler elindult - Napi jelentéssel")

    kuld_discordra("✅ **Velox Crawler elindult** - Napi jelentés aktív")

    while True:
        try:
            current_date = date.today()
            if current_date != last_report_date:
                send_daily_report()
                last_report_date = current_date

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

                            mar_ellenorzott.add(link)
                            stats["total"] += 1
                            site_name = site.split("//")[1].split("/")[0]
                            site_stats[site_name] = site_stats.get(site_name, 0) + 1

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
