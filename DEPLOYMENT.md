# Deployment Information

## Public URL
https://agent-production-801fc1a9.up.railway.app

## Platform
Railway (service `agent` build từ `06-lab-complete/Dockerfile` theo `06-lab-complete/railway.toml`, kèm service `Redis` trong cùng project)

## Test Commands

### Health Check
```bash
curl https://agent-production-801fc1a9.up.railway.app/health
# Expected: {"status": "ok"}

curl https://agent-production-801fc1a9.up.railway.app/ready
# Expected: {"ready": true}
```

### API Test (with authentication)
```bash
# Không có key → 401
curl -X POST https://agent-production-801fc1a9.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'

# Có key → 200
curl -X POST https://agent-production-801fc1a9.up.railway.app/ask \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```

Kết quả (25/11/2026):

```text
GET  /health                 -> 200 {"status":"ok"}
GET  /ready                  -> 200 {"ready":true}
POST /ask (không X-API-Key)  -> 401 {"detail":"Invalid or missing API key"}
POST /ask (có X-API-Key)     -> 200 {"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock). ..."}
```

## Environment Variables Set
- PORT (Railway tự cấp)
- REDIS_URL (reference `${{Redis.REDIS_URL}}`)
- AGENT_API_KEY (Railway sinh ngẫu nhiên bằng `${{secret(32)}}`)
- ENVIRONMENT=production
- RATE_LIMIT_PER_MINUTE=10
- DAILY_BUDGET_USD=1.0

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
