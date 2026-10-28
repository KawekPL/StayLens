# StayLens — zakres i realizacja do 3 listopada

Decyzja: użytkownik zaakceptował temat 28.10.2026. Data 03.11 jest jego terminem pracy. Formalny termin z ogłoszenia prowadzącego to 01.01.2027 dla możliwości oceny 5 i rundy poprawek. Nie gwarantujemy oceny.

## Potrzeba i odbiorca

Osoba porównująca noclegi w Berlinie chce zobaczyć ofertę na tle innych o zbliżonych cechach, aby szybciej ocenić cenę. Główny przepływ: filtry → mapa/oferty → szczegóły → porównanie do 3 ofert → cena z modelu i kontekst błędu. Odrębny mały formularz umożliwi oszacowanie ceny noclegu o zadanych parametrach.

Jedno miasto i jeden problem regresji. Bez kont użytkowników, płatności, rezerwacji, automatycznego pobierania prywatnych danych ani udawania aktualnej dostępności. Polski interfejs, źródłowe nazwy ofert pozostają w swoim języku. Nie potrzeba NLP ani tłumaczenia zbioru treningowego.

## Architektura docelowa

Przeglądarka → React/Leaflet → FastAPI → kontrolowany pipeline scikit-learn.

Jeden obraz Docker: frontend zbudowany do plików statycznych, backend serwujący te pliki i `/api`. Model przygotowany offline i dołączony jako wersjonowany artefakt; żadnego treningu przy starcie aplikacji. Zweryfikowany, zredukowany katalog ofert obsługiwany przez API. Paginacja/limity danych, walidacja wejścia, health endpoint. Żadnego API tłumaczącego tekst.

Azure Container Apps + istniejący wzorzec ACR/Log Analytics. Terraform zarządza zasobami i obrazem; GitHub Actions CI buduje/testuje, CD przekazuje digest obrazu do Terraform. Dokładne ponowne wykorzystanie zasobów wymaga planu stanu i kosztów; nowe zasoby i wdrożenie StayLens nie zostały jeszcze wykonane. Unikamy dublowania kosztu rejestru kontenerów. Konfiguracja SupportRouter wskazuje rozbieżność 10 EUR vs zgoda 10 USD; trzeba ją poprawić w ramach prac nad infra.

## Harmonogram

| Termin | Zakres | Kryterium |
| --- | --- | --- |
| 28.10 | S01 — dane, makieta klikalna, zakres | Źródło/licencja/podział zapisane, interfejs uruchamia się, użytkownik może ocenić kierunek |
| 29.10 | S02 — pilot ML i API | Baseline + jeden kandydat, grupowana walidacja, jawny błąd, odłożony test, kontrakt API |
| 30.10 | S03 — pełna integracja | UI korzysta z tego samego pipeline co ocena, formularz oszacowania i porównania, odpowiedzi na błędy |
| 31.10 | S04 — dostawa | Rzeczywisty build Docker, Terraform, CI/CD i wdrożenie Azure |
| 01.11 | S05 — odbiór | Testy głównych ścieżek desktop/mobile, ograniczenia, monitoring i poprawki |
| 02.11 | S06 — pakiet | README, data/model card, wyniki końcowe, dostęp prowadzącego, demo i szkic maila |
| 03.11 | Rezerwa | Ostatnie poprawki i wysłanie przez użytkownika |

Nie traktuj dat jako wykonanych zadań. Statusy w STATUS.md.

S02 ukończony wcześniej, 28.10: [porównanie modeli](../reports/s02/REPORT.md). Wybrany boosting (MAE validation 53,61 EUR vs 67,87 EUR). S03 wykorzysta API pełnego modelu dla nowych parametrów oraz zapisane przewidywania out-of-fold dla ofert train z katalogu. Test końcowy pozostaje do odbioru po zamrożeniu rozwiązania. Szczególnie duże błędy dla drogich ofert oraz małe próby hotel/shared należy pokazać w UI.

Dodatkowy S02b wykonany 28.10 na prośbę użytkownika: 38 cech oraz kontrolowana augmentacja, 6 wariantów. [Wyniki](../reports/s02b/REPORT.md) nie uzasadniły zastąpienia S02. Harmonogram S03–S06 pozostaje bez zmian; nowy kontrakt cech jest eksperymentalny, nie jest częścią działającego API. Nie zwiększamy dalej zbioru sztucznymi wierszami bez nowej, sprawdzalnej hipotezy.

Dodatkowy S02c wykonany 28.10: [audyt zewnętrznych źródeł i cztery warianty](../reports/s02c/REPORT.md). Nowe sygnały jakości połączone bezpiecznie dla 1962 ofert; deklarowany metraż z istniejących opisów dla 785. MAE CV 54,57 vs 54,90 EUR, poniżej ustalonego minimum korzyści. Nadal integrujemy S02. Nie przedłużamy eksperymentów przez dobieranie kolejnych parametrów do już znanych wyników; priorytetem S03–S06 do 03.11.

## Wymagania kursu

Ogłoszenie użytkownika oraz L01 s.5 wymagają frontendu (Streamlit **lub inny**), Dockera, chmury, CI/CD i Terraform oraz jakości kodu, Gita i czytelnej logiki. Wszystkie pięć elementów musi mieć dowody rzeczywistego użycia w StayLens. Stare wdrożenie jest materiałem do adaptacji, nie dowodem wdrożenia nowej aplikacji.

Źródło lokalne: C:/Users/szymo/Documents/ChatGPT/PJATK/SUML/tekst_zrodlowy/SUML_2627_L01_online.txt, PAGE 5. Ogłoszenie w rozmowie jest źródłem terminu i wymogów maila (repozytorium, działający link, autorzy). L02 s.13 uzasadnia opis użytkownika, potrzeby i korzyści. To nie jest odrębna rubryka punktowa.

## Odbiór

- Wygląd i przepływ zrozumiałe dla użytkownika, działające filtry/mapa/porównanie, czytelność na telefonie.
- Model faktycznie wytrenowany, porównany z bazą, brak użycia testu do wyboru. Wyniki bez obietnic niepopartych oceną.
- Ostateczny adres działa, repo dostępne prowadzącemu, kontener i IaC/CI/CD odtwarzalne.
- Hosting dostępny również w czasie oceny: historyczny grant Azure wygasa 17.11.2026, odnowienie niepotwierdzone. Odbiór 03.11 nie oznacza gwarancji hostingu do stycznia.
