---
name: burgenmaler
description: Macht aus einer Burgenmeier-Rekonstruktion (castle.json) ein verschönertes Schaubild – interaktive 3D-Seite mit Mauerwerks- und Dachtexturen, weichem Gelände, Himmel, Licht und Schatten, abwechslungsreichen Bäumen – und rendert daraus hochaufgelöste Bilder aus beliebigen Blickwinkeln (z. B. aus der Blickrichtung einer Vedute). Verwenden, wenn ein Burgenmeier-Modell „schöner“, „detailreicher“, „weniger low-poly“, als Illustration, Schaubild, Poster oder druckfähiges Bild gewünscht wird.
---

# Burgenmaler

Der Burgenmeister liefert die belegte Rekonstruktion, der Burgenmaler das Schaubild dazu. Die
**Geometrie bleibt unverändert**: Grundrisse, Höhen und Dachformen stammen aus `castle.json`. Dazu
kommen nur Darstellungsmittel: Texturen, Licht, Himmel, Dunst und Bewuchs. Deshalb gilt:

- Alles, was der Maler hinzufügt (Steinformat, Dachdeckung im Detail, Baumformen, Farbstimmung), ist
  **illustrativ**. Sag das dem Nutzer, und gib Bilder nie als Befund aus.
- Der Schalter **Befundlage** bleibt im Schaubild erhalten und färbt die Bauteile nach Befundstufe.
- Soll sich an der Burg selbst etwas ändern (Höhe, Dach, Bauteil), ändere `castle.json` mit dem
  Burgenmeister und male neu. Erfinde im Schaubild keine Bauteile.

`$SKILL` ist das Verzeichnis dieser Datei, `$BM` das des Skills **burgenmeier** (wird automatisch
gesucht: Nachbarordner, `/mnt/skills/*/burgenmeier`, `~/.claude/skills/burgenmeier`; sonst
`--burgenmeier PFAD` oder `BURGENMEIER_DIR`). Benötigt: Python 3 mit `numpy`, für Bilder Node mit
Playwright/Chromium.

## Ablauf

1. **castle.json beschaffen.** Liegt keine vor, erst mit dem Burgenmeister rekonstruieren. Prüfe sie mit
   `python $BM/scripts/validate.py castle.json`.
2. **Schaubild erzeugen:**
   ```bash
   python $SKILL/scripts/paint.py castle.json -o burg_schaubild.html
   ```
   Die Seite lädt three.js r128 vom CDN. Ohne Netz: `--three pfad/zu/three.min.js` bettet es ein
   (`npm i three@0.128.0` liefert `node_modules/three/build/three.min.js`).
3. **Bilder rendern** (Chromium ohne Bildschirm, Software-WebGL, wenige Sekunden je Bild):
   ```bash
   node $SKILL/scripts/render.mjs burg_schaubild.html --out bilder/ --views vogelschau,sued,umgebung
   node $SKILL/scripts/render.mjs burg_schaubild.html --out bilder/ --views "" \
        --cam "vedute_1630:az=230,el=14,dist=260,fov=30" --licht abend --width 3600 --height 2400
   node $SKILL/scripts/render.mjs burg_schaubild.html --out bilder/ --views vogelschau --befund
   ```
   - Ansichten: `vogelschau sued nord ost west grundriss umgebung`.
   - `--cam name:az=…,el=…,dist=…,fov=…[,x=…,y=…,z=…]`: Blickrichtung `az` in Kompassgrad (von wo aus
     man schaut; 180 = von Süden), `el` Höhenwinkel, `dist` Abstand in m, `x,y,z` Zielpunkt lokal.
     Für eine Vedute: Standort des Zeichners aus Karte/Bild schätzen, `az` = Richtung vom Burgmittelpunkt
     zum Zeichner, `el` klein (5–15°), `fov` 25–35 für die typische Tele-Wirkung.
   - `--licht morgen|mittag|abend` (Standard: Licht aus Nordwest wie in den Zeichnungen).
   - `--befund` färbt nach Befundlage, `--ohne-umgebung` blendet Siedlung, Flur und Bäume aus.
   - Fehlt `three.js` vom CDN, nimmt das Skript `--three` oder `THREE_JS` oder `node_modules/three`.
4. **Selbst kontrollieren.** Sieh dir jedes Bild an: schwebt oder versinkt etwas, ist die Burg im Bild,
   stimmt die Blickrichtung mit der Vorlage? Korrigiere Kamera oder `castle.json` und rendere neu.
5. **Abgeben**: HTML-Schaubild und PNGs, dazu ein Satz, was illustrativ ist und wo die Befundlage steht.

## Was der Maler macht

| Bereich | Darstellung |
|---|---|
| Gelände | bikubisch verfeinert, weich schattiert und mit Eigenschatten der Hänge; Mulden dunkler; der Ausschnitt geht in eine ferne Hügellandschaft über |
| Boden | eine Bodenkarte (≈ 0,2 m je Pixel), direkt aus den Vektoren der `castle.json` gemalt: geglättete Wege mit Bankett, Ackerstreifen nach `strip_width` mit Furchen und Rainen, Waldboden, Hofstellen, Burghof, Gräben, Flussufer, Fels an Steilhängen |
| Mauern | im Browser gemaltes Bruchstein-, Ziegel-, Putz-, Fachwerk- und Holzmuster nach `material`, Relief, dunklerer Mauerfuß, Rundtürme geglättet |
| Dächer | Biberschwanz, Schiefer, Schindel, Stroh, Blei nach `roof_material` |
| Wasser | spiegelnd mit bewegten Wellen |
| Bäume | mehrere Kronenformen je Art, gestufte Nadelbäume, Farbstreuung je Baum; Wald läuft über den Rand hinaus aus |
| Licht | Himmel mit Sonne, weiche Schatten, Himmelslicht, Luftperspektive, Filmkurve (ACES) |

Grenzen: keine Fenster, Erker oder Wehrgänge, solange `castle.json` sie nicht enthält. Wege werden
aufs Gelände gemalt, nicht eingeschnitten. Fotorealismus (Blender, Pfadverfolgung) ist nicht Teil
dieses Skills.
