# Nebulis HTTP API (the parts this skill uses)

Source: nebulis-app/nebulis, `server/routes/library.ts`, `server/routes/meta.ts`, `server/middleware/auth.ts`, `server/middleware/apiEnvelope.ts`, and the contract test `tests/backend/pixinsightContract.test.ts`. Base path `/api/v1`.

## Authentication and envelope

- Header `X-API-Key: neb-…` (or `Authorization: Bearer neb-…`). The `?apiKey=` query parameter was removed. A key acts as its owner with the owner's role; admin-only routes answer 403 otherwise.
- Every JSON answer is `{ "ok": true, "data": … }` or `{ "ok": false, "data": null, "error": { "code", "message" } }`.

## Routes

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/meta/version` | | `{ version }` |
| GET | `/library/objects` | | `[{ id, name, folderName, sessionCount? }]` |
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
| GET | `/library/objects/:id/project-archives` | | `[{ id, originalName, size, uploadedAt, title, … }]` |
| POST | `/library/objects/:id/project-archives` (admin) | multipart: `archive` (.zip, .xpsm, .pxiproject), `title`, `notes`, `software` | the stored record |

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
