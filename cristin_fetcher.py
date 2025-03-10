import requests
import csv

# === KONFIG ===
START_YEAR = 2020
END_YEAR = 2024
CRISTIN_ID_FIL = "cristin_ids.txt"
OUTPUT_FILE = "cristin_publikasjoner.csv"
CRISTIN_API_BASE = "https://api.cristin.no/v2"

def hent_navn_fra_api(cristin_id):
    url = f"{CRISTIN_API_BASE}/persons/{cristin_id}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"⚠️  Klarte ikke hente navn for {cristin_id} ({response.status_code})")
        return "Ukjent navn"
    data = response.json()
    fornavn = data.get("first_name", "")
    etternavn = data.get("surname", "")
    return f"{fornavn} {etternavn}".strip()

def hent_publikasjoner(cristin_id, navn):
    url = f"{CRISTIN_API_BASE}/persons/{cristin_id}/results"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Feil ved henting av resultater for {cristin_id}: {response.status_code}")
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
            nvi = "-"
            publiseringssted = "Ukjent"
            media_type = ""
            url_resultat = pub.get("url", "")

            # Journal + NVI
            journal_felt = pub.get("journal")
            if isinstance(journal_felt, dict):
                name_felt = journal_felt.get("name", {})
                if isinstance(name_felt, dict):
                    publiseringssted = name_felt.get("nb") or name_felt.get("en") or publiseringssted
                publisher = journal_felt.get("publisher")
                if isinstance(publisher, dict):
                    nvi = publisher.get("nvi_level", "-")
            elif isinstance(journal_felt, str) and journal_felt:
                publiseringssted = journal_felt

            # Hvis fortsatt ukjent, prøv place
            if publiseringssted == "Ukjent" and pub.get("place"):
                publiseringssted = pub.get("place")

            # Hvis fortsatt ukjent, prøv publisher utenfor journal
            if publiseringssted == "Ukjent" and "publisher" in pub:
                publisher_felt = pub.get("publisher")
                if isinstance(publisher_felt, dict):
                    name_felt = publisher_felt.get("name", {})
                    if isinstance(name_felt, dict):
                        publiseringssted = name_felt.get("nb") or name_felt.get("en") or publiseringssted
                elif isinstance(publisher_felt, str):
                    publiseringssted = publisher_felt

            # Media type
            if "media_type" in pub:
                code_name = pub["media_type"].get("code_name", {})
                if isinstance(code_name, dict):
                    media_type = code_name.get("en", "")
                elif isinstance(pub["media_type"], str):
                    media_type = pub["media_type"]

            if not publiseringssted:
                publiseringssted = "Ukjent"

            resultatliste.append({
                "Cristin-ID": cristin_id,
                "Navn": navn,
                "Tittel": tittel,
                "År": år,
                "Kategori": kategori,
                "Publiseringssted / Kanal": publiseringssted,
                "Media type": media_type,
                "NVI-nivå": nvi,
                "Resultat-URL": url_resultat,
                "Cristin Resultat-ID": pub.get("cristin_result_id", "")
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
    print(f"{len(publikasjoner)} resultater lagret i '{filnavn}'.")

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

