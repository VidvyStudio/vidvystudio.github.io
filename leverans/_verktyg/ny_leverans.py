#!/usr/bin/env python3
"""Skapar en lösenordsskyddad leveranssida under leverans/ på vidvystudio.se.

Användning:
    python3 leverans/_verktyg/ny_leverans.py kund.json [--losenord LÖSENORD] [--okrypterad-till MAPP]

kund.json (exempel finns i leverans/_verktyg/exempel.json):
    kund         Visas som "Leverans till ...".
    slug         Början på adressen, t.ex. "birka". En slumpad del läggs till
                 så att adressen inte går att gissa. Sätt "adress" för att
                 återanvända en befintlig mapp (vid uppdatering).
    rubrik       Sidans rubrik, t.ex. "Drönarfilm för Birka".
    datumrad     T.ex. "Filmat 12 augusti 2026 · Levererat 17 november 2026".
    namn         Kontaktpersonens förnamn, används i hälsningen (valfritt).
    halsning     Egen hälsning i stället för standardtexten (valfritt).
    status       "klar" eller "forhandsversion".
    media        Lista med {"typ": "video"|"bild", "src": ..., "poster": ..., "titel": ...}.
                 En lokal fil kopieras in i sidans mapp. Håll videor små
                 (under ca 50 MB), de ligger i hemsidans lagring.
    filer        Lista med {"namn": ..., "detalj": ...} (visas vid status "klar").
    nedladdning  {"url": ..., "tjanst": "SwissTransfer", "giltig_till": "...", "losenord": "..."}.
    omdome       false för att inte be om ett omdöme på Google (valfritt). Annars
                 visas rutan på färdiga leveranser när OMDOME_URL nedan är ifylld.

Lösenordet till sidan skapas slumpmässigt om det inte anges. Skriptet skriver ut
adressen, lösenordet och en direktlänk som öppnar sidan utan att kunden skriver
lösenordet. Den oskyddade versionen sparas utanför repot och ska inte committas.
"""

import argparse
import html
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import quote

REPO = Path(__file__).resolve().parents[2]
LEVERANS = REPO / "leverans"
MALL = LEVERANS / "_mall.html"
LOSENORDSMALL = LEVERANS / "_losenord.html"
SITE = "https://vidvystudio.se"
STATICRYPT = "staticrypt@3.5.4"

# Länken där kunden skriver ett omdöme om Vidvy Studio på Google. Hämtas från
# Google-företagsprofilen ("Be om omdömen"). Tom = ingen omdömesruta.
OMDOME_URL = ""

# Utan tecken som är lätta att blanda ihop (0/o, 1/l/i).
TECKEN = "abcdefghjkmnpqrstuvwxyz23456789"

LADDA_NER_IKON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
    '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>'
)
STJARNA_IKON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
    '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9z"/></svg>'
)
MEJL_IKON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
    '<rect x="3" y="5" width="18" height="14" rx="1"/><path d="m3 7 9 6 9-6"/></svg>'
)


def e(text):
    return html.escape(str(text), quote=True)


def slumpa(n):
    return "".join(secrets.choice(TECKEN) for _ in range(n))


def nytt_losenord():
    return "-".join(slumpa(4) for _ in range(4))


def slugga(text):
    byt = str.maketrans({"å": "a", "ä": "a", "ö": "o", "é": "e", " ": "-"})
    ren = "".join(c for c in text.lower().translate(byt) if c.isalnum() or c == "-")
    return "-".join(filter(None, ren.split("-"))) or "leverans"


def media_html(media, mapp):
    delar = []
    for m in media:
        src = m["src"]
        poster = m.get("poster", "")
        for falt in ("src", "poster"):
            vag = m.get(falt, "")
            if vag and not vag.startswith(("/", "http://", "https://")):
                kalla = Path(vag).expanduser()
                if not kalla.exists():
                    sys.exit(f"Hittar inte filen {kalla}")
                shutil.copy2(kalla, mapp / kalla.name)
                if falt == "src":
                    src = kalla.name
                else:
                    poster = kalla.name
        titel = e(m.get("titel", ""))
        if m.get("typ", "video") == "video":
            poster_attr = f' poster="{e(poster)}"' if poster else ""
            delar.append(
                f'        <div class="lev-media">\n'
                f'            <video controls playsinline preload="metadata"{poster_attr} aria-label="{titel}">\n'
                f'                <source src="{e(src)}" type="video/mp4">\n'
                f"            </video>\n"
                f"        </div>"
            )
        else:
            delar.append(
                f'        <div class="lev-media">\n'
                f'            <img src="{e(src)}" alt="{titel}">\n'
                f"        </div>"
            )
    return "\n".join(delar)


