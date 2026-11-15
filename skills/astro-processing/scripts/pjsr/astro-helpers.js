// astro-helpers.js: PJSR helpers for the astro-processing skill.
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

// ─── Background checks (Gate G4) ─────────────────────────────────────────────
//
// `exclude` is an optional ellipse around the subject, in pixels of the view:
//   { cx, cy, a, b, angleDeg }  (a: semi-major axis, b: semi-minor axis, angle of the major axis from +x)
// Pixels inside it are left out, so the subject's own light is not read as background.
// Statistics use a low percentile (default 0.35) of each region, which keeps stars and faint
// sources out without a star mask. Results are in units of sigma = 1.4826 x MAD of the green
// channel of the whole view, so they read the same before and after a stretch.

function __excluder(exclude) {
  if (!exclude) return function () { return false; };
  var t = (exclude.angleDeg || 0) * Math.PI / 180, c = Math.cos(t), s = Math.sin(t);
  return function (x, y) {
    var dx = x - exclude.cx, dy = y - exclude.cy, u = dx * c + dy * s, v = -dx * s + dy * c;
    return (u * u) / (exclude.a * exclude.a) + (v * v) / (exclude.b * exclude.b) < 1;
  };
}

function __channels(img) {
  var W = img.width, H = img.height, n = img.numberOfChannels, out = [];
  for (var c = 0; c < n; ++c) { var a = new Float32Array(W * H); img.getSamples(a, new Rect(0, 0, W, H), c); out.push(a); }
  return out;
}

function __sigma(img) {
  img.selectedChannel = Math.min(1, img.numberOfChannels - 1);
  var s = 1.4826 * img.MAD();
  img.resetSelections();
  return s;
}

function __pct(v, p) { v.sort(function (a, b) { return a - b; }); return v.length ? v[Math.min(v.length - 1, v.length * p | 0)] : NaN; }

// Radial background profile around the image centre: one value per annulus and channel, relative to
// the outermost annulus, in %. A centre-bright or blue-edged pattern (flat or vignetting residual) shows
// here and not in a four-corner comparison. `span` is the max - min over the annuli, per channel.
function radialProfile(id, exclude, pct) {
  var w = ImageWindow.windowById(id);
  if (w.isNull) throw new Error("View not found: " + id);
  var img = w.mainView.image, W = img.width, H = img.height, cx = W / 2, cy = H / 2, A = __channels(img);
  var inSubject = __excluder(exclude), rmax = Math.sqrt(cx * cx + cy * cy), step = rmax / 7, rings = [];
  pct = pct || 0.35;
  for (var k = 0; k < 7; ++k) {
    var r0 = k * step, r1 = (k + 1) * step, v = A.map(function () { return []; });
    for (var y = 0; y < H; y += 3) for (var x = 0; x < W; x += 3) {
      var d = Math.sqrt((x - cx) * (x - cx) + (y - cy) * (y - cy));
      if (d < r0 || d >= r1 || inSubject(x, y)) continue;
      for (var c = 0; c < A.length; ++c) v[c].push(A[c][y * W + x]);
    }
    if (v[0].length > 500) rings.push({ ring: Math.round(r0) + "-" + Math.round(r1), level: v.map(function (a) { return __pct(a, pct); }) });
  }
  var ref = rings[rings.length - 1].level, span = ref.map(function () { return 0; });
  rings.forEach(function (r) {
    r.relPct = r.level.map(function (v, c) { return +(100 * (v / ref[c] - 1)).toFixed(3); });
  });
  for (var c = 0; c < ref.length; ++c) {
    var vals = rings.map(function (r) { return r.relPct[c]; });
    span[c] = +(Math.max.apply(null, vals) - Math.min.apply(null, vals)).toFixed(3);
  }
  return { id: id, rings: rings.map(function (r) { return { ring: r.ring, relPct: r.relPct }; }), spanPct: span };
}

