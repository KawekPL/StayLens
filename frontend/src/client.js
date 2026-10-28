export async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, options);
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error(
      "Nie udało się połączyć z usługą StayLens. Spróbuj ponownie.",
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message =
      typeof body?.detail === "string"
        ? body.detail
        : response.status === 422
          ? "Sprawdź wymagane pola i dopuszczalne wartości formularza."
          : "Nie udało się połączyć z usługą StayLens. Spróbuj ponownie.";
    throw new Error(message);
  }
  return response.json();
}

export function catalogUrl(filters, sort, offset = 0) {
  const params = new URLSearchParams({
    district: filters.district,
    room_type: filters.roomType,
    guests: String(filters.guests),
    max_price: String(filters.maxPrice),
    query: filters.query,
    sort,
    offset: String(offset),
    limit: "12",
  });
  return `/api/catalog/listings?${params}`;
}

export const AMENITY_LABELS = {
  wifi: "Wi-Fi",
  kitchen: "Kuchnia",
  washer: "Pralka",
  air_conditioning: "Klimatyzacja",
  elevator: "Winda",
  parking: "Parking",
  workspace: "Miejsce do pracy",
  self_check_in: "Samodzielne zameldowanie",
};

export function estimatePayload(form, district) {
  const required = ["latitude", "longitude", "accommodates"];
  const optional = ["bedrooms", "beds", "bathrooms", "minimum_nights"];
  const payload = {
    district,
    room_type: form.room_type,
    property_type: form.property_type,
  };
  for (const key of required) payload[key] = Number(form[key]);
  for (const key of optional)
    payload[key] = form[key] === "" ? null : Number(form[key]);
  for (const key of Object.keys(AMENITY_LABELS))
    payload[key] = form[key] === "unknown" ? null : form[key] === "yes";
  return payload;
}
