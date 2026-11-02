# Karta danych i modelu — StayLens S02

Autor projektu: Szymon Kawlowski, s29670. Stan końcowy 02.11.2026.

## Cel i użytkownik

Osoba przeglądająca noclegi w Berlinie może zestawić cenę ogłoszenia z innymi ofertami oraz orientacyjną ceną ML. Przedmiotem regresji jest dodatnia historyczna cena ofertowa jednej nocy w EUR. Model nie przewiduje przychodu, obłożenia, opłacalności, ceny transakcyjnej ani dostępności w terminie podróży.

## Dane

Źródło: Inside Airbnb, Berlin, snapshot 19.09.2026, zbiór CC BY 4.0. Źródła plików i sumy: `reports/data_preflight.json`; atrybucja i zakres zmian: `THIRD_PARTY_NOTICES.md`. 12 376 rekordów źródłowych; 4219 bez dodatniej ceny pominięto, co ogranicza reprezentatywność. Oceniana populacja: 8157 rekordów z ceną i poprawną lokalizacją według zapisanej reguły. Znak `$` w eksporcie nie zmienia lokalnej waluty Berlina — EUR.

Rozdzielenie gospodarzy przed treningiem: SHA256(`staylens-v1:` + host_id), pierwsze 8 cyfr hex modulo 100, train <70, validation 70–84, test ≥85. Faktyczne liczby: train 5814 ofert/3114 gospodarzy, validation 1108/680, test 1235/624. Brak przecięcia gospodarzy i ID ofert. Równe wartości cech nie dowodzą tożsamości obiektów; w test trzy wiersze miały cechy identyczne z train.

Katalog publiczny zawiera wyłącznie 5814 ofert train (domyślne filtry pokazują 3438). ID gospodarzy i surowe opisy nie są udostępniane w API. W finalnym modelu/katalogu nie ma danych syntetycznych ani danych Doorstep z odrzuconych eksperymentów.

## Cechy i przetwarzanie

18 cech: dzielnica, rodzaj pokoju, typ nieruchomości, szerokość/długość geograficzna, pojemność, sypialnie, łóżka, łazienki, minimalna liczba nocy, Wi-Fi, kuchnia, pralka, klimatyzacja, winda, parking, miejsce do pracy, samodzielne zameldowanie. Metraż i oceny gości nie są używane przez ten model.

Braki numeryczne pozostają NaN obsługiwane przez boosting; `null` udogodnienia oznacza brak wiedzy, nie `false`. Łazienki odzyskano deterministycznym parserem `bathrooms_text`. Kodowanie kategorii OrdinalEncoder dopasowane tylko na części fit, nieznane kategorie kodowane jako -1 i obsługiwane jak brak. Cena oraz ID gospodarza/oferty nie są cechami.

## Algorytm i wybór

HistGradientBoostingRegressor: absolute_error, 250 iteracji, learning_rate 0,05, max_leaf_nodes 15, max_depth 6, min_samples_leaf 30, L2=10, early_stopping=false, seed 42. Szczegóły: `configs/s02_protocol.json`. Sklearn1.9.1, numpy2.5.4, pandas3.1.0, joblib1.6.0; zależności i sumy w lockfile.

Baseline to mediany segmentów uczone wyłącznie na train, z kolejnymi fallbackami do większych grup i mediany globalnej. Wybór nastąpił przed testem, przez 3-fold GroupKFold po gospodarzach w train i validation. Dalsze eksperymenty nie osiągnęły ustalonej korzyści i nie zastąpiły S02.

Model pełnego train obsługuje formularz. Oszacowania istniejących ofert katalogu pochodzą z zapisanych foldów CV, w których ich gospodarza nie było w treningu. Nie utożsamiamy obu ścieżek z jednym dopasowanym artefaktem, choć korzystają z tego samego algorytmu i kontraktu cech.

## Ocena

| Część | MAE modelu | MAE baseline |
| --- | ---: | ---: |
| CV, 5814 ofert | 54,90 EUR | 69,23 EUR |
| Validation, 1108 | 53,61 EUR | 67,87 EUR |
| Test, 1235 | **56,10 EUR** | **68,35 EUR** |

Test: mediana błędu28,66 EUR, RMSE 152,81 EUR, 42,67% przewidywań w 20% ceny, 51,34% w 30 EUR. Błąd skrajnych cen pozostaje duży; dla >400 EUR MAE 381,90 EUR (66 ofert). Hotel 12 i shared 2 to zbyt małe próby do mocnych wniosków. Porównanie grup, bootstrap i kontrola hashy: `reports/s05/REPORT.md` oraz `test_evaluation.json`.

Jednorazowa ocena 02.11.2026, protokół zapisany wcześniej, żadnego fit ani strojenia po wyniku. SHA256 aktywnego modelu: `47ed42c9c8ccec4db103da7ec437ea240d5045191eaf20df9e9e4bd85265d7bf`. Historyczny manifest S02 zachowany; aktualne metadane produkcyjne dodają osobno ocenę końcową.

## Użycie i ograniczenia

Orientacyjny punkt odniesienia dla Berlina w historycznym snapshotcie. Brak walidacji czasowej/geograficznej, gwarancji braku overfittingu i indywidualnych przedziałów cen. MAE nie oznacza „cena ±56 EUR”. Niższa cena niż przewidywanie nie dowodzi okazji. Zdjęcia i mapy zależą od usług zewnętrznych. Lokalizacje są przybliżone. Aplikacja informuje o ograniczeniach.

Nie ma treningu online, modeli od użytkowników ani zewnętrznego API LLM. Health i logi monitorują działanie usługi; nie zastępują monitorowania jakości na przyszłych prawdziwych cenach. Aplikacja nie zbiera takich etykiet.
