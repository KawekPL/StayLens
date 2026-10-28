# StayLens

Polskojęzyczna aplikacja do eksplorowania i porównywania ofert noclegów w Berlinie. Projekt zaliczeniowy SUML, wybrany przez użytkownika 28 października 2026. Termin pracy: **3 listopada 2026**, pakiet do oddania 2 listopada. Zastępuje SupportRouter PL jako wybrany temat; tamten projekt zachowano.

## Stan: działająca lokalna aplikacja z ML (S03)

- React + FastAPI: mapa, filtry, wyszukiwarka, sortowanie, paginacja, szczegóły i porównanie do trzech ofert oraz formularz **Wycena**.
- Rzeczywiste dane Inside Airbnb Berlin z 19.09.2026. Podgląd obejmuje 5814 ofert z części treningowej.
- Katalog pokazuje zapisane oszacowania z grupowanego CV: dana oferta i jej gospodarz nie uczestniczyli w treningu modelu, który ją oceniał. Formularz nowych parametrów korzysta z modelu dopasowanego do całego train. Mediany są osobnymi statystykami.
- **Model ML wytrenowany i porównany:** boosting MAE 53,61 EUR, mediana segmentów 67,87 EUR na 1108 ofertach walidacyjnych (poprawa 21%). Grupowane CV: 54,90 vs 69,23 EUR. Test końcowy nadal nieoceniany. [Wyniki i ograniczenia](reports/s02/REPORT.md).
- Formularz sprawdza lokalizację w granicach Berlina, dobiera dzielnicę oraz rozróżnia brak udogodnienia od braku informacji. Wyniki zawierają ograniczenia jakości, szczególnie dla drogich ofert.
- Dodatkowe eksperymenty [S02b](reports/s02b/REPORT.md) i [S02c](reports/s02c/REPORT.md) nie spełniły kryteriów zastąpienia S02. Aktywny model pozostał bez zmian.
- S03: **75 testów Pythona, 7 testów JS**, produkcyjny build, rzeczywiste HTTP przez proxy oraz przeglądarkowe sprawdzenie głównych ścieżek desktop/mobile. [Raport S03](reports/s03/REPORT.md).
- Późniejszy audyt jakości [S03b](reports/s03b/REPORT.md) i [S03c](reports/s03c/REPORT.md): 10 nowych wariantów i krzywe uczenia. Najlepsze CV 53,34 zamiast 54,90 EUR, zbyt mała poprawa do awansu. **Precyzyjnej wyceny nie osiągnięto; aktywny model i validation 53,61 EUR pozostają bez zmian.** Pełna suita po tych badaniach: 81 testów Pythona; wymaga dodatkowego lockfile research.
- Docker, GitHub, CI/CD, Terraform i wdrożenie StayLens są kolejnym etapem S04. Obecny adres jest lokalny.

## Uruchomienie

Uruchomienie podglądu w osobnym procesie Windows (pozostaje aktywny po zakończeniu polecenia):

```powershell
cd C:\Users\szymo\Documents\ChatGPT\StayLens
.\scripts\start-preview.ps1
```

Skrypt uruchamia API i frontend, a przy ponownym wywołaniu wykorzystuje działające procesy. Wymaga lokalnego modelu `artifacts/s02-v1` i katalogu `data/prepared/s03`. Opcjonalny parametr `-OpenBrowser` otwiera adres w przeglądarce systemowej. Logi są w `.local/`. Po restarcie komputera uruchom skrypt ponownie.

Instalacja zależności frontendu (Python i artefakty opisane w instrukcji poniżej):

```powershell
cd C:\Users\szymo\Documents\ChatGPT\StayLens\frontend
npm.cmd ci
```

Podczas pracy programistycznej można użyć `npm.cmd run dev` przy działającym API na 8001. Ta sesja działa tylko do zamknięcia terminala. Vite przekazuje żądania `/api` do FastAPI.

Adres: <http://127.0.0.1:5174/>. Katalog pobierany jest stronicowo z API; pełnego pliku ofert nie ma w publicznym katalogu frontendu. Podgląd działa na tym komputerze; adres loopback nie jest linkiem do aplikacji w chmurze.

Przy odtwarzaniu katalogu z istniejących źródeł i artefaktów S02:

```powershell
cd C:\Users\szymo\Documents\ChatGPT\StayLens
.\.venv\Scripts\python.exe scripts\build_catalog.py
```

Skrypt weryfikuje SHA256 źródeł i zapisanych przewidywań, przygotowuje wyłącznie train i nie trenuje modelu. Dane, model oraz duży katalog pozostają poza Git; sam świeży klon nie wystarcza do startu bez odtworzenia tych plików. Dostarczanie zweryfikowanych artefaktów do kontenera/CI jest zakresem S04.

## Sprawdzenia

Backend, trening i odtwarzanie opisano w [API_AND_REPRODUCTION.md](docs/API_AND_REPRODUCTION.md). Istniejący lokalny model uruchomisz poleceniem:

```powershell
cd C:\Users\szymo\Documents\ChatGPT\StayLens
.\scripts\start-api.ps1
```

Dokumentacja API: <http://127.0.0.1:8001/docs>. Po zmianach kodu API można użyć `scripts/start-api.ps1 -Restart`; skrypt sprawdza tożsamość procesu przed jego zatrzymaniem. Testy backendu: `.\.venv\Scripts\python.exe -m pytest -q`. Kontrola danych i rzeczywistego HTTP przy działającym podglądzie: `.\.venv\Scripts\python.exe scripts/verify_s03.py`.

Sprawdzenia frontendu:

```powershell
cd C:\Users\szymo\Documents\ChatGPT\StayLens\frontend
npm.cmd test
npm.cmd run build
```

## Plan i źródła

- [Zakres, architektura i harmonogram](docs/PLAN.md)
- [Status i następny krok](docs/STATUS.md)
- [Pochodzenie danych i zasady oceny ML](docs/DATA_AND_ML.md)
- [Atrybucja źródeł](THIRD_PARTY_NOTICES.md)
- [Raport wstępnej kontroli danych](reports/data_preflight.json)
- [Porównanie modeli S02](reports/s02/REPORT.md)
- [Data engineering i sztuczne wersje ofert — S02b](reports/s02b/REPORT.md)
- [Dodatkowe rzeczywiste dane — S02c](reports/s02c/REPORT.md)
- [Integracja aplikacji i ML — S03](reports/s03/REPORT.md)
- [Audyt celu ofert, inne modele i krzywe uczenia — S03b](reports/s03b/REPORT.md)
- [Bogatsze rzeczywiste wejścia i końcowa decyzja badawcza — S03c](reports/s03c/REPORT.md)
- [API, instalacja i odtwarzanie](docs/API_AND_REPRODUCTION.md)

Źródło: [Inside Airbnb](https://insideairbnb.com/get-the-data/), CC BY 4.0. Ceny w EUR, historyczne ceny ofertowe, bez potwierdzenia dostępności i przychodów. Lokalizacje są przybliżone. StayLens nie jest powiązany z Airbnb. Zdjęcia ładowane z oryginalnych linków nie są kopiowane do projektu; prawa do nich pozostają po stronie właścicieli.
