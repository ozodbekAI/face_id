# FaceID Global Backend (RBAC)

This version adds **RBAC** (admin/owner) and removes image upload from user creation.

## Roles
- **admin**: create companies, create owners (assign to company), manage owners.
- **owner**: manage employees (users) and view attendance/events **only for their company**.

There is **no register endpoint**.

## Bootstrap admin
On first startup, if no admin exists, the server creates one.

- Configure with env:
  - `ROOT_ADMIN_USERNAME` (default: `admin`)
  - `ROOT_ADMIN_PASSWORD` (if empty, a random password is generated and printed into logs)

## Login
`POST /auth/login`

Request:
```json
{"username":"admin","password":"..."}
```

Response:
```json
{"access_token":"...","token_type":"bearer","expires_at":"...","role":"admin","company_id":null}
```

Use token:
`Authorization: Bearer <access_token>`

## Admin API
- `POST /admin/companies`
- `GET /admin/companies`
- `PUT /admin/companies/{company_id}`
- `DELETE /admin/companies/{company_id}`

Owners:
- `POST /admin/owners` (assign to company, returns password once)
- `GET /admin/owners`
- `POST /admin/owners/{owner_id}/reset-password` (returns new password once)
- `DELETE /admin/owners/{owner_id}`

## Owner API
Company info:
- `GET /companies/{company_id}/info`

Employees:
- `POST /companies/{company_id}/users`
- `GET /companies/{company_id}/users`
- `PUT /companies/{company_id}/users/{user_id}`

Attendance:
- `GET /companies/{company_id}/attendance/days`

Events:
- `GET /companies/{company_id}/events`

## Hikvision webhook
Unchanged:

`POST /hooks/hikvision/{edge_key}/acs_events`

Map rule:
- If event has `employeeNoString="33"` and user with id **33** exists in this company, event is linked.

## Websocket
Recommended:
`ws://HOST/ws/company/{company_id}?token=<access_token>`

Legacy:
`ws://HOST/ws/company/{company_id}?api_key=<company_api_key>`