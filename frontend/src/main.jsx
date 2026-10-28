import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import L from "leaflet";
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BedDouble,
  Bookmark,
  Check,
  ChevronDown,
  Compass,
  ExternalLink,
  House,
  Info,
  Layers,
  MapPin,
  Plus,
  Search,
  SlidersHorizontal,
  Star,
  Users,
  X,
} from "lucide-react";
import "leaflet/dist/leaflet.css";
import "./styles.css";
import {
  DEFAULT_FILTERS,
  ROOM_NAMES,
  count,
  filterListings,
  histogram,
  median,
  money,
  peerStats,
} from "./market.js";

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

function PriceNote({ row, listings }) {
  const stats = peerStats(row, listings);
  if (stats.percent == null)
    return (
      <span className="price-note neutral">Za mało ofert do porównania</span>
    );
  return (
    <span className={`price-note ${stats.percent > 0 ? "neutral" : ""}`}>
      {stats.percent === 0
        ? "Na poziomie mediany"
        : `${Math.abs(stats.percent)}% ${stats.percent < 0 ? "poniżej" : "powyżej"} mediany dzielnicy`}
    </span>
  );
}

function MiniHistogram({ rows }) {
  const bins = histogram(rows.map((row) => row.price));
  const maximum = Math.max(1, ...bins.map((bin) => bin.count));
  return (
    <div
      className="histogram"
      role="img"
      aria-label={`Rozkład cen ${rows.length} przefiltrowanych ofert`}
    >
      {bins.map((bin, index) => (
        <span
          key={index}
          style={{ height: `${Math.max(5, (bin.count / maximum) * 100)}%` }}
          title={`${money(bin.start)}: ${bin.count} ofert`}
        />
      ))}
    </div>
  );
}

function MapView({ rows, selected, onSelect, geo, onReset }) {
  const container = useRef(null);
  const mapRef = useRef(null);
  const markers = useRef(null);
  const clickRef = useRef(onSelect);
  clickRef.current = onSelect;
  useEffect(() => {
    if (!container.current) return;
    const map = L.map(container.current, {
      zoomControl: false,
      scrollWheelZoom: true,
      minZoom: 9,
      maxZoom: 18,
    }).setView([52.519, 13.401], 12);
    mapRef.current = map;
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
      maxZoom: 19,
    }).addTo(map);
    L.control.zoom({ position: "bottomright" }).addTo(map);
    markers.current = L.layerGroup().addTo(map);
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(container.current);
    return () => {
      observer.disconnect();
      map.remove();
      mapRef.current = null;
    };
  }, []);
  useEffect(() => {
    if (!geo || !mapRef.current) return;
    const layer = L.geoJSON(geo, {
      style: { color: "#819b8d", weight: 1, opacity: 0.25, fillOpacity: 0.015 },
      interactive: false,
    }).addTo(mapRef.current);
    return () => layer.remove();
  }, [geo]);
  useEffect(() => {
    if (!markers.current) return;
    markers.current.clearLayers();
    // A bounded number of markers avoids obscuring the basemap and crowding controls.
    const visible = rows.slice(0, 60);
    if (selected && !visible.some((row) => row.id === selected.id))
      visible.push(selected);
    for (const row of visible) {
      const active = row.id === selected?.id;
      const marker = L.marker([row.lat, row.lon], {
        icon: L.divIcon({
          className: `price-marker ${active ? "selected" : ""}`,
          html: `<span>${money(row.price)}</span>`,
          iconSize: [68, 34],
          iconAnchor: [34, 17],
        }),
        title: `Oferta ${row.id}: ${money(row.price)}`,
        zIndexOffset: active ? 1000 : 0,
      }).on("click", () => clickRef.current(row));
      markers.current.addLayer(marker);
    }
  }, [rows, selected]);
  useEffect(() => {
    if (selected && mapRef.current)
      mapRef.current.flyTo([selected.lat, selected.lon], 14, { duration: 0.7 });
  }, [selected]);
  useEffect(() => {
    if (rows.length && mapRef.current && !selected) {
      mapRef.current.fitBounds(
        L.latLngBounds(rows.slice(0, 60).map((row) => [row.lat, row.lon])),
        { padding: [60, 60], maxZoom: 13, animate: false },
      );
    }
  }, [rows, selected]);
  return (
    <div className="map-wrap">
      <div
        className="map-canvas"
        ref={container}
        aria-label="Interaktywna mapa ofert w Berlinie"
      />
      <div className="map-label">
        <span className="live-dot" /> Berlin{" "}
        <span className="map-label-separator" /> {Math.min(60, rows.length)}{" "}
        ofert na mapie
      </div>
      <button
        className="map-reset"
        onClick={() => {
          onReset();
          mapRef.current?.setView([52.519, 13.401], 12);
        }}
      >
        <Compass size={16} /> Całe miasto
      </button>
    </div>
  );
}

