# API i odtwarzanie S02

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

## Źródło i trening

```powershell
py -3.12 scripts/prepare_preview.py
.\.venv\Scripts\python.exe scripts/run_s02.py
```

Pierwsze polecenie jest potrzebne, gdy brakuje źródeł; odtwarza także publiczny katalog train. Drugie odmawia nadpisania istniejącego `artifacts/s02-v1`. Nie trzeba ponawiać go przy każdym starcie aplikacji. Zapisuje protokół i hashe przed fit, liczy grupowane CV, walidację, segmenty, bootstrap i selekcję według zamrożonych warunków. Test nie jest oceniany.

Jednorazowe kontrolne powtórzenie w osobnych katalogach (wykonano w S02):

```powershell
.\.venv\Scripts\python.exe scripts/run_s02.py --output .local/s02-reproduction --report-dir .local/s02-reproduction-reports
.\.venv\Scripts\python.exe scripts/verify_s02.py
```

Kolejne powtórzenie wymaga nowych nazw katalogów; nie usuwać automatycznie wyników poprzedniego eksperymentu. `verify_s02.py` sprawdza również hashe kodu użytego w S02; świadoma zmiana implementacji wymaga nowej wersji eksperymentu, nie przepisywania historii.

## Uruchomienie API

```powershell
.\scripts\start-api.ps1
```

Otwórz <http://127.0.0.1:8001/docs>. Skrypt uruchamia ukryty proces Windows, sprawdza gotowość, nie zatrzymuje innych aplikacji i przy ponownym wywołaniu wykorzystuje istniejące API. Serwer dostępny tylko na tym komputerze, nie przetrwa restartu Windows. Logi: `.local/api.stdout.log`, `.local/api.stderr.log`; PID w `.local/api-process.json`.

Uruchomienie bez skryptu, w aktywnym terminalu:

```powershell
.\.venv\Scripts\python.exe -m uvicorn staylens.api:app --host 127.0.0.1 --port 8001
```

`STAYLENS_ARTIFACT_DIR` może wskazywać inny **zaufany lokalny** katalog z manifestem i modelem. Joblib nie jest bezpiecznym formatem dla niezaufanych danych. SHA256 wykrywa niezgodność z manifestem, nie stanowi podpisu wydawcy. Brak modelu, błędny hash lub niezgodne wersje bibliotek blokują start.

## Kontrakt

| Endpoint | Znaczenie |
| --- | --- |
| `GET /health` | Gotowość po załadowaniu modelu, wersja |
| `GET /api/model` | Model, pochodzenie, cechy, wyniki rozwojowe i ograniczenia |
| `GET /api/schema` | Schemat wejścia, kategorie i zakresy train, zasady braków |
| `POST /api/predict` | Jedna predykcja w EUR/noc z kontekstem błędu |

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

Wymagane są trzy kategorie, współrzędne i liczba gości. Pozostałe cechy można pominąć lub przekazać `null` (nieznane). W flagach `false` oznacza brak udogodnienia, `true` obecność. API nie zamienia nieznanych wartości automatycznie na brak udogodnienia. Współrzędne mają granice obszaru Berlina z S01, dzielnica musi pochodzić ze schematu. W S02 nie sprawdzamy jeszcze zgodności punktu z wielokątem wybranej dzielnicy — formularz/mapa S03 powinny zapewnić spójność wyboru lokalizacji.

Nieznany typ nieruchomości jest przyjmowany z ostrzeżeniem jako brak kategorii. Kategorie z mniej niż 50 przykładami treningowymi, brakujące cechy oraz wartości poza zaobserwowanym zakresem train powodują ostrzeżenie. `Hotel room` i `Shared room` wymagają w UI dodatkowej informacji o bardzo małej próbie walidacyjnej, niezależnie od liczby train. Ceny luksusowych ofert mają duży błąd — nie interpretować odpowiedzi jako profesjonalnej wyceny.

Nadmiarowe pola (np. `price`, `host_id`), niewłaściwe typy, wartości nieskończone i naruszenia zakresów odrzucane z HTTP 422. `/api/predict` nie uczy modelu, nie zapisuje wejścia i nie wykonuje zewnętrznych zapytań. Model i manifest ładowane raz w lifespan.

Pole `development_mae_eur` to średni błąd **walidacyjny całego zbioru**, nie błąd tej konkretnej predykcji i nie przedział ufności. `/api/model` wskazuje, że test końcowy nie był oceniany. Frontend na 5174 nadal pokazuje mediany — jego integracja jest S03.

## Sprawdzenia

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check src tests scripts/run_s02.py scripts/verify_s02.py
.\.venv\Scripts\ruff.exe format --check src tests scripts/run_s02.py scripts/verify_s02.py
.\.venv\Scripts\uv.exe pip check --python .venv\Scripts\python.exe
```

Testy integracyjne wymagają lokalnego modelu; bez niego są jawnie pomijane. Przy odbiorze S02 wykonano wszystkie 27, bez pominięć, oraz prawdziwe zapytania HTTP. Plan CI/S04 musi zapewnić artefakt przed uruchomieniem testów integracyjnych, aby pominięcia nie udawały pełnej weryfikacji.
