import React from "react";
import { Info, ArrowLeft, ArrowUpRight } from "lucide-react";
import { count } from "./market.js";
import evaluation from "../public/final-evaluation.json";

export function FinalEvaluationNote() {
  const eur = (value) =>
    value.toLocaleString("pl-PL", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  return (
    <p>
      Test końcowy: {evaluation.test_rows} ofert {evaluation.test_hosts} innych
      gospodarzy. Średni błąd wyniósł {eur(evaluation.metrics.mae_eur)} €, wobec{" "}
      {eur(evaluation.baseline_metrics.mae_eur)} € dla mediany segmentu. Model
      pozostał bez zmian. To ocena na tym samym historycznym obrazie Berlina,
      bez gwarancji jakości dla innych terminów lub miast.
    </p>
  );
}

export function ModelCaution({ compact = false }) {
  return (
    <div className={`model-caution ${compact ? "compact" : ""}`}>
      <Info size={16} />
      <p>
        {compact
          ? "Cena modelu jest orientacyjna. Niższa cena ogłoszenia nie gwarantuje okazji."
          : "Model szacuje historyczną cenę ofertową za noc. Średni błąd walidacji to 54 €; dla ofert droższych niż 400 € wynosił 357 € i model często zaniżał cenę. Wynik nie jest ofertą rezerwacji ani przedziałem pewności."}
      </p>
    </div>
  );
}

export function ListingWarnings({ row }) {
  const messages = {
    high_price:
      "Droga oferta: model może mocno zaniżać cenę. Błąd walidacji dla ofert >400 € wynosił średnio 357 €.",
    small_sample:
      "Mała próba walidacyjna: 8 pokoi hotelowych i 4 współdzielone. Zachowaj większą ostrożność.",
    missing_features:
      "Brakuje części parametrów tego noclegu. Traktuj oszacowanie orientacyjnie.",
  };
  return row.model.warnings.length ? (
    <ul className="listing-warnings">
      {row.model.warnings.map((key) => (
        <li key={key}>{messages[key]}</li>
      ))}
    </ul>
  ) : null;
}

export function About({ meta, onBack }) {
  return (
    <section className="about-page">
      <button className="back-button" onClick={onBack}>
        <ArrowLeft size={17} /> Wróć do odkrywania
      </button>
      <span className="eyebrow">CENA POTRZEBUJE KONTEKSTU</span>
      <h1>
        Najpierw dane.
        <br />
        Potem decyzja.
      </h1>
      <p className="page-subtitle">
        StayLens łączy rzeczywiste ogłoszenia z modelem szacującym cenę.
      </p>
      <div className="about-grid">
        <article>
          <span className="step-number">01</span>
          <h2>Rzeczywiste oferty</h2>
          <p>
            Źródłem jest publiczny zbiór Inside Airbnb dla Berlina z{" "}
            {meta.snapshot}. W podglądzie jest {count(meta.previewRows)} ofert z
            części przeznaczonej do treningu. Dane bez dodatniej ceny pominięto.
          </p>
          <a href={meta.sourceUrl} target="_blank" rel="noopener noreferrer">
            Źródło · CC BY 4.0 <ArrowUpRight size={15} />
          </a>
        </article>
        <article>
          <span className="step-number">02</span>
          <h2>Porównania, które możesz sprawdzić</h2>
          <p>
            Mediana dzielnicy dotyczy innych ofert tego samego typu. Nie
            uwzględnia wszystkich różnic w standardzie, wielkości ani terminie.
            Cena z ogłoszenia nie jest potwierdzoną ceną transakcji.
          </p>
        </article>
        <article>
          <span className="step-number">03</span>
          <h2>Model z jawnym błędem</h2>
          <p>
            Model S02 uczył się z 5814 ofert. Na 1108 ofertach innych gospodarzy
            średni błąd wyniósł 53,61 € wobec 67,87 € dla prostej mediany. Dla
            katalogu używamy prognoz bez ocenianego gospodarza w treningu
            (średni błąd 54,90 €). Formularz korzysta z pełnego modelu. Metraż
            nie jest cechą tego modelu.
          </p>
          <FinalEvaluationNote />
        </article>
      </div>
      <ModelCaution />
      <p className="field-help">
        Pokoje hotelowe i współdzielone: tylko 8 i 4 przykłady w walidacji.
        Wyniki tych grup wymagają szczególnej ostrożności.
      </p>
      <div className="about-note">
        <Info size={20} />
        <p>
          To historyczny obraz rynku, bez sprawdzania dostępności na wybrany
          termin. Lokalizacje są przybliżone. Zdjęcia pochodzą z linków ofert i
          mogą być niedostępne. StayLens nie jest powiązany z Airbnb.
        </p>
      </div>
    </section>
  );
}
