# Dostawa StayLens — S04

Model wykonawczy pozostaje dokładnie S02, SHA256 `47ed42c9c8ccec4db103da7ec437ea240d5045191eaf20df9e9e4bd85265d7bf`. Nie ma treningu podczas budowy obrazu ani startu serwera. Test końcowy nie jest oceniany w CI.

## Architektura

Przeglądarka → publiczny HTTPS Azure Container Apps → jeden kontener (React zbudowany przez Vite + FastAPI + model scikit-learn). Katalog wyświetla wcześniejsze przewidywania host-out-of-fold. Formularz używa tego samego pełnego modelu train co lokalnie. Nowy moduł `staylens.production` opakowuje aplikację; historyczne moduły ML pozostają niezmienione.

Azure: osobna grupa `rg-staylens-14055600`, aplikacja `staylens`, tożsamości runtime/deploy i Storage `stlens14055600` ze stanami Terraform. Rejestr `srpl14055600` i środowisko `env-supportrouter-14055600` są współdzielonymi istniejącymi zależnościami. StayLens nie przejmuje ich do swojego stanu, nie modyfikuje starej aplikacji ani jej stanu. Dodaje tylko własne uprawnienia do pobierania/wysyłania obrazów i dołączania do środowiska. Usunięcie starego środowiska lub rejestru uszkodzi również StayLens — przed sprzątaniem konieczna migracja obu aplikacji.

Runtime: użytkownik 10001 bez roota, jeden worker, 0,5 vCPU / 1 GiB, 0–1 repliki, sondy startup/readiness/liveness. Uśpienie do zera oszczędza kredyt; pierwsze wejście może wymagać zimnego startu. HTTPS zapewnia Azure, HTTP jest przekierowywane. Kod nie przyjmuje modeli od użytkownika. Kompresja odpowiedzi i cache zasobów statycznych ograniczają transfer. Logi aplikacji zawierają szablon trasy, status i czas, bez ciał formularzy, wyszukiwanych fraz, identyfikatorów ofert i adresów IP.

## Wersjonowane artefakty

`deploy/artifacts.json` określa SHA256 archiwów i każdego dozwolonego pliku. Prywatne wydanie GitHub `s02-artifacts-v1` zawiera:

- `staylens-runtime.zip`: model + manifest oraz zweryfikowany katalog S03 + manifest + geometria. W obrazie nie ma surowego CSV, identyfikatorów gospodarzy ani predykcji validation.
- `staylens-ci.zip`: wyłącznie zapisane wcześniej predykcje CV/validation potrzebne do testów regresji metryk, z usuniętym `host_id`. Nie jest częścią obrazu. Nie zawiera zbioru testowego.

`scripts/release_artifacts.py fetch` pobiera prywatne wydanie przez GitHub CLI, sprawdza hashe i dokładną listę plików, dopiero wtedy odtwarza `.runtime`. `--ci` dodatkowo odtwarza ścieżki wymagane przez pełne testy. Nie uruchamiaj `fetch --ci` w oryginalnym katalogu badań: wersja CI tabel ma usuniętą kolumnę gospodarza i nie zastępuje oryginałów badawczych. Użyj świeżego klonu.

Odświeżenie artefaktów jest osobnym świadomym procesem: nowa wersja, hashe i raport. Zwykły deploy nie zmienia modelu. Pliki joblib są zaufanymi artefaktami projektu; sam hash nie jest podpisem zewnętrznego dostawcy.

## Świeży klon i lokalny Docker

Wymagane Git, GitHub CLI z dostępem do prywatnego repo, Python 3.12 i Docker z silnikiem Linux:

```powershell
git clone https://github.com/KawekPL/StayLens.git
cd StayLens
gh auth status
py -3.12 scripts/release_artifacts.py fetch
docker build --platform linux/amd64 -t staylens:local .
docker run --rm --name staylens-local -p 127.0.0.1:8080:8080 --cpus 0.5 --memory 1g --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m --cap-drop ALL --security-opt no-new-privileges staylens:local
```

