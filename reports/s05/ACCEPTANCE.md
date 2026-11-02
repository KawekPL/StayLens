# Końcowy odbiór StayLens — 02.11.2026

**Wynik: główne ścieżki aplikacji i wdrożenie działają.** Oceniono zamrożony model, dokumentacja i pakiet przekazania przygotowane. Nie wysłano pracy prowadzącemu.

Wydanie aplikacji 0.5.0, modelS02, commit `7ab5350e9a721a67f3cb48f84a7ae38a67f04451`. [Publiczna aplikacja](https://staylens.ashybay-e9483837.polandcentral.azurecontainerapps.io/), [udany CI/CD](https://github.com/KawekPL/StayLens/actions/runs/41416768082), [repo](https://github.com/KawekPL/StayLens).

## Sprawdzenia

| Obszar | Dowód / wynik |
| --- | --- |
| Python |97 testów, zero błędów i pominięć, lokalnie i w świeżym CI; znane ostrzeżenie Starlette/httpx |
| Frontend |7 testów, build produkcyjny poprawny |
| Docker i Azure | Budowa i test HTTP kontenera w CI, ten sam obraz wdrożony; publiczny smoke ponownie wykonany z komputera |
| Katalog |3438 ofert domyślnie,873Mitte; paginacja12 → 24 karty; wyszukiwanie bez wyników pokazuje czytelny pusty stan, wyczyszczenie przywraca wyniki |
| Sortowanie | Cena rosnąco: pierwsze widoczne ceny23, 26, 27, 28, 28 EUR; reset i powrót do sortowania po opiniach |
| Szczegóły | Oferta 45475252:122 EUR, oszacowanie182 EUR, mediana169 EUR; odrębne opisy ML/median i link źródłowy |
| Porównanie | Trzy oferty obok siebie; w wąskim widoku dodanie i usunięcie oferty, pusty stan po usunięciu |
| Formularz | Kompletny przykład181,30 EUR przezHTTP/181 EUR w UI; poprawna dzielnicaMitte, kasowanie starego wyniku po zmianie parametrów |
| Błędna lokalizacja |52.31,13.06 odrzucone komunikatem o granicach Berlina, przycisk wyceny nieaktywny; poprawienie danych przywraca wycenę |
| Widok wąski | Formularz, wynik, mapa z powiększaniem, przełączenie lista/mapa, porównanie i informacje o modelu działają; brak poziomego overflow w zmierzonych widokach |
| Wynik końcowy w UI | Opis testu1235 ofert/624 gospodarzy,56,10 EUR vs 68,35 EUR widoczny w „Jak powstał wynik?” i opisie aplikacji |
| Błędy przeglądarki | Nie zaobserwowano błędów konsoli w odbiorze |
| API | Poprawne odpowiedzi dla katalogu, szczegółów, porównania i wyceny, błędne dane422, nieznane zasoby404, prywatne pliki niedostępne |
| Terraform | Efektywna konfiguracja zgodna; pięć uprzednio opisanych różnic odczytu domyślnych wartości nadal jawnie kontrolowanych, nie twierdzimy że surowy plan aplikacji ma exit0 |
| Logi | Log Analytics odczytany po nowym wdrożeniu; żądania200, trasa/status/czas, bez treści formularza |
| Repozytorium | Upublicznione po wyraźnej zgodzie autora; anonimowy odczytHTTP200; przed publikacją kontrola207 tekstowych obiektów historii nie znalazła typowych kluczy ani prywatnych ścieżek |

Dowody maszynowe: [HTTP](azure_smoke.json), [konfiguracja](effective_configuration.json), [CI/hosting/repo](operations.json), [wynik testu](test_evaluation.json), [niezależna weryfikacja ML](verification.json).

## Próba odtworzenia pakietu

ZIP z kodem commita `a0b6d92` wypakowano do nowego katalogu. Z tego katalogu (bez użycia plików pierwotnego workspace jako wejścia budowy) zbudowano obraz Docker linux/amd64 i uruchomiono go jako użytkownik 10001 z limitem 0,5 CPU/1 GiB, read-only i bez dodatkowych uprawnień. Istniejące warstwy zależności Dockera mogły zostać użyte z cache. Kontrola rzeczywistego HTTP pod lokalnym portem8082 przeszła: katalog3438, wycena181,30EUR, aktualna ocena końcowa, błędy422/404 i niedostępne pliki prywatne. [Dowód](package_check.json). Finalny ZIP uzupełniono później wyłącznie o ten zapis i dokumentację; kod aplikacji i wszystkie wejścia obrazu pozostają te same. Każde pakowanie weryfikuje CRC, listę plików i ich dokładną zawartość.

## Zakres odbioru przeglądarkowego

Testy w przeglądarce aplikacji Codex, tryb desktop i wąski. Żądane rozmiary viewport 1440×1000 i390×844; warstwa przeglądarki raportowała efektywne szerokości CSS 1096 i288px. Dla tych efektywnych szerokości `scrollWidth == clientWidth`. Nie przedstawiamy tego jako fizycznego testu telefonu ani dokładnej emulacji konkretnego modelu urządzenia. Po testach przywrócono domyślny rozmiar i pozostawiono publiczny adres.

Zrzuty tylko lokalnie w `.local/s05-screenshots/`: desktop-estimator.png, desktop-catalog.png, mobile-estimator.png, mobile-map.png i final-preview.png. Nie kopiowano fotografii źródłowych do repo/pakietu. Po przywróceniu zwykłego podglądu (375px CSS) cztery sprawdzone obrazy Numa miały complete=true i naturalWidth3500/4000; wcześniejsze zrzuty mogły przedstawiać jeszcze pola zastępcze podczas ładowania. Warstwa przechwytywania przy nadpisanym rozmiarze skalowała obraz, dlatego sam zrzut nie jest dowodem dokładnych rozmiarów fizycznego ekranu. Część kontroli katalogu zaczęto podczas wdrażania nowej wersji; po wdrożeniu odświeżono stronę i sprawdzono końcowy formularz, opis testu, widok wąski, sortowanie oraz API. Logika predykcji/katalogu pozostaje bez zmian.

## Rzeczy pozostające poza tą kontrolą

- To nie test obciążeniowy, pełny audyt bezpieczeństwa, zgodności dostępności ani wszystkich przeglądarek. Skan sekretów nie gwarantuje wykrycia każdego możliwego sekretu.
- Nie wyłączano produkcyjnej usługi w celu symulowania awarii. Testy klienta obejmują odpowiedzi błędne i awarię sieci; wcześniejszy lokalny test S03 potwierdzał zachowanie formularza po awarii API.
- Dane są historyczne, brak gwarancji aktualnej dostępności zdjęć/kafelków lub cen rezerwacji. Nie zmieniono ograniczeń modelu.
- Odczyt Azure 02.11: subskrypcjaEnabled, spendingLimitOn, szacowane98,06 USD, grant do 17.11.2026. Alert8 EUR to około 8,91 USD przy listopadowym kursie0,89770636 EUR/USD; nie jest odcięciem wydatków. Nie potwierdzono odnowienia.
- Ręczny rollback opisany w DEPLOYMENT.md, ale nie wykonywano cofnięcia produkcyjnego obrazu podczas tego odbioru.

**Do wykonania przez autora:** przejrzenie demo i materiałów, wysłanie maila, utrzymanie hostingu podczas oceny. Publiczne repo nie wymaga już zaproszenia prowadzącego. Termin przygotowania03.11 jest zachowany; formalny termin z ogłoszenia01.01.2027.