// Background uniformity over the whole field: the spread (p95 - p5) of block levels, in sigma, for the
// luminance and for the chroma (R - G, B - G). Blocks of `block` px (default 64); compare 64 and 256 to
// tell noise (spread drops with size) from structure (spread stays).
function bgBlocks(id, block, exclude) {
  var w = ImageWindow.windowById(id);
  if (w.isNull) throw new Error("View not found: " + id);
  var img = w.mainView.image, W = img.width, H = img.height, A = __channels(img), B = block || 64;
  var inSubject = __excluder(exclude), lum = [], rg = [], bg = [], sig = __sigma(img), color = A.length >= 3;
  for (var by = 0; by + B <= H; by += B) for (var bx = 0; bx + B <= W; bx += B) {
    if (inSubject(bx + B / 2, by + B / 2)) continue;
    var q = A.map(function (a) {
      var v = []; for (var y = by; y < by + B; y += 2) for (var x = bx; x < bx + B; x += 2) v.push(a[y * W + x]);
      return __pct(v, 0.4);
    });
    lum.push(color ? 0.2126 * q[0] + 0.7152 * q[1] + 0.0722 * q[2] : q[0]);
    if (color) { rg.push(q[0] - q[1]); bg.push(q[2] - q[1]); }
  }
  function spread(a) { return a.length ? (__pct(a.slice(), 0.95) - __pct(a.slice(), 0.05)) / sig : null; }
  function r3(x) { return x === null ? null : +x.toFixed(3); }
  return { id: id, blocks: lum.length, block: B, sigma: sig, lumSpreadSigma: r3(spread(lum)),
           rgSpreadSigma: r3(spread(rg)), bgSpreadSigma: r3(spread(bg)) };
}

// Background level of vertical strips (`strip` px, default 60), relative to the median strip, in sigma.
// Bands of ±0.3 sigma or more that are already in the stacked master point at the flats (panel structure).
// Pass rows = true for horizontal strips.
function colProfile(id, strip, exclude, rows) {
  var w = ImageWindow.windowById(id);
  if (w.isNull) throw new Error("View not found: " + id);
  var img = w.mainView.image, W = img.width, H = img.height, A = __channels(img), S = strip || 60;
  var inSubject = __excluder(exclude), sig = __sigma(img), color = A.length >= 3, vals = [];
  var along = rows ? H : W, across = rows ? W : H;
  for (var s0 = 0; s0 + S <= along; s0 += S) {
    var v = [];
    for (var t = 0; t < across; t += 2) for (var u = s0; u < s0 + S; u += 2) {
      var x = rows ? t : u, y = rows ? u : t;
      if (inSubject(x, y)) continue;
      var i = y * W + x;
      v.push(color ? 0.2126 * A[0][i] + 0.7152 * A[1][i] + 0.0722 * A[2][i] : A[0][i]);
    }
    vals.push(__pct(v, 0.35));
  }
  var med = __pct(vals.slice(), 0.5);
  var rel = vals.map(function (v) { return +((v - med) / sig).toFixed(2); });
  return { id: id, strip: S, rows: !!rows, relSigma: rel,
           spanSigma: +(Math.max.apply(null, rel) - Math.min.apply(null, rel)).toFixed(2) };
}

// Remove vertical (or, with rows = true, horizontal) bands from a LINEAR starless view: per channel,
// the background level of each column (40th percentile over the rows, subject excluded), smoothed over
// ±halfWidth px (default 40), minus its median, is subtracted. Writes a new view `newId`; the source is
// not changed. Returns the largest correction per channel. Check with colProfile before and after.
function correctBands(id, newId, exclude, halfWidth, rows) {
  var src = ImageWindow.windowById(id);
  if (src.isNull) throw new Error("View not found: " + id);
  var img = src.mainView.image, W = img.width, H = img.height, n = img.numberOfChannels, hw = halfWidth || 40;
  var inSubject = __excluder(exclude), along = rows ? H : W, across = rows ? W : H, info = [];
  var out = new ImageWindow(W, H, n, 32, true, img.isColor, newId);
  out.mainView.beginProcess();
  out.mainView.image.assign(img);
  for (var c = 0; c < n; ++c) {
    var a = new Float32Array(W * H); img.getSamples(a, new Rect(0, 0, W, H), c);
    var lvl = new Float64Array(along);
    for (var k = 0; k < along; ++k) {
      var v = [];
      for (var t = 0; t < across; t += 2) { var x = rows ? t : k, y = rows ? k : t; if (!inSubject(x, y)) v.push(a[y * W + x]); }
      lvl[k] = __pct(v, 0.4);
    }
    var sm = new Float64Array(along);
    for (var k2 = 0; k2 < along; ++k2) {
      var sum = 0, cnt = 0;
      for (var j = Math.max(0, k2 - hw); j <= Math.min(along - 1, k2 + hw); ++j) { sum += lvl[j]; cnt++; }
      sm[k2] = sum / cnt;
    }
    var med = __pct(Array.prototype.slice.call(sm), 0.5), maxC = 0;
    for (var y2 = 0; y2 < H; ++y2) for (var x2 = 0; x2 < W; ++x2) {
      var d = sm[rows ? y2 : x2] - med; a[y2 * W + x2] -= d; if (Math.abs(d) > maxC) maxC = Math.abs(d);
    }
    out.mainView.image.setSamples(a, new Rect(0, 0, W, H), c);
    info.push({ channel: c, maxCorrection: maxC });
  }
  out.mainView.endProcess();
  out.keywords = src.keywords;
  return { id: newId, corrections: info };
}
