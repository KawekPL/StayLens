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
