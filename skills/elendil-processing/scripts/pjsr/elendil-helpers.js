// elendil-helpers.js: PJSR helpers for the elendil-processing skill.
//
// Load with run_pjsr: include: ["<absolute path to this file>"], then call the functions in `code`.
// The code is eval-ed as a script: no top-level return; the last expression is the result.
//
// commonBorders is adapted from scanBorders in mxcoppell/pixinsight-connector-skills
// (skills/pixinsight-lrgb-linear-basic/reference/pjsr-helpers.js), MIT License, Copyright (c) 2026 Min Xie.

// Registration borders of one view: pixels to remove on each side (L, R, T, B), from bands that are
// zero (or NaN) for more than 1% of their samples or whose median drifts more than 5% from the band
// 60-100 px inside the edge. Samples the middle 60% of each edge, channel 0.
function scanBorders(id, maxDepth) {
  var w = ImageWindow.windowById(id);
  if (w.isNull) throw new Error("View not found: " + id);
  var img = w.mainView.image, W = img.width, H = img.height, res = {};
  maxDepth = maxDepth || 60;
  function band(side, d0, d1) {
    var vals = [], zero = 0, n = 0, along = (side == "L" || side == "R") ? H : W;
    var a = Math.floor(along * 0.2), b = Math.floor(along * 0.8);
    for (var d = d0; d < d1; ++d) for (var t = a; t < b; t += 7) {
      var x, y;
      if (side == "L") { x = d; y = t; } else if (side == "R") { x = W - 1 - d; y = t; }
      else if (side == "T") { x = t; y = d; } else { x = t; y = H - 1 - d; }
      var v = img.sample(x, y, 0); n++;
      if (v <= 1e-9 || v !== v) zero++; else vals.push(v);
    }
    vals.sort(function (p, q) { return p - q; });
    return { zero: zero / n, med: vals.length ? vals[vals.length >> 1] : 0 };
  }
  ["L", "R", "T", "B"].forEach(function (s) {
    var ref = band(s, 60, 100).med, cut = 0;
    for (var d = 0; d < maxDepth; d += 2) {
      var bd = band(s, d, d + 2);
      if (bd.zero > 0.01 || (bd.med > 0 && ref > 0 && Math.abs(bd.med / ref - 1) > 0.05)) cut = d + 2;
    }
    res[s] = cut;
  });
  return { id: id, width: W, height: H, borders: res };
}

// The crop that removes the registration borders of every listed view, plus a safety margin: the
// largest border per side over all views, plus `margin` px (default 10). Use the same amounts for
// crop_image on every view, so the masters keep the same geometry.
function commonBorders(ids, maxDepth, margin) {
  margin = (margin === undefined) ? 10 : margin;
  var crop = { left: 0, right: 0, top: 0, bottom: 0 }, per = [];
  ids.forEach(function (id) {
    var r = scanBorders(id, maxDepth);
    per.push(r);
    crop.left = Math.max(crop.left, r.borders.L);
    crop.right = Math.max(crop.right, r.borders.R);
    crop.top = Math.max(crop.top, r.borders.T);
    crop.bottom = Math.max(crop.bottom, r.borders.B);
  });
  for (var k in crop) crop[k] += margin;
  var sizes = per.map(function (r) { return r.width + "x" + r.height; });
  return { crop: crop, sameSize: sizes.every(function (s) { return s == sizes[0]; }), views: per };
}
