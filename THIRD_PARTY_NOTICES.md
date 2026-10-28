# Źródła i atrybucja

## Inside Airbnb

StayLens korzysta z projektu **Inside Airbnb**, danych przygotowanych przez jego autorów i współtwórców, w tym Murray Cox. Źródło: https://insideairbnb.com/get-the-data/. Berlin, snapshot 19 września 2026. Licencja zbioru: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).

Zmiany: wybór rekordów z poprawną dodatnią ceną i lokalizacją w Berlinie, podział gospodarzy, wybór części treningowej, ograniczenie pól, serializacja do JSON, polski interfejs, obliczenia median oraz własne oszacowania ML. S03 dodaje zapisane przewidywania z grupowanego CV, bez używania danych Doorstep. Nie sugerujemy poparcia autorów dla projektu. Dokładne źródła i SHA256 są w reports/data_preflight.json i reports/s03/catalog_manifest.json.

[Założenia źródła](https://insideairbnb.com/data-assumptions/): lokalizacje są przybliżone, brak dostępności dnia nie jest równoznaczny z rezerwacją, snapshot nie gwarantuje aktualności.

Fotografie nie są kopiowane ani dołączane do repo; UI korzysta z publicznych URL w źródle. Praw do fotografii i znaków Airbnb nie utożsamiamy z licencją tabelarycznego zbioru. Prawa pozostają przy odpowiednich właścicielach. Każda oferta ma odnośnik do źródła. Przed publicznym wydaniem trzeba potwierdzić końcowy sposób prezentacji zdjęć lub zastąpić je własnymi wyraźnie ilustracyjnymi materiałami.

## Doorstep Analytics — wyłącznie lokalny eksperyment S02c

Źródło: [Berlin, Germany](https://doorstepanalytics.com/report?country=Germany&location=Berlin), autor/dostawca Doorstep Analytics (Simon Salamian). Darmowy EssentialsPackage 19092026 pobrany 28.10.2026, obserwacje 18–19.09.2026. Dokładna wersja, SHA256, przetwarzanie i wyniki: [raport S02c](reports/s02c/REPORT.md).

Zmieniono: wybrano wyłącznie dwie cechy (Guest Favourite, liczba udogodnień dostępności), dopasowano po dokładnym ID i sprawdzono gospodarza/datę/cechy obiektu; sprzeczności odłożono. Nie przedstawiamy tego jako certyfikacji standardu ani poparcia dostawcy.

[Warunki](https://doorstepanalytics.com/legal/terms), sprawdzone 28.10.2026: publiczne darmowe grafiki, mapy i raporty są opisane jako CC BY-NC-SA 4.0. Surowy pobrany CSV nie ma w tym sformułowaniu jednoznacznie określonego zakresu. Dane pozostają lokalnym materiałem badawczym poza Git; brak ich publikacji i integracji z publicznym katalogiem. Przed taką publikacją/komercyjnym wykorzystaniem trzeba wyjaśnić prawa. Nie zakładamy, że obejmuje je licencja Inside Airbnb. Płatna licencja dostawcy nie została zakupiona.

## Mapa

Dane mapy © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL. Kafelki z https://tile.openstreetmap.org, z zachowaniem [Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/): atrybucja widoczna, standardowy ruch przeglądarki i cache, brak masowego pobierania/prefetch/offline. Wersja demonstracyjna o niskim ruchu; brak gwarancji dostępności serwera map.

## Biblioteki i fonty

React/React DOM oraz Vite: MIT. Leaflet: BSD-2-Clause. Lucide: ISC. Dokładne wersje i zależności: frontend/package-lock.json, licencje w zainstalowanych pakietach. DM Sans i Manrope dostarczane przez Google Fonts; rodziny na licencji SIL Open Font License. Przed finalnym wydaniem fonty można hostować lokalnie wraz z licencjami. Geometria znaku StayLens i ilustracja miasta w interfejsie są własnymi elementami SVG projektu.
