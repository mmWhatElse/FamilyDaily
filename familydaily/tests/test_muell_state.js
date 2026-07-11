const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("app/static/assets/app.js", "utf8");
const start = source.indexOf("function parseMuellState");
const end = source.indexOf("\n}\n", start) + 3;
if (start < 0 || end < 3) throw new Error("parseMuellState nicht gefunden");

const context = {};
vm.runInNewContext(source.slice(start, end) + ";this.parse = parseMuellState", context);

const cases = [
  ["Altpapier in 10 tagen", "later"],
  ["Gelber Sack, Restmüll Heute", "today"],
  ["Biomüll MORGEN", "tomorrow"],
  ["Restmüll in 1 Tag", "tomorrow"],
  ["unavailable", null],
];

for (const [input, expected] of cases) {
  const result = context.parse(input);
  if ((result && result.urgency) !== expected) {
    throw new Error(`${input}: ${JSON.stringify(result)} statt ${expected}`);
  }
}

const mixedBins = context.parse("Gelber Sack, Restmüll Heute").bins;
if (mixedBins[0].kind !== "yellow" || mixedBins[1].kind !== "residual") {
  throw new Error(`Falsche Müllfarben: ${JSON.stringify(mixedBins)}`);
}

console.log(`${cases.length} Mülltag-Formate OK`);
