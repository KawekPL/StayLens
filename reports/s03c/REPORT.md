# S03c — mocniejszy model z bogatszymi danymi

28.10.2026. Po niewielkich zyskach na dotychczasowych wejściach sprawdzono ostatnią, oddzielnie zamrożoną hipotezę: **CatBoost z 40 cechami**. Protokół/kod zapisano w Git **05d5ff3 przed pierwszym fit tej serii**. Znane były już wcześniejsze eksperymenty i część wyników S03b; ta wiedza jest jawnie odnotowana. **Żaden z dwóch wariantów nie spełnił kryteriów. Model aplikacji pozostaje S02.**

## Dane i założenia

Te same 5814 ofert, ceny i podziały gospodarzy. Bez usuwania cen skrajnych i bez syntetycznych wierszy. Użyto wyłącznie posiadanego Inside Airbnb; żadnych danych Doorstep.

Oryginalne 18 wejść uzupełniono o 13 udogodnień (np. zmywarka, suszarka, przestrzeń zewnętrzna, sauna), wspólną łazienkę i dwa pola deklarowanego metrażu odpowiednio lokalu lub pokoju. Dodatkowo pięć deterministycznych cech i siatka współrzędnych dają łącznie 40. Surowej nazwy mniejszej okolicy nie użyto, aby formularz nie wymagał niezgodnego z treningiem przypisania adresu. Teksty służą tylko dotychczasowemu, zamrożonemu parserowi metrażu; nie są wejściami modelu.

Deklarowany metraż jest dostępny dla **667 lokali i 118 pokoi**; pozostałe wartości pozostają brakami. Obecność/nieobecność udogodnienia oznacza zapis w źródłowej liście, nie niezależną kontrolę obiektu. Nie dodawano domyślnych wymyślonych powierzchni.

Porównano tylko dwa ustalone warianty: MAE w EUR i RMSE po log1p ceny. Parametry CatBoost takie jak w S03b. Każdy model dodatkowo oceniono po ustawieniu wszystkich 16 nowych pól na „nieznane”, bez ponownego treningu. To sprawdza sytuację użytkownika wypełniającego jedynie obecne pola formularza.

## Wyniki CV

| Wariant | MAE, EUR | Mediana błędu, EUR | Błąd do 20% ceny |
| --- | ---: | ---: | ---: |
| Obecny S02 | 54,90 | 27,58 | 44,62% |
| CatBoost 40 cech, MAE | **53,34** | **27,16** | **45,91%** |
| CatBoost 40 cech, log ceny | 53,39 | 27,80 | 45,29% |
| Wariant MAE, nowe pola nieznane | 54,93 | 28,18 | 45,05% |
| Wariant log, nowe pola nieznane | 54,52 | 27,70 | 45,48% |

Najlepszy zysk to **1,56 EUR, czyli 2,85%**. Mediana poprawiła się o około 0,42 EUR, a udział trafień do 20% o 1,29 punktu procentowego. To mniej niż zapisane minimum 5%/2%/2 punkty procentowe. Oba modele przeszły ochronę głównych segmentów i kontrolę brakujących nowych pól, ale nie wymagania podstawowej korzyści. **Validation ani test nie były oceniane.** Nie zmieniono progów po wynikach.

Bootstrap po 3114 gospodarzach train z przewidywaniami OOF daje dla różnicy MAE najlepszego wariantu zakres 0,44–2,68 EUR. Jest opisowy, po wyborze wariantu i wielokrotnym użyciu CV; nie koryguje selekcji. W JSON historyczny helper zawiera etykietę „validation hosts”, ale faktyczny zakres jest tutaj train/OOF, nie nowy zbiór walidacyjny.

| Cena rzeczywista | MAE S02 | MAE bogatszego CatBoost |
| --- | ---: | ---: |
| Do 100 EUR | 23,10 | 22,54 |
| 100–200 EUR | 34,80 | **35,68** |
| 200–400 EUR | 72,83 | 71,29 |
| Ponad 400 EUR | 394,00 | 364,27 |

Spadek ogólnego błędu nie oznacza lepszej wyceny typowych ofert: w przedziale 100–200 EUR MAE wzrósł. To segmenty znanej ceny po ocenie, nie kryterium wdrożeniowego filtrowania.

## Decyzja i znaczenie dla aplikacji

Zakończono tę iterację badań zgodnie z zapisanym warunkiem stopu, bez dokładania kolejnych konfiguracji do znanych wyników. Nie rozszerzano formularza o 16 nowych pól, ponieważ zysk nie uzasadnia takiego kosztu dla użytkownika. Nie podmieniono modelu, cen w katalogu ani historycznych metryk. Aplikacja nadal działa na S02; jej wynik validation pozostaje **53,61 EUR**. Wyniku 53,34 EUR z CV nie przedstawiamy jako nowego błędu walidacyjnego aplikacji.

Łącznie S03b/S03c sprawdziły **10 nowych wariantów**, kontrolę S02 i krzywą uczenia; nie osiągnięto jakości pozwalającej wiarygodnie rozstrzygać niewielkie różnice cen. To nie dowodzi, że lepszy model jest niemożliwy. Wyniki nie uzasadniają jednak dalszego przypadkowego strojenia ani obietnicy błędu 10–15 EUR na obecnych danych.

Praktyczna rekomendacja: zachować StayLens jako eksplorator ofert z orientacyjnym odniesieniem ML i jawną jakością. Precyzyjna wycena wymagałaby nowej hipotezy i danych lepiej opisujących konkretny produkt (termin, pełny standard, powierzchnię i porównywalne warunki ceny), z osobnym planem oceny. Nie zmieniono automatycznie tematu ani zakresu zaliczenia. Docker/CI/CD/Terraform/Azure pozostają kolejną pracą dostawczą, a nie sposobem poprawy jakości predykcji.

## Weryfikacja i odtwarzanie

[Weryfikacja](verification.json) potwierdza tożsamość celów, podziały gospodarzy, hashe kodu i wyników, 40 cech, brak danych Doorstep oraz metryki dla kompletnych i nieznanych nowych pól. [Pełne wyniki](comparison.json), [protokół](../../configs/s03c_protocol.json). Cała suita ma **81 testów Pythona, 0 pominięć**; znane ostrzeżenie TestClient/httpx pozostało. Rzeczywiste HTTP działającej aplikacji nadal przechodzi kontrolę S03.

Instalacja badawczego lockfile jak w [S03b](../s03b/REPORT.md). W świeżej kopii projektu z lokalnymi źródłami i artefaktami S02, bez istniejącego katalogu s03c-v1:

```powershell
.\.venv\Scripts\python.exe scripts/run_s03c.py
.\.venv\Scripts\python.exe scripts/verify_s03c.py
```

Skrypt odmawia nadpisania oryginalnego eksperymentu. Dane cech, przewidywania i identyfikatory pozostają poza Git. Oryginalne moduły i artefakty S02/S02b/S02c nie zostały zmienione.
