import React, { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BedDouble,
  Bookmark,
  Check,
  ExternalLink,
  House,
  MapPin,
  Plus,
  Star,
  Users,
  X,
} from "lucide-react";
import { ROOM_NAMES, count, money } from "./market.js";
import { ModelCaution, ListingWarnings } from "./ModelNotes.jsx";

function Photo({ row, className = "" }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [row.id]);
  return !failed && row.image ? (
    <img
      className={className}
      src={row.image}
      alt={row.title}
      loading="lazy"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
    />
  ) : (
    <div className={`photo-fallback ${className}`}>
      <House size={38} strokeWidth={1.2} />
      <span>{row.neighbourhood}</span>
    </div>
  );
}

function PriceNote({ row }) {
  const percent = Math.round(row.model.deltaPercent);
  return (
    <span
      className={`price-note ${percent > 0 || row.model.warnings.includes("high_price") ? "neutral" : ""}`}
    >
      {percent === 0
        ? "Na poziomie oszacowania ML"
        : `${Math.abs(percent)}% ${percent < 0 ? "poniżej" : "powyżej"} oszacowania ML`}
    </span>
  );
}

export function ListingCard({ row, saved, onSave, onSelect, active }) {
  return (
    <article className={`listing-card ${active ? "active" : ""}`}>
      <button
        className="listing-photo"
        onClick={() => onSelect(row)}
        aria-label={`Zobacz ofertę: ${row.title}`}
      >
        <Photo row={row} />
        <span className="photo-tag">{row.neighbourhood}</span>
      </button>
      <button
        className={`save-button ${saved ? "saved" : ""}`}
        onClick={() => onSave(row)}
        aria-pressed={saved}
        aria-label={`${saved ? "Usuń z porównania" : "Dodaj do porównania"}: ${row.title}`}
      >
        <Bookmark size={17} fill={saved ? "currentColor" : "none"} />
      </button>
      <div className="card-copy">
        <div className="card-eyebrow">
          <span>{ROOM_NAMES[row.roomType] || row.roomType}</span>
          <span className="rating">
            <Star size={12} fill="currentColor" />{" "}
            {row.rating?.toFixed(2) || "—"}
          </span>
        </div>
        <button className="card-title" onClick={() => onSelect(row)}>
          {row.title}
        </button>
        <p className="card-details">
          <Users size={12} /> {row.guests} os. <span>·</span>
          <BedDouble size={13} /> łóżka: {row.beds == null ? "—" : row.beds}{" "}
          <span>·</span> {count(row.reviews)} opinii
        </p>
        <div className="card-bottom">
          <div>
            <strong>{money(row.price)}</strong>
            <span> / noc</span>
          </div>
          <button
            className="round-link"
            onClick={() => onSelect(row)}
            aria-label={`Szczegóły oferty ${row.id}`}
          >
            <ArrowUpRight size={17} />
          </button>
        </div>
        <div className="card-model">
          Model: <b>{money(row.model.estimatedPrice)}</b> / noc
        </div>
        <PriceNote row={row} />
        {row.model.warnings.includes("high_price") && (
          <p className="card-warning">Duży błąd modelu dla drogich ofert</p>
        )}
        {row.model.warnings.includes("small_sample") && (
          <p className="card-warning">Mała próba oceny tego rodzaju noclegu</p>
        )}
      </div>
    </article>
  );
}

