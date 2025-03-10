import pandas as pd
import os

# === KONFIGURASJON ===
INPUT_CSV = "cristin_publikasjoner_kategoriadaptiv.csv"
OUTPUT_DIR = "excel_per_person"

# === Lag output-katalog om den ikke finnes ===
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Les hele CSV-filen ===
df = pd.read_csv(INPUT_CSV)

# === Gruppér etter person og lag én Excel-fil per person ===
for (cristin_id, navn), gruppe in df.groupby(["Cristin-ID", "Navn"]):
    # Del opp navn i fornavn og etternavn
    navn_deler = navn.strip().split()
    if len(navn_deler) >= 2:
        etternavn = navn_deler[-1]
        fornavn = " ".join(navn_deler[:-1])
    else:
        etternavn = navn
        fornavn = ""

    # Sett filnavn: "publikasjoner - Etternavn, Fornavn.xlsx"
    safe_fornavn = fornavn.replace("/", "_").replace("\\", "_")
    safe_etternavn = etternavn.replace("/", "_").replace("\\", "_")
    filnavn = f"{OUTPUT_DIR}/publikasjoner - {safe_etternavn}, {safe_fornavn}.xlsx".strip().replace(" ,", ",")

    # Lag Excel-fil
    gruppe.to_excel(filnavn, index=False)
    print(f"✅ Lagret: {filnavn}")

print("🎯 Ferdig!")

