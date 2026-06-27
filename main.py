import os
import re
import time
import json
import requests
import feedparser
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1520529578928377886/dJVhNw34V8YYp-IMSOprhx2qQ9MU1lLs7b0BpZKmiMqe-VZclK3EW7bccaZX5Vk6dooZ"

FIGYELT_KULCSSZAVAK = ["critical", "database", "admin", "error", "config", "server", "backup", "vulnerability"]

def kuld_discordra(szoveg, embed=None):
    payload = {"username": "Velox Crawler"}
    if embed:
        payload["embeds"] = [embed]
    else:
        payload["content"] = szoveg
        
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"[Velox] Discord küldési hiba: {e}")

def target_oldalak_betoltese():
    try:
        with open("sites.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Velox] Hiba: {e}")
        return ["https://paste.org/archive", "https://index.hu/24ora/rss", "https://telex.hu/rss"]

def teljes_cikk_szoveg_letoltese(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            paragrafusok = []
            
            if "index.hu" in url:
                cikk_doboz = soup.find(class_="cikk-torzs") or soup.find(id="cikk-torzs")
                if cikk_doboz:
                    for p in cikk_doboz.find_all("p"):
                        paragrafusok.append(p.get_text().strip())
            elif "telex.hu" in url:
                cikk_doboz = soup.find(class_="article-html-content")
                if cikk_doboz:
                    for p in cikk_doboz.find_all(["p", "h2"]):
                        paragrafusok.append(p.get_text().strip())
            
            if not paragrafusok:
                for p in soup.find_all("p"):
                    text = p.get_text().strip()
                    if len(text) > 40:
                        paragrafusok.append(text)
                        
            return "\n\n".join(paragrafusok)
    except Exception as e:
        print(f"[Velox] Hiba: {e}")
    return ""

def hir_oldal_feldolgozas(rss_url, mar_ellenorzott):
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:3]:
            link = entry.link
            if link not in mar_ellenorzott:
                cim = entry.get("title", "Nincs cím")
                print(f"[Velox] Új hír: {cim}")
                
                teljes_tartalom = teljes_cikk_szoveg_letoltese(link)
                if not teljes_tartalom:
                    teljes_tartalom = "Nem sikerült beolvasni a cikk tartalmát."

                kep_url = None
                if "media_content" in entry and len(entry.media_content) > 0:
                    kep_url = entry.media_content[0].get("url")
                elif "links" in entry:
                    for l in entry.links:
                        if "image" in l.get("type", ""):
                            kep_url = l.get("href")

                embed = {
                    "title": f"📰 {cim}",
                    "description": teljes_tartalom[:1500] + "...\n\n*(A cikk hossza miatt a Discordon rövidítve jelenik meg)*",
                    "url": link,
                    "color": 3447003
                }
                if kep_url:
                    embed["image"] = {"url": kep_url}
                    
                kuld_discordra("", embed=embed)
                mar_ellenorzott.add(link)
    except Exception as e:
        print(f"[Velox] Hiba: {e}")

def paste_oldal_feldolgozas(url, mar_ellenorzott):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"[Velox] Státusz hiba: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, "html.parser")
        linkek = ["https://paste.org" + a_tag["href"] for a_tag in soup.find_all("a", href=True) if "/paste/" in a_tag["href"]]
        
        print(f"[Velox] {len(linkek)} db friss link.")
        
        for link in linkek[:5]:
            if link not in mar_ellenorzott:
                raw_url = link.replace("/paste/", "/raw/")
                raw_resp = requests.get(raw_url, headers=headers, timeout=10)
                
                if raw_resp.status_code == 200:
                    szoveg = raw_resp.text
                    szoveg_lowered = szoveg.lower()
                    meret_kb = round(len(szoveg) / 1024, 2)
                    
                    print(f" -> Elemzés: {link} ({meret_kb} KB) ... ", end="")
                    
                    email_minta = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
                    ipv4_minta  = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
                    url_minta   = r"https?://[^\s]+"
                    
                    emailek = list(set(re.findall(email_minta, szoveg)))
                    ip_cimek = list(set(re.findall(ipv4_minta, szoveg)))
                    web_linkek = list(set(re.findall(url_minta, szoveg)))
                    
                    talalt_szavak = [szo for szo in FIGYELT_KULCSSZAVAK if szo in szoveg_lowered]
                    
                    if emailek or ip_cimek or talalt_szavak:
                        print("TALÁLAT!")
                        
                        embed = {
                            "title": "📋 Velox Pastebin Monitor Találat",
                            "url": link,
                            "color": 15158332,
                            "description": f"**Forrás:** {link}\n**Adatméret:** {meret_kb} KB\n\n"
                        }
                        
                        if talalt_szavak:
                            embed["description"] += f"⚠️ **Riasztási kulcsszavak:** {', '.join(talalt_szavak)}\n"
                        if emailek:
                            embed["description"] += f"📧 **E-mail címek (max 5):** {', '.join(emailek[:5])}\n"
                        if ip_cimek:
                            embed["description"] += f"🌐 **IP címek (max 5):** {', '.join(ip_cimek[:5])}\n"
                        if web_linkek:
                            embed["description"] += f"🔗 **Belső linkek (max 3):** {', '.join(web_linkek[:3])}\n"
                            
                        embed["description"] += f"""\n**Szövegkivonat:**\n
