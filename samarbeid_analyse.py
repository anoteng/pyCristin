import requests
import argparse
from collections import defaultdict, Counter
from datetime import datetime
import pandas as pd
import time

CRISTIN_API_BASE = "https://api.cristin.no/v2"

kontinent_mapping = {
    "Africa": ["DZ", "AO", "EG", "ET", "KE", "NG", "ZA", "TZ", "UG", "ZM", "ZW"],
    "Asia": ["CN", "IN", "ID", "JP", "KR", "MY", "PH", "SG", "TH", "VN", "IL", "IR", "SA"],
    "Europe": ["NO", "SE", "DK", "FI", "DE", "FR", "NL", "BE", "UK", "CH", "IT", "ES", "PT", "PL"],
    "North America": ["US", "CA", "MX"],
    "South America": ["AR", "BR", "CL", "CO", "PE"],
    "Oceania": ["AU", "NZ"]
}

land_til_kontinent = {kode: kontinent for kontinent, koder in kontinent_mapping.items() for kode in koder}

PEER_REVIEWED_CATEGORIES = {"ARTICLE", "ACADEMICREVIEW", "ARTICLEJOURNAL"}

def hent_med_retry(url):
    for _ in range(3):
        resp = requests.get(url)
        if resp.status_code == 503:
            time.sleep(2)
        else:
            return resp
    return resp

def hent_publikasjoner(unit_id, start_year, end_year):
    page = 1
    results = []
    while True:
        url = f"{CRISTIN_API_BASE}/units/{unit_id}/results?page={page}&per_page=100"
        resp = hent_med_retry(url)
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        for entry in data:
            year = int(entry.get("year_published", 0))
            cat_code = entry.get("category", {}).get("code", "")
            if start_year <= year <= end_year and cat_code in PEER_REVIEWED_CATEGORIES:
                results.append(entry)
        page += 1
    return results

def hent_landkode_og_navn(unit):
    if not unit:
        return None, None
    unit_url = unit.get("url")
    if unit_url:
        resp = hent_med_retry(unit_url)
        if resp.status_code == 200:
            data = resp.json()
            landkode = data.get("country")
            inst = data.get("institution", {})
            if inst:
                inst_url = inst.get("url")
                inst_resp = hent_med_retry(inst_url)
                if inst_resp.status_code == 200:
                    inst_data = inst_resp.json()
                    navn = inst_data.get("institution_name", {}).get("en") or inst_data.get("institution_name", {}).get("nb")
                    return landkode, navn
    return None, None

def hent_inst_landkode_og_navn(inst):
    if not inst:
        return None, None
    inst_url = inst.get("url")
    if inst_url:
        resp = hent_med_retry(inst_url)
        if resp.status_code == 200:
            data = resp.json()
            landkode = data.get("country_code")
            navn = data.get("institution_name", {}).get("en") or data.get("institution_name", {}).get("nb")
            return landkode, navn
    return None, None

def hent_eget_universitetsnavn(unit_id):
    url = f"{CRISTIN_API_BASE}/units/{unit_id}"
    resp = hent_med_retry(url)
    if resp.status_code != 200:
        return None
    data = resp.json()
    inst = data.get("institution", {})
    if inst:
        inst_url = inst.get("url")
        inst_resp = hent_med_retry(inst_url)
        if inst_resp.status_code == 200:
            inst_data = inst_resp.json()
            navn = inst_data.get("institution_name", {}).get("en") or inst_data.get("institution_name", {}).get("nb")
            return navn
    return None

def analyser_samarbeid(publikasjoner, eget_universitet):
    uten = 0
    nasjonale = 0
    internasjonale = 0
    institusjoner = set()
    institusjonsteller = Counter()
    kontinent_teller = defaultdict(set)

    for pub in publikasjoner:
        result_id = pub.get("cristin_result_id")
        contributors_url = f"{CRISTIN_API_BASE}/results/{result_id}/contributors"
        resp = hent_med_retry(contributors_url)
        if resp.status_code != 200:
            continue
        personer = resp.json()
        landkoder = set()
        inst_navn = set()

        for p in personer:
            affil = p.get("affiliations", [])
            for a in affil:
                unit = a.get("unit", {})
                inst = a.get("institution", {})

                ccu, nu = hent_landkode_og_navn(unit)
                cci, ni = hent_inst_landkode_og_navn(inst)

                if ccu:
                    landkoder.add(ccu)
                    if nu and nu != eget_universitet:
                        inst_navn.add(nu)
                elif cci:
                    landkoder.add(cci)
                    if ni and ni != eget_universitet:
                        inst_navn.add(ni)

        if not inst_navn:
            uten += 1
        elif landkoder == {"NO"}:
            nasjonale += 1
        else:
            internasjonale += 1
            for kode in landkoder:
                kontinent = land_til_kontinent.get(kode, "Ukjent")
                kontinent_teller[kode].add(result_id)
            for navn in inst_navn:
                institusjoner.add(navn)
                institusjonsteller[navn] += 1

    return {
        "uten": uten,
        "nasjonale": nasjonale,
        "internasjonale": internasjonale,
        "institusjonsteller": institusjonsteller,
        "kontinent_teller": {k: len(v) for k, v in kontinent_teller.items()},
        "antall_institusjoner": len(institusjoner)
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit", required=True)
    parser.add_argument("--start", type=int, default=2018)
    parser.add_argument("--end", type=int, default=2024)
    args = parser.parse_args()

    pub = hent_publikasjoner(args.unit, args.start, args.end)
    print(f"🔍 Antall peer reviewed publikasjoner funnet: {len(pub)}")

    eget_universitet = hent_eget_universitetsnavn(args.unit)
    stats = analyser_samarbeid(pub, eget_universitet)

    print("\n📊 Oppsummering av samarbeid:")
    print(f"Uten samarbeidspartnere: {stats['uten']}")
    print(f"Kun nasjonale samarbeidspartnere: {stats['nasjonale']}")
    print(f"Internasjonale samarbeidspartnere: {stats['internasjonale']}")
    print(f"Antall unike institusjoner: {stats['antall_institusjoner']}")

    print("\n🌍 Samarbeid per kontinent:")
    for k, v in stats['kontinent_teller'].items():
        print(f"{k}: {v} artikler")

    print("\n🏫 Topp 10 samarbeidende institusjoner:")
    for navn, ant in stats['institusjonsteller'].most_common(10):
        print(f"{navn}: {ant}")

if __name__ == "__main__":
    main()

