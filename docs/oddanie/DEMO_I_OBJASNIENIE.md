# Demonstracja i objaśnienie projektu

Szymon Kawlowski, s29670. Scenariusz około 4–5 minut; wskazane kwoty są przykładem dla konkretnego snapshotu.

## Przejście przez aplikację

1. Otwórz adres Azure. Pokaż katalog z 3438 ofertami przy domyślnych filtrach, mapę i atrybucję danych. Wyjaśnij, że to historyczne ogłoszenia z Berlina, bez możliwości rezerwacji.
2. Wybierz dzielnicę Mitte — 873 oferty przy pozostałych domyślnych filtrach. Zmień sortowanie ceny lub wyszukaj nazwę; reset przywraca stan początkowy.
3. Otwórz szczegóły. Rozróżnij cenę ogłoszenia, oszacowanie ML i medianę innych podobnych ofert. Dodaj 2–3 oferty do porównania.
4. Otwórz Wycena. Dla 52.52,13.405, całego mieszkania/Entire rental unit, 2 gości, 1 sypialni, 1 łóżka, 1 łazienki, minimum2 nocy oraz Wi-Fi/kuchni/pralki/windy/miejsca do pracy/self-check-in=Tak, klimatyzacji/parkingu=Nie model zwraca **181,30 EUR** (interfejs zaokrągla do 181 EUR). Wynik nie jest ceną rezerwacji.
5. Pokaż „Jak powstał wynik?” i informacje o danych: test 1235 ofert, MAE 56,10 EUR, bez zmiany modelu. Zmień parametr i zauważ, że poprzednia wycena jest usuwana.
6. Otwórz GitHub Actions i ostatni udany przebieg: testy → budowa/test Dockera → publikacja do ACR → Terraform → test publicznego adresu.

## Jak wyjaśnić architekturę

Przeglądarka uruchamia React i Leaflet. Żądania trafiają przez HTTPS do Azure Container Apps. W jednym kontenerze FastAPI serwuje pliki frontendu i API, a model jest ładowany raz przy starcie. Katalog korzysta z przygotowanego wcześniej JSON, formularz wywołuje lokalne predict. Nie ma potrzeby bazy danych ani zewnętrznego API tłumaczącego.

GitHub Actions odtwarza przypięte artefakty, testuje aplikację i obraz. Dokładnie ten przetestowany obraz trafia do rejestru ACR. Terraform wdraża jego niezmienny digest. OIDC zapewnia krótkotrwałe logowanie, bez stałego hasła Azure w repo. Stan Terraform znajduje się w dwóch prywatnych kontenerach Blob, osobno dla bootstrap i aplikacji.

StayLens ma osobną aplikację/grupę/Storage/tożsamości; współdzieli starszy ACR, środowisko Container Apps i logi, żeby nie dublować kosztów. Nie wolno usuwać tych wspólnych zależności podczas sprzątania poprzedniego projektu.

## Pytania, które warto umieć wyjaśnić własnymi słowami

**Dlaczego nie Streamlit?** Ogłoszenie dopuszcza inny framework. React umożliwia wybrany interfejs z mapą, katalogiem i porównaniem; FastAPI obsługuje model.

**Dlaczego podział po gospodarzach?** Jeden gospodarz może mieć podobne lokale. Losowanie pojedynczych wierszy mogłoby umieścić jego oferty w treningu i teście, zawyżając ocenę uogólniania.

**Co znaczy MAE 56,10 EUR?** Średnia wartość bezwzględnej różnicy między ceną z ogłoszenia i przewidywaniem dla1235 ofert. Nie jest gwarancją błędu konkretnego noclegu. Mediana28,66 EUR pokazuje inną stronę rozkładu błędów.

**Dlaczego modele z dodatkowymi cechami nie zostały wdrożone?** Nie osiągnęły ustalonego wcześniej minimum poprawy na danych rozwojowych. Wdrożenie zachowuje wcześniejszy model, a raporty pokazują nieudane próby.

**Czy wynik testu zmienił model?** Nie. Oceniono zapisany wcześniej plik, bez fit; sprawdzono identyczne sumy kontrolne. Testu nie wykorzystuje się do kolejnego strojenia.

**Co daje Docker?** Ten sam zestaw aplikacji i zależności można uruchomić lokalnie, w CI i Azure. Sam plik Dockerfile nie byłby dowodem — obraz faktycznie zbudowano i przetestowano.

**Co daje Terraform?** Zasoby, uprawnienia i konfiguracja są zapisane jako kod; zmiany są planowane, kontrolowane i stosowane powtarzalnie. Udokumentowano ograniczenie odczytu domyślnych wartości Azure, bez ukrywania rzeczywistych zmian.

**Co jest monitorowane?** Gotowość procesu/modelu i żądania: trasa,status,czas. Bez treści formularza. Nie monitorujemy błędu na przyszłych rezerwacjach, bo takich etykiet nie zbieramy.

**Co poprawiłoby produkt w przyszłości?** Bardziej informacyjne, legalnie dostępne dane o standardzie i terminie, walidacja na nowszym snapshotcie, obsługa zmian rynku. Nie należy obiecywać konkretnego niższego błędu bez badania.

Kod i dokumentacja były rozwijane z pomocą asystenta AI. Autor powinien umieć przejść powyższy scenariusz i wyjaśnić decyzje. Gotowe odpowiedzi nie są potwierdzeniem opanowania materiału ani pytaniami zadanymi przez prowadzącego.
