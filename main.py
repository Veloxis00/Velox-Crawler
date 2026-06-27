import os
import re
import time
import json
import requests
import threading
import feedparser
from bs4 import BeautifulSoup
from http.server import HTTPServer, BaseHTTPRequestHandler

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1520529578928377886/dJVhNw34V8YYp-IMSOprhx2qQ9MU1lLs7b0BpZKmiMqe-VZclK3EW7bccaZX5Vk6dooZ"

FIGYELT_KULCSSZAVAK = ["critical", "database", "admin", "error", "config", "server", 
                       "backup", "vulnerability", "password", "passwd", "secret", "key", 
                       "credential", "leak", "dump", "private", "confidential"]

CHECK_INTERVAL = 300
MAX_HISTORY = 10000

def start_dummy_server():
    class HealthCheck(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        def log_message(self, format, *args):
            return

    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheck)
    server.serve_forever()

def kuld_discordra(szoveg=None, embed=None):
    if not DISCORD_WEBHOOK_URL or "discord.com/api/webhooks/" not in DISCORD_WEBHOOK_URL:
        return
    payload = {"username": "Velox Crawler"}
    if embed: payload["embeds"] = [embed]
    else: payload["content"] = szoveg
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=15)
    except Exception:
        pass

def load_sites():
    try:
        with open("sites.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return ["https://paste.org/archive", "https://index.hu/24ora/rss", "https://telex.hu/rss"]

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
                    if text and len(text) > 30: paragrafusok.append(text)
        elif "telex.hu" in url.lower():
            cikk = soup.find(class_="article-html-content")
            if cikk:
                for tag in cikk.find_all(["p", "h2", "h3"]):
                    text = tag.get_text().strip()
                    if text: paragrafusok.append(text)
        if len(paragrafusok) < 4:
            for p in soup.find_all("p"):
                text = p.get_text().strip()
                if len(text) > 50: paragrafusok.append(text)
        return "\n\n".join(paragrafusok[:15])
    except Exception:
        return ""

def hir_oldal_feldolgozas(rss_url: str, mar_ellenorzott: set):
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:5]:
            link = entry.link
            if link in mar_ellenorzott: continue
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
    except Exception:
        pass

def paste_oldal_feldolgozas(url: str, mar_ellenorzott: set):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; VeloxCrawler/1.0)"}
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        linkek = ["https://paste.org" + a["href"] for a in soup.find_all("a", href=True) if a["href"].startswith("/paste/")]
        for link in linkek[:8]:
            if link in mar_ellenorzott: continue
            raw_url = link.replace("/paste/", "/raw/")
            raw_resp = requests.get(raw_url, headers=headers, timeout=10)
            if raw_resp.status_code != 200: continue
            szoveg = raw_resp.text
            szoveg_low = szoveg.lower()
            emailek = list(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", szoveg)))
            ip_cimek = list(set(re.findall(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", szoveg)))
            talalt_szavak = [szo for szo in FIGYELT_KULCSSZAVAK if szo in szoveg_low]
            if emailek or ip_cimek or talalt_szavak:
                description = f"**Forrás:** {link}\n\n"
                if talalt_szavak: description += f"⚠️ **Kulcsszavak:** {', '.join(talalt_szavak)}\n"
                if emailek: description += f"📧 **E-mailek:** {', '.join(emailek[:6])}\n"
                if ip_cimek: description += f"🌐 **IP-címek:** {', '.join(ip_cimek[:6])}\n"
                description += f"\n**Kivonat:**\n{szoveg[:750]}..."
                embed = {
                    "title": "📋 Velox Találat - Érzékeny adat",
                    "url": link,
                    "color": 15158332,
                    "description": description[:4000]
                }
                kuld_discordra(embed=embed)
            mar_ellenorzott.add(link)
    except Exception:
        pass

def main():
    threading.Thread(target=start_dummy_server, daemon=True).start()
    mar_ellenorzott = set()
    print("🚀 Velox Crawler elindult...")
    while True:
        sites = load_sites()
        for site in sites:
            if "paste.org" in site.lower(): paste_oldal_feldolgozas(site, mar_ellenorzott)
            else: hir_oldal_feldolgozas(site, mar_ellenorzott)
        if len(mar_ellenorzott) > MAX_HISTORY: mar_ellenorzott = set(list(mar_ellenorzott)[-MAX_HISTORY//2:])
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