function ListingCard({ row, listings, saved, onSave, onSelect, active }) {
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
        <PriceNote row={row} listings={listings} />
      </div>
    </article>
  );
}

function Detail({ row, listings, saved, onSave, onClose }) {
  const stats = peerStats(row, listings);
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
          <span>Mediana w dzielnicy</span>
          <b>{money(stats.median)}</b>
        </div>
        <PriceNote row={row} listings={listings} />
        <p>
          {count(stats.n)} innych ofert tego samego typu. To porównanie cen,
          jeszcze nie wynik modelu ML.
        </p>
      </div>
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

function Comparison({ rows, listings, onSave, onBack }) {
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
                <PriceNote row={row} listings={listings} />
                <dl>
                  {[
                    ["Dzielnica", row.district],
                    ["Typ", ROOM_NAMES[row.roomType]],
                    ["Miejsca", row.guests],
                    ["Sypialnie", row.bedrooms ?? "Brak danych"],
                    ["Ocena", row.rating?.toFixed(2) ?? "Brak ocen"],
                    ["Liczba opinii", count(row.reviews)],
                    ["Minimum nocy", row.minNights ?? "Brak danych"],
                    [
                      "Mediana w dzielnicy",
                      money(peerStats(row, listings).median),
                    ],
                  ].map(([name, value]) => (
                    <div key={name}>
                      <dt>{name}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
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

function About({ meta, onBack }) {
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
        StayLens pomaga porównywać noclegi. Ten podgląd pokazuje pierwszy etap
        aplikacji.
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
          <h2>Model jako kolejny etap</h2>
          <p>
            Model ML nie został jeszcze wytrenowany. Przygotowaliśmy oddzielne
            grupy treningowe, walidacyjne i testowe według gospodarza. Po ocenie
            dodamy szacowanie ceny i opis jego błędu.
          </p>
        </article>
      </div>
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

function App() {
  const [dataset, setDataset] = useState(null);
  const [geo, setGeo] = useState(null);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({ ...DEFAULT_FILTERS });
  const [sort, setSort] = useState("reviewed");
  const [selected, setSelected] = useState(null);
  const [saved, setSaved] = useState([]);
  const [view, setView] = useState("explore");
  const [visibleCount, setVisibleCount] = useState(12);
  const [toast, setToast] = useState("");
  const [mobileMap, setMobileMap] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/data/listings.json", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Nie udało się pobrać ofert.");
        return response.json();
      })
      .then(setDataset)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    fetch("/data/neighbourhoods.geojson", { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : null))
      .then(setGeo)
      .catch(() => {});
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    const escape = (e) => {
      if (e.key === "Escape") setSelected(null);
    };
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, []);
  const listings = dataset?.listings || [];
  const filtered = useMemo(
    () => filterListings(listings, filters, sort),
    [listings, filters, sort],
  );
  const savedRows = saved
    .map((id) => listings.find((row) => row.id === id))
    .filter(Boolean);
  const summary = useMemo(
    () => ({
      median: median(filtered.map((row) => row.price)),
      min: filtered.length
        ? Math.min(...filtered.map((row) => row.price))
        : null,
    }),
    [filtered],
  );
  function update(name, value) {
    setFilters((previous) => ({ ...previous, [name]: value }));
    setSelected(null);
    setVisibleCount(12);
  }
  function reset() {
    setFilters({ ...DEFAULT_FILTERS });
    setSelected(null);
    setVisibleCount(12);
  }
  function toggleSave(row) {
    if (saved.includes(row.id)) {
      setSaved((previous) => previous.filter((id) => id !== row.id));
      setToast("Oferta usunięta z porównania.");
    } else if (saved.length === 3)
      setToast("Możesz porównać 3 oferty. Usuń jedną, aby dodać kolejną.");
    else {
      setSaved((previous) => [...previous, row.id]);
      setToast("Dodano do porównania.");
    }
  }
  if (error)
    return (
      <main className="loading-state">
        <h1>Nie udało się wczytać danych</h1>
        <p>{error}</p>
        <button
          className="primary-button"
          onClick={() => window.location.reload()}
        >
          Spróbuj ponownie
        </button>
      </main>
    );
  if (!dataset)
    return (
      <main className="loading-state">
        <img src="/favicon.svg" width="54" height="54" alt="" />
        <h1>Otwieramy perspektywę na Berlin.</h1>
        <p>Wczytujemy oferty…</p>
      </main>
    );
  return (
    <>
      <header className="site-header">
        <button
          className="brand"
          onClick={() => setView("explore")}
          aria-label="StayLens — strona główna"
        >
          <img src="/favicon.svg" width="35" height="35" alt="" />
          <span>
            stay<span className="brand-light">lens</span>
            <span className="brand-dot">.</span>
          </span>
        </button>
        <nav aria-label="Nawigacja główna">
          <button
            className={view === "explore" ? "nav-active" : ""}
            onClick={() => setView("explore")}
          >
            Odkrywaj
          </button>
          <button
            className={view === "compare" ? "nav-active" : ""}
            onClick={() => setView("compare")}
          >
            Porównaj <span className="nav-count">{saved.length}</span>
          </button>
          <button
            className={view === "about" ? "nav-active" : ""}
            onClick={() => setView("about")}
          >
            Jak to działa
          </button>
        </nav>
        <div className="header-end">
          <span className="preview-pill">Podgląd projektu</span>
          <span className="city-tag">
            <MapPin size={14} /> Berlin, DE
          </span>
        </div>
      </header>
      {view === "explore" ? (
        <main className="explore-page">
          <section className="intro">
            <div>
              <div className="eyebrow">
                <span className="small-line" /> MNIEJ ZGADYWANIA. WIĘCEJ
                PERSPEKTYWY.
              </div>
              <h1>
                Berlin, w dobrej <span>cenie.</span>
              </h1>
              <p>Odkrywaj noclegi. Porównuj oferty. Zobacz, co stoi za ceną.</p>
            </div>
            <div className="intro-aside">
              <div className="city-sketch" aria-hidden="true">
                <svg viewBox="0 0 210 80">
                  <path d="M5 73h200M18 73V55h24v18M26 55V42h9v13M50 73V40h31v33M47 40h37M53 35h25M59 35V19h13v16M62 19V9h7v10M90 73V53h26v20M96 53V40h14v13M129 73V39m-7 0h14l-5-7V7h-3v25Zm5 34 2-34 3 34M153 73V42h41v31M150 42l24-15 24 15M159 73V48m10 25V48m10 25V48m10 25V48" />
                </svg>
              </div>
              <span>
                Miasto możliwości.
                <br />
                <b>Jedna nowa perspektywa.</b>
              </span>
            </div>
          </section>
          <section className="filter-bar" aria-label="Filtry ofert">
            <div className="filter-field location-filter">
              <MapPin size={19} />
              <label>
                <span>OKOLICA</span>
                <select
                  aria-label="Dzielnica"
                  value={filters.district}
                  onChange={(e) => update("district", e.target.value)}
                >
                  <option value="">Cały Berlin</option>
                  {dataset.meta.districts.map((d) => (
                    <option key={d}>{d}</option>
                  ))}
                </select>
              </label>
              <ChevronDown size={14} />
            </div>
            <div className="filter-field">
              <House size={19} />
              <label>
                <span>RODZAJ NOCLEGU</span>
                <select
                  aria-label="Rodzaj noclegu"
                  value={filters.roomType}
                  onChange={(e) => update("roomType", e.target.value)}
                >
                  <option value="">Wszystkie rodzaje</option>
                  {Object.entries(ROOM_NAMES).map(([value, text]) => (
                    <option key={value} value={value}>
                      {text}
                    </option>
                  ))}
                </select>
              </label>
              <ChevronDown size={14} />
            </div>
            <div className="filter-field guests-filter">
              <Users size={19} />
              <label>
                <span>GOŚCIE</span>
                <select
                  aria-label="Liczba gości"
                  value={filters.guests}
                  onChange={(e) => update("guests", Number(e.target.value))}
                >
                  {[1, 2, 3, 4, 5, 6, 8].map((n) => (
                    <option key={n} value={n}>
                      {n} {n === 1 ? "osoba" : n < 5 ? "osoby" : "osób"}
                    </option>
                  ))}
                </select>
              </label>
              <ChevronDown size={14} />
            </div>
            <div className="filter-field budget-filter">
              <label htmlFor="budget">
                <span>
                  BUDŻET ZA NOC <b>do {money(filters.maxPrice)}</b>
                </span>
                <input
                  id="budget"
                  aria-label="Maksymalna cena za noc"
                  type="range"
                  min="30"
                  max="600"
                  step="10"
                  value={filters.maxPrice}
                  onChange={(e) => update("maxPrice", Number(e.target.value))}
                />
              </label>
            </div>
            <button
              className="reset-button"
              onClick={reset}
              aria-label="Resetuj filtry"
            >
              <SlidersHorizontal size={18} />
              <span>Resetuj</span>
            </button>
          </section>
          <section
            className={`workspace ${mobileMap ? "mobile-map-active" : ""}`}
          >
            <div className="results-pane">
              <div className="results-heading">
                <div>
                  <h2>
                    {count(filtered.length)} noclegów <span>do odkrycia</span>
                  </h2>
                  <p>
                    {filters.district || "Wszystkie dzielnice"} <span>·</span>{" "}
                    ceny ofertowe w EUR
                  </p>
                </div>
                <label className="sort-label">
                  <span className="sr-only">Sortowanie</span>
                  <select
                    aria-label="Sortowanie"
                    value={sort}
                    onChange={(e) => {
                      setSort(e.target.value);
                      setVisibleCount(12);
                    }}
                  >
                    <option value="reviewed">Najwięcej opinii</option>
                    <option value="price-asc">Cena: rosnąco</option>
                    <option value="price-desc">Cena: malejąco</option>
                  </select>
                  <ChevronDown size={13} />
                </label>
              </div>
              <div className="search-box">
                <Search size={15} />
                <input
                  aria-label="Szukaj ofert"
                  placeholder="Szukaj nazwy lub okolicy…"
                  value={filters.query}
                  onChange={(e) => update("query", e.target.value)}
                />
                {filters.query && (
                  <button
                    onClick={() => update("query", "")}
                    aria-label="Wyczyść wyszukiwanie"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
              <div className="listing-scroll">
                {filtered.length ? (
                  <>
                    <div className="listing-grid">
                      {filtered.slice(0, visibleCount).map((row) => (
                        <ListingCard
                          key={row.id}
                          row={row}
                          listings={listings}
                          saved={saved.includes(row.id)}
                          onSave={toggleSave}
                          onSelect={setSelected}
                          active={selected?.id === row.id}
                        />
                      ))}
                    </div>
                    {visibleCount < filtered.length && (
                      <button
                        className="load-more"
                        onClick={() =>
                          setVisibleCount((previous) => previous + 12)
                        }
                      >
                        Pokaż kolejne 12 ofert <ArrowRight size={16} />
                      </button>
                    )}
                  </>
                ) : (
                  <div className="empty-state">
                    <Search size={32} />
                    <h3>Tutaj jest jeszcze spokojnie.</h3>
                    <p>Zmień budżet lub wybierz szerszy obszar.</p>
                    <button className="primary-button" onClick={reset}>
                      Resetuj filtry
                    </button>
                  </div>
                )}
              </div>
            </div>
            <div className="map-pane">
              <MapView
                rows={filtered}
                geo={geo}
                selected={selected}
                onSelect={setSelected}
                onReset={() => {
                  reset();
                }}
              />
              {selected ? (
                <Detail
                  row={selected}
                  listings={listings}
                  saved={saved.includes(selected.id)}
                  onSave={toggleSave}
                  onClose={() => setSelected(null)}
                />
              ) : (
                <div className="market-card">
                  <div className="market-card-title">
                    <span className="market-icon">
                      <Layers size={17} />
                    </span>
                    <div>
                      <h3>Rynek w pigułce</h3>
                      <p>Twój aktualny wybór</p>
                    </div>
                    <button
                      onClick={() => setView("about")}
                      aria-label="Jak obliczamy porównania"
                    >
                      <Info size={16} />
                    </button>
                  </div>
                  <div className="market-numbers">
                    <div>
                      <span>Mediana za noc</span>
                      <strong>{money(summary.median)}</strong>
                    </div>
                    <div>
                      <span>Oferty od</span>
                      <strong>{money(summary.min)}</strong>
                    </div>
                  </div>
                  <MiniHistogram rows={filtered} />
                  <div className="histogram-labels">
                    <span>niższe ceny</span>
                    <span>wyższe ceny</span>
                  </div>
                  <p className="market-footnote">
                    Porównanie {count(filtered.length)} ofert · dane historyczne
                  </p>
                </div>
              )}
              <div className="map-bottom-label">
                <MapPin size={12} /> Lokalizacje są przybliżone
              </div>
            </div>
          </section>
          <button
            className="mobile-view-button"
            onClick={() => setMobileMap((previous) => !previous)}
          >
            {mobileMap ? <Layers size={17} /> : <MapPin size={17} />}{" "}
            {mobileMap ? "Pokaż oferty" : "Pokaż mapę"}
          </button>
        </main>
      ) : view === "compare" ? (
        <Comparison
          rows={savedRows}
          listings={listings}
          onSave={toggleSave}
          onBack={() => setView("explore")}
        />
      ) : (
        <About meta={dataset.meta} onBack={() => setView("explore")} />
      )}
      <footer className="site-footer">
        <span>
          <span className="live-dot" /> Inside Airbnb · Berlin ·{" "}
          {dataset.meta.snapshot}
        </span>
        <span>Ceny historyczne · podgląd bez modelu ML</span>
        <button onClick={() => setView("about")}>
          O danych i ograniczeniach <ArrowUpRight size={12} />
        </button>
      </footer>
      {toast && (
        <div className="toast" role="status">
          <Check size={17} />
          {toast}
          {saved.length > 0 && (
            <button
              onClick={() => {
                setView("compare");
                setToast("");
              }}
            >
              Porównaj <ArrowRight size={14} />
            </button>
          )}
        </div>
      )}
    </>
  );
}

createRoot(document.getElementById("root")).render(<App />);
