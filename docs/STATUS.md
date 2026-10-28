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

### Jeszcze niewykonane

Trening, wyniki ML, backend, Docker nowego projektu, repo GitHub StayLens, CI/CD, Terraform nowej aplikacji, wdrożenie Azure, dostęp prowadzącego i oddanie. Sam podgląd nie spełnia jeszcze wszystkich wymagań SUML.
