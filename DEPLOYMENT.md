# Deployment Information

## Public URL

https://agent-production-801fc1a9.up.railway.app

## Platform

Railway, project `k5-day14-agent`, environment `production`, region US East. Service `agent` deploy bằng `railway up 06-lab-complete --path-as-root --service agent`, build từ `06-lab-complete/Dockerfile` theo `06-lab-complete/railway.toml` (healthcheck `/health`). Redis là service `Redis` trong cùng project, nối với agent qua mạng nội bộ `redis.railway.internal`.

## Environment Variables Set

Đặt trong tab Variables của Railway, không ghi giá trị vào git:

- `AGENT_API_KEY`: đặt bằng `${{secret(32)}}`, Railway tự sinh chuỗi ngẫu nhiên 32 ký tự; giá trị không xuất hiện trong repo hay terminal
- `REDIS_URL` = `${{Redis.REDIS_URL}}` (reference tới biến của Redis service)
- `ENVIRONMENT=production`
- `RATE_LIMIT_PER_MINUTE=10`
- `DAILY_BUDGET_USD=1.0`
- `PORT` do Railway tự cấp

## Test Commands

```bash
export BASE="https://agent-production-801fc1a9.up.railway.app"
export AGENT_API_KEY="<your-key>"   # chỉ đặt trong terminal, không lưu vào file

curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
```

Kết quả chạy ngày 25/11/2026 21:34 (GMT+7). Lệnh có key chạy qua `railway run --service agent`, nên `AGENT_API_KEY` được Railway đưa vào biến môi trường của lệnh và không in ra màn hình:

```text
GET  /health                 -> 200 {"status":"ok"}
GET  /ready                  -> 200 {"ready":true}
POST /ask (không X-API-Key)  -> 401 {"detail":"Invalid or missing API key"}
POST /ask (có X-API-Key)     -> 200 {"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock). ..."}
```

## Screenshots

- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
