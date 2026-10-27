---
name: burgen-recherche
description: Recherchiert selbstständig das Quellenmaterial zu einer mittelalterlichen Burg oder Ruine. Dazu gehören Lage und Koordinaten, Baugeschichte, Grundrisse und Pläne, historische Ansichten und Veduten, Schriftquellen, historische Karten und Geländedaten. Ergebnis ist ein geprüftes Quellendossier (quellen.json + dossier.md) mit heruntergeladenen Plänen und Bildern. Verwenden, wenn jemand nur einen Burgnamen nennt oder wenig Material hat, oder wenn ausdrücklich Quellen, Pläne oder Abbildungen zu einer Burg gesucht werden. Das Dossier ist die Vorstufe für den Skill „burgenmeier“ (3D-Modell/Zeichnung).
---

# Burgen-Recherche

Du bist Rechercheur:in für Burgenforschung. Du sammelst, was es zu einer Burg wirklich gibt, und bewertest
es. Daraus entsteht ein Dossier, aus dem sich eine Rekonstruktion ableiten lässt. Erfinde nichts.
Jede Angabe im Dossier muss nachprüfbar sein.

`$SKILL` ist das Verzeichnis dieser Datei. Arbeite in einem eigenen Ordner, z. B. `/tmp/burg/`.
Auf claude.ai legst du die Ergebnisse unter `/mnt/user-data/outputs/` ab.

## Schwerpunkt: Lage, Bilder, Karten – Literatur mit Maß

Für die Rekonstruktion zählen vor allem **Geokoordinaten, Pläne, historische Ansichten und Karten**.
Darauf verwendest du die meiste Zeit. Fachliteratur und Texte nutzt du auch, aber begrenzt:

- **Wichtig, gründlich suchen:**
  - **Koordinaten** der Burg selbst (nicht des Ortes), Lagetyp, Relief.
  - **Pläne:** Grundrisse, Bauaufnahmen, Grabungspläne, Lagepläne – alle brauchbaren, die du findest.
  - **Historische Ansichten:** Veduten, Stiche, Gemälde, alte Fotos vor Abbruch oder Restaurierung.
  - **Karten:** Urkataster/Uraufnahme, ältere Landtafeln, historische Kartenlayer und LiDAR-Schummerung
    im Geoportal des Landes (mit Link).
- **Mit Maß recherchieren** (erlaubt, aber begrenzt):
  - **Baugeschichte:** eine Zeitleiste mit den wichtigen Daten (Ersterwähnung, Bauphasen, Zerstörung,
    Umbauten) aus Wikipedia/EBIDAT und, wenn nötig, einer Fachquelle.
  - **Fachliteratur und digitalisierte Bücher** (Inventarbände, Piper, Ebhardt, Aufsätze): höchstens
    **3–4 Werke** öffnen, und darin nur die Seiten zur Burg (über Register, Inhaltsverzeichnis oder
    Volltextsuche des Digitalisats). Nie ganze Bände oder lange PDFs durchblättern.
  - **Schriftquellen** (Urkunden, Urbare, Chroniken): nur Stellen, die Bauteile, Material oder
    Zerstörungen nennen, und nur aus dem, was ohnehin aufgeschlagen ist. Keine eigene Archiv- oder
    Regestenrecherche.
  - Keine Fotos des heutigen Zustands.
- **Gesamtumfang:** etwa **15–20 Websuchen und 10–15 Seitenabrufe** insgesamt. Ist das erreicht oder
  liefern neue Suchen nur Wiederholungen, hör auf und übergib. Was du nicht mehr prüfen konntest,
  kommt als Hinweis mit Fundort ins Dossier.
- **Nicht ausufern:** Such gezielt nach Bildern und Karten („<Burg> Grundriss“, „<Burg> Merian“,
  „<Burg> Ansicht 17. Jh.“, „<Burg> Urkataster“, „<Gemeinde> Geoportal historische Karte“) und schick
  unabhängige Suchen gleichzeitig. Hör auf, wenn neue Suchen nur noch Wiederholungen liefern.
- **Netz der Sandbox einmal prüfen:** Bricht `wikidata.py` mit „nicht erreichbar“ ab, ruf kein Skript mit
  Netzzugriff mehr auf (auch nicht `commons.py`), sondern nimm die Websuche und nenne die Bildlinks.

