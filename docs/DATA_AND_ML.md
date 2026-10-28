# Dane i plan ML

## Źródło

[Inside Airbnb — Berlin](https://insideairbnb.com/get-the-data/), snapshot 19.09.2026, licencja zbioru CC BY 4.0. [Słownik pól](https://docs.google.com/spreadsheets/d/1iWCNJcSutYqpULSQHlNyGInUvHg2BoUGoNRIGa6Szc4/edit) definiuje `price` jako dzienną cenę w lokalnej walucie. Znak `$` to artefakt eksportu: dla Berlina używamy EUR, nie USD.

Pobrano 12 376 rekordów. Odrzucono z etapu ceny 4219 rekordów bez dodatniej ceny; nie twierdzimy, że to nieistniejące oferty. Pozostało 8157. Reguła ceny ma konsekwencje dla reprezentatywności — model będzie oceniany wśród ofert z dostępną ceną.

Grupa = `host_id`. SHA256(`staylens-v1:` + host_id), pierwsze 8 znaków hex modulo 100, progi 70/85. Liczby faktyczne: train 5814, validation 1108, test 1235. Proporcje dotyczą przestrzeni hash, nie są wymuszonymi proporcjami wierszy. Gospodarz i jego wszystkie oferty trafiają do jednej części. W publicznym podglądzie są wyłącznie oferty train, bez host_id, nazwiska/profilu gospodarza i opisów osobistych.

Manifest z URL, hashami, filtrami i schematem: [data_preflight.json](../reports/data_preflight.json). Surowe pliki nie są w Git. `prepare_preview.py` kontroluje sumy i odmawia cichej zamiany źródła.

## Pierwszy eksperyment (jeszcze niewykonany)

- Cel: `price`, cena ofertowa za noc w EUR. Model nie przewiduje popytu, przychodu ani rentowności.
- Kandydaci cech do audytu na train: lokalizacja, dzielnica, typ pokoju/nieruchomości, liczba gości, sypialni/łóżek/łazienek, wybrane udogodnienia. Dane opinii mogą być dodatkowymi cechami dla istniejącej oferty, z konsekwentnym traktowaniem braków dla nowej.
- Wykluczyć identyfikatory i teksty ujawniające docelową cenę, inne pochodne cen, szacowane przychody/obłożenie. Nie traktować zamkniętych dni kalendarza jako potwierdzonych rezerwacji.
- Baseline: mediana uczona na train, np. segment dzielnica × typ z bezpiecznym fallbackiem. Świeże mediany wyliczone na własnym zbiorze testowym byłyby przeciekiem.
- Jeden mocniejszy kandydat: boosting drzew na danych tabelarycznych; wybór implementacji po kontroli braków/wersji. Transformacja celu log1p może pomóc przy skośnych cenach; decyzję i metryki zapisujemy przed odczytem testu.
- Pipeline imputacji/kodowania dopasowany tylko na train. Mała grupowana walidacja wewnątrz train albo ustalony dev według host_id — szczegóły zamrozić przed fit.
- Raportować MAE w EUR, medianę błędu bezwzględnego, RMSE i wyniki segmentów z licznością. Bez obiecanego progu jakości przed pilotem.
- Test odłożony do pojedynczego odbioru końcowego po zamrożeniu wyboru. Pilot ma wykazać, czy kandydat daje wartość ponad prosty punkt odniesienia.
- Przy porównaniu różnych snapshotów grupować ten sam listing/host; nie dopuszczać duplikatów tego samego obiektu do train i test.

## Co obecnie wyświetla UI

Mediana wyników obejmuje przefiltrowane rekordy train. „Mediana dzielnicy” obejmuje inne oferty tej samej dzielnicy i typu, z wyłączeniem wybranej oferty. Przy mniej niż 5 porównywalnych rekordach brak procentowego odniesienia. Nie jest to wycena ML ani dowód okazji; nie kontroluje wszystkich różnic w standardzie czy terminie. Oceny i liczby opinii pochodzą ze źródła, nie zostały wygenerowane.

## Ograniczenia

Historyczny snapshot, bez bieżącej dostępności. Lokalizacje są anonimizowane/przybliżone. Danych zagranicznych nie przedstawiamy jako polskich. Zdjęcia pozostają pod oryginalnymi URL i mogą nie działać; UI ma zastępstwo. Zbiór, model i UI nie są afiliowane z Airbnb. Przed wdrożeniem trzeba ocenić możliwość uogólniania, powtarzalne oferty i zakres właściwych predykcji; sam duży zbiór nie dowodzi braku overfittingu.
