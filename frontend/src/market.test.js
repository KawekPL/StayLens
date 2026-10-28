import { test } from "node:test";
import assert from "node:assert/strict";
import { filterListings, median, peerStats, histogram } from "./market.js";

test("joint filters exclude records that fail any criterion and preserve the input", () => {
  const rows = [
    {
      id: "1",
      title: "Loft",
      district: "Mitte",
      neighbourhood: "Park",
      roomType: "Entire home/apt",
      guests: 2,
      price: 80,
      reviews: 5,
    },
    {
      id: "2",
      title: "Loft",
      district: "Mitte",
      neighbourhood: "Park",
      roomType: "Entire home/apt",
      guests: 1,
      price: 70,
      reviews: 8,
    },
    {
      id: "3",
      title: "Loft",
      district: "Pankow",
      neighbourhood: "Park",
      roomType: "Entire home/apt",
      guests: 2,
      price: 60,
      reviews: 8,
    },
    {
      id: "4",
      title: "Loft",
      district: "Mitte",
      neighbourhood: "Park",
      roomType: "Entire home/apt",
      guests: 2,
      price: 120,
      reviews: 9,
    },
  ];
  const copy = JSON.stringify(rows);
  assert.deepEqual(
    filterListings(rows, {
      district: "Mitte",
      roomType: "Entire home/apt",
      guests: 2,
      maxPrice: 100,
      query: " LOFT ",
    }).map((row) => row.id),
    ["1"],
  );
  assert.equal(JSON.stringify(rows), copy);
});
test("a reference median excludes the selected offer and does not claim a score with too few peers", () => {
  const row = {
    id: "self",
    district: "Mitte",
    roomType: "Private room",
    price: 900,
  };
  const peer = { ...row, id: "peer", price: 50 };
  assert.deepEqual(peerStats(row, [row, peer]), {
    n: 1,
    median: 50,
    percent: null,
  });
});
test("medians handle even samples and absence of data", () => {
  assert.equal(median([1, 9, 3, 7]), 5);
  assert.equal(median([]), null);
});
test("histogram does not lose the maximum value or identical values", () => {
  for (const values of [
    [10, 20, 30, 40],
    [10, 10, 10],
  ]) {
    assert.equal(
      histogram(values).reduce((sum, bin) => sum + bin.count, 0),
      values.length,
    );
  }
});
