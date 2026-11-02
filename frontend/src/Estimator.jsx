import React, { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { ArrowLeft, ArrowRight, MapPin } from "lucide-react";
import { api, AMENITY_LABELS, estimatePayload } from "./client.js";
import { money, ROOM_NAMES } from "./market.js";
import { ModelCaution, FinalEvaluationNote } from "./ModelContext.jsx";

function LocationPicker({ latitude, longitude, onChange }) {
  const container = useRef(null),
    map = useRef(null),
    marker = useRef(null),
    callback = useRef(onChange);
  callback.current = onChange;
  useEffect(() => {
    const value = L.map(container.current, { scrollWheelZoom: false }).setView(
      [52.52, 13.405],
      12,
    );
    map.current = value;
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
      maxZoom: 19,
    }).addTo(value);
    marker.current = L.circleMarker([52.52, 13.405], {
      radius: 9,
      color: "#fff",
      fillColor: "#d75c3c",
      fillOpacity: 1,
      weight: 3,
    }).addTo(value);
    value.on("click", ({ latlng }) =>
      callback.current(latlng.lat.toFixed(5), latlng.lng.toFixed(5)),
    );
    const observer = new ResizeObserver(() => value.invalidateSize());
    observer.observe(container.current);
    return () => {
      observer.disconnect();
      value.remove();
      map.current = null;
    };
  }, []);
  useEffect(() => {
    const lat = Number(latitude),
      lon = Number(longitude);
    if (
      latitude !== "" &&
      longitude !== "" &&
      lat > 52.3 &&
      lat < 52.7 &&
      lon > 13.05 &&
      lon < 13.8
    ) {
      marker.current?.setLatLng([lat, lon]);
      map.current?.panTo([lat, lon], { animate: false });
    }
  }, [latitude, longitude]);
  return (
    <div
      ref={container}
      className="location-picker"
      aria-label="Wskaż lokalizację noclegu na mapie"
    />
  );
}

const INITIAL = {
  room_type: "Entire home/apt",
  property_type: "Entire rental unit",
  latitude: "52.52",
  longitude: "13.405",
  accommodates: "2",
  bedrooms: "1",
  beds: "1",
  bathrooms: "1",
  minimum_nights: "2",
  ...Object.fromEntries(
    Object.keys(AMENITY_LABELS).map((key) => [key, "unknown"]),
  ),
};

