# Private Service Attachments: Frontend Integration Guide

This document describes how tutors upload files for a service and how authorized users access them.

## 1. Feature Rules

Service attachments are private files stored in the existing AWS S3 bucket.

A file is visible only to:

- The tutor who owns the service.
- A student who has a booking for that exact service/session.

Other students, unauthenticated users, and tutors who do not own the service cannot list or download the files.

The backend stores the S3 object key and file metadata in the database. It does not return a permanent public S3 URL. Every successful list/download request generates a short-lived presigned URL.

The frontend must treat the presigned URL as temporary and must request a fresh one when it expires.

## 2. API Base URL and Authentication

The backend API prefix is currently `/v1`. Examples assume:

```text
https://api.example.com/v1
```

All attachment endpoints require the normal access token:

```http
Authorization: Bearer <access_token>
```

The backend gets the authenticated user ID from the JWT. Do not send a user ID in the request body to decide access.

## 3. Attachment Object

Successful responses contain this object:

```json
{
  "id": "attachment-uuid",
  "service_id": "service-uuid",
  "tutor_id": "tutor-uuid",
  "original_filename": "week-1-notes.pdf",
  "content_type": "application/pdf",
  "file_size": 245760,
  "created_at": "2026-09-13T15:30:00+00:00",
  "download_url": "https://s3.amazonaws.com/...temporary-signature..."
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | UUID string | Attachment ID used for download and delete operations. |
| `service_id` | UUID string | Service to which the file belongs. |
| `tutor_id` | UUID string | Owner tutor profile. |
| `original_filename` | string | Filename to display to the user. |
| `content_type` | string | MIME type of the uploaded file. |
| `file_size` | number | File size in bytes. |
| `created_at` | datetime string or `null` | Upload timestamp. |
| `download_url` | string or `null` | Presigned URL, valid for approximately five minutes. |

The S3 object key is intentionally not part of the response.

## 4. Supported Files and Limits

The current backend accepts files up to 50 MB.

Supported MIME types:

- `application/pdf`
- Microsoft Word: `application/msword`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Microsoft Excel: `application/vnd.ms-excel`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Microsoft PowerPoint: `application/vnd.ms-powerpoint`, `application/vnd.openxmlformats-officedocument.presentationml.presentation`
- Archives: `application/zip`, `application/x-zip-compressed`
- `text/plain`
- Images: `image/jpeg`, `image/png`, `image/webp`

The frontend should validate file size and type before upload for a better user experience, but the backend remains the final authority.

## 5. Tutor Upload

### Endpoint

```http
POST /v1/service/{service_id}/attachments/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

The multipart field name must be `file`.

Example browser request:

```javascript
const formData = new FormData();
formData.append("file", selectedFile);

const response = await fetch(
  `${API_BASE_URL}/service/${serviceId}/attachments/`,
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: formData,
  }
);

const result = await response.json();
```

Do not set `Content-Type` manually when using `FormData`; the browser must add the multipart boundary.

### Successful response

```json
{
  "success": true,
  "message": "Service attachment uploaded.",
  "metadata": {},
  "data": {
    "id": "attachment-uuid",
    "service_id": "service-uuid",
    "tutor_id": "tutor-uuid",
    "original_filename": "week-1-notes.pdf",
    "content_type": "application/pdf",
    "file_size": 245760,
    "created_at": "2026-09-13T15:30:00+00:00",
    "download_url": "https://temporary-presigned-url"
  }
}
```

### Upload rules

- Only the tutor associated with the service can upload.
- The service must already exist as a published service.
- Uploading a file does not create a service revision and does not require admin approval.
- Each upload creates one attachment record.
- Multiple files are uploaded with multiple requests. The backend currently does not expose a batch upload endpoint.

## 6. List Files for a Service

### Endpoint

```http
GET /v1/service/{service_id}/attachments/
Authorization: Bearer <access_token>
```

Example response:

```json
{
  "success": true,
  "message": "Service attachments fetched.",
  "metadata": {},
  "data": [
    {
      "id": "attachment-uuid",
      "service_id": "service-uuid",
      "tutor_id": "tutor-uuid",
      "original_filename": "week-1-notes.pdf",
      "content_type": "application/pdf",
      "file_size": 245760,
      "created_at": "2026-09-13T15:30:00+00:00",
      "download_url": "https://temporary-presigned-url"
    }
  ]
}
```

The list is ordered newest first.

The endpoint succeeds only when the authenticated user is either:

- The service owner tutor.
- A student with a `service_bookings` record for this exact `service_id`.

A student who booked a different service owned by the same tutor is not authorized.

## 7. Download a Specific File

### Endpoint

```http
GET /v1/service/attachments/{attachment_id}/download/
Authorization: Bearer <access_token>
```

