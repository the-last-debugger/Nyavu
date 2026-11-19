import io, json, socket, sys, time
sys.stdout.reconfigure(encoding="utf-8")

# name, registrable domain, category, where the domain is published
TABLE = [
  # --- Kenyan banks (CBK licensed; domains as published by each bank)
  ("KCB Bank", "kcb.co.ke", "bank", "kcbgroup.com"),
  ("Equity Bank", "equitybank.co.ke", "bank", "equitygroupholdings.com"),
  ("Co-operative Bank", "coopbank.co.ke", "bank", "coopbank.co.ke"),
  ("NCBA Bank", "ncbagroup.com", "bank", "ncbagroup.com"),
  ("Absa Kenya", "absabank.co.ke", "bank", "absa.co.ke"),
  ("Stanbic Bank Kenya", "stanbicbank.co.ke", "bank", "standardbank.com"),
  ("I&M Bank", "imbank.com", "bank", "imbank.com"),
  ("Diamond Trust Bank", "dtbafrica.com", "bank", "dtbafrica.com"),
  ("Standard Chartered Kenya", "sc.com", "bank", "sc.com"),
  ("Family Bank", "familybank.co.ke", "bank", "familybank.co.ke"),
  ("National Bank of Kenya", "nationalbank.co.ke", "bank", "nationalbank.co.ke"),
  ("SBM Bank Kenya", "sbmgroup.mu", "bank", "sbmgroup.mu"),
  ("Sidian Bank", "sidianbank.co.ke", "bank", "sidianbank.co.ke"),
  ("Ecobank Kenya", "ecobank.com", "bank", "ecobank.com"),
  ("HFC", "hfgroup.co.ke", "bank", "hfgroup.co.ke"),
  ("Kingdom Bank", "kingdombank.co.ke", "bank", "kingdombank.co.ke"),
  ("Credit Bank", "creditbank.co.ke", "bank", "creditbank.co.ke"),
  ("Bank of Africa Kenya", "boakenya.com", "bank", "boakenya.com"),
  ("Prime Bank", "primebank.co.ke", "bank", "primebank.co.ke"),
  ("Victoria Commercial Bank", "vcb.co.ke", "bank", "vcb.co.ke"),
  ("Gulf African Bank", "gulfafricanbank.com", "bank", "gulfafricanbank.com"),
  ("Consolidated Bank", "consolidated-bank.com", "bank", "consolidated-bank.com"),
  ("Access Bank Kenya", "accessbankplc.com", "bank", "accessbankplc.com"),
  ("Citibank Kenya", "citibank.com", "bank", "citigroup.com"),
  ("M Oriental Bank", "morientalbank.co.ke", "bank", "morientalbank.co.ke"),
  # --- mobile money and telecoms
  ("Safaricom", "safaricom.co.ke", "telecom", "safaricom.co.ke"),
  ("M-Pesa", "m-pesa.co.ke", "mobile money", "safaricom.co.ke"),
  ("Airtel Kenya", "airtel.co.ke", "telecom", "airtel.co.ke"),
  ("Telkom Kenya", "telkom.co.ke", "telecom", "telkom.co.ke"),
  ("Jamii Telecommunications", "jtl.co.ke", "telecom", "jtl.co.ke"),
  # --- government
  ("Kenya Revenue Authority", "kra.go.ke", "government", "kra.go.ke"),
  ("eCitizen", "ecitizen.go.ke", "government", "ecitizen.go.ke"),
  ("NTSA", "ntsa.go.ke", "government", "ntsa.go.ke"),
  ("HELB", "helb.co.ke", "government", "helb.co.ke"),
  ("Huduma Centre", "hudumacentre.go.ke", "government", "hudumacentre.go.ke"),
  ("NSSF Kenya", "nssf.or.ke", "government", "nssf.or.ke"),
  ("SHA (Social Health Authority)", "sha.go.ke", "government", "sha.go.ke"),
  ("Kenya Government", "kenya.go.ke", "government", "kenya.go.ke"),
  ("Treasury", "treasury.go.ke", "government", "treasury.go.ke"),
  ("Parliament of Kenya", "parliament.go.ke", "government", "parliament.go.ke"),
  ("Independent Electoral and Boundaries Commission", "iebc.or.ke", "government", "iebc.or.ke"),
  # --- universities
  ("Kabarak University", "kabarak.ac.ke", "university", "kabarak.ac.ke"),
  ("University of Nairobi", "uonbi.ac.ke", "university", "uonbi.ac.ke"),
  ("Strathmore University", "strathmore.edu", "university", "strathmore.edu"),
  ("Kenyatta University", "ku.ac.ke", "university", "ku.ac.ke"),
  ("JKUAT", "jkuat.ac.ke", "university", "jkuat.ac.ke"),
  ("Moi University", "mu.ac.ke", "university", "mu.ac.ke"),
  ("Egerton University", "egerton.ac.ke", "university", "egerton.ac.ke"),
  ("Maseno University", "maseno.ac.ke", "university", "maseno.ac.ke"),
  ("Daystar University", "daystar.ac.ke", "university", "daystar.ac.ke"),
  ("USIU Africa", "usiu.ac.ke", "university", "usiu.ac.ke"),
  ("Multimedia University of Kenya", "mmu.ac.ke", "university", "mmu.ac.ke"),
  ("Technical University of Kenya", "tukenya.ac.ke", "university", "tukenya.ac.ke"),
  # --- commerce and services
  ("Jumia Kenya", "jumia.co.ke", "retail", "jumia.co.ke"),
  ("Kilimall", "kilimall.co.ke", "retail", "kilimall.co.ke"),
  ("Kenya Airways", "kenya-airways.com", "airline", "kenya-airways.com"),
  ("Nation Media Group", "nationmedia.com", "media", "nationmedia.com"),
  ("Standard Media", "standardmedia.co.ke", "media", "standardmedia.co.ke"),
  ("Royal Media Services", "royalmedia.co.ke", "media", "royalmedia.co.ke"),
  ("Betika", "betika.com", "betting", "betika.com"),
  ("SportPesa", "sportpesa.com", "betting", "sportpesa.com"),
  ("Kenya Power", "kplc.co.ke", "utility", "kplc.co.ke"),
  ("Nairobi Water", "nairobiwater.co.ke", "utility", "nairobiwater.co.ke"),
  ("Kenya Red Cross", "redcross.or.ke", "nGO", "redcross.or.ke"),
  # --- global brands (these dominate our corpus)
  ("Google", "google.com", "global", "google.com"),
  ("Gmail", "gmail.com", "global", "google.com"),
  ("Microsoft", "microsoft.com", "global", "microsoft.com"),
  ("Outlook", "outlook.com", "global", "microsoft.com"),
  ("Apple", "apple.com", "global", "apple.com"),
  ("iCloud", "icloud.com", "global", "apple.com"),
  ("Amazon", "amazon.com", "global", "amazon.com"),
  ("Facebook", "facebook.com", "global", "meta.com"),
  ("Meta", "meta.com", "global", "meta.com"),
  ("WhatsApp", "whatsapp.com", "global", "meta.com"),
  ("Instagram", "instagram.com", "global", "meta.com"),
  ("Netflix", "netflix.com", "global", "netflix.com"),
  ("PayPal", "paypal.com", "global", "paypal.com"),
  ("Binance", "binance.com", "global", "binance.com"),
  ("DHL", "dhl.com", "global", "dhl.com"),
  ("FedEx", "fedex.com", "global", "fedex.com"),
  ("LinkedIn", "linkedin.com", "global", "linkedin.com"),
  ("X (Twitter)", "x.com", "global", "x.com"),
  ("Telegram", "telegram.org", "global", "telegram.org"),
  ("Zoom", "zoom.us", "global", "zoom.us"),
  ("Dropbox", "dropbox.com", "global", "dropbox.com"),
  ("Adobe", "adobe.com", "global", "adobe.com"),
  ("Steam", "steampowered.com", "global", "steampowered.com"),
  ("Booking.com", "booking.com", "global", "booking.com"),
  ("Airbnb", "airbnb.com", "global", "airbnb.com"),
  ("Uber", "uber.com", "global", "uber.com"),
  ("Bolt", "bolt.eu", "global", "bolt.eu"),
]

