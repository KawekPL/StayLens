# S04 — Docker, CI/CD, Terraform i Azure

**Wykonano 28.10.2026.** [Działająca aplikacja](https://staylens.ashybay-e9483837.polandcentral.azurecontainerapps.io) · [repozytorium prywatne](https://github.com/KawekPL/StayLens) · [udane pełne CI/CD](https://github.com/KawekPL/StayLens/actions/runs/40779379265).

## Wydanie i zakres

- Kod obrazu: `205f2276e0185a3918b0c9dc09b02fad49a743dd`.
- Obraz: `srpl14055600.azurecr.io/staylens@sha256:6376509c8b33eadc5ec1719f7b861c56e00f4cc54a0c336446494def5003465c`.
- Model: oryginalny `s02-v1`, SHA256 `47ed42c9c8ccec4db103da7ec437ea240d5045191eaf20df9e9e4bd85265d7bf`, validation MAE 53,61 EUR. Nie zmieniono parametrów, danych ani modelu. Test końcowy nieoceniany.
- Publiczny katalog: 5814 rzeczywistych rekordów train i zapisane przewidywania host-OOF. Nie dołączono danych Doorstep ani danych syntetycznych.
- Wydanie danych/modelu: [s02-artifacts-v1](https://github.com/KawekPL/StayLens/releases/tag/s02-artifacts-v1), sumy i allowlista w `deploy/artifacts.json`. Osobny pakiet dowodów CI nie trafia do kontenera.

## Wyniki sprawdzeń

| Kontrola | Wynik |
| --- | --- |
| GitHub Actions, świeży Linux | verify i deploy zakończone sukcesem |
| Python | 95 testów, 0 błędów, 0 pominięć; jedno wcześniejsze ostrzeżenie Starlette/httpx |
| JavaScript | 7 testów, 0 błędów/pominięć |
| Ruff, build frontendu, Terraform validate | poprawne |
| Docker lokalnie i w CI | rzeczywisty build i HTTP, użytkownik 10001, ograniczone zasoby; lokalny proces około 151 MiB podczas odczytu, nie benchmark |
| Niezmienność modelu | identyczne SHA256; przykład 181,30 EUR w kontenerze i Azure |
| Publiczny HTTPS | health, model, katalog, szczegóły, porównanie, formularz, błędy 422/404 i brak publicznych plików modelu poprawne |
| Przeglądarka Azure | mapa/zdjęcia, 3438 ofert domyślnie, 873 Mitte, porównanie i wycena; brak zaobserwowanych błędów konsoli |
| Stan Terraform | osobne prywatne stany bootstrap/app w Blob; bootstrap exit 0 |
| Efektywna konfiguracja aplikacji | poprawna; pięć jawnych różnic domyślnych wartości odczytu API, wszystkie inne różnice odrzucane |
| Logi | potwierdzone w Log Analytics: trasa/status/czas, bez treści formularzy |

Dowody: [lokalny kontener](local_container.json), [HTTP Azure](azure_smoke.json), [konfiguracja](effective_configuration.json), [infrastruktura/budżet](infrastructure.json), [przeglądarka i logi](browser_and_logs.json). Pełne wyniki testów są artefaktami wskazanego workflow. Zrzuty do wglądu lokalnie: `.local/azure-catalog.png`, `.local/azure-estimator.png`; nie publikowano kopii fotografii ofert w repo.

## Rzeczywiste problemy rozwiązane w etapie

Pierwszy przebieg [40777312199](https://github.com/KawekPL/StayLens/actions/runs/40777312199) przeszedł testy, ale Azure odrzucił starszy format OIDC. Nowe repozytorium używa identyfikatorów właściciela/repo w `sub`. Dopasowano zaufanie przez Terraform, bez dodawania stałego sekretu i bez rozszerzenia na inne gałęzie.

Drugi [40778021649](https://github.com/KawekPL/StayLens/actions/runs/40778021649) wdrożył aplikację i przeszedł publiczny smoke test, lecz plan kontrolny ujawnił rozbieżności odczytu API. Odczyt ARM oraz kod AzureRM potwierdziły brak domyślnego `httpGet.scheme` i domyślnych czasów skalowania. Usunięto niepotrzebne wymaganie liczby nieaktywnych rewizji. Kontroler dopuszcza wyłącznie `"" → HTTP` dla trzech sond i `0 → 30/300` dla dwóch czasów; niezależnie sprawdza rzeczywisty obraz, porty, ścieżki, limity i tożsamości. Testy negatywne odrzucają inne zmiany. **Nie twierdzimy, że surowy plan aplikacji ma exit 0**; pipeline sprawdza równoważną konfigurację i zapisuje listę tych różnic. Bootstrap ma zwykły plan bez zmian.

Streaming logów lokalnego CLI zwrócił `eventStreamEndpoint`; potwierdzono działający odczyt przez API Log Analytics. Nie była to awaria aplikacji.

## Koszty i pozostałe kroki

Osobna aplikacja, grupa, Storage i tożsamości; istniejące ACR/środowisko/logi są współdzielone. SupportRouter nie usunięto ani nie wdrożono ponownie. App ma 0–1 repliki, 0,5 vCPU/1 GiB; może mieć zimny start. Nie utworzono drugiego płatnego rejestru.

Zgoda do 10 USD kredytu/miesiąc; nowy alert całej subskrypcji 8 EUR, 80/100%, według odczytanego kursu poniżej zgody. Alert nie jest twardym limitem. Grant Active, około 98,06 USD szacowanego salda, termin **17.11.2026**; odnowienie niepotwierdzone.

S05/S06 nadal obejmują odbiór i pakiet do oddania. Nie wykonano nowego testu fizycznego telefonu ani prób obciążeniowych, rollback opisano, ale nie wywołano cofnięcia obrazu. Repo prywatne — trzeba ustalić dostęp prowadzącego. Nie wysłano pracy ani maila. Utrzymanie aplikacji po 17 listopada wymaga rozstrzygnięcia grantu/hostingu. [Instrukcja operacyjna i odtwarzanie](../../docs/DEPLOYMENT.md).