export default function Estimator({ meta, onBack }) {
  const [form, setForm] = useState(INITIAL),
    [district, setDistrict] = useState("");
  const [locationError, setLocationError] = useState(""),
    [error, setError] = useState("");
  const [busy, setBusy] = useState(false),
    [result, setResult] = useState(null),
    [retry, setRetry] = useState(0);
  const request = useRef(null),
    revision = useRef(0);
  function change(values) {
    revision.current += 1;
    request.current?.abort();
    setBusy(false);
    setResult(null);
    setError("");
    if ("latitude" in values || "longitude" in values) {
      setDistrict("");
      setLocationError("");
    }
    setForm((previous) => ({ ...previous, ...values }));
  }
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController();
    setDistrict("");
    setLocationError("");
    const timer = setTimeout(() => {
      if (form.latitude === "" || form.longitude === "") {
        setLocationError("Podaj obie współrzędne lub wybierz punkt na mapie.");
        return;
      }
      api(
        `/api/location?${new URLSearchParams({ latitude: form.latitude, longitude: form.longitude })}`,
        { signal: controller.signal },
      )
        .then((data) => {
          if (!controller.signal.aborted) setDistrict(data.district);
        })
        .catch((e) => {
          if (!controller.signal.aborted) setLocationError(e.message);
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [form.latitude, form.longitude, retry]);
  async function submit(event) {
    event.preventDefault();
    if (!district) return;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    const submitted = revision.current;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const data = await api("/api/estimate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(estimatePayload(form, district)),
        signal: controller.signal,
      });
      if (!controller.signal.aborted && submitted === revision.current)
        setResult(data);
    } catch (e) {
      if (!controller.signal.aborted) setError(e.message);
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return (
    <main className="estimate-page">
      <button className="back-button" onClick={onBack}>
        <ArrowLeft size={17} /> Wróć do odkrywania
      </button>
      <span className="eyebrow">TWÓJ NOCLEG. JEGO KONTEKST.</span>
      <h1>Ile może kosztować noc?</h1>
      <p className="page-subtitle">
        Wskaż miejsce i parametry. Model porówna je z historycznym rynkiem
        Berlina.
      </p>
      <div className="estimate-layout">
        <form onSubmit={submit} className="estimate-form">
          <fieldset>
            <legend>01 · Lokalizacja</legend>
            <p className="field-help">
              Kliknij na mapie. Dzielnicę ustalimy automatycznie. Możesz też
              wpisać współrzędne poniżej.
            </p>
            <LocationPicker
              latitude={form.latitude}
              longitude={form.longitude}
              onChange={(latitude, longitude) =>
                change({ latitude, longitude })
              }
            />
            <div className="form-grid">
              <label>
                Szerokość geograficzna
                <input
                  required
                  type="number"
                  step="any"
                  min="52.30001"
                  max="52.69999"
                  value={form.latitude}
                  onChange={(e) => change({ latitude: e.target.value })}
                />
              </label>
              <label>
                Długość geograficzna
                <input
                  required
                  type="number"
                  step="any"
                  min="13.05001"
                  max="13.79999"
                  value={form.longitude}
                  onChange={(e) => change({ longitude: e.target.value })}
                />
              </label>
            </div>
            <p className="location-status" role="status">
              <MapPin size={14} />{" "}
              {district || locationError || "Sprawdzamy lokalizację…"}
            </p>
            {locationError && (
              <button
                type="button"
                className="back-button"
                onClick={() => setRetry((n) => n + 1)}
              >
                Sprawdź lokalizację ponownie
              </button>
            )}
          </fieldset>
          <fieldset>
            <legend>02 · Przestrzeń</legend>
            <div className="form-grid">
              <label>
                Rodzaj noclegu
                <select
                  value={form.room_type}
                  onChange={(e) =>
                    change({
                      room_type: e.target.value,
                      property_type:
                        meta.propertyTypesByRoom[e.target.value][0],
                    })
                  }
                >
                  {Object.entries(ROOM_NAMES).map(([key, value]) => (
                    <option key={key} value={key}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Typ obiektu (nazwy źródłowe)
                <select
                  value={form.property_type}
                  onChange={(e) => change({ property_type: e.target.value })}
                >
                  {meta.propertyTypesByRoom[form.room_type].map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
              </label>
              {[
                ["accommodates", "Liczba gości", 1, 16, 1],
                ["bedrooms", "Sypialnie (0 = studio)", 0, 50, 1],
                ["beds", "Łóżka", 0, 100, 1],
                ["bathrooms", "Łazienki", 0, 50, 0.5],
                ["minimum_nights", "Minimalny pobyt (noce)", 1, 3650, 1],
              ].map(([key, label, min, max, step]) => (
                <label key={key}>
                  {label}
                  <input
                    type="number"
                    required={key === "accommodates"}
                    min={min}
                    max={max}
                    step={step}
                    placeholder="Nie wiem"
                    value={form[key]}
                    onChange={(e) => change({ [key]: e.target.value })}
                  />
                </label>
              ))}
            </div>
            <p className="field-help">
              Nieznane parametry możesz pozostawić puste. Model nie korzysta z
              metrażu ani terminu podróży.
            </p>
          </fieldset>
          <fieldset>
            <legend>03 · Udogodnienia</legend>
            <div className="form-grid amenities-grid">
              {Object.entries(AMENITY_LABELS).map(([key, label]) => (
                <label key={key}>
                  {label}
                  <select
                    value={form[key]}
                    onChange={(e) => change({ [key]: e.target.value })}
                  >
                    <option value="unknown">Nie wiem</option>
                    <option value="yes">Tak</option>
                    <option value="no">Nie</option>
                  </select>
                </label>
              ))}
            </div>
          </fieldset>
          <button
            className="primary-button"
            type="submit"
            disabled={busy || !district}
          >
            {busy ? "Obliczamy cenę…" : "Oszacuj cenę"}
            <ArrowRight size={16} />
          </button>
        </form>
        <aside className="estimate-result" aria-live="polite" aria-busy={busy}>
          <span className="eyebrow">PERSPEKTYWA MODELU</span>
          {busy ? (
            <h2>Sprawdzamy parametry…</h2>
          ) : result ? (
            <>
              <h2 className="estimated-value">
                {money(result.estimated_price_eur)}
                <small> / noc</small>
              </h2>
              <p>Szacowana cena ofertowa · {district}</p>
              <p className="field-help">
                Wynik dla wpisanych parametrów. Po zmianie danych oblicz go
                ponownie.
              </p>
              {result.warnings.length > 0 && (
                <ul className="listing-warnings">
                  {result.warnings.map((message) => (
                    <li key={message}>{message}</li>
                  ))}
                </ul>
              )}
              <details className="model-method">
                <summary>Jak powstał wynik?</summary>
                <p>
                  Model S02 wytrenowany na 5814 ofertach. Osobna walidacja
                  obejmowała 1108 ofert innych gospodarzy. Dane z 19.09.2026.
                </p>
                <FinalEvaluationNote />
              </details>
            </>
          ) : (
            <>
              <h2>
                Najpierw miejsce,
                <br />
                potem cena.
              </h2>
              <p>Uzupełnij parametry po lewej i wybierz „Oszacuj cenę”.</p>
            </>
          )}
          {error && (
            <div className="inline-error" role="alert">
              <strong>Nie udało się obliczyć ceny.</strong>
              <p>{error}</p>
              <p>
                Parametry zostały zachowane. Spróbuj ponownie przyciskiem
                formularza.
              </p>
            </div>
          )}
          <ModelCaution />
          <p className="field-help">
            To pomoc w porównywaniu ofert, bez potwierdzenia dostępności i opłat
            za konkretną rezerwację.
          </p>
        </aside>
      </div>
    </main>
  );
}
