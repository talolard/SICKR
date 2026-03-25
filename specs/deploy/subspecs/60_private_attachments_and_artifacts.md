# Private Attachments And Artifacts

This subspec defines the v1 storage and delivery contract for uploaded
attachments and generated runtime artifacts.

Read [00_context.md](./00_context.md) first for shared deployment assumptions.
Read [10_cloudfront_product_images.md](./10_cloudfront_product_images.md) for
the separate public product-image path.
Read [20_terraform_aws_setup.md](./20_terraform_aws_setup.md) for the private
bucket and IAM shape that this application contract uses.
Read [30_dockerization_and_cicd.md](./30_dockerization_and_cicd.md) for runtime
configuration boundaries.
Read [50_edge_and_app_routing.md](./50_edge_and_app_routing.md) for the
same-origin route ownership this spec preserves.

Implementation branch rule:
- start work for this subspec from `tal/deployproject` or from a stacked branch
  that descends from it

## Decision

Attachments and generated runtime artifacts must live in a private S3 bucket and
must be addressed by stable application-level ids, not by durable storage URLs.

For this deployment:

- product images are public and separate
- attachments and generated artifacts are private
- browser upload stays same-origin through `/api/attachments`
- browser read stays same-origin through `/attachments/{attachment_id}`
- durable state stores ids plus metadata, not presigned URLs

## Current Code Reality

The current code already gives us the right user-facing contract:

- the browser uploads through Next `POST /api/attachments`
- Next forwards that request to backend `POST /attachments`
- the backend returns an `AttachmentRef`
- `AttachmentRef.uri` is `/attachments/{attachment_id}`
- the browser reads through Next `GET /attachments/{attachment_id}`
- the backend currently resolves that id to local disk and returns the file
- durable asset metadata already exists in `app.assets`

Today `app.assets.storage_path` contains a local filesystem path.
In deployed AWS environments, treat that field as a storage locator whose value
is an S3 object key or bucket-relative path.
We do not need to rename the column in v1.
For the app-side contract, locator strings such as `local://...` or
`s3://bucket/key` are acceptable durable values as long as the browser contract
stays on stable attachment ids.

## Artifact Families

This subspec covers two private artifact families.

### User Attachments

These are browser-uploaded files that become part of the active thread or run.

For v1, this includes:

- uploaded room photos
- uploaded images used by image-analysis and floor-plan flows

### Generated Runtime Artifacts

These are backend- or tool-generated files that the UI may render or download.

For v1, this includes:

- image-analysis outputs such as masks, overlays, and depth maps
- floor-plan PNG and SVG outputs
- other thread- or run-scoped binary files referenced from `app.assets`

This subspec does not include trace bundles, which remain developer-oriented and
out of the first public rollout.

## Durable Contract

The durable contract must remain stable even if the storage implementation
changes.

Required durable fields:

- `asset_id` or `attachment_id`
- `kind`
- `mime_type`
- `file_name`
- `thread_id`
- `run_id` when applicable
- `sha256`
- `size_bytes`
- storage locator in backend persistence

Required durable URI shape:

- the app-facing URI remains `/attachments/{attachment_id}`

Do not store these durably:

- raw presigned S3 URLs
- redirect targets
- bucket/object URLs exposed directly to the browser as the long-term contract

## Stable Browser Contract

The current browser-visible contract must remain stable.

Required route ownership:

- browser upload uses Next `POST /api/attachments`
- browser read uses Next `GET /attachments/{attachment_id}`
- generated artifacts that are rendered as attachment refs also use
  `/attachments/{attachment_id}`

The UI should not need to know whether the bytes came from local disk, S3, a
proxy fetch, or a presigned GET generated behind the scenes.

## Storage Layout

The private bucket should distinguish uploads from generated artifacts.

Required v1 prefix families:

- `attachments/user-upload/<thread-id>/<asset-id>.<ext>`
- `attachments/generated/<thread-id>/<run-id-or-none>/<asset-id>.<ext>`
- `attachments/floor-plan/<thread-id>/<asset-id>.<ext>`

Prefix intent:

- `user-upload` is for direct browser uploads
- `generated` is for tool outputs such as analysis images and overlays
- `floor-plan` is for generated floor-plan outputs

The exact filename suffix can follow MIME type or source filename, but the
object key must include the stable asset id.

## Upload Contract

The upload contract must preserve the current same-origin browser behavior.

Required upload path:

1. browser uploads bytes to `POST /api/attachments`
2. Next proxies that request to backend `POST /attachments`
3. backend validates MIME type and upload size
4. backend allocates a new attachment id
5. backend writes the bytes to the private bucket under the correct prefix
6. backend writes or updates `app.assets` metadata with the object locator
7. backend returns typed attachment metadata

Required returned payload shape:

- `attachment_id`
- `mime_type`
- `uri`
- optional display metadata such as `file_name`

The returned `uri` must remain:

- `/attachments/{attachment_id}`

Direct browser-to-S3 upload is out of scope for v1.

## Read And Download Contract

The browser-visible read path must stay stable even though S3 access is
ephemeral under the hood.

