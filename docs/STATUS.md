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

### Jeszcze niewykonane

Trening, wyniki ML, backend, Docker nowego projektu, repo GitHub StayLens, CI/CD, Terraform nowej aplikacji, wdrożenie Azure, dostęp prowadzącego i oddanie. Sam podgląd nie spełnia jeszcze wszystkich wymagań SUML.