def huvudruta(cfg):
    if cfg["status"] == "forhandsversion":
        amne = quote(f"Ändringar: {cfg['rubrik']}")
        return (
            '            <section class="lev-card is-main" aria-labelledby="nasta-steg">\n'
            '                <h2 id="nasta-steg">Vad händer nu</h2>\n'
            "                <p>Titta igenom filmen och säg till om du vill ändra något. "
            "Det blir enklast om du skriver var i filmen det gäller, till exempel "
            "&rdquo;0:42, byt till ett annat klipp&rdquo;.</p>\n"
            f'                <a class="lev-button lev-button-gap" href="mailto:kontakt@vidvystudio.se?subject={amne}">'
            f"{MEJL_IKON}Skicka ändringar</a>\n"
            "                <p class=\"lev-note\">Ser allt bra ut räcker det att svara på mejlet och skriva det.</p>\n"
            "            </section>"
        )

    ned = cfg["nedladdning"]
    rader = "\n".join(
        f'                    <li><span class="file-name">{e(f["namn"])}</span>'
        f'<span class="file-meta">{e(f.get("detalj", ""))}</span></li>'
        for f in cfg.get("filer", [])
    )
    lista = f'                <ul class="lev-files">\n{rader}\n                </ul>\n' if rader else ""
    tjanst = e(ned.get("tjanst", "SwissTransfer"))
    notis = f"Filerna ligger hos {tjanst}, som jag använder för stora filer."
    if ned.get("giltig_till"):
        notis += f" Länken gäller till och med {e(ned['giltig_till'])}."
    if ned.get("losenord"):
        notis += f' Lösenord där:<span class="lev-code">{e(ned["losenord"])}</span>'
    return (
        '            <section class="lev-card is-main" aria-labelledby="filer">\n'
        '                <h2 id="filer">Filer</h2>\n'
        f"{lista}"
        f'                <a class="lev-button" href="{e(ned["url"])}" target="_blank" rel="noopener noreferrer">'
        f"{LADDA_NER_IKON}Ladda ner alla filer</a>\n"
        f'                <p class="lev-note">{notis}</p>\n'
        "            </section>"
    )


def fakta(cfg):
    if cfg["status"] == "forhandsversion":
        punkter = [
            "Förhandsversionen har vattenmärke.",
            "En ändringsrunda ingår. Skriv gärna allt du vill ändra i samma mejl.",
            "Har jag inte hört något inom 14 dagar räknas förhandsversionen som godkänd.",
            "Originalfilerna kommer hit när fakturan är betald.",
        ]
    else:
        punkter = [
            "Spara en egen kopia av filerna. Jag sparar inte materialet hur länge som helst.",
            'Du får använda materialet fritt, privat eller i din verksamhet. Mer om det står i '
            '<a href="/villkor.html#ratt-att-anvanda-materialet">villkoren</a>.',
            "Lägger du upp filmen går det bra att tagga @vidvystudio.",
            'Frågor? Svara på mejlet eller skriv till '
            '<a href="mailto:kontakt@vidvystudio.se">kontakt@vidvystudio.se</a>.',
        ]
    return "\n".join(f"                    <li>{p}</li>" for p in punkter)


def halsning(cfg):
    if cfg.get("halsning"):
        return e(cfg["halsning"])
    hej = f"Hej {cfg['namn']}!" if cfg.get("namn") else "Hej!"
    if cfg["status"] == "forhandsversion":
        return f"{e(hej)} Här är förhandsversionen. Titta igenom den och säg till om du vill ändra något."
    if cfg.get("media"):
        return f"{e(hej)} Här är den färdiga filmen. Du kan titta på den här och ladda ner originalfilerna nedan."
    return f"{e(hej)} Här är filerna från uppdraget. Du laddar ner dem nedan."


def bygg_sida(cfg, mapp):
    status = (
        '<span class="lev-status is-preview">Förhandsversion</span>'
        if cfg["status"] == "forhandsversion"
        else '<span class="lev-status">Klar att ladda ner</span>'
    )
    ersatt = {
        "{{SIDTITEL}}": e(cfg["rubrik"]),
        "{{OVERRAD}}": e(f"Leverans till {cfg['kund']}"),
        "{{RUBRIK}}": e(cfg["rubrik"]),
        "{{DATUMRAD}}": e(cfg.get("datumrad", "")),
        "{{STATUS}}": status,
        "{{HALSNING}}": halsning(cfg),
        "{{MEDIA}}": media_html(cfg.get("media", []), mapp),
        "{{HUVUDRUTA}}": huvudruta(cfg),
        "{{FAKTA}}": fakta(cfg),
        "{{OMDOME}}": omdome(cfg),
        "{{AR}}": str(date.today().year),
    }
    sida = MALL.read_text(encoding="utf-8")
    sida = sida.split("-->", 1)[1].lstrip() if sida.startswith("<!DOCTYPE html>\n<!--") else sida
    if not sida.startswith("<!DOCTYPE"):
        sida = "<!DOCTYPE html>\n" + sida
    for nyckel, varde in ersatt.items():
        sida = sida.replace(nyckel, varde)
    if "{{" in sida:
        sys.exit("Mallen har platshållare kvar: " + sida[sida.index("{{"):][:40])
    return sida


