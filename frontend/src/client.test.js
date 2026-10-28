import { test } from "node:test";
import assert from "node:assert/strict";
import { api, catalogUrl, estimatePayload, AMENITY_LABELS } from "./client.js";

test("query encoding preserves search content and uses bounded pagination", () => {
  const url = new URL(
    catalogUrl(
      {
        district: "Mitte",
        roomType: "Entire home/apt",
        guests: 2,
        maxPrice: 300,
        query: "a&b / café",
      },
      "price-asc",
      12,
    ),
    "http://localhost",
  );
  assert.equal(url.searchParams.get("query"), "a&b / café");
  assert.equal(url.searchParams.get("offset"), "12");
  assert.equal(url.searchParams.get("limit"), "12");
});
test("unknown, no, yes and numeric zeros retain their distinct meanings", () => {
  const form = {
    ...Object.fromEntries(
      Object.keys(AMENITY_LABELS).map((k) => [k, "unknown"]),
    ),
    room_type: "Entire home/apt",
    property_type: "Entire rental unit",
    latitude: "52.52",
    longitude: "13.405",
    accommodates: "2",
    bedrooms: "0",
    beds: "1",
    bathrooms: "",
    minimum_nights: "2",
    wifi: "yes",
    parking: "no",
  };
  const payload = estimatePayload(form, "Mitte");
  assert.equal(payload.bedrooms, 0);
  assert.equal(payload.bathrooms, null);
  assert.equal(payload.wifi, true);
  assert.equal(payload.parking, false);
  assert.equal(payload.washer, null);
  assert.equal(payload.accommodates, 2);
  assert.ok(!("price" in payload));
});
test("HTTP and network failures are actionable and aborts stay aborts", async (t) => {
  t.mock.method(globalThis, "fetch", async () => ({
    ok: false,
    status: 422,
    json: async () => ({ detail: "Wskaż punkt wewnątrz Berlina." }),
  }));
  await assert.rejects(api("/api/location"), /Wskaż punkt/);
  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };
  await assert.rejects(api("/api/catalog/meta"), /Nie udało się połączyć/);
  globalThis.fetch = async () => {
    throw new DOMException("cancelled", "AbortError");
  };
  await assert.rejects(api("/api/catalog/meta"), { name: "AbortError" });
});
