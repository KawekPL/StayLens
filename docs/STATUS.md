# Status StayLens

## 28 października 2026 — S01

Użytkownik wybrał StayLens. Termin 03.11.2026, pakiet do 02.11.2026. SupportRouter PL zachowany, jego chmura/repo nie zostały zmienione w tym etapie.

### Wykonane

- Osobny katalog C:/Users/szymo/Documents/ChatGPT/StayLens.
- Pobrane rzeczywiste dane Inside Airbnb Berlin 19.09.2026 oraz granice obszarów. SHA256 przypięte, odtwarzalny skrypt standardowej biblioteki Python.
- Preflight: 12 376 źródłowych rekordów, 4219 bez dodatniej ceny pominięte. Podział według gospodarza: 5814 train / 1108 validation / 1235 test. Podgląd tylko train.
- React + Vite + Leaflet. Lista i zdjęcia ofert, mapa z cenami, filtry, wyszukiwanie, sortowanie, szczegóły, porównanie do 3 ofert, informacje o danych.
- Procentowe porównanie dotyczy mediany dzielnicy dla tego samego typu, bez wybranej oferty. Nie jest wynikiem ML. Jasny status funkcji w UI.
- Responsywne style i widok mapy przełączany na telefonach. Nie oznacza to potwierdzonego testu na urządzeniach.

### Sprawdzenia

- Instalacja zależności z dokładnymi wersjami; npm zgłosił 0 znanych podatności przy instalacji (wynik chwili sprawdzenia).
- Produkcyjny build Vite: sukces.
- 4 testy funkcji: filtrowanie, mediana, brak wybranej oferty w grupie porównawczej, histogram — sukces.
- Niezależna kontrola wszystkich 5814 rekordów podglądu: unikalne ID, wyłącznie gospodarze train, brak przecięcia grup gospodarzy między train/validation/test, brak pól tożsamości gospodarza w publicznym JSON. Wynik w reports/preview_verification.json.
- Lokalny HTTP GET /: 200.
- 3 adresy zdjęć czołowych ofert zwróciły HTTP 200. Nie dowodzi to renderowania wszystkich zdjęć.
- **UI w przeglądarce nieweryfikowane**: pierwsza próba CUA zwróciła `Local browser use is disabled in Work settings`. Nie obchodzono ograniczenia, nie ma screenshotu ani potwierdzonego testu klikania.
- Próba otwarcia panelu Codex zwróciła `queued`; nie potwierdza wyświetlenia użytkownikowi.
- Kod JS/JSX/CSS sformatowany Prettier. Lokalne repo Git na gałęzi codex/staylens-prototype; brak zdalnego repo i publikacji w tym etapie.

### Kolejny krok

Obejrzenie przez użytkownika kierunku interfejsu pod http://127.0.0.1:5174/ (tylko ten komputer) i ewentualne wskazówki wizualne. Następnie S02: audyt cech, ustalenie protokołu, model bazowy i jeden kandydat, ocena oraz FastAPI. Kontrola UI w narzędziu, gdy dostępna, nadal wymagana przed wydaniem.

### Naprawa podglądu — 28.10.2026

Użytkownik zgłosił brak podglądu. Potwierdzono brak procesu nasłuchującego na 5174 i ERR_CONNECTION_REFUSED; poprzedni serwer był uruchomiony w tymczasowej sesji polecenia. Dodano scripts/start-preview.ps1, uruchamiający Vite w oddzielnym ukrytym procesie Windows, wyłącznie na 127.0.0.1. Skrypt sprawdza gotowość, zapisuje logi i przy powtórnym uruchomieniu wykorzystuje istniejący podgląd; nie zatrzymuje cudzych procesów na zajętym porcie.

Zweryfikowano działanie po wyjściu skryptu, ponowne uruchomienie bez duplikatu oraz HTTP 200 dla strony/danych. Dostęp przeglądarkowy jest już możliwy. Dwie stare karty zawierały stronę błędu; otwarto świeżą kartę z działającą aplikacją i zachowano ją do podglądu. W przeglądarce potwierdzono 3438 ofert w widoku domyślnym, 873 po wyborze Mitte, szczegóły oferty 45475252 (122 EUR, mediana 169 EUR) i reset do widoku domyślnego. Obejrzano renderowanie zdjęć i mapy. Nie jest to pełny odbiór wszystkich funkcji ani test mobilny. Zrzut lokalny: .local/preview-restored.jpg.

