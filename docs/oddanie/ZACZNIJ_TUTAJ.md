# StayLens — projekt zaliczeniowy SUML

**Szymon Kawlowski · s29670 · praca indywidualna · 2 listopada 2026**

StayLens to polskojęzyczna aplikacja do porównywania noclegów w Berlinie. Łączy katalog rzeczywistych ofert, mapę, filtry, porównanie do trzech obiektów i orientacyjną wycenę ML na podstawie parametrów noclegu. Pomaga zestawić cenę ogłoszenia z podobnymi ofertami i oszacowaniem modelu. Nie obsługuje rezerwacji i nie potwierdza aktualnej dostępności ani „okazji”.

- **Aplikacja:** https://staylens.ashybay-e9483837.polandcentral.azurecontainerapps.io/
- **Repozytorium:** https://github.com/KawekPL/StayLens
- **Automatyzacja:** https://github.com/KawekPL/StayLens/actions
- **Kontakt/autorstwo:** Szymon Kawlowski, numer albumu s29670.

Repozytorium jest publiczne od 02.11.2026, zgodnie z decyzją autora. Sprawdzono odczyt bez zalogowania, bez potrzeby zaproszenia prowadzącego. Archiwum dodatkowo zawiera kompletny kod bieżącego wydania i zamrożony model. Nie wysłano pracy ani maila.

## Pięć wymagań technologicznych

| Wymaganie ogłoszenia | Wykonanie | Dowód w katalogu `StayLens` |
| --- | --- | --- |
| Streamlit lub inny frontend | React + Vite + Leaflet, API FastAPI | `frontend/src/`, `src/staylens/application.py` |
| Docker | Jeden obraz: UI, API, zamrożony model; użytkownik bez roota | `Dockerfile`, `.dockerignore` |
| Chmura | Azure Container Apps, ACR, Storage, Log Analytics | publiczny adres, `deploy/azure.json`, raporty S04/S05 |
| CI/CD | GitHub Actions: testy, budowa, test kontenera, OIDC, wdrożenie digesta | `.github/workflows/delivery.yml` |
| Terraform | Zasoby i uprawnienia bootstrap oraz aplikacja; dwa stany Blob | `infra/bootstrap/`, `infra/app/` |

Git i czytelna logika: kod podzielony na cechy/model, API/katalog, frontend i dostawę; wersje bibliotek i sumy artefaktów przypięte. Raporty rozróżniają historię badań, walidację, test końcowy i rzeczywiste wdrożenie. Zastosowanie innego frontendu niż Streamlit jest wprost dopuszczone w ogłoszeniu prowadzącego. Ocena końcowa należy do prowadzącego.

## Wynik ML i granice zastosowania

Inside Airbnb, Berlin 19.09.2026. Podział po gospodarzach: 5814 ofert train, 1108 validation, 1235 test. HistGradientBoostingRegressor, 18 cech. Test końcowy: MAE **56,10 EUR**, mediana błędu **28,66 EUR**; baseline MAE **68,35 EUR**, poprawa **17,92%**. Część testowa obejmuje 624 innych gospodarzy; nie była używana do strojenia.

Wysoki błąd dla cen powyżej 400 EUR (381,90 EUR na 66 ofertach), małe próby hotelowych/współdzielonych pokoi. Ceny są ofertowe, historyczne, a lokalizacje przybliżone. Metraż, daty podróży i aktualna dostępność nie są wejściami modelu. Model nie został zmieniony przy odbiorze. Katalog wykorzystuje zapisane przewidywania bez ocenianego gospodarza w treningu; formularz korzysta z modelu uczonego na pełnym train.

## Zawartość pakietu ZIP

