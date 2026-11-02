# API i odtwarzanie S02/S03

**S05, 02.11:** produkcyjne `staylens.production:create_production_app` w wersji0.5.0 wymaga także statycznego `final-evaluation.json` (dostarczanego przez build Vite). `/api/model` dodaje `test_evaluated: true` i `final_evaluation` z wynikiem testu1235ofert. Zamrożony historyczny `staylens.api:create_app`/manifest S02 nadal opisuje pierwotną ocenę rozwojową. Model, wejścia i przewidywania nie zmieniły się. Pełne CI:97 testów Python i7 JS. Repo jest publiczne; pakiet dla odbiorcy ma gotowe `.runtime` i nie wymaga pobierania z GitHub.

**S04:** gotowy obraz serwuje produkcyjny frontend oraz API przez `staylens.production:create_production_app`. Pobieranie przypiętych artefaktów, świeży klon, Docker i Azure opisano w [DEPLOYMENT.md](DEPLOYMENT.md). Pełne CI ma teraz 95 testów Python i 7 JS. Poniższe instrukcje zachowują odtwarzanie historycznych badań i lokalny tryb deweloperski. Nie używaj pakietu CI z usuniętym `host_id` do zastępowania oryginalnych artefaktów badawczych.

Python 3.12; zależności dokładnie przypięte w `pyproject.toml` i dwóch uniwersalnych lockfile z SHA256. Modele są lokalne, nie ma klucza OpenAI ani treningu przy starcie serwera.

## Instalacja

