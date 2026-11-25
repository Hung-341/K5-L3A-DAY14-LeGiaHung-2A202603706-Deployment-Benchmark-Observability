# Deployment Information

## Public URL

<PUBLIC_URL>

## Platform

Railway. Service agent build từ `06-lab-complete/Dockerfile` theo `06-lab-complete/railway.toml`, kèm một Redis service trong cùng project.

## Environment Variables Set

Đặt trong tab Variables của Railway, không ghi giá trị vào git:

- `AGENT_API_KEY` (secret)
- `REDIS_URL` (reference tới biến `REDIS_URL` của Redis service)
- `ENVIRONMENT=production`
- `RATE_LIMIT_PER_MINUTE=10`
- `DAILY_BUDGET_USD=1.0`
- `PORT` do Railway tự cấp

## Test Commands

```bash
export BASE="<PUBLIC_URL>"
export AGENT_API_KEY="<your-key>"   # chỉ đặt trong terminal, không lưu vào file

curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
```

Kết quả:

```text
<DÁN_4_STATUS_CODE>
```

## Screenshots

- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