The response contains a newly generated presigned URL:

```json
{
  "success": true,
  "message": "Attachment download URL generated.",
  "metadata": {},
  "data": {
    "id": "attachment-uuid",
    "service_id": "service-uuid",
    "tutor_id": "tutor-uuid",
    "original_filename": "week-1-notes.pdf",
    "content_type": "application/pdf",
    "file_size": 245760,
    "created_at": "2026-09-13T15:30:00+00:00",
    "download_url": "https://fresh-temporary-presigned-url"
  }
}
```

The frontend can open the URL directly:

```javascript
const { data } = await api.get(
  `/service/attachments/${attachmentId}/download/`
);

window.open(data.download_url, "_blank", "noopener,noreferrer");
```

For a download button, requesting a fresh URL at click time is preferable to relying on the URL returned from an older list request.

## 8. Tutor Delete

### Endpoint

```http
DELETE /v1/service/attachments/{attachment_id}/
Authorization: Bearer <access_token>
```

Only the owner tutor can delete the attachment. Booked students cannot delete it.

Response:

```json
{
  "success": true,
  "message": "Service attachment deleted.",
  "metadata": {},
  "data": {
    "id": "attachment-uuid",
    "deleted": true
  }
}
```

After success, remove the attachment from the local list. A deleted attachment should not be retried or shown as downloadable.

## 9. Recommended Frontend Flows

### Tutor service page

1. Load the tutor's service details.
2. Request `GET /service/{service_id}/attachments/`.
3. Render each file using `original_filename`, `content_type`, and `file_size`.
4. Upload files with `POST /service/{service_id}/attachments/`.
5. Add the returned attachment to the list immediately after success.
6. For deletion, ask for confirmation, call the DELETE endpoint, then remove the item locally.
7. For download, request a fresh URL using the attachment download endpoint.

### Student booked-session page

1. Load the student's booking/session data.
2. Request the attachment list using the booking's `service_id`.
3. If the request returns `403`, do not show the attachment area as available.
4. Display files only for the exact booked service.
5. Request a fresh download URL when the student clicks a file.

Do not infer access from tutor ID, service visibility, or the fact that the student has booked another service.

## 10. Error Handling

| Status | Meaning | Frontend action |
| --- | --- | --- |
| `400` | Unsupported file type, missing filename, or file larger than 50 MB. | Show validation feedback and do not retry unchanged. |
| `401` | Missing, expired, or invalid JWT. | Run the normal refresh-token/login flow. |
| `403` | User is not the service owner and has not booked this service. | Hide or disable the attachment area. |
| `404` | Service or attachment is not available to the user. | Refresh the parent service/session state. |
| `503` | S3 signing/storage is temporarily unavailable. | Keep the item in local state and offer retry with backoff. |
| `5xx` | Unexpected backend failure. | Show a retryable error and preserve unsent upload state. |

Presigned URLs can expire independently of the API response. If S3 returns an expired-signature error, call the attachment download endpoint again instead of retrying the old URL.

## 11. Security and S3 Requirements

The bucket must not allow anonymous public reads for the private attachment prefix:

```text
tutor-media/service-attachments/*
```

The backend uploads these files to that prefix and grants access only through presigned URLs after database authorization. The frontend must never expose the S3 object key, AWS credentials, or a permanent public bucket URL.

Existing service images/videos may continue using the current service-media behavior. They are separate from private service attachments and should not be assumed to have the same access policy.

For browser previews, use the presigned URL directly. If the browser cannot render a file type, use download behavior instead of trying to proxy the file through the frontend.

## 12. TypeScript Types

```typescript
export interface ServiceAttachment {
  id: string;
  service_id: string;
  tutor_id: string;
  original_filename: string;
  content_type: string;
  file_size: number;
  created_at: string | null;
  download_url: string | null;
}

export interface ServiceAttachmentResponse {
  success: boolean;
  message: string;
  metadata: Record<string, unknown>;
  data: ServiceAttachment;
}

export interface ServiceAttachmentListResponse {
  success: boolean;
  message: string;
  metadata: Record<string, unknown>;
  data: ServiceAttachment[];
}
```

## 13. Database and Deployment

A migration creates the `service_attachments` table. Apply it before using these endpoints:

```bash
poetry run alembic upgrade head
```

The migration is reversible:

```bash
poetry run alembic downgrade -1
poetry run alembic upgrade head
```

The backend must have AWS permissions for:

- `s3:PutObject` on `tutor-media/service-attachments/*`
- `s3:GetObject` on `tutor-media/service-attachments/*`
- `s3:DeleteObject` on `tutor-media/service-attachments/*`

The backend generates presigned URLs using its configured AWS credentials or IAM role. The frontend does not need AWS credentials.
