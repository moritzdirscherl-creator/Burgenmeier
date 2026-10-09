# Typologie und Richtmaße (Mitteleuropa, ca. 1000–1500)

Die Werte sind **Richtwerte** für fehlende Angaben. Einzelfälle weichen stark ab. Was du hieraus
ergänzt, ist höchstens `analogie`. Mit konkretem Vergleichsbau ist das besser: nenne ihn als Quelle
(`type: analogy`).

## Lagetypen → `site.terrain.type`
| Burgtyp | terrain | Hinweise |
|---|---|---|
| Spornburg | `spur` | an drei Seiten Steilhang; Halsgraben + Schildmauer/Bergfried zur Bergseite |
| Gipfelburg | `hilltop` | Ringmauer folgt Höhenlinie, Graben oft fehlend oder ringförmig |
| Felsenburg | `crag` | Bauten auf/um Felsklötze, kleine Grundfläche |
| Hangburg | `slope` | bergseitig gefährdet: Schildmauer, tiefer Graben oben |
| Niederungs-/Wasserburg | `lowland` + `ditch` mit `water: true` | Hauptburg auf Insel, oft Vorburg mit eigenem Graben |
| Inselburg | `island` + Gewässer | |
| Motte (Turmhügelburg, 10.–13. Jh.) | `lowland`, Plateau klein und erhöht (Hügel über `base`/`plateau.height`) | Holzturm + Palisade, Graben ringsum |

## Bauteile
| Bauteil | Maße (typisch) | Dach / Abschluss |
|---|---|---|
| **Bergfried** quadr. | 7–12 m Seite, 20–35 m hoch, Mauer 2–4 m, Hocheingang 8–12 m über Grund | Zinnenkranz (`crenellated`) **oder** Pyramiden-/Kegelhelm; Helme oft erst spätmittelalterlich |
| **Bergfried** rund | Ø 8–12 m (`radius` 4–6) | Kegel (`cone`) oder Zinnenkranz |
| **Wohnturm / Donjon** | 10–20 m Seite, 15–30 m hoch | Walm- oder Satteldach |
| **Ringmauer** | 1,5–2,5 m stark, 6–12 m hoch | Wehrgang mit Zinnen; später teils überdacht |
| **Schildmauer** | 3–5 m stark, 15–25 m hoch | Zinnen, teils mit Ecktürmen |
| **Zwingermauer** | 1–1,5 m stark, 4–7 m hoch, 5–15 m vor der Hauptmauer | Zinnen, Schießscharten; ab 14./15. Jh. |
| **Flanken-/Schalenturm** | Ø 6–10 m, ragt aus der Mauerflucht, 12–20 m hoch | Kegel, Pyramide; Schalenturm feldseitig rund, hofseitig offen |
| **Torhaus / Torturm** | 7–12 × 8–12 m, 10–18 m hoch, Durchfahrt 2,8–3,5 m breit, 3,5–4,5 m hoch | Walm-/Pyramidendach |
| **Palas** | 10–15 m tief, 20–40 m lang, 2–3 Geschosse, Traufe 10–16 m | Satteldach 45–60° |
| **Kapelle** | 6–9 × 10–15 m, Traufe 6–10 m, Chor meist nach Osten | Satteldach, ggf. Dachreiter |
| **Wirtschaftsbau** (Stall, Backhaus) | 6–10 × 12–25 m, Traufe 4–7 m, oft Fachwerk/Holz | Pult- oder Satteldach |
| **Halsgraben** | 10–25 m breit, 5–15 m tief | |
| **Wassergraben** | 10–30 m breit, 2–4 m tief | |
| **Brücke** | 2,5–4 m breit, Holz auf Steinpfeilern; Zugbrücke am Tor | |

Geschosshöhen: Wohngeschoss 3,5–5 m, Saalgeschoss bis 6 m. Mauerstärken nehmen mit der Höhe ab, die Krone
ist schmaler (das Modell vereinfacht auf eine durchgehende Stärke).

## Epochen
- **10.–12. Jh.:** Motten und frühe Höhenburgen, viel Holz. Palisaden (`wall`, `material: wood`) und
  Holztürme. Steinbau zunächst bei Hochadel und Reichsburgen.
- **Mitte 12. – Mitte 13. Jh. (staufisch/romanisch):** Bergfried an der Angriffsseite, Buckelquader,
  Ringmauer mit Zinnen, Palas mit Arkadenfenstern, Satteldächer.
- **Mitte 13. – 14. Jh. (gotisch):** Flankentürme, größere Wohnbauten, Zwinger ab dem 14. Jh. Kastellburgen
  mit regelmäßigem Grundriss in Ordens- und Königslandschaften.
- **15. Jh.:** Anpassung an Feuerwaffen: Geschütztürme und Rondelle (`tower` rund, niedrig, dick),
  Zwinger, Bastionen. Wohnkomfort steigt, Dachlandschaften werden steiler und reicher.
- Ab dem **16. Jh.:** Schlossumbauten. Für mittelalterliche Rekonstruktionen meist weglassen.

## Material und Region (Hinweise)
- Bruchstein verputzt oder steinsichtig (`stone`), Quader aus Sandstein (Pfalz, Franken, Main, Neckar:
  `sandstone`/`red_sandstone`).
- Backstein (`brick`) im Norddeutschen Tiefland, Ordensland, Teilen Bayerns und Österreichs.
- Dachdeckung: Schiefer (`slate`) in Mittelgebirgen mit Schiefervorkommen (Rheinisches
  Schiefergebirge, Thüringen), sonst Ziegel (`tile`), Holzschindeln (`shingle`) in Alpen und Wäldern,
  Stroh/Schilf (`thatch`) bei bäuerlichen Bauten.
- Fachwerk (`timber`) für Obergeschosse, Wirtschaftsbauten und Vorburgen verbreitet.
