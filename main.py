import os
import re
import time
import json
import requests
from bs4 import BeautifulSoup
import feedparser

# ====================== KONFIG ======================

# IDE ÍRD BE A SAJÁT WEBHOOK-ODAT!
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1520529578928377886/dJVhNw34V8YYp-IMSOprhx2qQ9MU1lLs7b0BpZKmiMqe-VZclK3EW7bccaZX5Vk6dooZ"  

FIGYELT_KULCSSZAVAK = ["critical", "database", "admin", "error", "config", "server", 
                       "backup", "vulnerability", "password", "passwd", "secret", "key", 
                       "credential", "leak", "dump", "private", "confidential"]

CHECK_INTERVAL = 300   # másodperc (5 perc)
MAX_HISTORY = 10000    # maximum ennyi linket őrzünk meg

# ====================================================

def kuld_discordra(szoveg=None, embed=None):
    if not DISCORD_WEBHOOK_URL or DISCORD_WEBHOOK_URL.startswith("https://discord.com/api/webhooks/") is False:
        print("HIBA: Nincs érvényes Discord webhook URL beállítva!")
        return

    payload = {"username": "Velox Crawler"}
    if embed:
        payload["embeds"] = [embed]
    else:
        payload["content"] = szoveg

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=15)
        if response.status_code not in (200, 204):
            print(f"Discord hiba: {response.status_code}")
    except Exception as e:
        print(f"Discord küldési hiba: {e}")


def load_sites():
    try:
        with open("sites.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        print("sites.json nem található vagy hibás. Alapértelmezett oldalak használata.")
        return [
            "https://paste.org/archive",
            "https://index.hu/24ora/rss",
            "https://telex.hu/rss"
        ]


def teljes_cikk_szoveg_letoltese(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; VeloxCrawler/1.0)"}
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        paragrafusok = []

        if "index.hu" in url.lower():
            cikk = soup.find(class_="cikk-torzs") or soup.find(id="cikk-torzs")
            if cikk:
                for p in cikk.find_all("p"):
                    text = p.get_text().strip()
                    if text and len(text) > 30:
                        paragrafusok.append(text)

        elif "telex.hu" in url.lower():
            cikk = soup.find(class_="article-html-content")
            if cikk:
                for tag in cikk.find_all(["p", "h2", "h3"]):
                    text = tag.get_text().strip()
                    if text:
                        paragrafusok.append(text)

        # Általános fallback
        if len(paragrafusok) < 4:
            for p in soup.find_all("p"):
                text = p.get_text().strip()
                if len(text) > 50:
                    paragrafusok.append(text)

        return "\n\n".join(paragrafusok[:15])
    except Exception as e:
        print(f"Cikk letöltési hiba ({url}): {type(e).__name__}")
        return ""


def hir_oldal_feldolgozas(rss_url: str, mar_ellenorzott: set):
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:5]:
            link = entry.link
            if link in mar_ellenorzott:
                continue

            cim = entry.get("title", "Nincs cím")
            tartalom = teljes_cikk_szoveg_letoltese(link)

            embed = {
                "title": f"📰 {cim[:240]}",
                "description": (tartalom[:1450] + "...") if tartalom else "Nincs elérhető tartalom.",
                "url": link,
                "color": 3447003
            }
            kuld_discordra(embed=embed)
            mar_ellenorzott.add(link)
    except Exception as e:
        print(f"RSS hiba ({rss_url}): {type(e).__name__}")


def paste_oldal_feldolgozas(url: str, mar_ellenorzott: set):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; VeloxCrawler/1.0)"}
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        linkek = ["https://paste.org" + a["href"] for a in soup.find_all("a", href=True) 
                  if a["href"].startswith("/paste/")]

        for link in linkek[:8]:
            if link in mar_ellenorzott:
                continue

            raw_url = link.replace("/paste/", "/raw/")
            raw_resp = requests.get(raw_url, headers=headers, timeout=10)
            
            if raw_resp.status_code != 200:
                continue

            szoveg = raw_resp.text
            szoveg_low = szoveg.lower()

            emailek = list(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", szoveg)))
            ip_cimek = list(set(re.findall(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", szoveg)))
            talalt_szavak = [szo for szo in FIGYELT_KULCSSZAVAK if szo in szoveg_low]

            if emailek or ip_cimek or talalt_szavak:
                description = f"**Forrás:** {link}\n\n"
                if talalt_szavak:
                    description += f"⚠️ **Kulcsszavak:** {', '.join(talalt_szavak)}\n"
                if emailek:
                    description += f"📧 **E-mailek:** {', '.join(emailek[:6])}\n"
                if ip_cimek:
                    description += f"🌐 **IP-címek:** {', '.join(ip_cimek[:6])}\n"

                description += f"\n**Kivonat:**\n{szoveg[:750]}..." 

                embed = {
                    "title": "📋 Velox Találat - Érzékeny adat",
                    "url": link,
                    "color": 15158332,
                    "description": description[:4000]
                }
                kuld_discordra(embed=embed)
                mar_ellenorzott.add(link)

    except Exception as e:
        print(f"paste.org hiba: {type(e).__name__}")


# ====================== FŐCIKLUS ======================
def main():
    mar_ellenorzott = set()
    sites = load_sites()

    print("🚀 Velox Crawler elindult...")
    print(f"Figyelt kulcsszavak száma: {len(FIGYELT_KULCSSZAVAK)}")

    while True:
        try:
            for site in sites:
                if "paste.org" in site.lower():
                    paste_oldal_feldolgozas(site, mar_ellenorzott)
                else:
                    hir_oldal_feldolgozas(site, mar_ellenorzott)

            # Túl nagy history takarítása
            if len(mar_ellenorzott) > MAX_HISTORY:
                mar_ellenorzott = set(list(mar_ellenorzott)[-MAX_HISTORY//2:])

            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ciklus kész. Következő ellenőrzés {CHECK_INTERVAL//60} perc múlva.")
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n\nCrawler leállítva felhasználó által.")
            break
        except Exception as e:
            print(f"Váratlan hiba: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
