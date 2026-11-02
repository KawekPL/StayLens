# Status StayLens

**Aktualnie: S05/S06 — końcowy odbiór, test i pakiet do oddania, 02.11.2026.** [Aplikacja](https://staylens.ashybay-e9483837.polandcentral.azurecontainerapps.io), [publiczne repo](https://github.com/KawekPL/StayLens), [udany pipeline](https://github.com/KawekPL/StayLens/actions/runs/41416768082), [odbiór](../reports/s05/ACCEPTANCE.md), [pakiet](oddanie/ZACZNIJ_TUTAJ.md). Model pozostaje S02. Poniższe starsze sekcje to historia; wzmianki o prywatnym repo i nieocenionym teście są już nieaktualne.

## 2 listopada 2026 — końcowa ocena i przekazanie

Pakiet S06 zweryfikowany również z wypakowanego archiwum: rzeczywista budowa Docker i smokeHTTP przeszły. Kod/model identyczne z wydaniem produkcyjnym; finalny ZIP dodaje dowody i dokumentację. Skrypt `build_submission.py` zapisuje archiwum oraz SHA256 w `artifacts/submission/`, bez sekretów i wierszowych danych testowych. [Dowód](../reports/s05/package_check.json).

Użytkownik zlecił końcowy odbiór, ocenę odłożonego testu i pakiet ze szkicem maila. Potwierdził dane: Szymon Kawlowski, s29670, oraz wyraził zgodę na publiczne repo z dokumentacją autora. Repo upublicznione, odczyt anonimowy200. Nie wysłano maila ani zaproszeń.

Protokół i runner zamrożono w a0895ab przed odczytem testu.1235ofert/624innych gospodarzy: MAE56,10EUR vs68,35EUR, poprawa17,92%, mediana błędu28,66EUR. Zero fit, brak zmiany modelu/preprocessingu i wszystkich oryginalnych artefaktów S02. Wysokie ceny nadal mają duży błąd; wynik opisano bez obietnicy dokładnej wyceny. Przewidywania z ID tylko lokalnie. Niezależna kontrola sześciu metryk i hashy przeszła. [Raport](../reports/s05/REPORT.md).

Wersja0.5.0, kod7ab5350, obrazsha256:f9bc66c2e5984fe4d0d0d61ed90b1fc008706d5559bdef50b680a2c41788f5ae. Zmieniono wyłącznie opis/udostępnienie oceny końcowej, nie model. CI97testów Python i7JS, zero pominięć, Docker/Terraform/publiczneHTTPS poprawne. Testy UI katalogu, wyszukiwania, paginacji, porównania, wyceny, niepoprawnej lokalizacji i wąskiego widoku; szczegóły i faktyczne szerokości CSS w raporcie odbioru. Nie jest to fizyczny test telefonu. Logi Log Analytics potwierdzone.

Przygotowano przewodnik, kartę danych/modelu, demo/objaśnienia, szkic maila i skrypt archiwum z kodem oraz zamrożonym `.runtime`. Odczyt Azure02.11 potwierdził expiry17.11, spendingLimitOn, estimated98,06USD. Listopadowy kurs0,89770636EUR/USD utrzymuje alert8EUR poniżej zgody10USD; odnowienie niepotwierdzone. Pozostaje wysłanie przez autora i dopilnowanie dostępności podczas oceny. Żadnego dalszego test-driven tuningu.

## 28 października 2026 — S04 ukończony

Utworzono prywatne repo `KawekPL/StayLens`, główną gałąź `main` i przypięte wydanie artefaktów `s02-artifacts-v1`. Jeden obraz Docker buduje frontend i serwuje go razem z API; kontener działa jako użytkownik bez roota. Model, biblioteki wykonawcze, oryginalne artefakty i moduły badań bez zmian. Test końcowy nadal nieoceniany.

GitHub Actions na świeżym Linuksie: **95 testów Python, 7 JS, zero pominięć**, Ruff, build frontendu, walidacja Terraform, build/test kontenera, OIDC, publikacja przetestowanego obrazu do ACR, plan/apply i test publicznego HTTPS — sukces. Wdrożony commit `205f2276e0185a3918b0c9dc09b02fad49a743dd`, obraz `sha256:6376509c8b33eadc5ec1719f7b861c56e00f4cc54a0c336446494def5003465c`. W przeglądarce potwierdzono renderowanie katalogu/mapy/zdjęć, filtr Mitte, porównanie i wycenę. To nie nowy test fizycznego telefonu. Log Analytics potwierdził logi żądań bez treści formularzy; lokalny streaming logów CLI ma błąd `eventStreamEndpoint`, opisano działający odczyt przez workspace.

Terraform utworzył 17 zasobów/przypisań bootstrap oraz jedną aplikację. Dwa prywatne stany Blob, logowanie Entra/OIDC, klucze Storage i publiczny dostęp do Blob wyłączone. Wspólny rejestr i środowisko Azure nie zostały skopiowane ani przejęte do nowego stanu; SupportRouter nie usunięto ani nie aktualizowano. StayLens ma 0–1 repliki, 0,5 vCPU/1 GiB i trzy sondy HTTP. Bootstrap ma plan exit 0. Plan aplikacji nadal ujawnia pięć dokładnych różnic odczytu domyślnych wartości Azure; niezależny kontroler dopuszcza tylko te przypadki i weryfikuje rzeczywistą konfigurację. Inne zmiany blokują CI. Nie opisujemy surowego planu aplikacji jako bezwarunkowego „no changes”.

Pierwszy deploy ujawnił nowy format OIDC GitHuba (z ID właściciela/repo); naprawiono przez Terraform. Drugi wdrożył działającą aplikację, lecz nie przeszedł naiwnego warunku plan exit 0. Trzeci pełny przebieg przeszedł wszystkie kontrole. Szczegóły i odtwarzanie w [DEPLOYMENT.md](DEPLOYMENT.md).

Odczyt Azure: grant Active do **17.11.2026**, spendingLimit On, estimatedBalance 98,06 USD. Zgoda pozostaje 10 USD/miesiąc. Dodano konserwatywny budżet **8 EUR dla całej subskrypcji**, z alertami 80/100% (kurs API 0,8799718409 EUR/USD). Alert nie jest twardym limitem. Stary alert 10 EUR nie został zmieniony; nowy obejmuje także zasoby wspólne. Odnowienia grantu nie potwierdzono. Repo nadal prywatne, bez dostępu prowadzącego, zaproszeń i wysłania pracy. Termin 03.11 pozostaje aktualny.

## 28 października 2026 — zakończony dodatkowy audyt jakości S03b/S03c

Użytkownik zakwestionował użyteczność błędu 53,61 EUR i zlecił samodzielne przemyślenie oraz wykonanie poprawy. Zamrożono dwa osobne protokoły w commitach 4187c95 i 05d5ff3 przed ich treningami. Łącznie sprawdzono 10 nowych wariantów na tych samych 5814 prawdziwych ofertach i grupach gospodarzy, 39 dopasowań w CV/krzywych, bez syntetycznych cen i bez usuwania trudnych rekordów z oceny.

S03b: CatBoost, ExtraTrees, uczenie log ceny, pięć cech wyliczanych z obecnego formularza, stała mieszanka oraz pominięcie flag event/photo tylko w fit. Konserwatywne wzorce znalazły pięć ofert, opisy sprawdzone przez asystenta bez cen; nie wszystkie wykluczają nocleg. Najlepsze CV 53,37 vs 54,90 EUR (2,79%), typowa mediana błędu niemal bez zmiany. Krzywa uczenia: 60,82/55,94/54,11/53,37 EUR przy 25/50/75/100% gospodarzy fit; trening przy pełnym fit 41,64 EUR. Audyt samych pięciu ofert nie wyjaśnia wysokiego błędu.

S03c: dwa dodatkowe CatBoost z 40 cechami Inside Airbnb, w tym wcześniejsze udogodnienia, wspólna łazienka, deklarowany metraż 667 lokali/118 pokoi i siatka współrzędnych. Bez Doorstep. Najlepsze CV 53,34 EUR (2,85% poprawy), trafienia do 20% ceny 45,91% vs 44,62%. Po pozostawieniu wszystkich nowych pól nieznanych MAE 54,93 EUR. Dla przedziału 100–200 EUR pełny wariant pogorszył MAE z 34,80 do 35,68 EUR.

Żaden wariant nie osiągnął zamrożonego minimum korzyści (m.in. 5% MAE i +2 punkty procentowe trafień do 20%). **Nie oceniano validation ani testu, nie podmieniono modelu/UI.** Wynik validation działającej aplikacji pozostaje 53,61 EUR. Zgodnie z warunkiem stopu nie dokładano kolejnych konfiguracji po tej serii. Nie osiągnięto precyzyjnej wyceny; rekomendacja to zachowanie orientacyjnej funkcji ML albo osobna, nowa hipoteza z bardziej informacyjnymi danymi, bez obietnicy błędu 10–15 EUR.

81 testów Pythona przeszło (0 pominięć); Ruff i zgodność zależności poprawne. Kontrole verify_s03b.py/verify_s03c.py potwierdzają hashe, ceny, foldy, metryki i decyzje. Istniejące API/katalog oraz HTTP przez frontend przeszły verify_s03.py; podgląd pozostaje działający. Dodano opcjonalny CatBoost 1.2.10 i osobny lock badawczy, bez zmiany bazowych wersji. Pełna suita wymaga research lockfile. Surowe dane, opisy i ID pozostają poza Git. Chmury/SupportRouter nie zmieniano.

Raporty: [S03b](../reports/s03b/REPORT.md), [S03c](../reports/s03c/REPORT.md). Termin 03.11 i zakres technologiczny bez zmian. S04 pozostaje niewykonany; test końcowy dopiero po zamrożeniu rozwiązania do odbioru.

## 28 października 2026 — S03 ukończony

Podłączono zaakceptowany interfejs do modelu S02: API katalogu z filtrowaniem i paginacją, szczegóły, porównanie do trzech ofert oraz formularz Wycena. Katalog korzysta z zapisanych przewidywań host-out-of-fold; formularz z modelu pełnego train. Mediany pozostały osobnym odniesieniem. Pełny statyczny katalog S01 przeniesiono poza publiczny frontend do ignorowanego lokalnego archiwum. Katalog S03 zawiera 5814 rzeczywistych ofert train, bez pól gospodarza i bez danych Doorstep.

Formularz ma wybór lokalizacji na mapie lub przez współrzędne, automatyczną dzielnicę, zgodne pary typów, parametry przestrzeni i osiem udogodnień z opcją „Nie wiem”. API sprawdza wielokąt dzielnicy i waliduje wejście. Zmiana parametrów usuwa poprzednią wycenę. Dodano ładowanie, błędy i ponowienie; ograniczenia jakości dla drogich ofert i małych prób hotel/shared są widoczne. Nie zmieniono modelu ani zamrożonych modułów S02/S02b/S02c; test końcowy nieoceniany.

75 testów Python i 7 JS przeszło, 0 pominięć. Ruff, formatowanie zmienionego frontendu i build produkcyjny poprawne. Niezależna kontrola całego katalogu potwierdziła identyczność cen ML z oryginalnymi wynikami CV, tylko gospodarzy train, brak host_id i niezmienione hashe S02. Rzeczywiste HTTP przez proxy Vite sprawdzone dla listy, szczegółów, porównania, wyceny i błędnych żądań.

Sprawdzono UI w przeglądarce przy 1440×1000 i emulowanej szerokości telefonu 390×844. Potwierdzono filtry, paginację, szczegóły, porównanie, wycenę i odrzucenie lokalizacji poza Berlinem. Naprawiono układ nagłówka mobilnego oraz mapę próbującą wycentrować ukryty kontener, co wcześniej powodowało zniknięcie strony. Rozdzielono inicjalizację korzenia React od komponentu aplikacji. Celowo zatrzymano zweryfikowane API projektu, potwierdzono zachowanie danych formularza po błędzie, uruchomiono API ponownie i uzyskano wycenę. To testy w przeglądarce, nie fizycznego telefonu ani wszystkich silników przeglądarek.

`scripts/start-preview.ps1` startuje teraz cały stos; API S03 to `staylens.application:app`. Podgląd pozostawiono działający w osobnych procesach Windows. Artefakty są nadal lokalne; świeży klon potrzebuje ich odtworzenia. Dostarczanie artefaktów do kontenera/CI, chmura i odbiór wdrożenia pozostają przed nami. Infrastruktura SupportRouter nie była zmieniana. [Raport S03](../reports/s03/REPORT.md), [weryfikacja](../reports/s03/verification.json).

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

## 28 października 2026 — S02b ukończony, model S02 zachowany

Na prośbę użytkownika wykonano data engineering i kontrolowany eksperyment ze sztucznymi danymi. Dodano wersjonowany kontrakt 38 cech: mniejszy obszar Berlina, 13 udogodnień, wspólna łazienka, proporcje pojemności, dystans do stałego punktu i brakujące cechy. Nie zmieniano kontraktu S02 w działającym API.

Przygotowano 263 maskowane wersje prawdziwych drogich ofert i osobny kontrolny zbiór 263 dokładnych powtórzeń. Każdy wariant pełnego treningu ma 6077 wierszy, ale nadal tylko 5814 rzeczywistych obserwacji. Ceny i współrzędne niezmienione, parent_listing_id/host_id/rodzaj maskowania zachowane lokalnie. W CV generowanie zawsze po podziale, tylko z gospodarzy fit. Zero sztucznych wierszy w ocenie i publicznym katalogu.

Porównano 6 wcześniej ustalonych wariantów na 3-fold GroupKFold. MAE ogólne / ponad 400 EUR: kontrola S02 54,90 / 394,00; cechy 54,47 / 397,53; cechy + min. 15 przykładów w liściu 54,33 / 397,30; błąd kwadratowy 60,96 / 340,41; powtarzanie 55,32 / 376,54; maskowanie 54,75 / 395,00. Żaden nie spełnił kryteriów łączących poprawę i ochronę pozostałych ofert. Nie wybierano nowego kandydata na validation; sprawdzono tylko zgodność kontroli S02 z zapisanymi przewidywaniami. Test końcowy nadal nieoceniany. Nie zmieniono progów po wynikach.

37 testów przeszło, 0 pominięć; niezależna kontrola pochodzenia wszystkich dodatkowych wierszy, rozdzielenia foldów, metryk, wyboru i hashy poprawna. Istniejące ostrzeżenie upstream TestClient/httpx pozostaje takie jak w S02. Wygląd/UI/API i chmura niezmienione. Artefakty i przygotowane CSV poza Git; kod, manifesty, protokół, raport i wykres w repo. Szczegóły: [raport S02b](../reports/s02b/REPORT.md).

Następna zaplanowana praca S03 korzysta z S02. S02b nie dostarczył podstaw do zastąpienia modelu. Dalsze badania wymagają osobnego protokołu; warto szukać rzeczywistych informacji o standardzie/powierzchni lub kolejnych prawdziwych obserwacji. Nie przedstawiać powielania lub maskowania jako zwiększenia liczby niezależnych obserwacji rynku.

## 28 października 2026 — S02c: zewnętrzne dane i deklarowany metraż

Sprawdzono źródła Doorstep Analytics, Inside Airbnb, AirROI, Hotelstars i visitBerlin. Pobrano darmowy EssentialsPackage Doorstep Berlin 19092026: 5847 rekordów/69 pól, daty 18–19.09.2026, przypięty SHA256. Nie znaleziono w nim powierzchni, ale są sygnały Guest Favourite i liczba udogodnień dostępności. Nie są skalą luksusu ani gwiazdkami hotelowymi.

Do train pasuje 3852 ID. Po odłożeniu konfliktów gospodarza (105), pojemności (3) i łóżek (1782) oraz sprawdzeniu typu/daty/pozostałych cech zaakceptowano 1962 połączenia. Brak połączenia oznacza NaN; wszystkie 5814 ofert pozostały w ocenie. Z posiadanych opisów Inside Airbnb parser odzyskał 667 powierzchni lokalu i 118 powierzchni pokoju. Są deklaracjami gospodarza, nie niezależnym pomiarem; odrzucono zakresy, sumy, ogrody/tarasy i niejasny zakres. Asystent sprawdził próbkę 55 fragmentów bez cen, bez deklarowania niezależnej walidacji człowieka.

W osobnym zamrożonym eksperymencie 3-fold CV porównano kontrolę S02, metraż, nowe sygnały jakości oraz oba dodatki. MAE ogólne: 54,90 / 54,59 / 54,79 / 54,57 EUR. Łączny zysk 0,61%, dla >400 EUR 0,85%; żaden kandydat nie spełnił kryterium minimalnej korzyści. Nie uruchomiono oceny validation ani testu. Kontrola odtworzyła stare przewidywania S02. **Model/API/UI bez zmiany; następny krok S03.**

60 testów przeszło (0 pominięć), lint poprawny, osobna kontrola hashy/podziałów/połączeń i metryk poprawna. Źródła, cechy, opisy, gospodarze i predykcje wyłącznie w ignorowanych lokalnych plikach; repo zawiera kod/protokół/raporty. Warunki darmowych treści Doorstep mówią o CC BY-NC-SA, ale nie określają jednoznacznie zakresu dla surowego CSV; nie publikowano go ani wzbogaconego katalogu. Bez kont, płatności lub przekazywania danych kontaktowych. [Raport i źródła](../reports/s02c/REPORT.md).
