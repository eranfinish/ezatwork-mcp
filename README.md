# EZ@Work MCP Server

Connect [EZ@Work](https://www.ezatwork.com) — all-in-one business management
for freelancers, lawyers, agencies, and service businesses — to Claude, Gemini,
Cursor, and any MCP-compatible AI.

## Tools (v1)

| Tool | Description | Type |
|------|-------------|------|
| `list_clients` | List your clients/customers | Read |
| `list_projects` | List your projects/cases/work orders | Read |
| `log_time_entry` | Log billable hours to a project | Write |
| `create_invoice` | Create a draft invoice (auto currency/language/VAT) | Write |

## Setup

1. Create a free EZ@Work account at https://app.ezatwork.com
2. Generate an API token at https://app.ezatwork.com/settings/api-tokens
3. Add this connector to your AI client (see below)

### Claude Desktop / Claude.ai
Settings → Connectors → Add custom connector
- URL: `https://mcp.ezat.work/mcp`
- Authorization: `Bearer ezw_pat_...`

### MCP Inspector (local testing)
```bash
npx @modelcontextprotocol/inspector
```
Connect to `http://localhost:8080/mcp` with header `Authorization: Bearer ezw_pat_...`

## Security

- Your data stays in your EZ@Work account
- API tokens use scoped permissions — grant only what you need
- All tokens have mandatory expiration
- Authorization is verified on every request; invalid tokens are rejected immediately

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
docker run -p 8080:8080 -e EZ_API_BASE=https://api.ezat.work ezatwork-mcp
```

### Deploy to Cloud Run

```bash
gcloud run deploy ezatwork-mcp \
  --source . \
  --region europe-west1 \
  --project ezatwork-production \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars "EZ_API_BASE=https://api.ezat.work"
```

> `--allow-unauthenticated` is correct here — auth is enforced at the API token level,
> not at the Cloud Run level. Every MCP request must carry a valid `Bearer ezw_pat_...` token.

### Technical notes

- **Transport:** Streamable HTTP (`/mcp` endpoint)
- **Library:** `fastmcp>=2.0.0` — `get_http_headers()` from `fastmcp.server.dependencies`
- **Auth:** Per-request Bearer token extraction via `get_http_headers()`
- **Backend:** `GET /api/users/me` for locale (currency/language/businessMode)
- **Time entries:** `POST /api/timeentry` with `isBillable` field
- **Invoices:** `POST /api/invoices` with computed `dueDate` and `total` per item

---

## Built by

[EZ@Work](https://www.ezatwork.com) — the business OS for independents.