W katalogu projektu:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install uv==0.13.6
.\.venv\Scripts\uv.exe pip sync --python .venv\Scripts\python.exe --require-hashes requirements-dev.lock.txt
.\.venv\Scripts\uv.exe pip install --python .venv\Scripts\python.exe --no-deps -e .
```

W środowisku wykonawczym używa się `requirements.lock.txt`; dev zawiera także pytest, httpx, ruff i matplotlib. Nie kopiować `.venv` między Windows i Linux. Dla Linuksa zastąpić ścieżki `Scripts` odpowiednikami `.venv/bin/`.

## Źródło i trening S02

```powershell
New-Item -ItemType Directory -Force data/raw
Invoke-WebRequest https://data.insideairbnb.com/germany/be/berlin/2026-09-19/data/listings.csv.gz -OutFile data/raw/listings.csv.gz
Invoke-WebRequest https://data.insideairbnb.com/germany/be/berlin/2026-09-19/visualisations/neighbourhoods.geojson -OutFile data/raw/neighbourhoods.geojson
.\.venv\Scripts\python.exe scripts/run_s02.py
```

Pobieranie wykonuj tylko przy braku lokalnych źródeł. Trening sprawdza przypięty hash danych i odmawia nadpisania istniejącego `artifacts/s02-v1`. Nie trzeba ponawiać go przy każdym starcie aplikacji. Zapisuje protokół i hashe przed fit, liczy grupowane CV, walidację, segmenty, bootstrap i selekcję według zamrożonych warunków. Test nie jest oceniany. Dawny `prepare_preview.py` zachowano do odtwarzania S01; nie uruchamiaj go w zwykłym procesie S03, ponieważ tworzy nieużywany już duży plik ofert w publicznym katalogu frontendu.

Jednorazowe kontrolne powtórzenie w osobnych katalogach (wykonano w S02):

```powershell
.\.venv\Scripts\python.exe scripts/run_s02.py --output .local/s02-reproduction --report-dir .local/s02-reproduction-reports
.\.venv\Scripts\python.exe scripts/verify_s02.py
```

Kolejne powtórzenie wymaga nowych nazw katalogów; nie usuwać automatycznie wyników poprzedniego eksperymentu. `verify_s02.py` sprawdza również hashe kodu użytego w S02; świadoma zmiana implementacji wymaga nowej wersji eksperymentu, nie przepisywania historii.

## Katalog i uruchomienie aplikacji S03

Po przygotowaniu oryginalnych artefaktów S02:

```powershell
.\.venv\Scripts\python.exe scripts/build_catalog.py
```

Builder sprawdza źródło, geometrię i oryginalny plik przewidywań CV. Łączy dokładne ID/cenę/gospodarza, wymaga 5814 rzeczywistych ofert train i usuwa pola gospodarza z wyniku. Zapisuje katalog, geometrię i manifest w `data/prepared/s03`; manifest jest także w `reports/s03`. Nie trenuje modelu. Przypięty hash CV dotyczy artefaktu z oryginalnego środowiska S02: nowy format serializacji lub inne bajty wymagają wyjaśnienia i wersjonowania, nie wyłączenia kontroli.

API można uruchomić osobno:

```powershell
.\scripts\start-api.ps1
```

Otwórz <http://127.0.0.1:8001/docs>. Skrypt uruchamia ukryty proces Windows, sprawdza gotowość, nie zatrzymuje innych aplikacji i przy ponownym wywołaniu wykorzystuje istniejące API. Serwer dostępny tylko na tym komputerze, nie przetrwa restartu Windows. Logi: `.local/api.stdout.log`, `.local/api.stderr.log`; PID w `.local/api-process.json`.

Uruchomienie bez skryptu, w aktywnym terminalu:

```powershell
.\.venv\Scripts\python.exe -m uvicorn staylens.application:app --host 127.0.0.1 --port 8001
```

`STAYLENS_ARTIFACT_DIR` może wskazywać inny **zaufany lokalny** katalog z manifestem i modelem. Joblib nie jest bezpiecznym formatem dla niezaufanych danych. SHA256 wykrywa niezgodność z manifestem, nie stanowi podpisu wydawcy. Brak modelu, błędny hash lub niezgodne wersje bibliotek blokują start.

`STAYLENS_CATALOG_DIR` wskazuje katalog S03. Brak plików, niezgodność modelu/źródła/hashy, nadmiarowe pola lub nieprawidłowa liczba ofert blokują start. Model i katalog są ładowane raz. `scripts/start-preview.ps1` uruchamia API oraz Vite na 5174; `/api` jest przekazywane do 8001. Po zmianie kodu serwera `scripts/start-api.ps1 -Restart` restartuje wyłącznie proces zweryfikowany jako API tego projektu. Aplikacja S03 opakowuje zamrożone `staylens.api`, nie zmienia historycznego modułu.

## Kontrakt

| Endpoint | Znaczenie |
| --- | --- |
| `GET /health` | Gotowość po załadowaniu modelu, wersja |
| `GET /api/model` | Model, pochodzenie, cechy, wyniki rozwojowe i ograniczenia |
| `GET /api/schema` | Schemat wejścia, kategorie i zakresy train, zasady braków |
| `POST /api/predict` | Jedna predykcja w EUR/noc z kontekstem błędu |
| `GET /api/catalog/meta` | Źródło, dzielnice, dozwolone pary typu noclegu i obiektu, metoda i metryki |
| `GET /api/catalog/listings` | Filtry, sortowanie, offset i limit, statystyki całego wyboru, pierwsze 60 punktów mapy |
| `GET /api/catalog/listings/{id}` | Jedna oferta z oszacowaniem host-out-of-fold i medianą grupy |
| `GET /api/catalog/compare?ids=A&ids=B` | Od jednej do trzech różnych ofert, z zachowaniem kolejności |
| `GET /api/location?latitude=52.52&longitude=13.405` | Dzielnica z geometrii Berlina lub 422 dla punktu poza granicami |
| `POST /api/estimate` | Wycena formularza, kontrola dzielnicy i pary typów, polskie ostrzeżenia |

Katalog: `district`, `room_type`, `guests` (1–16), `max_price` (do 20000), `query` (do 120 znaków), `sort` (`reviewed`, `price-asc`, `price-desc`), `offset` (0–10000), `limit` (1–60; domyślnie 12). Odpowiedź zawiera `items`, `total`, `offset`, `limit`, `hasMore`, `mapItems` i `summary`. Statystyki i histogram liczone są ze wszystkich dopasowań. Kolejność ma stabilny klucz ID przy remisach. Nie ma endpointu zwracającego cały plik źródłowy ani identyfikatory gospodarzy; paginacja nie jest kontrolą dostępu do publicznych ofert.

Przykładowe ciało JSON do `/api/predict`:

```json
{
  "district": "Mitte",
  "room_type": "Entire home/apt",
  "property_type": "Entire rental unit",
  "latitude": 52.52,
  "longitude": 13.405,
  "accommodates": 2,
  "bedrooms": 1.0,
  "beds": 1.0,
  "bathrooms": 1.0,
  "minimum_nights": 2,
  "wifi": true,
  "kitchen": true,
  "washer": true,
  "air_conditioning": false,
  "elevator": true,
  "parking": false,
  "workspace": true,
  "self_check_in": true
}
```

Ten przykład daje **181,30 EUR** dla modelu s02-v1. Wartość dotyczy cech przykładu; brak terminu podróży i aktualnej dostępności. Wynik zaokrąglany do centów, co nie oznacza dokładności do centa.

Wymagane są trzy kategorie, współrzędne i liczba gości. Pozostałe cechy można pominąć lub przekazać `null` (nieznane). W flagach `false` oznacza brak udogodnienia, `true` obecność. API nie zamienia nieznanych wartości automatycznie na brak udogodnienia. Historyczny `/api/predict` zachowuje kontrakt S02: granice prostokąta i dzielnica ze schematu. Formularz korzysta z `/api/estimate`, który dodatkowo weryfikuje rzeczywisty wielokąt dzielnicy oraz zgodność typu obiektu i noclegu; nieznana lub niezgodna para daje 422. Dla prawidłowego wspólnego wejścia oba endpointy zwracają identyczną cenę z tego samego modelu.

Nieznany typ nieruchomości jest przyjmowany z ostrzeżeniem jako brak kategorii. Kategorie z mniej niż 50 przykładami treningowymi, brakujące cechy oraz wartości poza zaobserwowanym zakresem train powodują ostrzeżenie. `Hotel room` i `Shared room` wymagają w UI dodatkowej informacji o bardzo małej próbie walidacyjnej, niezależnie od liczby train. Ceny luksusowych ofert mają duży błąd — nie interpretować odpowiedzi jako profesjonalnej wyceny.

Nadmiarowe pola (np. `price`, `host_id`), niewłaściwe typy, wartości nieskończone i naruszenia zakresów odrzucane z HTTP 422. `/api/predict` nie uczy modelu, nie zapisuje wejścia i nie wykonuje zewnętrznych zapytań. Model i manifest ładowane raz w lifespan.

Pole `development_mae_eur` to średni błąd **walidacyjny całego zbioru**, nie błąd tej konkretnej predykcji i nie przedział ufności. `/api/model` wskazuje, że test końcowy nie był oceniany. Frontend pokazuje wyniki ML z API oraz osobno mediany. Katalog używa zapisanych wyników trzech modeli CV (`host_oof`), formularz modelu całego train (`full_train`); nie są to identyczne dopasowane artefakty.

## Sprawdzenia

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\python.exe scripts/verify_s03.py
.\.venv\Scripts\uv.exe pip check --python .venv\Scripts\python.exe
```

`verify_s03.py` wymaga działającego podglądu na 5174 i sprawdza również rzeczywiste HTTP przez proxy. Starsze testy S02 potrafią pominąć integrację przy braku modelu; nowe S03 wymagają artefaktów i w takiej sytuacji kończą się błędem. Przy odbiorze S03 wykonano wszystkie **75 testów Pythona, bez pominięć**, 7 testów JS oraz build Vite. TestClient nadal emituje znane ostrzeżenie o przyszłym wycofaniu obsługi httpx w Starlette. Plan CI/S04 musi dostarczyć artefakty przed testami. Sam świeży klon nie jest jeszcze gotowym pakietem wykonawczym.

Po badaniach S03b/S03c pełna suita liczy **81 testów** i wymaga opcjonalnego CatBoost. Do jej odtworzenia użyj `requirements-research.lock.txt` zamiast lockfile dev, następnie ponownie zainstaluj lokalny pakiet przez `uv pip install --no-deps -e .`. Bazowe wersje pozostają identyczne. Modele badawcze nie awansowały, więc wykonawczy model/API nadal używa bazowego `requirements.lock.txt`; CatBoost nie jest potrzebny przy serwowaniu S02. [Protokoły i odtwarzanie badań](../reports/s03b/REPORT.md).
