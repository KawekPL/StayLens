import React, { useEffect, useRef } from "react";
import L from "leaflet";
import { Compass } from "lucide-react";
import { money } from "./market.js";

export default function MapView({ rows, selected, onSelect, geo, onReset }) {
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
