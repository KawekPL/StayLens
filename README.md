# StayLens

Projekt SUML — Szymon Kawlowski, s29670.

Przeglądanie i porównywanie noclegów w Berlinie: mapa, filtry i formularz orientacyjnej wyceny za noc. React odpowiada za stronę, FastAPI za dane, a scikit-learn za wycenę. Wdrożenie: Docker, Azure Container Apps, GitHub Actions i Terraform.

[Aplikacja](https://staylens.ashybay-e9483837.polandcentral.azurecontainerapps.io/) · [GitHub Actions](https://github.com/KawekPL/StayLens/actions)

## Uruchomienie

Gotowy model i katalog ofert są w `runtime/`. Przy działającym Dockerze z silnikiem Linux wystarczą:

```powershell
docker build --platform linux/amd64 -t staylens .
docker run --rm -p 127.0.0.1:8080:8080 staylens
```

Strona: http://127.0.0.1:8080/. Budowanie wymaga Internetu.

Bez Dockera, w PowerShell w katalogu projektu (Python 3.12 i Node 24):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-dev.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
npm.cmd --prefix frontend ci
.\scripts\start-preview.ps1
```

Ostatnie polecenie buduje stronę i uruchamia jeden serwer na porcie 8080. Wypisuje też polecenie zatrzymania. Po zmianach kodu zatrzymaj serwer i uruchom je ponownie.

## Gdzie jest kod

- `frontend/src/App.jsx` — główny ekran; `MapView.jsx` — mapa; `Listings.jsx` — karty, szczegóły i porównanie; `Estimator.jsx` — formularz.
- `src/staylens/api.py` — serwer: odbiera dane formularza i zwraca wycenę lub oferty.
- `src/staylens/catalog.py` — filtrowanie ofert i ustalanie dzielnicy.
- `src/staylens/{data,features,models,evaluation}.py` — dane, cechy, modele i liczenie błędów.
- `scripts/train.py` — porównanie median segmentów z boostingiem; parametry są w `src/staylens/models.py`.
- `runtime/` — gotowy model oraz katalog; `tests/` — testy działania.
- `Dockerfile`, `.github/workflows/delivery.yml`, `infra/` — kontener, automatyczne testy i wdrożenie do Azure.

## Dane i wynik

Inside Airbnb, Berlin, 19.09.2026. HistGradientBoostingRegressor korzysta z 18 cech, m.in. lokalizacji, liczby gości i udogodnień. Podział po gospodarzach: 5814 ofert treningowych, 1108 walidacyjnych, 1235 testowych. Katalog pokazuje zapisane prognozy z walidacji krzyżowej; formularz korzysta z modelu wytrenowanego na całym train.

Średni błąd bezwzględny na teście: **56,10 EUR**, dla median segmentów: **68,35 EUR**. Ceny są historyczne, bez dostępności i rezerwacji. Wycena jest orientacyjna, szczególnie dla drogich lokali. [Wyniki](reports/s05/REPORT.md) · [Źródła i licencje](THIRD_PARTY_NOTICES.md).

Opcjonalny trening: `.\.venv\Scripts\python.exe scripts/download_data.py`, potem `scripts/train.py` i `scripts/build_catalog.py` tym samym Pythonem. Wyniki trafiają do `artifacts/training-run` i `data/prepared/catalog`; nie zastępują modelu aplikacji. Historyczne raporty w `reports/` opisują wcześniejsze uruchomienia i zachowują ich oryginalne sumy kontrolne.

Testy po zbudowaniu frontendu: `.\.venv\Scripts\python.exe -m pytest -q` oraz `npm.cmd --prefix frontend test`.
