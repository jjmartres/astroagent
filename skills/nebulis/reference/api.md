# Nebulis HTTP API (the parts this skill uses)

Source: nebulis-app/nebulis, `server/routes/library.ts`, `server/routes/meta.ts`, `server/routes/openapi.ts`, `server/lib/telescopeSchemas.ts`, `server/lib/observingSiteSchemas.ts`, `server/middleware/auth.ts`, `server/middleware/apiEnvelope.ts`, and the contract test `tests/backend/pixinsightContract.test.ts`. Base path `/api/v1`.

## Authentication and envelope

- Header `X-API-Key: neb-…` (or `Authorization: Bearer neb-…`). The `?apiKey=` query parameter was removed. A key acts as its owner with the owner's role; admin-only routes answer 403 otherwise.
- Every JSON answer is `{ "ok": true, "data": … }` or `{ "ok": false, "data": null, "error": { "code", "message" } }`.

## Routes

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/meta/version` | | `{ version }` |
| GET | `/library/objects` | `?search=` optional | `[{ id, catalogId, name, folderName, type, constellation, ra, dec, magnitude, distanceLy, sizeArcmin, description, aliases[], nicknames[], primaryTelescopeId, sessionCount, … }]` |
| GET | `/library/objects/:id/sessions` | `?includeVariants=true` optional | `[{ date, filters[], exposures[], subFrameCount, … }]` |
| GET | `/library/objects/:id/sessions/:date/frame-analysis` | `?includeVariants=1` optional | `{ objectId, date, frames[], reference, measured, total }`; each frame `{ path, name, timestamp, metrics, verdict: { score, grade, flags[], reasons[] }, review, kept }` |
| POST | `/library/frame-analysis/measure` (admin) | `{ path, force? }` | `{ path, metrics, cached }`; measures one frame, CPU-heavy |
| PUT | `/library/frame-analysis/review` (admin) | `{ path, keep: true \| false \| null }` | `{ path, keep }`; the review wins over the grade in exports |
| POST | `/library/objects/:id/stacking-export/plan` | `{ dates[], includeNotKept?, layout? }` | the plan: `{ objectId, nights, includeNotKept, groups[], unmeasuredByNight, totals }` |
| POST | `/library/objects/:id/stacking-export` | same body, `layout: "wbpp" \| "siril"` | `{ jobId }` (async ZIP build) |
| GET | `/library/download/status/:jobId` | | `{ status: running \| done \| error \| cancelled, filesTotal, filesDone, token?, filename?, size? }`; the job is forgotten once `done` has been read |
| GET | `/library/download/tmp/:token` | no auth: the token is the credential | the ZIP |
| GET | `/library/calibrations` | | `{ groups[] }`: calibration library by type, with `settingsGroups[]` (`key, exposureSec, binning, gain, sensorTempC, fileCount, isExpired, attachments?`) |
| GET | `/library/calibrations/attachments?objectId=` | `&date=` optional | `{ attachments[] }`: `{ id, objectId, date, calibrationType: flat \| flatDark, scope, folderName, settingsKey }` |
| GET | `/telescopes` | | `[{ id, name, model, kind, activeOpticalConfigId, opticalConfigs[{ id, name, focalLengthMm, sensorWidthMm, sensorHeightMm, pixelSizeUm }], rig{ sensorType, filters[] }, usedFilters[], transports[], … }]`; `nebulis.py` drops transports and credentials |
| GET | `/sites/active` | | `{ id, name, latitude, longitude, timezone, bortleClass, darkness, … }` |
| GET | `/library/objects/:id/project-archives` | | `[{ id, originalName, size, uploadedAt, title, … }]` |
| POST | `/library/objects/:id/project-archives` (admin) | multipart: `archive` (.zip, .xpsm, .pxiproject), `title`, `notes`, `software` | the stored record |
| GET | `/library/objects/:id/processed-images` | | `[{ id, objectId, date \| null, filename, originalName, title, notes, size, uploadedAt, source, url, thumbUrl, … }]`: finished images of the object, every session and object-level |
| POST | `/library/objects/:id/processed-images` (admin) | multipart: `image` (JPG, PNG, WebP, TIFF, XISF, FITS…; up to 2 GB), `title`, `notes` | the stored record, `date: null` (object-level: shown in the object's Processed images and the gallery) |

The two multipart POSTs stream to the server's disk (multer `diskStorage`); the limits are 20 GB for a project archive, 2 GB for a processed image (413 `LIMIT_FILE_SIZE` above). `nebulis.py` streams the body too, in 8 MiB writes with an exact `Content-Length`.

## Chunked uploads

For large files (`nebulis.py` uses them above 1 GiB, or with `--chunked`). Admin key on every call. A server without them answers 404 or 405 on `POST /uploads`, and `nebulis.py` falls back to the multipart POST.

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/uploads` | `{ target: "project-archive" \| "processed-image", objectId, filename, size, sha256, title, notes, software }` | `{ uploadId, chunkSize, maxSize, expiresAt }`; 413 with `maxSize` when `size` is over it |
| PUT | `/uploads/:uploadId/chunks/:index` | `application/octet-stream`, `Content-Range: bytes start-end/total` (end inclusive); chunk *i* starts at `i × chunkSize`, the last one is shorter | |
| GET | `/uploads/:uploadId` | | `{ received: [[start, end], …], size, status }`: byte ranges the server holds, end inclusive |
| POST | `/uploads/:uploadId/complete` | | the same record as the multipart POST of the target; the server checks the size and the sha256 |
| DELETE | `/uploads/:uploadId` | | drops the upload (`nebulis.py` never calls it: a stopped upload stays resumable until `expiresAt`) |

`nebulis.py` retries a failed chunk 3 times (1, 2, 4 s), then stops with exit 4 and keeps `<temp dir>/nebulis-upload-<uploadId>.json` (path, size, mtime, sha256, chunk size; never the key). `--resume UPLOAD_ID` reads it, calls `GET /uploads/:uploadId`, sends the missing chunks and completes.

## Plan group

```
{ id, night, filter, exposureSec, gain, binning, sensorTempC, frames, kept, bytes,
  dark | flat | flatDark | bias: { type, name, scope, folderName, key, source: attached | matched,
                                   fileCount, exposureSec, gain, binning, sensorTempC, filter,
                                   capturedAt, isExpired, deltaTempC?, deltaDays? } | null,
  issues: [{ code, severity: error | warning, params? }] }
```

Issue codes: `no_dark`, `dark_temp_far`, `dark_expired`, `no_flat`, `flat_other_night`, `no_flat_calibration`, `bias_expired`, `unknown_settings`.

Only flats and flat-darks can be attached to an object (whole object, or one night); darks and bias are always matched from the library by exposure, gain, binning and temperature.
