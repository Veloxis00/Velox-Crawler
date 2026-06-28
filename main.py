import re
import time
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ====================== KONFIGURÁCIÓ ======================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1520529578928377886/dJVhNw34V8YYp-IMSOprhx2qQ9MU1lLs7b0BpZKmiMqe-VZclK3EW7bccaZX5Vk6dooZ"
SITES_FILE = "sites.json"

# ====================== KULCSSZAVAK ======================
TECH = ["password", "secret", "api_key", "apikey", "access_key", "private_key", "credential", "token", "dump", "leak", "breach", "szivárogtatás", "config", "backup", "database"]
BEL = ["orbán", "magyar péter", "tisza párt", "fidesz", "dk", "momentum", "kormány", "választás"]
VILAG = ["trump", "putin", "zelenszkij", "ukrajna", "oroszország", "kína", "izrael", "gáza"]
FIGYELT_KULCSSZAVAK = TECH + BEL + VILAG

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}

def log(uzenet):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {uzenet}")

def kuld_discordra(embed):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=15)
    except Exception as e:
        log(f"Hiba a küldésnél: {e}")

def load_sites():
    try:
        with open(SITES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        log("Nem található sites.json, alapértelmezett oldal használata.")
        return ["https://paste.org/archive"]

def main():
    mar_ellenorzott = set()
    log("🚀 Velox Crawler elindult.")

    while True:
        sites = load_sites()
        for site in sites:
            try:
                resp = requests.get(site, headers=HEADERS, timeout=15)
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Linkek gyűjtése
                linkek = ["https://paste.org" + a["href"] for a in soup.find_all("a", href=True) if a["href"].startswith("/paste/")]
                
                for link in linkek[:10]:
                    if link in mar_ellenorzott: continue
                    
                    raw_resp = requests.get(link.replace("/paste/", "/raw/"), headers=HEADERS, timeout=10)
                    if raw_resp.status_code == 200:
                        text = raw_resp.text
                        text_low = text.lower()
                        
                        talalt = [kw for kw in FIGYELT_KULCSSZAVAK if kw in text_low]
                        emailek = list(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)))
                        
                        if talalt or emailek:
                            embed = {
                                "title": "📋 Találat",
                                "url": link,
                                "description": f"Kulcsszavak: {', '.join(talalt)}\nEmailek: {', '.join(emailek[:5])}",
                                "color": 15158332
                            }
                            kuld_discordra(embed)
                            log(f"Találat küldve: {link}")
                    
                    mar_ellenorzott.add(link)
                    time.sleep(2) 

            except Exception as e:
                log(f"Hiba a {site} feldolgozásakor: {e}")
        
        # Emlékezet ürítése, ha túl nagyra nő
        if len(mar_ellenorzott) > 2000: 
            mar_ellenorzott.clear()
            log("Emlékezet ürítve.")
            
        time.sleep(300) # 5 perc várakozás

if __name__ == "__main__":
    main()
