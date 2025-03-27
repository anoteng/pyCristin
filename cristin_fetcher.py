import requests
import csv

# === KONFIG ===
START_YEAR = 2018
END_YEAR = 2024
CRISTIN_ID_FIL = "cristin_ids.txt"
OUTPUT_FILE = "cristin_publikasjoner_kategoriadaptiv.csv"
CRISTIN_API_BASE = "https://api.cristin.no/v2"

def hent_navn_fra_api(cristin_id):
    url = f"{CRISTIN_API_BASE}/persons/{cristin_id}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"⚠️  Klarte ikke hente navn for {cristin_id} ({response.status_code})")
        return "Ukjent navn"
    data = response.json()
    return f"{data.get('first_name', '')} {data.get('surname', '')}".strip()

def bestem_publiseringssted(pub, kategori):
    kanal = ""
    kilde = ""

    # === 1: Journal
    journal = pub.get("journal")
    if isinstance(journal, dict) and isinstance(journal.get("name"), str):
        kanal = journal["name"]
        kilde = "journal.name"

    # === 2: Publisher
    if not kanal and isinstance(pub.get("publisher"), dict):
        kanal = pub["publisher"].get("name", "")
        if kanal:
            kilde = "publisher.name"

    # === 3: Lecture / Academic lecture – organiser/event
    if not kanal and kategori.lower() in ["lecture", "academic lecture"]:
        kanal = pub.get("organiser", "")
        if kanal:
            kilde = "organiser"
        elif pub.get("event", {}).get("arranged_by", {}).get("name"):
            kanal = pub["event"]["arranged_by"]["name"]
            kilde = "event.arranged_by.name"
        elif pub.get("event", {}).get("name") and pub.get("event", {}).get("location"):
            kanal = f"{pub['event']['name']} – {pub['event']['location']}"
            kilde = "event.name + location"
        elif pub.get("event", {}).get("name"):
            kanal = pub["event"]["name"]
            kilde = "event.name"

    # === 4: Doctoral dissertation – series
    if not kanal and kategori.lower() == "doctoral dissertation":
        kanal = pub.get("series", {}).get("name", "")
        if kanal:
            kilde = "series.name"

    # === 5: place
    if not kanal and pub.get("place"):
        kanal = pub["place"]
        kilde = "place"

    # === 6: media_type
    if not kanal and pub.get("media_type", {}).get("code_name", {}).get("en"):
        kanal = pub["media_type"]["code_name"]["en"]
        kilde = "media_type.code_name"

    # === 7: channel.title
    if not kanal and pub.get("channel", {}).get("title"):
        kanal = pub["channel"]["title"]
        kilde = "channel.title"

    if not kanal:
        kanal = "Ukjent"
        kilde = "Ingen relevante felter funnet"

    return kanal, kilde

def hent_publikasjoner(cristin_id, navn):
    url = f"{CRISTIN_API_BASE}/persons/{cristin_id}/results"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"❌ Feil ved henting av resultater for {cristin_id}: {response.status_code}")
        return []

    publikasjoner = response.json()
    resultatliste = []

    for pub in publikasjoner:
        try:
            år = int(pub.get("year_published", 0))
        except (ValueError, TypeError):
            continue

        if START_YEAR <= år <= END_YEAR:
            tittel = pub.get("title", {}).get(pub.get("original_language", ""), "(Uten tittel)")
            kategori = pub.get("category", {}).get("name", {}).get("en", "")
            # Hent nvi_level fra detaljvisning
            nvi = "-"
            resultat_id = pub.get("cristin_result_id")
            if resultat_id:
                resurl = f"{CRISTIN_API_BASE}/results/{resultat_id}"
                resresp = requests.get(resurl)
                if resresp.status_code == 200:
                    resdata = resresp.json()
                    journal = resdata.get("journal", {})
                    if isinstance(journal, dict):
                        nvi = journal.get("nvi_level") or journal.get("publisher", {}).get("nvi_level") or "-"

            publiseringssted, kanal_kilde = bestem_publiseringssted(pub, kategori)

            # Media type
            media_type = ""
            if isinstance(pub.get("media_type"), dict):
                media_type = pub["media_type"].get("code_name", {}).get("en", "")
            elif isinstance(pub.get("media_type"), str):
                media_type = pub["media_type"]

            resultatliste.append({
                "Cristin-ID": cristin_id,
                "Navn": navn,
                "Tittel": tittel,
                "År": år,
                "Kategori": kategori,
                "Publiseringssted / Kanal": publiseringssted,
                "Media type": media_type,
                "NVI-nivå": nvi,
                "Resultat-URL": pub.get("url", ""),
                "Cristin Resultat-ID": pub.get("cristin_result_id", ""),
                "Kanal-kilde (debug)": kanal_kilde  # Valgfritt – fjern om du vil
            })

    return resultatliste

def les_cristin_ids(filnavn):
    with open(filnavn, "r", encoding="utf-8") as f:
        return [linje.strip() for linje in f if linje.strip()]

def lagre_csv(publikasjoner, filnavn):
    if not publikasjoner:
        print("Ingen publikasjoner funnet.")
        return
    with open(filnavn, "w", newline="", encoding="utf-8") as csvfile:
        feltnavn = publikasjoner[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=feltnavn)
        writer.writeheader()
        writer.writerows(publikasjoner)
    print(f"✅ {len(publikasjoner)} resultater lagret i '{filnavn}'.")

def main():
    cristin_ids = les_cristin_ids(CRISTIN_ID_FIL)
    alle_publikasjoner = []

    for cristin_id in cristin_ids:
        navn = hent_navn_fra_api(cristin_id)
        print(f"Henter data for Cristin-ID: {cristin_id} ({navn}) ...")
        pubs = hent_publikasjoner(cristin_id, navn)
        alle_publikasjoner.extend(pubs)

    lagre_csv(alle_publikasjoner, OUTPUT_FILE)

if __name__ == "__main__":
    main()

