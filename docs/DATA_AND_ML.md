# Dane i plan ML

## Źródło

[Inside Airbnb — Berlin](https://insideairbnb.com/get-the-data/), snapshot 19.09.2026, licencja zbioru CC BY 4.0. [Słownik pól](https://docs.google.com/spreadsheets/d/1iWCNJcSutYqpULSQHlNyGInUvHg2BoUGoNRIGa6Szc4/edit) definiuje `price` jako dzienną cenę w lokalnej walucie. Znak `$` to artefakt eksportu: dla Berlina używamy EUR, nie USD.

Pobrano 12 376 rekordów. Odrzucono z etapu ceny 4219 rekordów bez dodatniej ceny; nie twierdzimy, że to nieistniejące oferty. Pozostało 8157. Reguła ceny ma konsekwencje dla reprezentatywności — model będzie oceniany wśród ofert z dostępną ceną.

Grupa = `host_id`. SHA256(`staylens-v1:` + host_id), pierwsze 8 znaków hex modulo 100, progi 70/85. Liczby faktyczne: train 5814, validation 1108, test 1235. Proporcje dotyczą przestrzeni hash, nie są wymuszonymi proporcjami wierszy. Gospodarz i jego wszystkie oferty trafiają do jednej części. W publicznym podglądzie są wyłącznie oferty train, bez host_id, nazwiska/profilu gospodarza i opisów osobistych.

Manifest z URL, hashami, filtrami i schematem: [data_preflight.json](../reports/data_preflight.json). Surowe pliki nie są w Git. `prepare_preview.py` kontroluje sumy i odmawia cichej zamiany źródła.

## Pierwotny plan eksperymentu S02 (zrealizowany poniżej)

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

Od S03 karty, szczegóły i porównanie pokazują oszacowanie ML oraz różnicę względem ceny ogłoszenia. Są to zapisane przewidywania host-out-of-fold S02. Formularz Wycena używa tego samego kontraktu 18 cech i modelu pełnego train. Metraż i cechy Doorstep z odrzuconych eksperymentów nie są używane.

Mediana wyników obejmuje wszystkie przefiltrowane rekordy train, niezależnie od paginacji. Osobna „mediana podobnych ofert” obejmuje inne oferty tej samej dzielnicy i typu, z wyłączeniem wybranej oferty; nie jest wynikiem ML ani kontrolą wszystkich różnic w standardzie czy terminie. Oceny i liczby opinii pochodzą ze źródła, nie zostały wygenerowane. Pełny katalog nie jest już statycznym publicznym plikiem — API zwraca ograniczone strony i maksymalnie 60 wyników do mapy.

## Wykonany eksperyment S02 — 28.10.2026

Zamrożono [protokół](../configs/s02_protocol.json), wykonano audyt cech train, porównanie mediany segmentów z jednym HistGradientBoostingRegressor, trzy grupowane podziały train oraz osobną walidację. Bez logarytmowania celu, bez usuwania skrajnych cen, bez cech opinii/ocen i bez przeszukiwania hiperparametrów. Lista 18 cech w protokole. Kolumnę liczby łazienek, pustą we wszystkich wierszach train, odtworzono z bathrooms_text; zostały 4 braki.

Boosting spełnił wszystkie kryteria: >=10% redukcji MAE validation, RMSE <=110% baseline, brak pogorszenia mediany błędu oraz poprawa zbiorczego MAE CV. Wynik validation: MAE 53,61 EUR vs 67,87 EUR (21,0% poprawy), mediana błędu 27,46 vs 39,00 EUR. CV: 54,90 vs 69,23 EUR. Test nadal nieoceniany. Dane przedziałów cenowych ujawniają duży błąd w drogich ofertach; Hotel room i Shared room mają bardzo małą próbę oceny.

Pełne liczby, grupy, bootstrap, analiza powtórzeń cech i ograniczenia: [raport S02](../reports/s02/REPORT.md). Parametry i wyniki tego eksperymentu zachować; dalsze zmiany wymagają nowej wersji protokołu. Ostateczna pojedyncza ocena testowa dopiero po zamrożeniu rozwiązania, bez używania jej do kolejnego strojenia.

W S03 katalog pokazuje oferty train, dlatego należy użyć dla nich zapisanych przewidywań out-of-fold, a nie przewidywań pełnego modelu na własnym treningu. Formularz nowych parametrów korzysta z wybranego modelu pełnego train. To dwie jawnie oznaczone ścieżki tego samego ustalonego algorytmu/kontraktu, a nie tożsamy dopasowany artefakt. Żadna nie daje gwarancji „okazji” ani indywidualnego przedziału pewności.

## Ograniczenia

### Eksperyment S02b — cechy i augmentacja

28.10.2026, po analizie słabości drogich ofert, użytkownik poprosił o sztuczne dane i data engineering. W osobnym eksperymencie rozszerzono 18 cech do 38 oraz porównano sześć z góry ustalonych wariantów. Augmentacja oznaczała maskowanie części udogodnień w dodatkowej wersji istniejącej drogiej oferty, z zachowaniem jej ceny i współrzędnych. Osobny wariant powtarzał te oferty bez maskowania. Każdy dodał 263 wiersze, nie 263 nowe obserwacje rynku. Wszystko generowane wewnątrz części fit po podziale gospodarzy; ocena wyłącznie na danych rzeczywistych.

Najniższe ogólne MAE CV uzyskały cechy z mniejszymi liśćmi (54,33 vs 54,90 EUR), ale wynik drogich ofert pogorszył się (397,30 vs 394,00 EUR). Błąd kwadratowy pomógł drogim ofertom kosztem większości danych. Maskowane wersje nie dały wymaganej poprawy. Żaden wariant nie spełnił zamrożonych kryteriów, więc nadal obowiązuje S02. Nowych kandydatów nie oceniano na validation; test pozostaje odłożony. Wyniki nie są oceną wszystkich możliwych metod generowania danych.

[Pełny raport i wykres S02b](../reports/s02b/REPORT.md), [protokół](../configs/s02b_protocol.json), [weryfikacja pochodzenia i metryk](../reports/s02b/verification.json). Przygotowane CSV są w ignorowanym data/prepared/s02b-v1, z jawnymi flagami pochodzenia; nie trafiają do publicznego katalogu. Zgoda na badanie sztucznych danych nie oznacza przedstawiania ich jako prawdziwych ofert.

### Eksperyment S02c — rzeczywiste wzbogacenie

[Raport S02c](../reports/s02c/REPORT.md) dokumentuje pięć sprawdzonych źródeł. Bezpłatny plik Doorstep daje dokładne ID Airbnb, lecz nie metraż; po kontroli gospodarza/daty/cech wykorzystano 1962 z 3852 połączeń. Konflikty pozostają bez nowych cech. Dwa sygnały (Guest Favourite, liczba udogodnień dostępności) nie stanowią skali luksusu. Brak publikacji danych Doorstep; warunki i niejednoznaczny zakres praw do surowego CSV opisano w raporcie i THIRD_PARTY_NOTICES.md.

Z posiadanych opisów Inside Airbnb wyodrębniono deklarowany metraż 785 ofert (667 całych lokali, 118 pokoi). Zakresy, sumy, sprzeczności, części ogrodowe i niepewny zakres pominięto. To informacje gospodarzy przetworzone regułami, nie pomiary urzędowe. Braki pozostają NaN. Moduł enrichment.py i protokół s02c są oddzielone od kontraktu aktywnego modelu.

Cztery ustalone warianty z tymi samymi parametrami i foldami gospodarzy dały CV MAE: kontrola 54,90; metraż 54,59; jakość 54,79; oba 54,57 EUR. Nie osiągnięto wymaganej skali poprawy; validation nie wczytano do oceny, test nadal odłożony. Nadal obowiązuje S02. Samo dodanie metrażu do przyszłego formularza nie sprawi, że użyje go aktywny model.

### Dodatkowy audyt S03b/S03c — 28.10.2026

[S03b](../reports/s03b/REPORT.md) i [S03c](../reports/s03c/REPORT.md) sprawdziły 10 nowych wariantów z innymi algorytmami, logarytmem celu, dodatkowymi prawdziwymi atrybutami i filtrem przeznaczenia wyłącznie w treningu. Wszystkie główne oceny zachowują te same 5814 ofert, ceny i foldy gospodarzy. Najlepsze CV MAE 53,34 vs 54,90 EUR nie spełniło zadeklarowanego minimum korzyści; wynik w zakresie 100–200 EUR pogorszył się. Nie awansowano modelu na validation, test nadal nietknięty. Krzywe wskazują korzyść większego fit, lecz bez podstaw do obietnicy dokładnej wyceny. Nie ustalają nieprzekraczalnego limitu jakości.

Pięć tytułów z przeznaczeniem eventowym/zdjęciowym to sygnały do przeglądu, nie automatycznie błędne dane. Odrzucanie tych rekordów tylko z oceny sztucznie zmieniłoby problem. Dodatkowe metraże są nadal deklaracjami gospodarzy, braki nie są uzupełniane fikcyjnymi wartościami. Rozszerzone wejścia pozostają badawcze, nie w formularzu działającego S02. Samo spełnienie wymagań technicznych kursu nie potwierdza użyteczności predykcji.

### Ograniczenia źródła i zastosowania

Historyczny snapshot, bez bieżącej dostępności. Lokalizacje są anonimizowane/przybliżone. Danych zagranicznych nie przedstawiamy jako polskich. Zdjęcia pozostają pod oryginalnymi URL i mogą nie działać; UI ma zastępstwo. Zbiór, model i UI nie są afiliowane z Airbnb. Przed wdrożeniem trzeba ocenić możliwość uogólniania, powtarzalne oferty i zakres właściwych predykcji; sam duży zbiór nie dowodzi braku overfittingu.