def resolves(domain):
    try:
        socket.getaddrinfo(domain, 443, proto=socket.IPPROTO_TCP)
        return True
    except Exception:
        return False

rows, dead = [], []
for name, domain, category, source in TABLE:
    ok = resolves(domain)
    rows.append({"name": name, "domain": domain, "category": category,
                 "source": source, "resolves": ok})
    if not ok:
        dead.append((name, domain))

live = [r for r in rows if r["resolves"]]
print(f"entries {len(rows)} | resolve {len(live)} | do not resolve {len(dead)}")
for name, domain in dead:
    print("  dead:", name, domain)

io.open("data/institutions.json", "w", encoding="utf-8", newline="\n").write(
    json.dumps({"checked": time.strftime("%Y-%m-%d"), "source": "public sites, DNS validated",
                "entries": rows}, indent=1))

js = ["/* Generated by tools/institutions.py. Do not edit by hand.",
      "   Official domains of institutions and brands, checked against DNS on " + time.strftime("%Y-%m-%d") + ".",
      "   The claim is about this list: nothing is fetched when a link is checked. */",
      "window.NYAVU_INSTITUTIONS = {"]
for r in live:
    js.append(f'  "{r["domain"]}": {json.dumps(r["name"])},')
js.append("};")
io.open("app/static/institutions.js", "w", encoding="utf-8", newline="\n").write("\n".join(js) + "\n")
print("wrote data/institutions.json and app/static/institutions.js with", len(live), "live domains")
