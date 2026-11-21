import React, { useEffect, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  House,
  Info,
  Layers,
  MapPin,
  Search,
  SlidersHorizontal,
  Users,
  X,
} from "lucide-react";
import "leaflet/dist/leaflet.css";
import "./styles.css";
import { DEFAULT_FILTERS, ROOM_NAMES, count, money } from "./market.js";
import { api, catalogUrl } from "./client.js";
import Estimator from "./Estimator.jsx";
import MapView from "./MapView.jsx";
import { ListingCard, Detail, Comparison } from "./Listings.jsx";
import { ModelCaution, About } from "./ModelNotes.jsx";

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

function App() {
  const [meta, setMeta] = useState(null);
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
  const [toast, setToast] = useState("");
  const [mobileMap, setMobileMap] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    api("/api/catalog/meta", { signal: controller.signal })
      .then((meta) => {
        if (!controller.signal.aborted) setMeta(meta);
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
    if (!meta) return;
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
  }, [meta, filters, sort, offset, retry]);
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
    if (saved.some((item) => item.id === row.id)) {
      setSaved((previous) => previous.filter((item) => item.id !== row.id));
      setToast("Oferta usunięta z porównania.");
    } else if (saved.length === 3)
      setToast("Możesz porównać 3 oferty. Usuń jedną, aby dodać kolejną.");
    else {
      setSaved((previous) => [...previous, row]);
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
  if (!meta)
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
                  {meta.districts.map((d) => (
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
                          saved={saved.some((item) => item.id === row.id)}
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
                onReset={reset}
              />
              {selected ? (
                <Detail
                  row={selected}
                  saved={saved.some((item) => item.id === selected.id)}
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
          rows={saved}
          onSave={toggleSave}
          onBack={() => setView("explore")}
        />
      ) : view === "estimate" ? (
        <Estimator meta={meta} onBack={() => setView("explore")} />
      ) : (
        <About meta={meta} onBack={() => setView("explore")} />
      )}
      <footer className="site-footer">
        <span>
          <span className="live-dot" /> Inside Airbnb · Berlin · {meta.snapshot}
        </span>
        <span>Ceny historyczne · oszacowania ML · {meta.modelVersion}</span>
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