- `ZACZNIJ_TUTAJ.md` — ten przewodnik.
- `MAIL_DO_PROWADZACEGO.txt` — szkic do skopiowania, nie wiadomość wysłana.
- `MANIFEST.json` — wersja kodu, autor, suma modelu i sumy każdego pliku.
- `StayLens/` — kod i dokumentacja projektu z konkretnego commita.
- `StayLens/.runtime/` — zweryfikowany model oraz publiczny katalog, gotowe do budowy Dockera.
- `StayLens/docs/oddanie/` — karta modelu/danych, demonstracja i wyjaśnienie architektury.
- `StayLens/reports/s05/` — test końcowy, wykres, raport odbioru i dowody.

Pakiet nie zawiera sekretów, stanów Terraform, środowiska `.venv`, surowych zbiorów, identyfikatorów gospodarzy ani wierszowych przewidywań testowych. Nie dołączono danych Doorstep ani fotografii ofert. Zdjęcia i mapa są pobierane przez przeglądarkę od dostawców zewnętrznych; licencje i atrybucja w `THIRD_PARTY_NOTICES.md`.

## Uruchomienie z archiwum, bez konta GitHub

Wymagany Docker z silnikiem Linux oraz dostęp do Internetu podczas budowania (obrazy bazowe i przypięte zależności). Po wypakowaniu przejdź w PowerShell do katalogu `StayLens`, zawierającego Dockerfile i ukryty katalog `.runtime`:

```powershell
docker build --platform linux/amd64 -t staylens:submission .
docker run --rm --name staylens-submission -p 127.0.0.1:8080:8080 --cpus 0.5 --memory 1g --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m --cap-drop ALL --security-opt no-new-privileges staylens:submission
```

Otwórz http://127.0.0.1:8080. Zatrzymanie: Ctrl+C w terminalu kontenera. Nie potrzeba konta Azure, tokena OpenAI, ponownego treningu ani pobierania prywatnego wydania. W drugiej konsoli z Pythonem 3.12 można uruchomić `py -3.12 scripts/smoke_deployment.py http://127.0.0.1:8080`.

02.11 sprawdzono rzeczywistą budowę i uruchomienie z wypakowanego ZIP w osobnym katalogu. Test HTTP przeszedł, łącznie z wyceną181,30EUR i katalogiem3438ofert. Zapis znajduje się w `StayLens/reports/s05/package_check.json`. Kontener korzysta z przygotowanego modelu; niczego nie trenuje przy starcie.

Archiwum jest eksportem źródeł, bez historii `.git`. Historia, CI i wersjonowane wydania pozostają w repo. Pełne odtwarzanie środowiska testowego z GitHub opisuje `docs/DEPLOYMENT.md`; surowe dane badań pobiera skrypt `prepare_preview.py`. Nie uruchamiać eksperymentów ponownie tylko w celu obejrzenia aplikacji. Końcowy test został otwarty raz; jego wynik nie służy do dalszego strojenia.

## Dostępność podczas oceniania

Aplikacja działa w Azure w trybie 0–1 replik; pierwsze wejście po uśpieniu może wymagać kilkudziesięciu sekund. Odczyt konta 02.11.2026 potwierdził subskrypcję Azure for Students, ochronę wydatków On i termin grantu **17.11.2026**. Nie potwierdzono odnowienia. Przed tą datą autor musi zapewnić dalszą dostępność na czas oceny. Budżet z alertami 8 EUR nie zatrzymuje automatycznie usług. Archiwum pozwala również odtworzyć aplikację lokalnie.

## Ostatnie czynności autora

1. Otworzyć publiczny adres na swoim telefonie i przejść scenariusz demo.
2. Sprawdzić link do publicznego repo w prywatnym oknie przeglądarki.
3. Wysłać szkic po sprawdzeniu linków i dołączyć ZIP, jeśli wybrano ten sposób przekazania kodu.
4. Utrzymać działający hosting w okresie oceniania, również po 17 listopada.

Termin własny: 03.11.2026. Termin z ogłoszenia prowadzącego pozwalający zachować szansę na ocenę 5 i rundę poprawek: 01.01.2027. Gotowy pakiet nie oznacza wysłania ani przyznania oceny.
