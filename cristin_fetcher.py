import requests
import csv

# === KONFIG ===
INSTITUSJON = "nmbu"  # <- juster her hvis ikke alle er fra NTNU
START_YEAR = 2018
END_YEAR = 2024
OUTPUT_FILE = "cristin_publikasjoner.csv"
CRISTIN_ID_FIL = "cristin_ids.txt"

CRISTIN_API_BASE = "https://api.cristin.no/v2"

def hent_personnavn(cristin_id):
    url = f"{CRISTIN_API_BASE}/persons/{INSTITUSJON}/{cristin_id}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Feil ved henting av persondata for {cristin_id} ({response.status_code})")
        return "Ukjent navn"
    data = response.json()
    navn = data.get("full_name", "Ukjent navn")
    return navn

def hent_publikasjoner(cristin_id, navn):
    url = (
        f"{CRISTIN_API_BASE}/results?"
        f"contributor={INSTITUSJON}/{cristin_id}&"
        f"from_year={START_YEAR}&to_year={END_YEAR}"
    )
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Feil ved henting av publikasjoner for {cristin_id} ({response.status_code})")
        return []

    publikasjoner = response.json()
    resultatliste = []
    for pub in publikasjoner:
        tittel = pub.get("title", {}).get("nb") or pub.get("title", {}).get("en") or "(Uten tittel)"
        journal = ""
        if pub.get("journal"):
            journal = pub["journal"].get("name", {}).get("nb") or pub["journal"].get("name", {}).get("en", "")
        resultatliste.append({
            "Cristin-ID": cristin_id,
            "Navn": navn,
            "Tittel på publikasjon": tittel,
            "Tidsskrift / Journal": journal,
            "År": pub.get("year_published", ""),
            "Type": pub.get("category", ""),
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
    print(f"{len(publikasjoner)} publikasjoner lagret i '{filnavn}'.")

def main():
    cristin_ids = les_cristin_ids(CRISTIN_ID_FIL)
    alle_publikasjoner = []
    for cristin_id in cristin_ids:
        print(f"Henter data for Cristin-ID: {cristin_id} ...")
        navn = hent_personnavn(cristin_id)
        pubs = hent_publikasjoner(cristin_id, navn)
        alle_publikasjoner.extend(pubs)
    lagre_csv(alle_publikasjoner, OUTPUT_FILE)

if __name__ == "__main__":
    main()

