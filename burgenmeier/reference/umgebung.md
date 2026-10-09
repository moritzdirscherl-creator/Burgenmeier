# Umgebung rekonstruieren

Ziel: eine **plausible** Landschaft zum Zieldatum. Die Umgebung ist fast immer schwächer belegt als die
Burg. Kennzeichne sie entsprechend (meist `annahme`, mit Beleg `wahrscheinlich`).

## Datenquellen (vom Jüngsten zum Ältesten rückwärts arbeiten)
1. **Heutiger Zustand:** OpenStreetMap über `geo.py osm` und Höhenmodell über `geo.py terrain`.
   Landesvermessungen bieten oft freie Laserscan-DGM (1 m) und Geoportale mit Bodendenkmälern.
   Darin sieht man Wälle und Gräben, die im Gelände kaum noch erkennbar sind.
2. **Erste genaue Landesaufnahmen (ca. 1800–1880):** Urkataster und Uraufnahmen, preußische
   Urmesstischblätter, Tranchot-Karte (Rheinland, um 1800–1820), Schmitt'sche Karte (Südwestdeutschland,
   um 1797), bayerische Uraufnahme (1808–1864). Sie zeigen Flussläufe vor der Begradigung, alte Wege,
   Flurgrenzen, Weinberge und Mühlen, und sie stehen dem Mittelalter oft näher als die heutige Landschaft.
3. **Frühneuzeitliche Karten und Ansichten:** Merians Topographia (17. Jh.), Landtafeln
   (z. B. Apian, Bayern 1568), Forstkarten, Grenzbeschreibungen.
4. **Mittelalterliche Schriftquellen:** Urbare und Zinsbücher (Mühlen, Weinberge, Höfe, Fischweiher),
   Weistümer, Ersterwähnungen von Dörfern, Rodungsnamen (-rod, -reut, -schwand, -brand).

Recherchiere 2. und 3. per Websuche (Digitalisate bei Landesarchiven, Geoportalen, Wikimedia Commons).
Nenne jede Karte als eigene Quelle (`type: map`).

## Heuristiken für das Zieldatum
- **Flüsse und Bäche:** vor den Begradigungen des 19./20. Jh. stärker gewunden, breiter, teils verzweigt,
  Auen nass (Weide/Wiese statt Acker). Mühlgräben und Mühlen an Dorf- und Burgbächen. Stauseen, Kanäle und
  Hafenbecken weglassen.
- **Wald:** Durch die hochmittelalterliche Rodungsperiode (ca. 1050–1300) war die Waldfläche oft kleiner
  als heute. Gute Ackerlagen waren gerodet, steile Hänge, Kuppen und arme Böden bewaldet. Wälder waren meist
  Laub- und Mischwald, lichter, beweidet, mit Niederwald. Heutige Fichten- und Kiefernforste sind meist
  neuzeitlich. Rund um die Burg wurden Hänge häufig für Sicht und Verteidigung freigehalten, besonders auf
  der Angriffsseite.
- **Flur:** Dreifelderwirtschaft. Gewannflur aus langen, schmalen Streifen (`acker`, `strip_width` 10–25 m)
  um Dörfer, mit Wiesen in den Auen und Weide auf Hängen. Hausgärten und Obst direkt am Dorf.
- **Weinbau:** im Mittelalter deutlich weiter verbreitet als heute, auch nördlich der heutigen Grenzen.
  Typisch an Süd- bis Südwesthängen von Rhein, Mosel, Main, Neckar, Saale-Unstrut, Elbe und Donau (`weinberg`).
- **Siedlungen:** Burgweiler oder Burgmannensiedlung am Fuß der Burg oder als Vorburg. Dörfer an Quellen,
  Bachläufen und Wegkreuzungen. Kirche oft erhöht, Chor nach Osten. Häuser meist Fachwerk/Holz mit Stroh-
  oder Schindeldach (`settlements[].roof_material: thatch | shingle`). 10–40 Hofstellen je Dorf sind
  typisch. Städte haben eigene Mauern; die lassen sich als `wall`-Elemente mit `layer: "umgebung"` darstellen.
- **Wege:** Der Burgweg führt selten gerade hinauf. Er windet sich am Hang, oft so, dass Angreifer der Mauer
  die schildlose rechte Seite zuwenden. Fernwege folgen Tälern und Höhenrücken. Moderne Straßen liegen oft
  auf alten Trassen, aber begradigt. Lass Autobahnen, Bahnen und Neubaugebiete weg.
- **Burgumfeld:** Vorburg mit Wirtschaftsbauten, Gärten und Fischweihern. Bei Wasserburgen gehören Dämme
  und Wehre zur Anlage.

## Umsetzung in `castle.json`
1. Lies `osm_umgebung.json` und übernimm nur, was ins Zieldatum passt. Glätte und verlängere Flussläufe
   anhand historischer Karten. Den Fluss-`path` stets flussabwärts angeben.
2. Ergänze Flur, Wald und Siedlung als grobe Polygone. Ein paar Ecken genügen, das Modell ist Low-Poly.
3. Gib jeder Fläche `evidence`. Aus historischer Karte belegt: `wahrscheinlich` mit Kartenquelle.
   Nur aus Heuristik: `annahme` mit kurzer Begründung in `note`.
4. Wähle `site.extent` so, dass die Umgebung mit ihrem Bezug zur Burg sichtbar wird (Tal, Dorf, Fluss):
   meist 600–1500 m.
