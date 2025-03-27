import argparse
import requests
import pandas as pd
from datetime import datetime
import time

CRISTIN_API_BASE = "https://api.cristin.no/v2"


def hent_med_retry(url, params=None, debug=False, max_retries=3, delay=3):
    for attempt in range(max_retries):
        if debug:
            if params:
                print(f"🔎 GET {url} | params={params}")
            else:
                print(f"🔎 GET {url}")

        resp = requests.get(url, params=params)
        if resp.status_code == 503:
            print(f"⚠️  503 mottatt – prøver igjen om {delay} sekunder (forsøk {attempt + 1} av {max_retries})")
            time.sleep(delay)
        else:
            return resp
    return resp


def hent_publikasjoner_for_unit(unit_id, startaar, sluttaar, debug=False, lite=False):
    print(f"Henter fra unit {unit_id} ({startaar} til {sluttaar})...")
    side = 1
    per_page = 100
    alle_resultater = []

    while True:
        url = f"{CRISTIN_API_BASE}/units/{unit_id}/results"
        params = {
            "page": side,
            "per_page": per_page,
            "sort": "year_published",
            "order": "desc"
        }

        resp = hent_med_retry(url, params=params, debug=debug)
        if resp.status_code != 200:
            print(f"❌ Feil ved kall til API (side {side}): {resp.status_code}")
            break

        resultater = resp.json()
        if not resultater:
            break

        for pub in resultater:
            try:
                aar = int(pub.get("year_published", 0))
            except:
                continue

            if not (startaar <= aar <= sluttaar):
                continue

            resultat_id = pub.get("cristin_result_id")

            if lite:
                tittel = pub.get("title", {}).get(pub.get("original_language", ""), "(Uten tittel)")
                kategori = pub.get("category", {}).get("name", {}).get("en", "")
                publiseringssted = (
                    pub.get("channel", {}).get("title") or
                    pub.get("journal", {}).get("name") or
                    pub.get("publisher", {}).get("name") or
                    pub.get("place") or
                    pub.get("event", {}).get("name") or
                    "Ukjent"
                )
                nvi = "-"
                contributors = [
                    f"{c.get('first_name', '')} {c.get('surname', '')}".strip()
                    for c in pub.get("contributors", {}).get("preview", [])
                ]
                resultat_url = pub.get("url", "")
            else:
                detaljer_url = f"{CRISTIN_API_BASE}/results/{resultat_id}"
                detaljer_resp = hent_med_retry(detaljer_url, debug=debug)
                if detaljer_resp.status_code != 200:
                    continue
                detaljer = detaljer_resp.json()

                tittel = detaljer.get("title", {}).get(detaljer.get("original_language", ""), "(Uten tittel)")
                kategori = detaljer.get("category", {}).get("name", {}).get("en", "")

                # NVI-nivå
                nvi = "-"
                journal = detaljer.get("journal", {})
                if isinstance(journal, dict):
                    nvi = journal.get("nvi_level") or journal.get("publisher", {}).get("nvi_level") or "-"

                # Publiseringssted
                publiseringssted = (
                    detaljer.get("channel", {}).get("title") or
                    detaljer.get("journal", {}).get("name") or
                    detaljer.get("publisher", {}).get("name") or
                    detaljer.get("place") or
                    detaljer.get("event", {}).get("name") or
                    "Ukjent"
                )

                # Contributors (fullt)
                contributors_url = f"{CRISTIN_API_BASE}/results/{resultat_id}/contributors"
                contrib_resp = hent_med_retry(contributors_url, debug=debug)
                contributors = []
                if contrib_resp.status_code == 200:
                    for c in contrib_resp.json():
                        navn = f"{c.get('first_name', '')} {c.get('surname', '')}".strip()
                        cid = c.get("cristin_person_id", "")
                        if cid:
                            contributors.append(f"{navn} (ID: {cid})")
                        else:
                            contributors.append(navn)

                resultat_url = detaljer.get("url", "")

            alle_resultater.append({
                "Cristin Resultat-ID": resultat_id,
                "Tittel": tittel,
                "År": aar,
                "Kategori": kategori,
                "Publiseringssted / Kanal": publiseringssted,
                "NVI-nivå": nvi,
                "Bidragsytere": "; ".join(contributors),
                "Resultat-URL": resultat_url
            })

            time.sleep(0.1)  # Skånsom pacing mot API

        side += 1

    return alle_resultater


def lagre_resultater(resultater, filformat):
    df = pd.DataFrame(resultater)
    navn = f"unit_publikasjoner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{filformat}"
    if filformat == "csv":
        df.to_csv(navn, index=False)
    else:
        df.to_excel(navn, index=False)
    print(f"✅ Lagret til {navn}")


def main():
    parser = argparse.ArgumentParser(description="Hent Cristin-publikasjoner for en unit.")
    parser.add_argument("--unit", required=True, help="Cristin Unit-ID, f.eks. 192.11.0.0")
    parser.add_argument("--start", type=int, default=2015, help="Startår")
    parser.add_argument("--end", type=int, default=datetime.now().year, help="Sluttår")
    parser.add_argument("--format", choices=["csv", "xlsx"], default="csv", help="Filformat")
    parser.add_argument("--debug", action="store_true", help="Skriv ut API-kall")
    parser.add_argument("--lite", action="store_true", help="Unngå ekstra detaljkall for raskere uthenting")
    args = parser.parse_args()

    data = hent_publikasjoner_for_unit(args.unit, args.start, args.end, args.debug, args.lite)
    lagre_resultater(data, args.format)


if __name__ == "__main__":
    main()