Required browser-visible read path:

- `GET /attachments/{attachment_id}`

Required v1 server-side flow:

1. browser requests `/attachments/{attachment_id}`
2. Next forwards that request to the backend attachment resolver
3. backend loads durable metadata for the attachment id
4. backend resolves a fresh read against private storage
5. backend returns the file with the correct content type and filename

Preferred v1 delivery behavior:

- proxy or stream the bytes back through the app route

Why proxying is the default v1 choice:

- it preserves the current UI contract exactly
- it avoids exposing S3 object URLs to the browser
- it avoids leaking presigned query strings into client-side error handling or
  incidental logs
- the expected traffic volume is low enough that the extra hop is acceptable

Permitted internal implementation:

- the backend may use a fresh short-lived presigned GET internally
- a later version may redirect reads to a presigned URL if load or latency makes
  that worthwhile

But the durable and browser-visible contract must remain the attachment id and
`/attachments/{id}` path.

## Response And Cache Posture

Private attachment and artifact reads must not use the public product-image
cache behavior.

Required read posture:

- no public CloudFront behavior for private attachments
- no long-lived browser-cache assumption
- request-time storage resolution
- response headers should be private or no-store, not immutable public cache

## Security And Privacy Posture

This v1 is private at the storage layer, not a full multi-user authorization
system.

Required privacy rules:

- the S3 bucket blocks all public access
- only the runtime IAM role may read and write private objects
- browser access never depends on bucket public access
- durable app state does not expose raw object storage locations
- presigned URL query strings must never be logged
- attachment bytes must never be logged

Required application checks:

- continue enforcing image-only MIME restrictions at upload
- continue enforcing the current upload size limit
- return `404` for unknown attachment ids
- do not reveal bucket names or object keys in normal client responses

Important honesty rule:

- the friend-sharing deployment does not yet provide full user-by-user access
  control for attachments
- v1 privacy comes from private object storage plus opaque random ids and
  app-controlled reads

If the app later adds real accounts or shared/private workspaces, attachment
authorization must become a separate application-layer feature.

## Low-Volume Retention And Lifecycle

This deployment is not an archival system.
Use simple prefix-based lifecycle rules instead of a complicated retention
service.

Required v1 lifecycle posture:

- `attachments/user-upload/` expires after `90` days
- `attachments/generated/` expires after `30` days
- `attachments/floor-plan/` expires after `30` days
- incomplete multipart uploads are aborted after `7` days

Expected behavior after expiry:

- old attachment ids may resolve to missing objects
- v1 may return `404` when the underlying object is gone

Do not build a reconciliation service in v1 just to keep `app.assets` rows
perfectly synchronized with lifecycle expiry.

## Runtime And Config Contract

The deployed runtime needs a small explicit private-storage contract.

Required runtime capabilities:

- save uploaded bytes to private storage
- save generated artifact bytes to private storage
- resolve an `attachment_id` to stored object metadata
- fetch object bytes for proxied reads

Required config surface:

- private artifact bucket name
- optional private artifact prefix/root
- runtime IAM access to the private bucket
- local filesystem artifact root for local development fallback

The deployed runtime should not rely on container-local disk as the durable
storage of record.

## Launch Gates

The private-storage contract is not ready until all of these succeed:

- upload through `/api/attachments` succeeds
- the saved attachment ref survives reload as the same stable
  `/attachments/{attachment_id}` URI
- a later read still succeeds without depending on any earlier presigned URL
- generated artifact outputs also resolve through stable attachment ids
- private objects are not publicly readable from S3

## What This Subspec Defers

This subspec intentionally does not decide:

- the exact SDK calls used for S3 reads and writes
- multipart upload support for files larger than the current limit
- non-image upload support
- malware scanning or deep file inspection
- background cleanup of expired `app.assets` rows
- object deduplication by hash
- exact user-auth authorization rules

Those can change later without changing the stable attachment contract.

## Verification

When implemented, verify the private-storage contract with these checks:

- confirm uploads still enter through `/api/attachments`
- confirm reads still use `/attachments/{attachment_id}`
- confirm the backend stores object locators rather than presigned URLs
- confirm private objects are not publicly readable from S3
- confirm generated artifact outputs also resolve through stable attachment ids
- confirm browser snapshots and tool payloads continue to carry stable
  attachment URIs rather than presigned URLs
- confirm private reads are not routed through the public image cache path

## Summary

The private-asset contract for v1 is:

- keep attachments and generated artifacts in private storage
- keep `/api/attachments` and `/attachments/{attachment_id}` as the stable
  browser contract
- store durable ids and metadata, not expiring URLs
- resolve reads at request time through proxying or short-lived redirect
- keep public CloudFront image caching entirely separate from private asset
  delivery

The private storage contract is:

- one private bucket for attachments and generated runtime artifacts
- stable asset ids plus same-origin `/attachments/{id}` URIs
- S3 object keys in durable state, not presigned URLs
- app-proxied reads as the default v1 delivery behavior
- explicit prefix separation between uploads and generated artifacts
- simple lifecycle expiry instead of archival retention logic