def omdome(cfg):
    if cfg["status"] != "klar" or cfg.get("omdome") is False:
        return ""
    if not OMDOME_URL:
        print("Obs: OMDOME_URL är tom, så sidan får ingen omdömesruta.", file=sys.stderr)
        return ""
    return (
        '        <section class="lev-review" aria-labelledby="omdome">\n'
        '            <div>\n'
        '                <h2 id="omdome">Blev du nöjd?</h2>\n'
        "                <p>Ett kort omdöme på Google betyder mycket för ett litet företag som mitt. "
        "Det tar en minut och hjälper andra att hitta mig.</p>\n"
        "            </div>\n"
        f'            <a class="lev-button lev-button-green" href="{e(OMDOME_URL)}" target="_blank" rel="noopener noreferrer">'
        f"{STJARNA_IKON}Skriv ett omdöme på Google</a>\n"
        "        </section>"
    )


def kryptera(okrypterad, mapp, losenord, rubrik):
    salt = secrets.token_hex(16)
    miljo = {**os.environ, "STATICRYPT_PASSWORD": losenord}
    with tempfile.TemporaryDirectory() as tmp:
        kalla = Path(tmp) / "index.html"
        kalla.write_text(okrypterad, encoding="utf-8")
        ut = Path(tmp) / "ut"
        bas = ["npx", "--yes", STATICRYPT, str(kalla), "-c", "false", "--salt", salt]
        mall = [
            "-d", str(ut),
            "-t", str(LOSENORDSMALL),
            "--remember", "30",
            "--template-title", rubrik,
            "--template-instructions", "Skriv lösenordet från mejlet för att öppna sidan.",
            "--template-button", "Öppna",
            "--template-placeholder", "Lösenord",
            "--template-error", "Fel lösenord. Kolla mejlet och försök igen.",
            "--template-remember", "Kom ihåg mig på den här enheten",
            "--template-toggle-show", "Visa lösenord",
            "--template-toggle-hide", "Dölj lösenord",
        ]
        res = subprocess.run(bas + mall, capture_output=True, text=True, env=miljo)
        if res.returncode != 0 or not (ut / "index.html").exists():
            sys.exit(res.stderr or res.stdout or "StatiCrypt skapade ingen fil")
        shutil.copy2(ut / "index.html", mapp / "index.html")

        # Samma salt ger en direktlänk som öppnar sidan utan att kunden skriver lösenordet.
        dela = subprocess.run(
            bas + ["--share", f"{SITE}/leverans/{mapp.name}/"],
            capture_output=True, text=True, env=miljo,
        )
        return next((ord_ for ord_ in dela.stdout.split() if "#staticrypt_pwd=" in ord_), None)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config")
    ap.add_argument("--losenord")
    ap.add_argument("--okrypterad-till", default="/mnt/project-files/leverans/okrypterade")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    for falt in ("kund", "rubrik", "status"):
        if falt not in cfg:
            sys.exit(f"Saknar fältet {falt} i {args.config}")
    if cfg["status"] not in ("klar", "forhandsversion"):
        sys.exit('status ska vara "klar" eller "forhandsversion"')
    if cfg["status"] == "klar" and not cfg.get("nedladdning", {}).get("url"):
        sys.exit("Status klar kräver nedladdning.url")

    adress = cfg.get("adress") or f"{slugga(cfg.get('slug') or cfg['kund'])}-{slumpa(8)}"
    mapp = LEVERANS / adress
    mapp.mkdir(parents=True, exist_ok=True)

    okrypterad = bygg_sida(cfg, mapp)
    losenord = args.losenord or nytt_losenord()
    direkt = kryptera(okrypterad, mapp, losenord, cfg["rubrik"])

    spara = Path(args.okrypterad_till) / adress
    spara.mkdir(parents=True, exist_ok=True)
    (spara / "index.html").write_text(okrypterad, encoding="utf-8")

    print(f"Mapp:        leverans/{adress}/")
    print(f"Adress:      {SITE}/leverans/{adress}/")
    print(f"Lösenord:    {losenord}")
    if direkt:
        print(f"Direktlänk:  {direkt}")
    print(f"Oskyddad kopia (committa inte): {spara / 'index.html'}")


if __name__ == "__main__":
    main()
