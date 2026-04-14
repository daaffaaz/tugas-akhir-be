# Frontend Integration Guide: Google Auth -> Backend JWT

This guide explains how the frontend should integrate Google Sign-In with this backend.

## Goal

- Frontend gets Google `id_token`.
- Frontend sends `id_token` to backend endpoint `POST /api/auth/google/`.
- Backend verifies token with Google and returns app JWT:
  - `access`
  - `refresh`

Use `access` as `Authorization: Bearer <access>` for protected API calls.

## Backend Contract

- **Endpoint**: `POST /api/auth/google/`
- **Content-Type**: `application/json`
- **Body**:

```json
{
  "id_token": "<google-id-token>"
}
```

- **Success Response (200)**:

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "User Name",
  "avatar_url": "https://...",
  "refresh": "jwt-refresh-token",
  "access": "jwt-access-token"
}
```

## Prerequisites

1. Frontend must use the same Google OAuth **Client ID** as backend setting:
   - backend `.env`: `GOOGLE_OAUTH_CLIENT_ID=...apps.googleusercontent.com`
2. CORS must allow your frontend origin in backend:
   - backend `.env`: `CORS_ALLOWED_ORIGINS=http://localhost:3000,...`
3. Frontend has Google Identity Services configured.

## Recommended Frontend Flow

1. Show Google login button.
2. User signs in using Google.
3. Receive Google `credential` (`id_token`) from Google callback.
4. Send token to backend `POST /api/auth/google/`.
5. Save returned `access` and `refresh`.
6. Use `access` for API requests.
7. If `access` expires, refresh using `POST /api/auth/token/refresh/`.

## Example: Next.js/React (Google Identity Services)

Install:

```bash
npm install @react-oauth/google
```

Wrap app with provider:

```tsx
import { GoogleOAuthProvider } from "@react-oauth/google";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <GoogleOAuthProvider clientId={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!}>
      {children}
    </GoogleOAuthProvider>
  );
}
```

Login button and backend exchange:

```tsx
import { GoogleLogin } from "@react-oauth/google";

export default function GoogleSignIn() {
  return (
    <GoogleLogin
      onSuccess={async (credentialResponse) => {
        const idToken = credentialResponse.credential;
        if (!idToken) return;

        const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/google/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id_token: idToken }),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err?.id_token?.[0] || err?.detail || "Google login failed");
        }

        const data = await res.json();
        // Save tokens securely based on your auth strategy
        // e.g. memory + refresh cookie, or localStorage (less secure)
        console.log("Logged in:", data);
      }}
      onError={() => {
        console.error("Google Sign-In failed");
      }}
    />
  );
}
```

## Token Storage Recommendation

- Prefer secure storage strategy:
  - keep `access` in memory when possible
  - store `refresh` more carefully (httpOnly cookie via BFF is best)
- If using localStorage/sessionStorage, understand XSS risks.

## Refresh Flow

When API returns `401` due to expired access token:

1. Call `POST /api/auth/token/refresh/` with:

```json
{
  "refresh": "<refresh-token>"
}
```

2. Replace access token with new one.
3. Retry original request.

## Common Errors and Fixes

- **`400 {"id_token": ["Invalid Google ID token."]}`**
  - Wrong/expired token
  - Frontend and backend use different Client IDs
- **`400 {"detail":"GOOGLE_OAUTH_CLIENT_ID is not configured."}`**
  - Backend env var missing; set it and restart backend
- **CORS error in browser**
  - Add frontend origin to `CORS_ALLOWED_ORIGINS`
- **Works locally but fails in production**
  - Add production origin in Google OAuth configuration and backend CORS

## Frontend Environment Variables

Example `.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-web-client-id.apps.googleusercontent.com
```

`NEXT_PUBLIC_GOOGLE_CLIENT_ID` must match backend `GOOGLE_OAUTH_CLIENT_ID`.