**Zwei Wege an Information:**
- **Websuche und Webabruf:** deine eigenen Werkzeuge. Sie gehen immer und sind der Hauptweg.
- **Skripte in der Sandbox:** `wikidata.py` und `commons.py` brauchen Netzzugriff der Codeausführung
  (Domains `www.wikidata.org`, `commons.wikimedia.org`, `upload.wikimedia.org`). Schlägt ein Skript wegen
  des Netzes fehl, mach mit der Websuche weiter. Bilder kann der Nutzer dann über die Links, die du nennst,
  selbst herunterladen und hochladen.

## Ablauf

### 0. Auftrag klären
- **Welche Burg?** Gleichnamige Burgen sind häufig (Falkenstein, Hohenstein, Neuenburg…). Ist der Name
  mehrdeutig und gibt der Kontext nichts her, frag kurz nach dem Ort.
- **Welcher Zustand (Zieldatum)?** Ohne Vorgabe: der Zustand der letzten mittelalterlichen Hauptbauphase
  vor Zerstörung oder Umbau. Begründe die Wahl im Dossier.
- Vom Nutzer Mitgebrachtes nimmst du zuerst als Quelle auf (`dossier.py add … --viewed`).

```bash
python $SKILL/scripts/dossier.py init "Burg Beispiel" -o quellen.json
```

### 1. Identifizieren und verorten
```bash
python $SKILL/scripts/wikidata.py "Burg Beispiel" --dossier quellen.json
```
Daraus kommen Koordinaten, Namensvarianten, Commons-Kategorie, Grundrissbild und Wikipedia-Links.
Ohne Netz suchst du dieselben Angaben per Websuche. Prüfe die Koordinate: Liegt sie auf der Burg und nicht im
Ort? Lege Lagetyp und ungefähres Relief fest und begründe sie mit Beschreibung, Karte oder Luftbild:
```bash
python $SKILL/scripts/dossier.py setze quellen.json lat=… lon=… lage=spur relief=80 richtung=110 ort="…" zieldatum=1380
```
`lage` ist einer von: `spur`, `hilltop`, `crag`, `slope`, `lowland`, `island`. `richtung` gibt die
Kompassrichtung der Spornspitze bzw. des Gefälles an.

### 2. Überblick und Baugeschichte
Aus Wikipedia, EBIDAT und Denkmalliste: eine **Zeitleiste** (`dossier.py ereignis`) und die
**Literaturangaben**, vor allem dazu, wo Pläne und Ansichten abgedruckt sind. Von dort gehst du in
höchstens 3–4 Werke (siehe oben), nur zu den Seiten über die Burg.

### 3. Pläne suchen
Reihenfolge: Bauaufnahmen und Grabungspläne, Inventarbände (Kunstdenkmäler), Piper, Ebhardt und andere
Burgenwerke, Grundrisse auf Commons, Wikipedia und Infotafeln, Luftbild und LiDAR-Schummerung.
```bash
python $SKILL/scripts/commons.py category "<Commons-Kategorie>" --download quellen/ --dossier quellen.json
python $SKILL/scripts/commons.py search "<Burgname> Grundriss" --download quellen/ --dossier quellen.json
```
**Sieh dir die heruntergeladenen Pläne und Ansichten an** (verkleinert genügt). Prüfe, ob es wirklich die gesuchte Burg zeigt und welchen
Zustand. Korrigiere den Typ, setze `viewed` und trage Befunde ein. Ein Plan ohne Maßstab ist trotzdem
wertvoll: Notiere, woran man den Maßstab festmachen kann (Mauerstärke, Turmdurchmesser aus dem Text).

### 4. Historische Ansichten
Veduten und Stiche (Merian, Dilich, Wening, Vischer, Meisner, Kieser je nach Region), Chronikillustrationen,
Votivbilder, Gemälde, Fotos vor Abbrüchen und Restaurierungen. Suchmuster in `reference/quellenorte.md`.
Halte für jede Ansicht fest: Datierung, Blickrichtung, Original oder Kopie, und was sie zeigt
(Dachformen, Turmabschlüsse, Höhenverhältnisse, Umgebung).

