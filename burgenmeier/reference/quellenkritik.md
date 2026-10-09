# Quellenkritik und Befundstufen

## Grundregeln
- **Jede Aussage braucht eine Herkunft.** Was keine Quelle hat, ist `annahme`, auch wenn es plausibel ist.
- **Zieldatum beachten:** Eine Ansicht von 1650 zeigt nicht den Zustand von 1300. Prüfe, welche Bauteile
  später hinzukamen (Schießscharten für Feuerwaffen, Renaissance-Giebel, Zwerchhäuser, barocke Hauben).
- **Original vor Kopie:** Viele Veduten wurden abgekupfert, auch bei Merian. Suche die Vorlage, bevor du
  Details übernimmst.
- **Widersprüche dokumentieren**, nicht still auflösen. Halte in `note` fest, welche Quelle du warum
  bevorzugst.

## Quellenarten
| Quelle | Stärken | Schwächen | maximale Stufe (allein) |
|---|---|---|---|
| Bauaufnahme / steingerechter Plan, Grabungsplan | Lage, Maße, Mauerstärken | zeigt nur Erhaltenes; Bauphasen nicht immer getrennt | gesichert |
| Grundriss-Skizze, Inventarband (Kunstdenkmäler, um 1900) | Gesamtdisposition | vereinfacht, teils ergänzt, Maßstab ungenau | gesichert (Lage), wahrscheinlich (Maße) |
| Erhaltener Bestand (Fotos, Besuchsberichte) | Höhen, Details, Material | spätere Umbauten, Restaurierungen des 19./20. Jh. | gesichert |
| Vedute, Kupferstich, Gemälde | Silhouette, Dachformen, Höhenverhältnisse, Umgebung | Konventionen, Übertreibung der Höhen, Spiegelung, Kopien | wahrscheinlich |
| Karte (Kataster, Landesaufnahme) | Lage von Gräben, Wegen, Gewässern, Flur | jung (meist 19. Jh.), heutige Verhältnisse | wahrscheinlich |
| Schriftquelle (Urbar, Inventar, Baurechnung, Burgfrieden) | Existenz, Funktion, Datierung, Material („mit ziegeln gedeckt“) | selten Lage und Maße | wahrscheinlich (Existenz), Gestalt = analogie |
| Vergleichsbau, Typologie | Gestalt, Proportion | nicht der konkrete Ort | analogie |
| Recherche-Heuristik (Umgebung) | Plausibilität | kein Beleg | annahme |

## Illustrationen auswerten
1. **Datierung und Urheber** klären (Original oder Kopie, Augenzeuge?).
2. **Standpunkt** bestimmen: Aus welcher Richtung blickt der Zeichner? Das ist für `draw_view.py
   --azimuth` nützlich, um dieselbe Ansicht zum Vergleich zu erzeugen.
3. **Proportionen messen:** Setze bekannte Größen ins Verhältnis, etwa Turmhöhe zur Mauerhöhe oder zur
   Turmbreite. Absolute Maße kommen aus Plan oder Typologie.
4. **Konventionen herausrechnen:** Türme werden oft zu hoch und zu schlank gezeichnet, Dächer zu steil und
   Gelände zu dramatisch. Zeigen mehrere unabhängige Ansichten dasselbe Detail, steigt die Stufe.
5. **Vergleichsansicht erzeugen:** Rendere mit `draw_view.py` aus demselben Blickwinkel und vergleiche.
   Abweichungen sind entweder Fehler im Modell oder künstlerische Freiheit. Begründe die Entscheidung.

## Pläne auswerten
- Unterscheide Bestand (schwarz/schraffiert) und Ergänzung (gestrichelt/hell) im Plan selbst.
- Prüfe den Maßstab an zwei unabhängigen Stellen (Maßstabsleiste und bekannte Mauerstärke).
- Nordpfeil: magnetisch oder geografisch? Bei älteren Plänen kann die Missweisung mehrere Grad betragen.
  Bei Bedarf über die Lage im Luftbild bzw. in OSM nachjustieren (`plan.py overlay`).

## Texte auswerten
- Zitiere die Stelle wörtlich und kurz (Original und Übersetzung) in `meta.sources[].note` oder in der
  `note` des Bauteils.
- Nennungen wie „haus“, „turn“, „kemnate“, „capelle“, „zwinger“, „vorburg“, „mül“ belegen die Existenz.
  Die Gestalt bleibt `analogie`.
- Mengenangaben (z. B. Ziegel und Holz in Baurechnungen) können Dachdeckung und Größe stützen.