export function Detail({ row, saved, onSave, onClose }) {
  const stats = row.reference;
  return (
    <section className="detail-panel" aria-label="Szczegóły wybranej oferty">
      <button
        className="detail-close"
        onClick={onClose}
        aria-label="Zamknij szczegóły"
      >
        <X size={17} />
      </button>
      <div className="detail-top">
        <span className="eyebrow">SPOJRZENIE Z BLISKA</span>
        <h2>{row.title}</h2>
        <p>
          <MapPin size={13} /> {row.neighbourhood} · {row.district}
        </p>
      </div>
      <div className="detail-price">
        <div>
          <small>Cena w ogłoszeniu</small>
          <strong>
            {money(row.price)} <span>/ noc</span>
          </strong>
        </div>
        <div className="detail-rating">
          <Star size={15} fill="currentColor" />
          <b>{row.rating?.toFixed(2) || "—"}</b>
          <small>{count(row.reviews)} opinii</small>
        </div>
      </div>
      <div className="reference-box">
        <div>
          <span>Oszacowanie modelu</span>
          <b>{money(row.model.estimatedPrice)}</b>
        </div>
        <PriceNote row={row} />
        <p>Obliczone bez tej oferty i ofert jej gospodarza w treningu.</p>
        <ModelCaution compact />
      </div>
      <ListingWarnings row={row} />
      <p className="peer-reference">
        Mediana dzielnicy: <b>{money(stats.median)}</b> · {count(stats.n)}{" "}
        innych ofert tego samego typu. To osobna statystyka.
      </p>
      <div className="detail-facts">
        <span>
          <Users size={16} />
          {row.guests} os.
        </span>
        <span>
          <BedDouble size={16} />
          Sypialnie: {row.bedrooms ?? "—"}
        </span>
        <span>
          <House size={16} />
          Min. nocy: {row.minNights ?? "—"}
        </span>
      </div>
      <button
        className={`primary-button ${saved ? "is-saved" : ""}`}
        onClick={() => onSave(row)}
      >
        {saved ? <Check size={16} /> : <Plus size={16} />}{" "}
        {saved ? "W porównaniu" : "Dodaj do porównania"}
      </button>
      <a
        className="source-link"
        href={row.url}
        target="_blank"
        rel="noopener noreferrer"
      >
        Sprawdź ogłoszenie w Airbnb <ExternalLink size={13} />
      </a>
    </section>
  );
}

export function Comparison({ rows, onSave, onBack }) {
  return (
    <section className="comparison-page">
      <button className="back-button" onClick={onBack}>
        <ArrowLeft size={17} /> Wróć do odkrywania
      </button>
      <span className="eyebrow">TWÓJ KRÓTKI WYBÓR</span>
      <h1>Wszystko obok siebie.</h1>
      <p className="page-subtitle">
        Porównaj do trzech noclegów. Ten sam widok, łatwiejsza decyzja.
      </p>
      <ModelCaution />
      {!rows.length ? (
        <div className="empty-state">
          <Bookmark size={36} strokeWidth={1.3} />
          <h2>Co wpadło Ci w oko?</h2>
          <p>Dodaj oferty zakładką na karcie, a zobaczysz je tutaj.</p>
          <button className="primary-button" onClick={onBack}>
            Odkrywaj Berlin <ArrowRight size={16} />
          </button>
        </div>
      ) : (
        <div className="comparison-grid">
          {rows.map((row) => (
            <article className="comparison-card" key={row.id}>
              <div className="compare-photo">
                <Photo row={row} />
                <button
                  onClick={() => onSave(row)}
                  className="save-button saved"
                  aria-label={`Usuń z porównania: ${row.title}`}
                >
                  <X size={16} />
                </button>
              </div>
              <div className="compare-content">
                <span className="eyebrow">{row.neighbourhood}</span>
                <h2>{row.title}</h2>
                <strong className="comparison-price">
                  {money(row.price)} <small>/ noc</small>
                </strong>
                <PriceNote row={row} />
                <dl>
                  {[
                    ["Dzielnica", row.district],
                    ["Typ", ROOM_NAMES[row.roomType]],
                    ["Miejsca", row.guests],
                    ["Sypialnie", row.bedrooms ?? "Brak danych"],
                    ["Ocena", row.rating?.toFixed(2) ?? "Brak ocen"],
                    ["Liczba opinii", count(row.reviews)],
                    ["Minimum nocy", row.minNights ?? "Brak danych"],
                    ["Cena modelu", money(row.model.estimatedPrice)],
                    ["Mediana w dzielnicy", money(row.reference.median)],
                  ].map(([name, value]) => (
                    <div key={name}>
                      <dt>{name}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
                <p className="field-help">
                  Model oceniał tę ofertę bez jej gospodarza w treningu.
                </p>
                <ListingWarnings row={row} />
                <a
                  href={row.url}
                  className="source-link"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Zobacz źródło <ExternalLink size={13} />
                </a>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
