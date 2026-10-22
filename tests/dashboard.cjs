// Run without browser/network dependencies: node tests/dashboard.cjs
// Exercise the existing inline dashboard consumers against jQuery JSON responses.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const files = [
  'LoRa-Gateway/Gateway/PHP/index.php',
  'Demos_sourceCode/01_2017CES_TsuNaMi/Gateway/PHP/index.php',
  'LoRa-Gateway/Gateway/PHP/ifroglab.php',
];
const literalMarkup = '<img src=x onerror=alert(1)>';
let runs = 0;

for (const file of files) {
  const html = fs.readFileSync(path.join(root, file), 'utf8');
  const code = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)]
    .map(match => match[1]).join('\n');
  const compiled = new vm.Script(code, { filename: file });

  for (const objectResponse of [true, false]) {
    let onLoad;
    const draws = [];
    const texts = {};
    // More than 50 readings catches a dashboard that shows stale first-page data.
    const values = Array.from({ length: 55 }, (_, index) => ['x', String(index + 1)]);
    values.push(['y', '3'], ['z', '4'], ['x', '99'], [literalMarkup, '7']);
    const records = values.map((reading, index) => ({
      Id: index + 1,
      KeyName: reading[0],
      Data: reading[1],
      Datetime: `2026-10-22 06:00:${String(index).padStart(2, '0')}`,
    }));
    const payload = { Result: 'OK', TotalRecordCount: records.length, Records: records };
    const $ = selector => ({
      text(value) {
        if (value === undefined) return texts[selector] || '';
        texts[selector] = value;
      },
      html() { throw new Error('Untrusted sensor content must not enter an HTML sink.'); },
    });
    $.post = (url, callback) => {
      assert.equal(url, 'AjaxIoT.php?action=list');
      callback(objectResponse ? JSON.parse(JSON.stringify(payload)) : JSON.stringify(payload));
    };
    function Chart(element) {
      this.draw = table => draws.push({ id: element.id, rows: table.rows });
    }
    const sandbox = {
      console: { log() {} },
      Number, Date, Array, JSON, $,
      setInterval() {},
      document: { getElementById: id => ({ id }) },
      google: {
        charts: { load() {}, setOnLoadCallback(callback) { onLoad = callback; } },
        visualization: {
          arrayToDataTable: rows => ({ rows, setValue(row, column, value) { rows[row + 1][column] = value; } }),
          Gauge: Chart, BarChart: Chart, AreaChart: Chart,
        },
      },
    };
    vm.createContext(sandbox);
    compiled.runInContext(sandbox);
    assert.equal(typeof onLoad, 'function');
    onLoad();
    sandbox.FunCharRedraw();

    const advanced = file.endsWith('/ifroglab.php');
    const gauge = draws.find(draw => draw.id === (advanced ? 'gauge_div' : 'chart_div'));
    assert.ok(gauge, 'The gauge must redraw.');
    if (advanced) {
      const readings = new Map(gauge.rows.slice(1));
      assert.equal(readings.get('x'), 99);
      assert.equal(readings.get('y'), 3);
      assert.equal(readings.get('z'), 4);
      assert.ok(draws.some(draw => draw.id === 'bar_div_latest'));
    } else {
      assert.deepEqual(Array.from(gauge.rows.slice(1), row => row[1]), [99, 3, 4]);
    }
    assert.ok(texts['#chart_div_text'].includes(literalMarkup), 'Sensor text must remain literal text.');
    runs++;
  }
  console.log(`PASS dashboard JSON parsing, latest readings and safe text: ${file}`);
}
console.log(`Passed ${runs} dashboard scenarios.`);
