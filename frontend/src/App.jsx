import React, { useEffect, useRef, useState } from "react";
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
import { DEFAULT_FILTERS, ROOM_NAMES, count, money } from "./market.js";
import { api, catalogUrl } from "./client.js";
import Estimator from "./Estimator.jsx";
import {
  ModelCaution,
  ListingWarnings,
  FinalEvaluationNote,
} from "./ModelContext.jsx";

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

function MiniHistogram({ bins, total }) {
  const maximum = Math.max(1, ...bins.map((bin) => bin.count));
  return (
    <div
      className="histogram"
      role="img"
      aria-label={`Rozkład cen ${total} przefiltrowanych ofert`}
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
    return () => {
      map.stop();
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
    const map = mapRef.current;
    if (!map) return;
    const updateViewport = () => {
      map.stop();
      map.invalidateSize({ pan: false });
      const size = map.getSize();
      // The mobile list hides this container. Fit only after it becomes measurable.
      if (size.x <= 120 || size.y <= 120) return;
      if (selected)
        map.setView([selected.lat, selected.lon], 14, { animate: false });
      else if (rows.length)
        map.fitBounds(
          L.latLngBounds(rows.slice(0, 60).map((row) => [row.lat, row.lon])),
          { padding: [60, 60], maxZoom: 13, animate: false },
        );
    };
    updateViewport();
    const observer = new ResizeObserver(updateViewport);
    observer.observe(container.current);
    return () => observer.disconnect();
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
        <span className="map-label-separator" />{" "}
        {Math.min(60, rows.length) +
          (selected && !rows.slice(0, 60).some((row) => row.id === selected.id)
            ? 1
            : 0)}{" "}
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

function ListingCard({ row, saved, onSave, onSelect, active }) {
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

function Detail({ row, saved, onSave, onClose }) {
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

function Comparison({ rows, onSave, onBack, loading, error, onRetry }) {
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
      {loading ? (
        <p className="async-status" role="status">
          Wczytujemy porównanie…
        </p>
      ) : error ? (
        <div className="inline-error" role="alert">
          <p>{error}</p>
          <button className="primary-button" onClick={onRetry}>
            Spróbuj ponownie
          </button>
        </div>
      ) : !rows.length ? (
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

function App() {
  const [dataset, setDataset] = useState(null);
  const [geo, setGeo] = useState(null);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({ ...DEFAULT_FILTERS });
  const [sort, setSort] = useState("reviewed");
  const [selected, setSelected] = useState(null);
  const [saved, setSaved] = useState([]);
  const [view, setView] = useState("explore");
  const [offset, setOffset] = useState(0);
  const [catalog, setCatalog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [catalogError, setCatalogError] = useState("");
  const [retry, setRetry] = useState(0);
  const [savedRows, setSavedRows] = useState([]);
  const [compareState, setCompareState] = useState({
    loading: false,
    error: "",
  });
  const [detailState, setDetailState] = useState({
    loading: false,
    error: "",
    row: null,
  });
  const [toast, setToast] = useState("");
  const [mobileMap, setMobileMap] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    api("/api/catalog/meta", { signal: controller.signal })
      .then((meta) => {
        if (!controller.signal.aborted) setDataset({ meta });
      })
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
    if (!dataset) return;
    const controller = new AbortController();
    setLoading(true);
    setCatalogError("");
    if (!offset) setCatalog(null);
    const timer = setTimeout(() => {
      api(catalogUrl(filters, sort, offset), { signal: controller.signal })
        .then((data) => {
          if (controller.signal.aborted) return;
          setCatalog((previous) => ({
            ...data,
            items: offset
              ? [...(previous?.items || []).slice(0, offset), ...data.items]
              : data.items,
          }));
          setLoading(false);
        })
        .catch((e) => {
          if (!controller.signal.aborted) {
            setCatalogError(e.message);
            setLoading(false);
          }
        });
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [dataset, filters, sort, offset, retry]);
  useEffect(() => {
    const controller = new AbortController();
    setSavedRows([]);
    if (!saved.length) {
      setCompareState({ loading: false, error: "" });
      return () => controller.abort();
    }
    setCompareState({ loading: true, error: "" });
    const params = new URLSearchParams();
    saved.forEach((id) => params.append("ids", id));
    api(`/api/catalog/compare?${params}`, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) {
          setSavedRows(data.items);
          setCompareState({ loading: false, error: "" });
        }
      })
      .catch((e) => {
        if (!controller.signal.aborted)
          setCompareState({ loading: false, error: e.message });
      });
    return () => controller.abort();
  }, [saved, retry]);
  useEffect(() => {
    const controller = new AbortController();
    setDetailState({ loading: !!selected, error: "", row: null });
    if (selected)
      api(`/api/catalog/listings/${encodeURIComponent(selected.id)}`, {
        signal: controller.signal,
      })
        .then((row) => {
          if (!controller.signal.aborted)
            setDetailState({ loading: false, error: "", row });
        })
        .catch((e) => {
          if (!controller.signal.aborted)
            setDetailState({ loading: false, error: e.message, row: null });
        });
    return () => controller.abort();
  }, [selected?.id, retry]);
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
  const filtered = catalog?.items || [];
  const total = catalog?.total || 0;
  const summary = catalog?.summary || {
    median: null,
    min: null,
    histogram: [],
  };
  function update(name, value) {
    setFilters((previous) => ({ ...previous, [name]: value }));
    setSelected(null);
    setOffset(0);
    setLoading(true);
    setCatalog(null);
  }
  function reset() {
    setFilters({ ...DEFAULT_FILTERS });
    setSelected(null);
    setOffset(0);
    setLoading(true);
    setCatalog(null);
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
            className={view === "estimate" ? "nav-active" : ""}
            onClick={() => setView("estimate")}
          >
            Wycena
          </button>
          <button
            className={view === "about" ? "nav-active" : ""}
            onClick={() => setView("about")}
          >
            Jak to działa
          </button>
        </nav>
        <div className="header-end">
          <span className="preview-pill">Model S02 · Berlin</span>
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
              <div className="budget-controls">
                <label htmlFor="budget">
                  <span>
                    BUDŻET ZA NOC{" "}
                    <b>
                      {filters.maxPrice > 600
                        ? "wszystkie ceny"
                        : `do ${money(filters.maxPrice)}`}
                    </b>
                  </span>
                  <input
                    id="budget"
                    aria-label="Maksymalna cena za noc"
                    type="range"
                    min="30"
                    max="600"
                    step="10"
                    value={Math.min(600, filters.maxPrice)}
                    disabled={filters.maxPrice > 600}
                    onChange={(e) => update("maxPrice", Number(e.target.value))}
                  />
                </label>
                <label className="unlimited-budget">
                  <input
                    type="checkbox"
                    aria-label="Uwzględnij wszystkie ceny"
                    checked={filters.maxPrice > 600}
                    onChange={(e) =>
                      update("maxPrice", e.target.checked ? 20000 : 300)
                    }
                  />{" "}
                  Uwzględnij wszystkie ceny
                </label>
              </div>
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
          <div className="catalog-context">
            <ModelCaution compact />
            <button onClick={() => setView("about")}>
              Sprawdź błąd i ograniczenia modelu <ArrowUpRight size={12} />
            </button>
          </div>
          <section
            className={`workspace ${mobileMap ? "mobile-map-active" : ""}`}
          >
            <div className="results-pane">
              <div className="results-heading">
                <div>
                  <h2>
                    {loading && !catalog ? "…" : count(total)} noclegów{" "}
                    <span>do odkrycia</span>
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
                      setOffset(0);
                      setLoading(true);
                      setCatalog(null);
                      setSelected(null);
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
                  maxLength={120}
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
                {catalogError && (
                  <div className="inline-error" role="alert">
                    <p>{catalogError}</p>
                    <button
                      className="primary-button"
                      onClick={() => {
                        setLoading(true);
                        setRetry((n) => n + 1);
                      }}
                    >
                      Spróbuj ponownie
                    </button>
                  </div>
                )}
                {loading && (
                  <p className="async-status" role="status">
                    Wczytujemy oferty…
                  </p>
                )}
                {filtered.length ? (
                  <>
                    <div className="listing-grid">
                      {filtered.map((row) => (
                        <ListingCard
                          key={row.id}
                          row={row}
                          saved={saved.includes(row.id)}
                          onSave={toggleSave}
                          onSelect={(row) => {
                            setSelected(row);
                            setMobileMap(true);
                          }}
                          active={selected?.id === row.id}
                        />
                      ))}
                    </div>
                    {catalog?.hasMore && !catalogError && (
                      <button
                        className="load-more"
                        disabled={loading}
                        onClick={() => {
                          setLoading(true);
                          setOffset((previous) => previous + 12);
                        }}
                      >
                        Pokaż kolejne 12 ofert <ArrowRight size={16} />
                      </button>
                    )}
                  </>
                ) : !loading && !catalogError ? (
                  <div className="empty-state">
                    <Search size={32} />
                    <h3>Tutaj jest jeszcze spokojnie.</h3>
                    <p>Zmień budżet lub wybierz szerszy obszar.</p>
                    <button className="primary-button" onClick={reset}>
                      Resetuj filtry
                    </button>
                  </div>
                ) : null}
              </div>
            </div>
            <div className="map-pane">
              <MapView
                rows={catalog?.mapItems || []}
                geo={geo}
                selected={selected}
                onSelect={setSelected}
                onReset={() => {
                  reset();
                }}
              />
              {selected &&
              (detailState.loading ||
                !detailState.row ||
                detailState.row.id !== selected.id) ? (
                <section
                  className="detail-panel"
                  role={detailState.error ? "alert" : "status"}
                >
                  <button
                    className="detail-close"
                    aria-label="Zamknij szczegóły"
                    onClick={() => setSelected(null)}
                  >
                    <X size={17} />
                  </button>
                  <p>{detailState.error || "Wczytujemy szczegóły…"}</p>
                  {detailState.error && (
                    <button
                      className="primary-button"
                      onClick={() => setRetry((n) => n + 1)}
                    >
                      Spróbuj ponownie
                    </button>
                  )}
                </section>
              ) : selected ? (
                <Detail
                  row={detailState.row}
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
                  <MiniHistogram bins={summary.histogram} total={total} />
                  <div className="histogram-labels">
                    <span>niższe ceny</span>
                    <span>wyższe ceny</span>
                  </div>
                  <p className="market-footnote">
                    Porównanie {count(total)} ofert · dane historyczne
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
          loading={compareState.loading}
          error={compareState.error}
          onRetry={() => setRetry((n) => n + 1)}
          onSave={toggleSave}
          onBack={() => setView("explore")}
        />
      ) : view === "estimate" ? (
        <Estimator meta={dataset.meta} onBack={() => setView("explore")} />
      ) : (
        <About meta={dataset.meta} onBack={() => setView("explore")} />
      )}
      <footer className="site-footer">
        <span>
          <span className="live-dot" /> Inside Airbnb · Berlin ·{" "}
          {dataset.meta.snapshot}
        </span>
        <span>
          Ceny historyczne · oszacowania ML · {dataset.meta.modelVersion}
        </span>
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

export default App;
