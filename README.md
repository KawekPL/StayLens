# StayLens

Polskojęzyczna aplikacja do eksplorowania i porównywania ofert noclegów w Berlinie. Projekt zaliczeniowy SUML, wybrany przez użytkownika 28 października 2026. Termin pracy: **3 listopada 2026**, pakiet do oddania 2 listopada. Zastępuje SupportRouter PL jako wybrany temat; tamten projekt zachowano.

## Stan: pierwszy działający podgląd interfejsu

- React: mapa, filtry dzielnicy/typu/liczby gości/ceny, wyszukiwarka, sortowanie, szczegóły i porównanie trzech ofert.
- Rzeczywiste dane Inside Airbnb Berlin z 19.09.2026. Podgląd obejmuje 5814 ofert z części treningowej.
- Wskaźniki są obliczonymi medianami cen. **Model ML nie został jeszcze wytrenowany**, backend i nowe wdrożenie nie są ukończone.
- Build, testy funkcji i odczyt HTTP sprawdzone. Automatyczna kontrola wizualna/interakcji w przeglądarce niedostępna: narzędzie zwróciło `Local browser use is disabled in Work settings`. To nie jest potwierdzony odbiór UI.

## Uruchomienie

W PowerShell:

```powershell
cd C:\Users\szymo\Documents\ChatGPT\StayLens\frontend
npm.cmd ci
npm.cmd run dev
```

Adres: <http://127.0.0.1:5174/>. Dane do podglądu są w `frontend/public/data/`. Podgląd działa na tym komputerze; adres loopback nie jest linkiem do aplikacji w chmurze.

Przy odtwarzaniu danych:

```powershell
cd C:\Users\szymo\Documents\ChatGPT\StayLens
py -3.12 scripts\prepare_preview.py
```

Skrypt pobiera przypięte źródła, weryfikuje SHA256, usuwa rekordy bez dodatniej ceny i przygotowuje wyłącznie część treningową do interfejsu. Surowe dane zawierają więcej informacji niż publiczny podgląd i pozostają poza Git.

## Sprawdzenia

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

Źródło: [Inside Airbnb](https://insideairbnb.com/get-the-data/), CC BY 4.0. Ceny w EUR, historyczne ceny ofertowe, bez potwierdzenia dostępności i przychodów. Lokalizacje są przybliżone. StayLens nie jest powiązany z Airbnb. Zdjęcia ładowane z oryginalnych linków nie są kopiowane do projektu; prawa do nich pozostają po stronie właścicieli.