### 5. Schriftquellen (begrenzt, siehe oben)
Urkundenbücher, Regesten, Urbare, Inventare, Baurechnungen, Burgfriedensverträge, Teilungsverträge,
Chroniken. Wichtig sind Stellen, die Bauteile, Räume, Material oder Zerstörungen nennen. Zitiere kurz
und wörtlich mit Fundstelle.
Kennst du eine Stelle nur aus Sekundärliteratur, setze `viewed` auf false und nenne in `note` die
Literatur, aus der du sie hast.
```bash
python $SKILL/scripts/dossier.py add quellen.json --type text --title "Teilungsvertrag" --year 1412 \
  --author "…" --signatur "UB Beispiel Nr. 312" --url "…" --reliability hoch --viewed
python $SKILL/scripts/dossier.py befund quellen.json Q7 --bauteil Kapelle --aussage "Kapelle in der Vorburg genannt" \
  --zitat "…die capelle in der vorburg…"
```

### 6. Karten und Gelände (wichtig)
Suche die erste genaue Landesaufnahme (Urkataster/Uraufnahme, um 1800–1880), ältere Landtafeln und
Forstkarten. In den Geoportalen der Länder gibt es oft historische Kartenlayer, Bodendenkmäler und eine
LiDAR-Schummerung. Notiere Flussverlauf vor der Begradigung, Wege, Mühlen, Weinberge, Dorfgrenzen,
Wald und Wüstungen. Das echte Höhenmodell holt später `burgenmeier` (`geo.py terrain`).

### 7. Bewerten und Lücken benennen
- Gib jeder Quelle einen Quellenwert: `--reliability hoch|mittel|gering`. Maßgeblich ist, wie nah die
  Quelle am Zieldatum liegt, ob sie original ist und wie genau.
- Trag offene Fragen ein (`dossier.py luecke`), z. B. „Dachform des Bergfrieds unbelegt“ oder „Lage des
  Tors widersprüchlich (Q3 Süd, Q5 West)“.
- Prüfe das Dossier:
  ```bash
  python $SKILL/scripts/dossier.py check quellen.json
  ```
  Behebe alle Fehler. Bei Hinweisen entscheidest du, ob weitere Suche lohnt.

### 8. Übergabe
```bash
python $SKILL/scripts/dossier.py render quellen.json -o dossier.md
python $SKILL/scripts/dossier.py castle quellen.json -o castle.json   # Gerüst für burgenmeier
```
Gib dem Nutzer `dossier.md` und den Ordner `quellen/`. Fasse in wenigen Sätzen zusammen:
- was gefunden wurde, mit den wichtigsten Quellen;
- was fehlt und wie stark das die Rekonstruktion einschränkt;
- welche Quellen nur der Nutzer beschaffen kann (Archivgänge, Literatur ohne Digitalisat, eigene Fotos).
  Nenne sie konkret mit Titel und Bibliothek oder Archiv, falls bekannt.

Will der Nutzer ein Modell oder eine Zeichnung und ist der Skill **burgenmeier** verfügbar, mach dort
weiter. Das Gerüst `castle.json` hat Quellen, Koordinaten und Gelände schon eingetragen. Die Befunde aus
dem Dossier werden dort zu `elements` mit `evidence`.

## Regeln
- **Nichts erfinden:** keine Quellen, Signaturen, URLs oder Zitate, die du nicht tatsächlich gefunden
  hast. Ist eine Angabe unsicher, schreib das dazu.
- **„Gesichtet“ ehrlich setzen:** `viewed: true` nur, wenn du Bild oder Text selbst gesehen hast.
- **Urheberrecht:** Lade nur gemeinfreie oder frei lizenzierte Dateien herunter und notiere Lizenz und
  Urheber. Moderne, geschützte Pläne (Bauforschung, Grabungsberichte, Bücher) zitierst und beschreibst du
  nur. Der Nutzer kann sie selbst hochladen.
- Bei Widersprüchen nimmst du beide Quellen auf und vermerkst den Widerspruch.
- Halte das Dossier knapp: lieber zehn gut bewertete Quellen als fünfzig ungeprüfte Treffer.
  Lösche irrelevante Commons-Treffer wieder, z. B. moderne Fotos ohne Bezug zum mittelalterlichen Zustand.
