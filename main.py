import os
import re
import time
import json
import requests
import feedparser
from bs4 import BeautifulSoup

# IDE ILLESZD BE a Discordból kimásolt Webhook URL-t!
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1520529578928377886/dJVhNw34V8YYp-IMSOprhx2qQ9MU1lLs7b0BpZKmiMqe-VZclK3EW7bccaZX5Vk6dooZ"

def kuld_discordra(szoveg, embed=None):
    """Elküldi a talált adatokat a Discord csatornára (támogatja a képes formátumot is)"""
    payload = {
        "username": "Velox Crawler",
    }
    if embed:
        payload["embeds"] = [embed]
    else:
        payload["content"] = f"📡 **Velox Crawler Új Adat:**\n{szoveg}"
        
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"[Velox] Discord küldési hiba: {e}")

def target_oldalak_betoltese():
    """Beolvassa a crawlandó oldalak listáját a sites.json fájlból"""
    try:
        with open("sites.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Velox] Hiba a sites.json beolvasásakor: {e}")
        return []

def hir_oldal_feldolgozas(rss_url, mar_ellenorzott):
    """Beolvassa a híroldalak RSS feedjét, kiszedi a szöveget, linket és képeket"""
    try:
        feed = feedparser.parse(rss_url)
        # Csak a legfrissebb 3 hírt nézzük körönként
        for entry in feed.entries[:3]:
            link = entry.link
            
            if link not in mar_ellenorzott:
                cim = entry.get("title", "Nincs cím")
                # Tisztítjuk a leírást (cikk melletti szöveget) a HTML tagektől
                leiras_html = entry.get("summary", entry.get("description", ""))
                leiras = BeautifulSoup(leiras_html, "html.parser").get_text()[:250] + "..."
                
                # Kép keresése a hírben
                kep_url = None
                if "media_content" in entry and len(entry.media_content) > 0:
                    kep_url = entry.media_content[0].get("url")
                elif "links" in entry:
                    for l in entry.links:
                        if "image" in l.get("type", ""):
                            kep_url = l.get("href")
                
                # Ha nem talált az RSS-ben képet, megpróbáljuk kiszedni a HTML-ből
                if not kep_url and "img" in leiras_html:
                    img_soup = BeautifulSoup(leiras_html, "html.parser").find("img")
                    if img_soup:
                        kep_url = img_soup.get("src")

                # Szép Discord kártya (Embed) összerakása a hírnek
                embed = {
                    "title": cim,
                    "description": leiras,
                    "url": link,
                    "color": 3447003 # Kék szín
                }
                if kep_url:
                    embed["image"] = {"url": kep_url}
                
                print(f"[Velox] Új hír: {cim}")
                kuld_discordra("", embed=embed)
                mar_ellenorzott.add(link)
    except Exception as e:
        print(f"[Velox] Hiba a híroldal feldolgozásakor ({rss_url}): {e}")

def paste_oldal_feldolgozas(url, mar_ellenorzott):
    """A korábbi szöveges/IP/Email szűrő a paste oldalakhoz"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return
            
        soup = BeautifulSoup(response.text, "html.parser")
        linkek = []
        for a_tag in soup.find_all("a", href=True):
            if "/paste/" in a_tag["href"]:
                linkek.append("https://paste.org" + a_tag["href"])
        
        for link in linkek[:5]:
            if link not in mar_ellenorzott:
                raw_url = link.replace("/paste/", "/raw/")
                raw_resp = requests.get(raw_url, headers=headers, timeout=10)
                if raw_resp.status_code == 200:
                    szoveg = raw_resp.text
                    email_minta = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
                    ipv4_minta  = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
                    url_minta   = r"https?://[^\s]+"
                    
                    emailek = list(set(re.findall(email_minta, szoveg)))
                    ip_cimek = list(set(re.findall(ipv4_minta, szoveg)))
                    web_linkek = list(set(re.findall(url_minta, szoveg)))
                    
                    if emailek or ip_cimek or web_linkek:
                        riport = f"**Forrás:** {link}\n"
                        if emailek: riport += f"📧 **E-mail címek:** {', '.join(emailek[:5])}\n"
                        if ip_cimek: riport += f"🌐 **IP címek:** {', '.join(ip_cimek[:5])}\n"
                        if web_linkek: riport += f"🔗 **Linkek:** {', '.join(web_linkek[:3])}\n"
                        kuld_discordra(riport)
                mar_ellenorzott.add(link)
    except Exception as e:
        print(f"[Velox] Hiba a paste oldal feldolgozásakor: {e}")

# Fő programciklus
mar_ellenorzott = set()
print("=" * 40)
print("  VELOX CRAWLER ELINDÍTVA (HÍREK + ADATOK)  ")
print("=" * 40)

while True:
    target_oldalak = target_oldalak_betoltese()
    
    for celpont in target_oldalak:
        # Ha a linkben benne van az "rss", akkor híroldalként kezeljük
        if "rss" in celpont.lower():
            hir_oldal_feldolgozas(celpont, mar_ellenorzott)
        else:
            paste_oldal_feldolgozas(celpont, mar_ellenorzott)
                
        if len(mar_ellenorzott) > 500:
            mar_ellenorzott.clear()
            
    print("[Velox] Kör lefutott. Várakozás 1 percig...")
    time.sleep(60)
