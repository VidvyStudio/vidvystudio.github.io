#!/usr/bin/env python3
"""Hämtar Lantmäteriets uppskattade handläggningstid för spridningstillstånd
och skriver in den på hemsidan.

Texten byts där sidorna har <span data-lm-tid>...</span> (tiden) och
<span data-lm-datum>...</span> (datumet då den kollades).

Körs varje måndag av .github/workflows/handlaggningstid.yml. För hand:
    python3 _verktyg/handlaggningstid.py             hämtar från lantmateriet.se
    python3 _verktyg/handlaggningstid.py --dagar 60  sätter tiden själv

Lantmäteriets sidor anger ibland olika tider (2026-11-23: 45 arbetsdagar på
startsidan, 60 under vanliga frågor). Då används den längsta, så att sidan
inte lovar för kort tid. Hittas ingen tid ändras inget och skriptet avslutas
med fel, så att GitHub skickar ett mejl om att körningen misslyckades.
"""
import argparse
import datetime
import html
import pathlib
import re
import sys
import urllib.request
from zoneinfo import ZoneInfo

KALLOR = [
    "https://www.lantmateriet.se/sv/spridningstillstand/vanliga-fragor/",
    "https://www.lantmateriet.se/sv/spridningstillstand/ansokan/",
    "https://www.lantmateriet.se/sv/spridningstillstand/",
]
ROT = pathlib.Path(__file__).resolve().parent.parent
TAL = {1: "en", 2: "två", 3: "tre", 4: "fyra", 5: "fem", 6: "sex", 7: "sju",
       8: "åtta", 9: "nio", 10: "tio", 11: "elva", 12: "tolv"}
MANADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli",
           "augusti", "september", "oktober", "november", "december"]
TID_RE = re.compile(r"(<span data-lm-tid>)(.*?)(</span>)", re.S)
DATUM_RE = re.compile(r"(<span data-lm-datum>)(.*?)(</span>)", re.S)


def som_text(sida):
    sida = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", sida)
    sida = re.sub(r"<[^>]+>", " ", sida)
    return re.sub(r"\s+", " ", html.unescape(sida))


def dagar_i(text):
    """Alla "ca 60 arbetsdagar", "cirka 45 arbetsdagar" och liknande i texten."""
    return [int(d) for d in re.findall(
        r"(?:ca\.?|cirka|omkring|ungefär)\s*(\d{1,3})\s*arbetsdagar", text, re.I)]


def meningar(text):
    """Meningarna som nämner arbetsdagar eller vilken vecka de handlägger, för loggen."""
    hittade = re.findall(r"[^.!?]{0,200}?(?:arbetsdagar|vecka \d{1,2})[^.!?]{0,200}[.!?]", text)
    return list(dict.fromkeys(m.strip() for m in hittade))


def hamta(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; vidvystudio.se, veckovis koll av handläggningstid)"})
    with urllib.request.urlopen(req, timeout=30) as svar:
        return svar.read().decode("utf-8", errors="replace")


def beskrivning(dagar):
    """60 -> 'cirka 60 arbetsdagar, knappt tre månader'."""
    veckor = dagar / 5
    if veckor < 7.5:
        n = max(1, round(veckor))
        return f"cirka {dagar} arbetsdagar, ungefär {TAL[n]} {'vecka' if n == 1 else 'veckor'}"
    manader = dagar / 21  # ungefär 21 arbetsdagar i månaden
    n = min(12, round(manader))
    if abs(manader - n) < 0.1:
        ord_ = "ungefär"
    elif manader < n:
        ord_ = "knappt"
    else:
        ord_ = "drygt"
    return f"cirka {dagar} arbetsdagar, {ord_} {TAL[n]} {'månad' if n == 1 else 'månader'}"


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--dagar", type=int, help="sätt tiden själv i stället för att hämta den")
    args = p.parse_args()

    if args.dagar:
        dagar = args.dagar
    else:
        hittade = {}
        for url in KALLOR:
            try:
                text = som_text(hamta(url))
            except Exception as fel:  # en sida som inte svarar får inte stoppa de andra
                print(f"Kunde inte läsa {url}: {fel}", file=sys.stderr)
                continue
            d = dagar_i(text)
            print(f"{url}: {d or 'ingen tid hittad'}")
            for m in meningar(text):
                print(f"    {m}")
            if d:
                hittade[url] = max(d)
        if not hittade:
            sys.exit("Hittade ingen handläggningstid hos Lantmäteriet. Inget ändrat.")
        dagar = max(hittade.values())

    if not 5 <= dagar <= 250:
        sys.exit(f"{dagar} arbetsdagar verkar fel. Inget ändrat.")

    idag = datetime.datetime.now(ZoneInfo("Europe/Stockholm")).date()
    tid = beskrivning(dagar)
    datum = f"{idag.day} {MANADER[idag.month - 1]} {idag.year}"
    print(f"Handläggningstid: {tid} (kollat {datum})")

    for fil in sorted(ROT.glob("*.html")):
        gammal = fil.read_text(encoding="utf-8")
        ny = TID_RE.sub(lambda m: m.group(1) + tid + m.group(3), gammal)
        ny = DATUM_RE.sub(lambda m: m.group(1) + datum + m.group(3), ny)
        if ny != gammal:
            fil.write_text(ny, encoding="utf-8")
            print(f"Uppdaterade {fil.name}")


if __name__ == "__main__":
    main()
