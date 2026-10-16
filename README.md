# EZ@Work MCP Server

Connect [EZ@Work](https://www.ezatwork.com) — all-in-one business management
for freelancers, lawyers, agencies, and service businesses — to Claude, Gemini,
Cursor, and any MCP-compatible AI.

## Tools

| Tool | Description | Type |
|------|-------------|------|
| `list_clients` | List your clients/customers — id, name, company, status, email (+ default rate). Optional `status`, `search`, `limit` (default 50, max 200) | Read |
| `list_projects` | List your projects/cases/work orders — id, name, status, client. Optional `status`, `search`, `limit` | Read |
| `create_client` | Create a client; refuses a likely duplicate (same email, or same name when no email) unless `allow_duplicate=true` | Write |
| `log_time_entry` | Log billable hours to a project (0 < hours <= 24) | Write |
| `create_invoice` | Create a draft invoice, 1-50 line items (auto currency/language/VAT) | Write |

Write tools change data in your EZ@Work account. Their descriptions tell the AI
to confirm the exact values with you before calling them, and every tool
validates its arguments before anything reaches the EZ@Work API — a bad value
comes back as `{"error": "invalid_input", ...}`, a backend failure as a short
`{"error": ..., "status": ..., "message": ...}` (plan limits pass through as
`PLAN_LIMIT_REACHED`).

List tools return only the fields an assistant needs to pick a record — no
notes, phone numbers, VAT numbers, addresses or contacts — and mark record text
as user-entered data rather than instructions.

## Setup

### Claude Desktop / Claude.ai (OAuth — recommended)

Settings → Connectors → Add custom connector
- URL: `https://mcp.ezatwork.com/mcp`
- Authentication: OAuth (automatic)

### Claude Code / Cursor / MCP Inspector (API token)

1. Create a free EZ@Work account at https://app.ezatwork.com
2. Generate an API token at https://app.ezatwork.com/settings/api-tokens with the scopes
   `clients:read`, `clients:write`, `projects:read`, `time:write`, `invoices:write`
3. Connect to `https://mcp.ezatwork.com/mcp` with header `Authorization: Bearer ezw_pat_...`

**Local testing with MCP Inspector:**
```bash
npx @modelcontextprotocol/inspector
```
Connect to `http://localhost:8080/mcp` with header `Authorization: Bearer ezw_pat_...`

## Security

- Your data stays in your EZ@Work account
- OAuth mode: Google identity → EZ@Work account lookup; no credentials stored in the MCP
- API token mode: tokens have a mandatory expiration. Token scopes are being enforced
  server-side (a backend change is in progress), so don't rely on scopes alone to limit
  a token yet. Create tokens with only the scopes this server uses:
  `clients:read`, `clients:write`, `projects:read`, `time:write`, `invoices:write`
- Authorization is verified on every request

## Privacy Policy

https://www.ezatwork.com/privacy

## Universal Design

EZ@Work adapts to your business type: a lawyer sees "cases," a freelancer sees
"projects," a service business sees "work orders." Currency, language (24 supported),
and tax rules auto-detect from your profile — no configuration needed in the MCP.

---

## Development

### Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .

cp .env.example .env
# Edit .env: EZ_API_BASE=http://localhost:5000 for local backend

python -m ezatwork_mcp.server
# Server starts at http://localhost:8080/mcp
```

### Run tests

```bash
pip install pytest pytest-asyncio
pytest tests/
```

### Docker

```bash
docker build -t ezatwork-mcp .
docker run -p 8080:8080 -e EZ_API_BASE=https://api.ezatwork.com ezatwork-mcp
```

### Deploy to Cloud Run

```bash
gcloud run deploy ezatwork-mcp \
  --source . \
  --region europe-west1 \
  --project ezatwork-production \
  --allow-unauthenticated \
  --port 8080 \
  --update-env-vars "EZ_API_BASE=https://api.ezatwork.com,MCP_BASE_URL=https://mcp.ezatwork.com" \
  --update-secrets "GOOGLE_CLIENT_ID=ezmcp-google-client-id:latest" \
  --update-secrets "GOOGLE_CLIENT_SECRET=ezmcp-google-client-secret:latest" \
  --update-secrets "EZ_MCP_MASTER_TOKEN=ezmcp-master-token:latest"
```

> `--allow-unauthenticated` is correct — auth is enforced at the MCP layer (OAuth or API token),
> not at the Cloud Run IAM level.

### Technical notes

- **Transport:** Streamable HTTP (`/mcp` endpoint)
- **Library:** `fastmcp 3.x` (pinned `<4`)
- **Auth (OAuth):** `GoogleProvider` from `fastmcp.server.auth.providers.google`
- **OAuth redirect allowlist:** clients may only register Claude's callbacks and loopback URIs;
  set `MCP_ALLOWED_REDIRECT_URIS` (comma-separated patterns) to admit other clients
- **Auth (token):** `get_http_headers()` from `fastmcp.server.dependencies`
- **Dual-auth:** OAuth active when `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` + `MCP_BASE_URL` are set
- **Backend:** `GET /api/users/me` for locale; `GET /api/internal/users/by-email` for OAuth→user mapping
- **Lists:** `GET /api/clients` and `GET /api/projects` take no filters; status, search and
  limit are applied in the MCP server, which trims each record before returning it
- **Time entries:** `POST /api/timeentry` with `isBillable` field
- **Invoices:** `POST /api/invoices` with computed `dueDate` and `total` per item

---

## Built by

[EZ@Work](https://www.ezatwork.com) — the business OS for independents.
