# Netto accuvermogen — versie 0.1.2

Deze uitbreiding is optioneel. Bestaande topics en sensoren blijven werken. Vul in de integratieopties de drie nieuwe topics in om de sensoren toe te voegen. Alle nieuwe voorbeelden gebruiken `wican-pro/`; migreer bestaande werkende topics niet tegelijk met deze proef.

## WiCAN Pro instellen

Voeg in Automate → User Custom drie PIDs toe. Gebruik voor alle drie PID `2101`, PID Init `ATSP6;ATSH7E4;ATST96;`, periode `5000` ms en Destination Type `MQTT_Topic`. Schakel User Custom PIDs in. Bewaar met Store en herstart om de opgeslagen configuratie te laden. Laat de bestaande Vehicle Specific PIDs staan.

| Naam | Expression | Unit | Class | Destination |
|---|---|---|---|---|
| HV_VOLTAGE | `[B18:B19]/10` | V | voltage | `wican-pro/ioniq/hv_voltage` |
| BATTERY_CURRENT | `(S15*256+B17)/10` | A | current | `wican-pro/ioniq/battery_current` |
| BATTERY_POWER | `(0-(S15*256+B17))*[B18:B19]/100000` | kW | power | `wican-pro/ioniq/battery_power` |

Laat min/max leeg; stroom en vermogen moeten ook negatieve waarden kunnen doorgeven. Deze formules zijn specifiek voor het ruwe, meerregelige 2101-antwoord van de Ioniq 28 kWh met WiCAN Pro 4.52p. Gebruik ze niet zonder validatie bij een ander model of een parser die transportbytes verwijdert.

In de Home Assistant-integratieopties corresponderen de drie optionele topicvelden met bovenstaande destinations. Ze zijn standaard leeg, ook bij bestaande installaties. Spanning, stroom en vermogen vervallen bij ontbrekende verse metingen; een oude laadwaarde wordt niet als actueel hersteld.

## Betekenis en controle

Accustroom volgt de BMS-conventie: negatief tijdens laden, positief tijdens ontladen. Netto accuvermogen gebruikt het omgekeerde teken: positief naar de accu, negatief uit de accu (ook bij rijden). Het is dus geen sensor die uitsluitend tijdens laden positief is: regeneratie kan ook positief vermogen geven.

De vermogensformule gebruikt stroom én spanning uit één OBD-antwoord; de losse stroom- en spanningssensoren worden apart opgevraagd en kunnen op iets verschillende tijdstippen meten. Vermogen is geen beschikbare/maximale laadlimiet en geen Easee AC-meting. Het verschil met Easee omvat onder andere omzettingsverlies en hulpverbruik; dit is geen directe meting van chemisch opgeslagen energie.

Controleer eerst live MQTT-berichten tijdens laden, zonder Test: ongeveer 300–400 V en een plausibel positief accuvermogen onder het AC-ingangsvermogen bij stabiele omstandigheden. Vergelijk daarna stoppen en opnieuw starten. Bij geen antwoord hoort de sensor niet beschikbaar te worden, niet automatisch 0 kW.

## Formulevalidatie

Bron: [JejuSoul Ioniq 28 kWh BMS PID-definities](https://github.com/JejuSoul/OBD-PIDs-for-HKMC-EVs/blob/master/Ioniq%20EV%20-%2028kWh/extendedpids/Hyundai_Ioniq_EV_BMS_data.csv).

De Torque-payloadvelden K/L (signed stroom) en M/N (spanning) zijn naar de WiCAN-ruwe offsets vertaald. B16 is een ISO-TP-volgbyte; stroom is daarom S15/B17, geen aaneengesloten bytepaar. Gecontroleerd met een ruwe 7EC-response: FF/AC → -8,4 A; 0D/C3 → 352,3 V; netto vermogen +2,95932 kW. De drie expressions zijn uitgevoerd met de expression-parser uit firmware 4.52p en gecontroleerd voor laden en ontladen. Live validatie op de auto moet nog worden afgerond.

## Latere capaciteitsschatting

Integratie van het netto accuvermogen over een laadsessie levert elektrische kWh aan de accupolen. Deel deze door de stijging van een consequent gekozen SOC (als fractie) voor een schatting van de bruikbare capaciteit. Gebruik een ruim SOC-bereik, vergelijkbare temperatuur en meerdere sessies. Onvolledige meetperioden moeten een sessie ongeldig maken. SOC Display en BMS SOC gebruiken verschillende buffers; meng ze niet. Een SOH-percentage vereist een passende referentie voor dezelfde bruikbare capaciteit en is geen exacte laboratoriummeting. Deze versie implementeert nog geen kWh-integratie of SOH-schatting.