Przy oglądaniu wykryto dodatkowo błąd wysokości siatki: kontener wyników/mapy rozciągał się do 1976 px mimo wysokości obszaru 510 px, odsuwając znaczniki poza widok i powodując nakładanie stopki. Naprawiono minimalne wysokości elementów grid/flex, przewijanie listy oraz limit wysokości w układzie mobilnym. W kontrolnym widoku desktopowym potwierdzono zgodne wysokości obszaru, listy i mapy (około 510 px); tymczasowy rozmiar testowy przeglądarki przywrócono. Produkcyjny build po zmianie CSS przeszedł. Pełne testy mobilne i porównywanie nadal przed odbiorem.

### Jeszcze niewykonane na zakończenie S01

Trening, wyniki ML, backend, Docker nowego projektu, repo GitHub StayLens, CI/CD, Terraform nowej aplikacji, wdrożenie Azure, dostęp prowadzącego i oddanie. Sam podgląd nie spełnia jeszcze wszystkich wymagań SUML.

## 28 października 2026 — S02 ukończony

Użytkownik zlecił samodzielne wykonanie całego etapu. Protokół, parametry i kryteria wyboru zapisano przed pierwszym treningiem. Porównano medianę segmentów z HistGradientBoostingRegressor na tych samych grupach gospodarzy; 3-fold GroupKFold wewnątrz train oraz osobna walidacja. Test końcowy nadal nieoceniany.

- Wybrany boosting: MAE validation **53,61 EUR** vs **67,87 EUR**, poprawa **21,0%**. Mediana błędu 27,46 vs 39,00 EUR; RMSE 118,27 vs 133,82 EUR. CV MAE 54,90 vs 69,23 EUR, wygrana w każdym podziale.
- Audyt: odzyskano 5810/5814 brakujących wartości liczby łazienek z tekstu; dane numeryczne i udogodnienia ujednolicone w jednym kontrakcie. Brak ceny i identyfikatorów w cechach, brak opinii wymaganych dla nowych ofert.
- Dwie walidacyjne oferty mają komplet cech identyczny jak train; analiza wrażliwości bez nich nie zmienia wniosku. Nie usuwano skrajnych cen. MAE >400 EUR/noc wynosi 357,11 EUR; ograniczenie wymaga widocznego komunikatu w UI. Hotel/shared: tylko 8/4 wiersze walidacyjne.
- Kod, dokładne zależności, uniwersalne lockfile z hashami, wersje źródła/modelu, raport i wykres. Modele i przewidywania z identyfikatorami w ignorowanym artifacts/s02-v1. Drugie uruchomienie dało identyczne przewidywania; metryki niezależnie przeliczone.
- FastAPI: health, schemat, model card i predykcja, ładowanie artefaktu raz, bez treningu online, walidacja typów/zakresów i nadmiarowych pól, SHA256 oraz kontrola wersji. Skrypt start-api.ps1 uruchamia oddzielny ukryty proces lokalny.
- **27 testów przeszło, 0 pominiętych**; lint/format i kompatybilność zależności poprawne. TestClient emituje jedno ostrzeżenie o deprecjacji httpx w Starlette; dodatkowo wykonano rzeczywiste HTTP bez TestClient (200 poprawne żądanie, 422 z polem price). API docs: http://127.0.0.1:8001/docs.
- Podgląd 5174 nadal działa; nie zmieniano frontendu i nie twierdzimy, że został już zintegrowany z ML. Chmury/SupportRouter nie zmieniano.

Wyniki: [reports/s02/REPORT.md](../reports/s02/REPORT.md). Odtwarzanie/API: [API_AND_REPRODUCTION.md](API_AND_REPRODUCTION.md).

**Kolejny etap S03:** podłączenie formularza i szczegółów/porównania do modelu, API katalogu i paginacja, obsługa ładowania/błędów oraz ograniczeń. Dla katalogu ofert train wykorzystać zapisane przewidywania out-of-fold (bez gospodarza danej oferty w treningu), dla nowych parametrów pełny model train. Zmienić etykiety „bez modelu” dopiero po działającej integracji. Następnie S04 Docker/GitHub/CI/CD/Terraform/Azure, S05 odbiór i odłożony test po zamrożeniu modelu, S06 pakiet oraz dostęp prowadzącego. Termin 03.11 bez zmian.
