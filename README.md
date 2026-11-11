# WiCAN MQTT — 0.1.1

Eigen Home Assistant-integratie voor WiCAN en WiCAN Pro via de bestaande MQTT-integratie.
Eerste testversie, nog niet getest op een draaiende Home Assistant-installatie.
Geen afhankelijkheid van ha-wican of Smart EV Charging. Eigen domein: `wican_mqtt`.

## Installeren

Handmatig: kopieer `custom_components/wican_mqtt` naar `/config/custom_components/wican_mqtt`.
Herstart Home Assistant. Ga naar Instellingen → Apparaten & diensten → Integratie toevoegen → WiCAN MQTT.
MQTT/Mosquitto moet al geconfigureerd zijn. Deze integratie gebruikt de bestaande brokerverbinding.

HACS, nadat de repository bestaat: voeg `ProtonJeroen/Wican-HomeAssistant-integration` toe als aangepaste repository van type Integratie, download en herstart.

## Voorbeeldinstellingen voor een Pro

- Apparaat-ID: jouw eigen apparaat-ID (hier als voorbeeld `aabb11223344`)
- Naam: `WiCAN Pro` (gewone WiCAN apart toevoegen met andere ID en naam)
- Model: `WiCAN Pro`
- Status-topic nu: `wicanpro/aabb11223344/can/status`
- AutoPID-topics nu: `wicanpro/ioniq/soc_d`, `soc`, `soh`, `charger_connected`, `charging`, `charging_dc` (telkens met dezelfde prefix).
- Interval: 60 seconden; vervaltijd: 180 seconden.

Standaard stelt het formulier `wican-pro/...` voor. Pas die velden aan naar de hierboven vermelde bestaande topics zolang de firmware nog `wicanpro` gebruikt. De integratie hernoemt geen firmwaretopics. Om volledig over te gaan naar `wican-pro`, wijzig zowel de status- en AutoPID-topics in de module als die in de integratie. Elke sensor hoort op een eigen topic met een JSON-object met de overeenkomstige hoofdletterkey, bijvoorbeeld `{"SOC_D":52}`. De batterijpercentages worden ongewijzigd weergegeven, niet herschaald.

## Entiteiten en dashboard

Vier sensoren: 12V accuspanning, Accupercentage (SOC_D/dashboard), BMS accupercentage (SOC), Accugezondheid (SOH).
Drie binaire sensoren: Laadstekker aangesloten, Laden, DC laden.
Voeg de gewenste sensor toe via Dashboard → Bewerken → Kaart toevoegen → Entiteit.
Apparaten zijn strikt gescheiden op ID; entity-ID's kunnen via HA hernoemd worden zonder de koppeling te verliezen.
Smart EV Charging kan de nieuwe Accupercentage-sensor als wijzigbare SoC-bron gebruiken.

## Spanning en beschikbaarheid

Firmware 4.52p zet `/battery` alleen bij het verbinden. Daarom gebruikt deze integratie uitsluitend verse antwoorden op `get_vbatt`:
- Commando `wican/<id>/cmd`, payload `{"cmd":"get_vbatt"}`, QoS 0, retain false.
- Antwoord `wican/<id>/rsp`, JSON-key `battery_voltage`.
Deze hardwaretopics zijn vast in 4.52p en blijven onder `wican`, ook bij een Pro. Sensoren blijven onder het afzonderlijke Pro-apparaat; er worden geen extra of dubbele MQTT-topics gepubliceerd.

Een antwoord wordt alleen binnen 15 seconden na een aanvraag verwerkt. Retained meetwaarden worden genegeerd; een retained online-status geeft alleen aanleiding voor een nieuwe aanvraag. Een verse offline-status maakt de actuele status ongeldig. Spanning en binaire laadstatussen vervallen afzonderlijk na standaard 180 seconden. SoC (SOC_D en BMS SOC) en SOH blijven als laatst bekende waarde beschikbaar, ook bij slapen/offline. Hun attributen `last_measured_at`, `data_fresh` en `value_source` tonen wanneer de meting binnenkwam en of deze nog vers is. Bij herstart/herladen herstelt HA de percentages met de oorspronkelijke meettijd; herstelde waarden zijn nooit automatisch vers. Een onbekende meettijd blijft leeg. Retained MQTT-percentages worden nog steeds niet als nieuwe meting verwerkt. SoC-verkeer houdt een oude spanning niet beschikbaar.

Zonder verse gegevens wordt slechts eens per vijf minuten geprobeerd, om niet voortdurend te publiceren terwijl het apparaat slaapt. Een aanvraag kan een slapende WiCAN niet wakker maken. Het apparaat moet zelf ontwaken. De integratie verandert geen slaapinstellingen en leest geen extra voertuig-PIDs uit.

Als tijdens de test ooit een retained commando is verstuurd: wis het éénmalig door een lege payload met retain true naar het cmd-topic te publiceren. Gebruik daarna retain false.

## Wijzigen en verwijderen

MQTT-topics, model, naam, interval en vervaltijd zijn wijzigbaar via de integratieopties. De apparaat-ID blijft vast; voeg een vervangen apparaat als nieuwe integratie toe. Bij herladen/verwijderen worden timers en abonnementen opgeruimd.

## Ontwikkeling

`python -m unittest discover -s tests -v`
`python -m compileall -q custom_components`

Unit tests dekken parsing, freshness, retained data, polling, topic isolation en lifecycle met een gesimuleerde HA/MQTT-laag. Een echte HA-installatie en beide apparaten moeten nog worden getest. De Pro-opvraagopdracht is handmatig bevestigd met 14,8 V; ondersteuning op de gewone WiCAN moet op diens firmware worden geverifieerd.

Validatie 2026-11-11: 10 unit tests geslaagd. HA 2025.2.0 imports, configuratieschema en entity-metadata geslaagd met Python 3.13 (testomgeving gebruikt ciso8601 >=2.3.3 en lru-dict >=1.4.1 vanwege beschikbare wheels). Live HA Green/MQTT-installatietest nog uit te voeren.

## 0.1.1

Behoud laatst bekende percentages bij voertuigstilstand en herstart, met oorspronkelijke meettijd en freshness-attributen. Laadstatussen en spanning blijven vervallen. Smart EV Charging ziet hierdoor een laatst bekende SoC: controleer `data_fresh`/`last_measured_at` voor toepassingen die een recente meting vereisen.

## 0.1.2 — optionele HV-accumetingen

Voegt HV-accuspanning, signed accustroom en netto accuvermogen toe via drie optionele MQTT-topics. Positief vermogen betekent naar de tractieaccu. De nieuwe metingen vereisen verse berichten en worden niet als oude laadwaarde hersteld. Bestaande configuraties blijven werken; configureer de nieuwe topics via de integratieopties.

Zie [Ioniq 28 kWh: PID-instellingen en validatie](docs/ioniq-28-power.md). Live controle op de auto volgt; deze versie berekent nog geen laadenergie of SOH-schatting.
