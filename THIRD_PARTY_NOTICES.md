# Źródła i atrybucja

## Inside Airbnb

StayLens korzysta z projektu **Inside Airbnb**, danych przygotowanych przez jego autorów i współtwórców, w tym Murray Cox. Źródło: https://insideairbnb.com/get-the-data/. Berlin, snapshot 19 września 2026. Licencja zbioru: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).

Zmiany: wybór rekordów z poprawną dodatnią ceną i lokalizacją w Berlinie, podział gospodarzy, wybór części treningowej, ograniczenie pól, serializacja do JSON, polski interfejs i obliczenia median. Nie sugerujemy poparcia autorów dla projektu. Dokładne źródła i SHA256 są w reports/data_preflight.json.

[Założenia źródła](https://insideairbnb.com/data-assumptions/): lokalizacje są przybliżone, brak dostępności dnia nie jest równoznaczny z rezerwacją, snapshot nie gwarantuje aktualności.

Fotografie nie są kopiowane ani dołączane do repo; UI korzysta z publicznych URL w źródle. Praw do fotografii i znaków Airbnb nie utożsamiamy z licencją tabelarycznego zbioru. Prawa pozostają przy odpowiednich właścicielach. Każda oferta ma odnośnik do źródła. Przed publicznym wydaniem trzeba potwierdzić końcowy sposób prezentacji zdjęć lub zastąpić je własnymi wyraźnie ilustracyjnymi materiałami.

## Mapa

Dane mapy © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL. Kafelki z https://tile.openstreetmap.org, z zachowaniem [Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/): atrybucja widoczna, standardowy ruch przeglądarki i cache, brak masowego pobierania/prefetch/offline. Wersja demonstracyjna o niskim ruchu; brak gwarancji dostępności serwera map.

## Biblioteki i fonty

React/React DOM oraz Vite: MIT. Leaflet: BSD-2-Clause. Lucide: ISC. Dokładne wersje i zależności: frontend/package-lock.json, licencje w zainstalowanych pakietach. DM Sans i Manrope dostarczane przez Google Fonts; rodziny na licencji SIL Open Font License. Przed finalnym wydaniem fonty można hostować lokalnie wraz z licencjami. Geometria znaku StayLens i ilustracja miasta w interfejsie są własnymi elementami SVG projektu.
