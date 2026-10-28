import React from "react";
import { Info } from "lucide-react";

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
