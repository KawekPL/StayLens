export const DEFAULT_FILTERS = Object.freeze({
  district: "",
  roomType: "Entire home/apt",
  guests: 2,
  maxPrice: 300,
  query: "",
});
export const ROOM_NAMES = {
  "Entire home/apt": "Cały apartament",
  "Private room": "Pokój prywatny",
  "Shared room": "Pokój współdzielony",
  "Hotel room": "Pokój hotelowy",
};
export const money = (value) =>
  value == null
    ? "—"
    : `${new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 0 }).format(value)} €`;
export const count = (value) => new Intl.NumberFormat("pl-PL").format(value);
export function median(values) {
  const sorted = values.filter(Number.isFinite).toSorted((a, b) => a - b);
  if (!sorted.length) return null;
  const i = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[i] : (sorted[i - 1] + sorted[i]) / 2;
}
export function filterListings(listings, filters, sort = "reviewed") {
  const query = filters.query.trim().toLocaleLowerCase("pl");
  const rows = listings.filter(
    (row) =>
      (!filters.district || row.district === filters.district) &&
      (!filters.roomType || row.roomType === filters.roomType) &&
      row.guests >= Number(filters.guests) &&
      row.price <= Number(filters.maxPrice) &&
      (!query ||
        `${row.title} ${row.district} ${row.neighbourhood}`
          .toLocaleLowerCase("pl")
          .includes(query)),
  );
  return rows.sort((a, b) =>
    sort === "price-asc"
      ? a.price - b.price || a.id.localeCompare(b.id)
      : sort === "price-desc"
        ? b.price - a.price || a.id.localeCompare(b.id)
        : b.reviews - a.reviews ||
          (b.rating || 0) - (a.rating || 0) ||
          a.id.localeCompare(b.id),
  );
}
export function peerStats(row, listings) {
  const peers = listings.filter(
    (other) =>
      other.id !== row.id &&
      other.district === row.district &&
      other.roomType === row.roomType,
  );
  const reference = median(peers.map((other) => other.price));
  return {
    n: peers.length,
    median: reference,
    percent:
      reference && peers.length >= 5
        ? Math.round((row.price / reference - 1) * 100)
        : null,
  };
}
export function histogram(values, bucketCount = 18) {
  if (!values.length) return [];
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const step = (maximum - minimum || 1) / bucketCount;
  const bins = Array.from({ length: bucketCount }, (_, i) => ({
    start: minimum + i * step,
    count: 0,
  }));
  for (const value of values)
    bins[Math.min(bucketCount - 1, Math.floor((value - minimum) / step))]
      .count++;
  return bins;
}
