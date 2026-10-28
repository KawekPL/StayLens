# S03 — integracja aplikacji i modelu

Wykonano 28.10.2026. StayLens działa lokalnie jako React/Leaflet + FastAPI. Aktywny model pozostaje **s02-v1**, bez nowego treningu, strojenia ani oceny odłożonego testu. Kontener i wdrożenie są zakresem S04.

## Rezultat

- Katalog 5814 rzeczywistych ofert train jest obsługiwany przez API, z filtrowaniem, sortowaniem i paginacją po 12 wierszy. Mapa pokazuje pierwsze 60 dopasowań i ewentualnie dodatkową aktualnie wybraną ofertę. Mediana i histogram obejmują wszystkie dopasowania, nie tylko stronę.
- Karty, szczegóły i porównanie do trzech ofert pokazują cenę ofertową, oszacowanie ML i różnicę. Mediana grupy dzielnica × typ, bez wybranej oferty, jest osobną statystyką.
- Zakładka Wycena: lokalizacja na mapie lub współrzędne, automatyczna dzielnica, typ noclegu/obiektu, pojemność, sypialnie/łóżka/łazienki, minimalna długość pobytu i osiem udogodnień. Nieznane dane zachowane jako braki, niezrównane z odpowiedzią „nie”. Metraż z nieawansowanego S02c nie jest pozorną cechą formularza.
- Stan ładowania, brak wyników, błędy i ponowienie żądania. Zmiana parametrów usuwa nieaktualną wycenę. Anulowanie i kontrola aktualności żądań chronią przed nadpisaniem nowszego wyboru starszą odpowiedzią.
- Jeden skrypt startuje lokalne API i frontend w osobnych ukrytych procesach Windows. Podgląd pozostawiono działający; po restarcie komputera trzeba uruchomić go ponownie.

## Poprawne użycie ML

**Katalog:** zapisane przewidywania z trzech podziałów GroupKFold S02. Każdą ofertę oceniał model, którego trening nie obejmował jej gospodarza. Builder sprawdza oryginalny SHA256 CV oraz dokładną zgodność ID, gospodarza i ceny ze źródłem. Nie dopasowuje modelu. Pełnego modelu train nie używa się do oceniania własnych ofert treningowych w katalogu.

**Formularz:** zapisany model wytrenowany na całym train. Nowy endpoint `/api/estimate` sprawdza wielokąt dzielnicy i parę typu noclegu/obiektu, następnie używa oryginalnej predykcji S02. Test porównuje cenę z zamrożonym `/api/predict`. Zmiana interfejsu nie zmieniła modelu ani historycznych modułów badawczych.

Są to dwa sposoby użycia tego samego algorytmu i kontraktu cech, ale różne dopasowane artefakty. MAE validation **53,61 EUR**, CV **54,90 EUR** są wynikami rozwojowymi. Dla cen >400 EUR MAE validation wynosi **357,11 EUR**; Hotel room i Shared room mają tylko **8/4** obserwacje walidacyjne. UI pokazuje te ograniczenia. Brak gwarancji okazji, dostępności, ceny rezerwacji i indywidualnych przedziałów pewności.

## Weryfikacja

| Zakres | Wynik |
| --- | --- |
| Python | 75 testów przeszło, 0 pominięć |
| JavaScript | 7 testów przeszło |
| Ruff / Prettier / build Vite | Kontrola kodu i build poprawne |
| Cały katalog | 5814 unikalnych ID, tylko train, wszystkie ceny ML zgodne z zapisanym CV, bez host_id |
| Kod S02 | Historyczne hashe bez zmian |
| Rzeczywiste HTTP przez Vite | Metadane, lista, szczegóły, porównanie, wycena 200; błędne wejście 422; brak oferty 404 |
| Przeglądarka desktop 1440×1000 | Filtry, paginacja, szczegóły, porównanie, formularz i walidacja lokalizacji |
| Przeglądarka mobile 390×844 | Przełączenie listy/mapy, szczegóły, formularz; naprawiono wysokość nagłówka i mapę inicjowaną w ukrytym kontenerze |
| Awaria API | Po zatrzymaniu wyłącznie API projektu formularz pokazał błąd; dane pozostały, a ponowienie po starcie API dało wycenę |

Weryfikację danych/HTTP można powtórzyć przez `scripts/verify_s03.py`. [Wynik maszynowy](verification.json), [manifest katalogu](catalog_manifest.json), [obserwacje UI](ui_checks.json). Sprawdzenia UI to rzeczywiste interakcje asystenta w przeglądarce z emulacją rozmiaru, nie automatyczna suita end-to-end ani test fizycznego telefonu. Nie przeprowadzono odbioru wielu przeglądarek. Ostrzeżenie TestClient/httpx pozostaje znanym ostrzeżeniem zależności; HTTP sprawdzono także poza TestClient.

## Granice etapu i następny krok

Dane/model/katalog są lokalnymi ignorowanymi artefaktami. Z publicznego frontendu usunięto pełny JSON ofert S01; kopia zachowana lokalnie w `data/prepared/s01`. Publiczne odpowiedzi mają jawny schemat pól. Do katalogu nie włączono eksperymentalnych danych Doorstep. Zdjęcia, kafelki map i fonty nadal zależą od zewnętrznych dostawców.

S04 ma dostarczyć zweryfikowany model i katalog do kontenera oraz CI, utworzyć repo StayLens na GitHub, wdrożyć CI/CD i Terraform/Azure w uzgodnionym budżecie. S05 obejmie odbiór środowiska wdrożonego i jednorazową ocenę testową po zamrożeniu rozwiązania. S03 nie oznacza jeszcze spełnienia wszystkich wymagań kursu ani gotowości do wysyłki.
