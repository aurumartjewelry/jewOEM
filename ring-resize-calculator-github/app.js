// Taiwan International Ring Size table.
// Values are inner circumference in mm.
// This table follows the commonly published Taiwan "國際圍" convention.
// Example: #12 = 53.4 mm, #14 = 56.5 mm.
const RING_SIZES = {
  4: 40.8, 5: 42.4, 6: 44.0, 7: 45.6, 8: 47.1, 9: 48.7,
  10: 50.3, 11: 51.8, 12: 53.4, 13: 55.0, 14: 56.5, 15: 58.1,
  16: 59.7, 17: 61.3, 18: 62.8, 19: 64.4, 20: 66.0, 21: 67.6,
  22: 69.1, 23: 70.7, 24: 72.3, 25: 73.8, 26: 75.4, 27: 77.0,
  28: 78.5, 29: 80.1, 30: 81.7
};

// Approximate alloy densities in g/cm³.
// Actual density varies with the specific alloy formula.
const DENSITY = {
  999: 19.32,
  916: 17.5,
  750: 15.6,
  585: 13.2,
  375: 11.5
};

// Convert g/cm³ to g/mm³.
function densityGPerMm3(fineness) {
  return DENSITY[fineness] / 1000;
}

const $ = (id) => document.getElementById(id);

function fillRingSizes() {
  const from = $("fromSize");
  const to = $("toSize");

  Object.keys(RING_SIZES).forEach((size) => {
    from.add(new Option(`#${size}`, size));
    to.add(new Option(`#${size}`, size));
  });

  from.value = "12";
  to.value = "14";
}

function calculate() {
  const fineness = $("fineness").value;
  const from = Number($("fromSize").value);
  const to = Number($("toSize").value);
  const width = Number($("width").value);
  const thickness = Number($("thickness").value);
  const factor = Number($("factor").value);

  if (![width, thickness, factor].every(Number.isFinite) || width <= 0 || thickness <= 0 || factor < 1) {
    alert("請確認戒腳寬度、厚度與加工係數。");
    return;
  }

  if (to <= from) {
    alert("改圍號數必須大於原戒圍。這個版本專門估算「改大」補料金料。");
    return;
  }

  const sizeDiff = to - from;
  const circumferenceDiff = RING_SIZES[to] - RING_SIZES[from];

  // Rectangular cross-section approximation:
  // volume = width × thickness × additional inner circumference.
  const volumeMm3 = width * thickness * circumferenceDiff;
  const theoreticalWeight = volumeMm3 * densityGPerMm3(fineness);
  const recommendedWeight = theoreticalWeight * factor;

  $("sizeDiff").textContent = sizeDiff.toFixed(0);
  $("circumferenceDiff").textContent = circumferenceDiff.toFixed(1);
  $("theoreticalWeight").textContent = theoreticalWeight.toFixed(3);
  $("recommendedWeight").textContent = recommendedWeight.toFixed(3);
}

function resetForm() {
  $("fineness").value = "750";
  $("fromSize").value = "12";
  $("toSize").value = "14";
  $("width").value = "2.00";
  $("thickness").value = "1.70";
  $("factor").value = "1.15";
  calculate();
}

fillRingSizes();
$("calculate").addEventListener("click", calculate);
$("reset").addEventListener("click", resetForm);
calculate();