W drugiej konsoli: `py -3.12 scripts/smoke_deployment.py http://127.0.0.1:8080`. Przeglądarka: http://127.0.0.1:8080. Obraz ma przypięte digesta obrazów bazowych Node/Python i hash-lock zależności runtime. Badawcze CatBoost/matplotlib nie są instalowane w obrazie. Cały frontend buduje się w oddzielnym etapie Node.

## CI/CD

`.github/workflows/delivery.yml` uruchamia się dla PR, push do `main` zmieniającego kod/konfigurację i ręcznego uruchomienia. Zmiany samych raportów/Markdown nie powodują zbędnego deployu.

1. Świeży Linux runner pobiera zweryfikowane artefakty; instaluje pełny lock badawczy, sprawdza Ruff, wszystkie testy Python (zero pominięć), testy JS i build frontendu.
2. Waliduje Terraform bez uprawnień chmurowych. Buduje obraz, uruchamia ograniczony kontener i sprawdza rzeczywiste HTTP, oryginalną wycenę 181,30 EUR, błędy oraz brak dostępu do plików modelu.
3. Zapisuje dokładnie przetestowany obraz jako krótkotrwały artefakt GitHub. Zadanie deploy pobiera ten obraz; nie buduje drugiego, potencjalnie innego obrazu.
4. Deploy działa wyłącznie z `main`, poza PR. OIDC Azure ufa `repo:KawekPL@317614566/StayLens@1437674578:ref:refs/heads/main`; nie ma stałego hasła Azure w GitHub. To [format niezmiennych identyfikatorów GitHuba](https://docs.github.com/en/actions/reference/security/oidc) używany przez nowe repozytoria od 15.07.2026. Wartości potwierdzono przez REST repo oraz ustawienia OIDC, nie zgadnięto z nazwy. Sprawdzany jest także aktualny commit głównej gałęzi.
5. Obraz trafia do ACR pod SHA commita. Terraform dostaje **digest**, nie zmienny tag. Kontrola planu odrzuca usuwanie zasobów, inne aplikacje i zwiększenie limitu replik/zasobów.
6. Terraform stosuje plan, HTTP sprawdza publiczne wdrożenie i wersję commita. Kolejny plan ma wykazać brak zmian. Wyniki testów i odbioru są artefaktami workflow.

Repo jest prywatne. Dostęp prowadzącego trzeba uzgodnić przed oddaniem; samo wysłanie linku nie daje mu uprawnień. Nie wysyłano zaproszeń ani maila.

## Terraform i tożsamości

Terraform 1.16.5, AzureRM 4.81.0; lockfile dla Windows/Linux w obu katalogach.

- `infra/bootstrap`: zasoby bazowe StayLens, zaufanie OIDC, zakresy RBAC i budżet. Uruchamia operator, nie CI.
- `infra/app`: tylko aplikacja StayLens, digest obrazu i konfiguracja sond/skalowania. Uruchamia CI.
- Dwa oddzielne prywatne kontenery stanu, uwierzytelnienie Entra ID, blokowanie Blob lease, wersjonowanie i retencja usunięć 7 dni. Brak kluczy Storage w repo i CI.
- Deploy: Container Apps Contributor w nowej grupie i uprawnienie przyłączenia do wspólnego środowiska, Reader nowej grupy, Managed Identity Operator własnego runtime, AcrPush wspólnego rejestru, Blob Data Contributor wyłącznie stanu aplikacji. Nie ma Owner ani dostępu do stanu bootstrap.
- Runtime: tylko AcrPull. Nie potrzebuje dostępu do Storage, treningu ani zewnętrznego API ML.

Pierwszy bootstrap rozpoczyna się ze stanem lokalnym, a następnie migruje do utworzonego Blob przez `terraform init -migrate-state`. Przy odtwarzaniu istniejącego środowiska zawsze inicjalizuj istniejący zdalny stan; nie twórz nowego pustego stanu i nie importuj zasobów starego projektu. Nie publikuj state ani planów binarnych/JSON — mogą zawierać dane infrastruktury i pola oznaczone jako sensitive przez providera.

## Koszty i dostępność

Zgoda: do 10 USD kredytu miesięcznie, bez przechodzenia na ofertę płatną. Odczyt 28.10.2026: Azure for Students aktywne, spendingLimit On, estimatedBalance 98,06 USD, grant wygasa **17.11.2026 o 21:33 czasu polskiego**. Nie ma potwierdzenia automatycznego odnowienia.

Azure rozlicza tę subskrypcję w EUR; październikowy kurs API to 0,8799718409 EUR/USD. Dodatkowy budżet `budget-staylens-student-total` obejmuje **całą subskrypcję**, ma 8 EUR (około 9,09 USD przy tym kursie), alerty 80% i 100% do Owner. Stary alert 10 EUR pozostał własnością SupportRouter; nowy bardziej zachowawczy alert uwzględnia oba projekty i zasoby wspólne. Kurs należy sprawdzić ponownie przy kolejnym miesiącu.

Alert **nie jest twardym limitem i nie wyłącza usług**. Ochrona studencka działa na poziomie całego kredytu, nie miesięcznych 10 USD. Nie deklarujemy bezpłatnego hostingu. Koszt rejestru już istnieje; nie utworzono drugiego ACR ani nowego Log Analytics. Dodatkowe koszty to wykorzystanie aplikacji, mały Storage stanu i ewentualne logi/transfer. Ustawienie 0–1 replik i niski ruch demonstracyjny ograniczają zużycie, ale nie gwarantują limitu przy ciągłym ruchu. Przed 17 listopada należy rozstrzygnąć odnowienie/hosting na czas oceny.

Źródła: [rozliczanie Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/billing), [OIDC Azure/GitHub](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-azure), [tożsamość do pobierania obrazu](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity-image-pull), [backend Terraform](https://developer.hashicorp.com/terraform/language/backend/azurerm), [API kredytów](https://learn.microsoft.com/en-us/rest/api/consumption/credits/get?view=rest-consumption-2026-06-01).

## Obsługa i powrót do poprzedniego obrazu

`GET /health` potwierdza załadowanie modelu/katalogu; `/api/release` podaje commit obrazu; `/api/model` ujawnia metryki i ograniczenia. Logi: `az containerapp logs show -g rg-staylens-14055600 -n staylens --type console --tail 50`. Historyczne logi trafiają do wspólnego Log Analytics (istniejąca retencja 30 dni i dzienny limit ingestii 0,1 GB). Nie wdrożono monitorowania jakości na prawdziwych cenach rezerwacji — aplikacja nie zbiera takich etykiet.

Rollback wykonuje się przez ten sam `infra/app` i zdalny stan, zmieniając wyłącznie `image_digest` na poprzedni, istniejący digest repozytorium `staylens` w ACR. Najpierw `terraform plan -out=rollback.tfplan`, potem `check_deployment_plan.py` na JSON planu, sprawdzenie nazwy/grupy i `terraform apply rollback.tfplan`. Po zmianie uruchom `smoke_deployment.py` na adresie Azure i sprawdź `/api/release`. Nie używaj ręcznego `az containerapp update`, które powodowałoby rozbieżność ze stanem Terraform. Aktualne digesta i dowody wykonania zapisujemy w `reports/s04` oraz GitHub Actions.

Zatrzymanie/usunięcie infrastruktury wymaga osobnej decyzji. `min_replicas=0` oznacza uśpienie przy braku ruchu, nie wyłączenie aplikacji. Nie uruchamiaj `terraform destroy` przed zakończeniem oceny.
