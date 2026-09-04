"use strict";

const assert = require("node:assert/strict");
const Location = require("../frontend/room-location.js");

const rooms = [
  {
    smartroomId: "SR-CA-MSK-1",
    room: "ЦА, Москва, Кутузовский проспект, 3 этаж, Переговорная 1",
    devices: [{ mac: "001122334455", hostname: "codec-one" }],
  },
  {
    smartroomId: "SR-CA-MSK-2",
    address: "ЦА, Москва, Ленинградский проспект, 5 этаж, Переговорная 2",
    devices: [{ mac: "AABBCCDDEEFF", hostname: "codec-two" }],
  },
  {
    smartroomId: "SR-SZ-SPB-1",
    locationPath: "СЗ, Санкт-Петербург, Невский проспект, 2 этаж, Переговорная 3",
    devices: [{ mac: "102030405060", hostname: "codec-three" }],
  },
];

assert.deepEqual(Location.parse(rooms[0]), {
  tb: "ЦА",
  city: "Москва",
  site: "Кутузовский проспект",
  floor: "3 этаж",
  room: "Переговорная 1",
  path: "ЦА, Москва, Кутузовский проспект, 3 этаж, Переговорная 1",
});

let cascade = Location.cascade(rooms, { tb: "ЦА", city: "Москва", site: "Кутузовский проспект" });
assert.deepEqual(cascade.options.city, ["Москва"]);
assert.deepEqual(cascade.options.site, ["Кутузовский проспект", "Ленинградский проспект"]);
assert.deepEqual(cascade.options.floor, ["3 этаж"]);
assert.deepEqual(cascade.options.room, ["Переговорная 1"]);

cascade = Location.cascade(rooms, { tb: "СЗ", city: "Москва", site: "Кутузовский проспект" });
assert.equal(cascade.filters.city, "", "an invalid downstream city must be cleared after changing TB");
assert.deepEqual(cascade.options.city, ["Санкт-Петербург"]);
assert.deepEqual(cascade.options.site, ["Невский проспект"]);

assert.equal(Location.matches(rooms[0], { tb: "ЦА", city: "Москва", site: "Кутузовский проспект" }), true);
assert.equal(Location.matches(rooms[1], { tb: "ЦА", city: "Москва", site: "Кутузовский проспект" }), false);
assert.equal(Location.matches(rooms[0], {}, "codec-one"), true);
assert.equal(Location.matches(rooms[0], {}, "00:11:22:33:44:55"), true);
assert.equal(Location.matches(rooms[0], {}, "Невский"), false);

for (let missing = 0; missing < 5; missing++) {
  const parts = ["ЦА", "Москва", "Кутузовский проспект", "3 этаж", "Переговорная 1"];
  parts[missing] = "";
  const parsed = Location.parse({ room: parts.join(", ") });
  Location.fields.forEach((field, index) =>
    assert.equal(parsed[field], parts[index], `missing level ${missing}: ${field}`),
  );
}
const noFloor = { room: "ЦА, Москва, Кутузовский проспект, , Переговорная 1" };
const otherSite = { room: "ЦА, Москва, Другая площадка, , Переговорная 2" };
const incomplete = Location.cascade([noFloor, otherSite], { tb: "ЦА", city: "Москва", site: "Кутузовский проспект" });
assert.deepEqual(incomplete.options.floor, []);
assert.deepEqual(incomplete.options.room, ["Переговорная 1"]);
assert.equal(Location.matches(noFloor, incomplete.filters, "Переговорная 1"), true);
assert.equal(Location.matches(otherSite, incomplete.filters), false);
console.log("frontend room location test passed");
