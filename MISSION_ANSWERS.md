# Day 14 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. **Secret ghi thẳng trong code** (`OPENAI_API_KEY`, `DATABASE_URL` có mật khẩu). Push lên GitHub là lộ key, và muốn đổi key phải sửa code rồi deploy lại.
2. **Log ra secret bằng `print()`** (`print(f"[DEBUG] Using key: {OPENAI_API_KEY}")`). Ai đọc được log là có key; `print()` cũng không có level nên log aggregator không lọc được.
3. **Không có health check** (`GET /health` trả 404). Platform không biết process còn sống hay đã treo để restart.
4. **Host và port cố định** (`host="localhost"`, `port=8000`). Trong container, `localhost` chỉ nhận kết nối nội bộ, còn Railway/Render cấp port qua biến `PORT`, nên app không nhận được traffic.
5. **`reload=True` và `DEBUG = True` cố định.** Reload tốn tài nguyên và không dùng cho production; config không đổi được theo môi trường.
6. **Không xử lý shutdown.** Khi platform gửi SIGTERM, request đang chạy bị cắt ngang và kết nối không được dọn dẹp.

### Exercise 1.2: Run basic version

```text
POST /ask?question=Hello -> 200 {"answer":"Đây là câu trả lời từ AI agent (mock). ..."}
GET  /health             -> 404 {"detail":"Not Found"}
```

Log của server in nguyên văn secret:

```text
[DEBUG] Got question: Hello
[DEBUG] Using key: sk-hardcoded-fake-key-never-do-this
```

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config | Hardcode trong `app.py` | Đọc env qua `config.py` (`PORT`, `AGENT_API_KEY`, `LLM_MODEL`…) | Đổi config theo môi trường mà không sửa code; secret không nằm trong git |
| Secret | Ghi thẳng và in ra log | Đọc từ env, log chỉ ghi `question_length`, `client_ip` | Tránh lộ key qua repo và log |
| Health check | Không có (`/health` → 404) | `GET /health` (liveness) và `GET /ready` (readiness) | Platform dùng để restart container hỏng và quyết định có route traffic hay không |
| Logging | `print()` | JSON qua `logging` | Log aggregator lọc và đếm được theo field |
| Shutdown | Đột ngột | `lifespan` đặt `is_ready = False` rồi dọn dẹp, có handler SIGTERM | Request đang xử lý được trả xong trước khi tắt |
| Host/Port | `localhost:8000` | `0.0.0.0` và `PORT` từ env | Chạy được trong container và trên cloud |
| Reload/Debug | Luôn bật | Chỉ bật khi `DEBUG=true` | Production không chạy chế độ dev |

Kết quả chạy bản production:

```text
GET  /health -> 200 {"status":"ok","uptime_seconds":2.6,"version":"1.0.0",...}
GET  /ready  -> 200 {"ready":true}
POST /ask    -> 200 {"question":"Hello","answer":"Tôi là AI agent được deploy lên cloud. ...","model":"gpt-4o-mini"}
```

Ví dụ chỗ đã sửa: secret ở dòng 17 bản develop được thay bằng `api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", ""))` trong `01-localhost-vs-production/production/config.py`.

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. Base image: `python:3.11`, bản Python đầy đủ (Debian kèm compiler và nhiều thư viện hệ thống).
2. Working directory: `/app`.
3. COPY requirements.txt trước: Docker cache theo từng layer. Requirements ít thay đổi nên layer `pip install` được dùng lại; khi chỉ sửa `app.py`, Docker chỉ build lại các layer phía sau, không cài lại dependencies.
4. CMD vs ENTRYPOINT: `CMD` là lệnh mặc định và bị thay thế khi truyền lệnh khác vào `docker run <image> <cmd>`. `ENTRYPOINT` là lệnh cố định, tham số của `docker run` được nối vào sau nó. Thường dùng `ENTRYPOINT` cho file thực thi và `CMD` cho tham số mặc định.

### Exercise 2.2: Build and run

```text
$ docker run -p 8000:8000 my-agent:develop
$ curl -X POST "http://localhost:8000/ask?question=What%20is%20Docker"
HTTP/1.1 200 OK
{"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
```

### Exercise 2.3: Image size comparison

- Develop: 1667.8 MB
- Production: 239.8 MB
- Difference: 85.6 %

Stage 1 (`builder`) cài `gcc`, `libpq-dev` và chạy `pip install --user`. Stage 2 (`runtime`) bắt đầu lại từ `python:3.11-slim`, chỉ copy package đã cài và source code, chạy bằng user non-root và có `HEALTHCHECK`. Image cuối nhỏ hơn vì không chứa compiler, apt cache và file build tạm, đồng thời base `slim` nhỏ hơn nhiều so với `python:3.11` đầy đủ.

### Exercise 2.4: Docker Compose stack

```text
Client ──HTTP──▶ nginx (limit_req 10r/s)
                    │  proxy_pass agent:8000
                    ▼
                 agent (FastAPI, uvicorn 2 workers)
                    │                    │
                    ▼                    ▼
              redis:6379           qdrant:6333
        (session, rate limit)      (vector DB cho RAG)
```

Compose start 4 service: `agent`, `redis`, `qdrant`, `nginx`. Tất cả nằm trong network bridge `internal` và gọi nhau bằng tên service; chỉ nginx mở port ra host. Agent chờ `redis` và `qdrant` healthy (`depends_on: condition: service_healthy`) rồi mới chạy.

```text
$ curl -i http://localhost:8088/health
HTTP/1.1 200 OK
Server: nginx
{"status":"ok","uptime_seconds":101.1,"version":"2.0.0",...}

$ curl -i -X POST http://localhost:8088/ask -H "Content-Type: application/json" -d '{"question":"Explain microservices"}'
HTTP/1.1 200 OK
Server: nginx
{"answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

Nginx được map ra port 8088 vì port 80 trên máy chạy lab đã có service khác dùng.

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- URL: https://agent-production-801fc1a9.up.railway.app
- Screenshot: [dashboard](screenshots/dashboard.png), [running](screenshots/running.png), [test](screenshots/test.png)

### Exercise 3.2: So sánh `railway.toml` và `render.yaml`

| Điểm | `railway.toml` | `render.yaml` |
|---|---|---|
| Định dạng | TOML, chỉ mô tả service hiện tại | YAML Blueprint, mô tả nhiều service trong một file |
| Build | `builder = "DOCKERFILE"` | `runtime: docker`, `rootDir`, `dockerfilePath` |
| Health check | `healthcheckPath = "/health"`, `healthcheckTimeout = 300` | `healthCheckPath: /health` |
| Restart | `restartPolicyType = "ON_FAILURE"`, tối đa 10 lần | Không khai báo, Render tự restart |
| Redis | Không khai báo; tạo Redis service riêng rồi gán `REDIS_URL` | Khai báo service `keyvalue`, lấy `REDIS_URL` bằng `fromService` |
| Secret | Đặt trong tab Variables | `sync: false`, Render hỏi giá trị khi tạo Blueprint |
| Region, plan | Chọn trên dashboard | `plan: free`, `region: singapore` |

Hai file khác nhau vì Railway cấu hình hạ tầng chủ yếu qua dashboard/CLI, nên `railway.toml` chỉ giữ phần build và deploy của một service. Render Blueprint là infrastructure-as-code, nên một file mô tả cả web service, Redis và cách nối biến môi trường giữa chúng.

### Exercise 3.3: Cloud Run CI/CD

1. Bước `test` dùng `python:3.11-slim` cài requirements và chạy `pytest`.
2. Bước `build` dùng `gcr.io/cloud-builders/docker` build image, gắn tag `$COMMIT_SHA` và `latest`, dùng `--cache-from` để tận dụng layer cache.
3. Bước `push` đẩy image lên Container Registry `gcr.io/$PROJECT_ID/ai-agent`.
4. Bước `deploy` chạy `gcloud run deploy` với image theo `$COMMIT_SHA`, region `asia-southeast1`, lấy `OPENAI_API_KEY` từ Secret Manager. Các bước chạy tuần tự nhờ `waitFor`.
5. Tài nguyên bị giới hạn bằng `--memory=512Mi --cpu=1 --max-instances=10` trong `cloudbuild.yaml` và `limits: cpu "1", memory 512Mi`, `containerConcurrency: 80`, `minScale: "1"` (tránh cold start) trong `service.yaml`. `livenessProbe` gọi `/health`, `startupProbe` gọi `/ready`.

## Part 4: API Security

### Exercise 4.1-4.3: Test results

**4.1 API key.** `verify_api_key` đọc header bằng `APIKeyHeader(name="X-API-Key", auto_error=False)` và so với `AGENT_API_KEY` từ env; hàm được gắn vào `/ask` bằng `Depends`. Thiếu header trả 401, sai key trả 403. Muốn rotate key thì đổi biến `AGENT_API_KEY` trên platform rồi redeploy; để không gián đoạn có thể chấp nhận tạm cả key cũ và key mới.

```text
POST /ask (không key)    -> 401 {"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
POST /ask (key sai)      -> 403 {"detail":"Invalid API key."}
POST /ask (key đúng)     -> 200 {"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock). ..."}
```

**4.2 JWT.** Client gửi `POST /auth/token` với username/password. Server kiểm tra trong `DEMO_USERS`, rồi tạo JWT ký HS256 chứa `sub`, `role`, `iat`, `exp` (hết hạn sau 60 phút). Các request sau gửi `Authorization: Bearer <token>`; `verify_token` kiểm chữ ký và hạn dùng mà không cần tra database.

**4.3 Rate limiting.** Thuật toán là sliding window: mỗi user có một `deque` timestamp, request cũ hơn 60 giây bị bỏ rồi đếm số còn lại. User thường được 10 request/phút, admin được 100 request/phút; `app.py` chọn limiter theo role trong JWT, nên admin dùng limiter riêng thay vì bị chặn ở mức 10.

Kết quả 20 request bằng token của `student` (token đã che):

```text
POST /ask (không token)  -> 401 {"detail":"Authentication required. Include: Authorization: Bearer <token>"}
POST /auth/token         -> 200 {"access_token":"<JWT>","token_type":"bearer",...}
POST /ask #1             -> 200 {... "usage":{"requests_remaining":9, ...}}
...
POST /ask #10            -> 200 {... "usage":{"requests_remaining":0, ...}}
POST /ask #11            -> 429 {"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":39}}
...
POST /ask #20            -> 429 {"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":20}}
GET  /me/usage           -> 200 {"user_id":"student","requests":10,...,"cost_usd":0.000184,"budget_usd":1.0,...}
```

401 nghĩa là chưa xác thực, còn 429 nghĩa là đã xác thực nhưng gọi quá nhanh. Request 11–20 bị chặn nên không được tính vào usage.

### Exercise 4.4: Cost guard implementation

`06-lab-complete/app/cost_guard.py` lưu chi phí trong Redis để mọi instance dùng chung:

- `check_budget()` chạy trước khi gọi LLM: đọc key `agent:cost:daily:<YYYY-MM-DD>`, nếu tổng đã `>= DAILY_BUDGET_USD` thì trả 402.
- `record_cost()` chạy sau khi gọi LLM: tính `(input_tokens × 0.00015 + output_tokens × 0.0006) / 1000`, cộng vào Redis bằng `INCRBYFLOAT`, đặt `EXPIRE` tới nửa đêm UTC để budget tự reset mỗi ngày.
- Redis lỗi thì trả 503 thay vì cho request đi qua mà không đếm chi phí.

Rate limit và cost guard không thay thế nhau: rate limit chặn số request mỗi phút, còn cost guard chặn tổng tiền. Một client gọi chậm nhưng mỗi câu tốn nhiều token vẫn có thể vượt budget mà không chạm rate limit.

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes

**5.1 Health checks.** `GET /health` là liveness: process còn sống thì trả 200, không phụ thuộc Redis, vì nếu Redis lỗi mà `/health` cũng lỗi thì platform sẽ restart agent liên tục mà không sửa được gì. `GET /ready` là readiness: trả 200 khi instance sẵn sàng nhận traffic (Redis kết nối được, không đang tắt), trả 503 thì load balancer bỏ instance khỏi pool.

```text
GET  /health -> 200 {"status":"degraded",...,"checks":{"memory":{"status":"degraded","used_percent":94.2}}}
GET  /ready  -> 200 {"ready":true,"in_flight_requests":1}
POST /ask?question=Hello -> 200 {"answer":"Tôi là AI agent được deploy lên cloud. ..."}
```

`/health` vẫn trả 200 dù báo `degraded` (RAM dùng 94.2 %), vì process vẫn đang chạy.

**5.2 Graceful shutdown.** Handler SIGTERM chỉ ghi log rồi để uvicorn xử lý: uvicorn ngừng nhận kết nối mới, chờ request đang chạy xong, chạy phần shutdown của `lifespan`, rồi thoát.

```text
$ docker stop k5-day14-scaling-agent-1
exit=0
INFO:     Waiting for application shutdown.
INFO:app:Instance instance-072d95 shutting down
INFO:     Application shutdown complete.
```

**5.3 Stateless design.** Session được lưu trong Redis (`session:<id>`, `SETEX` TTL 3600 s) thay vì dict trong RAM. Mỗi instance có RAM riêng, nên nếu lưu history trong RAM thì request rơi vào instance khác sẽ không thấy history, và instance restart sẽ mất dữ liệu.

**5.4–5.5 Load balancing và test stateless.** Chạy `docker compose up -d --scale agent=3` rồi `python test_stateless.py`:

```text
Request 1: [instance-072d95]
Request 2: [instance-4bbf73]
Request 3: [instance-7f7eab]
Request 4: [instance-072d95]
Request 5: [instance-4bbf73]
Instances used: {'instance-7f7eab', 'instance-072d95', 'instance-4bbf73'}
✅ All requests served despite different instances!
Total messages: 10
✅ Session history preserved across all instances via Redis!
```

Nginx chia request lần lượt cho 3 instance. Sau khi dừng `agent-1`, 4 request tiếp theo cùng `session_id` được 2 instance còn lại phục vụ và history tăng từ 10 lên 18 tin nhắn, nên state không phụ thuộc instance nào.

```text
served_by instance-4bbf73 storage redis
served_by instance-7f7eab storage redis
served_by instance-4bbf73 storage redis
served_by instance-7f7eab storage redis
messages 18
```

## Part 6: Final Project — output `check_production_ready.py`

```text
================================================================
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 43/43 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
================================================================
```

## AI log

| Việc | Công cụ AI | AI làm gì | Tôi kiểm tra thế nào |
|---|---|---|---|
| Part 6: code `06-lab-complete/` | Claude Code | Viết code theo các TODO và hợp đồng trong `06-lab-complete/README.md` | Chạy `python check_production_ready.py`; đọc lại luồng `/ask` (auth → rate limit → budget → LLM → record cost) |
| Part 1–5: chạy lệnh và ghi kết quả | Claude Code | Chạy các app mẫu, build image, chạy Compose, gom output | Đối chiếu output với code trong repo; số MB lấy từ `docker image inspect` |
| Part 7: đo benchmark, sửa `KNOWLEDGE_BASE` | Claude Code | Chạy `load_test.py`, `run_eval.py`, Locust; thêm mục còn thiếu vào `KNOWLEDGE_BASE`; điền `BENCHMARK_REPORT.md` | So từng số trong report với file JSON/CSV trong `reports/`, `benchmark-results/` |
| Sửa stack observability | Claude Code | Thêm `ENV PYTHONUSERBASE=/home/agent/.local` vào `benchmark-observability/production/Dockerfile` để agent non-root tìm thấy package; thêm `--no-deps` cho lệnh Locust để giữ đúng số instance | Kiểm tra `docker ps` và `sum(up{job="agent"})` trên Prometheus trước mỗi lần đo |
| Deploy Railway và chụp ảnh | Claude Code | Dùng Railway CLI tạo project, Redis, service `agent`, đặt biến môi trường, deploy; chụp 7 ảnh trong `screenshots/` | Gọi URL public kiểm tra 4 status code; xem lại từng ảnh |
| Soạn câu trả lời | Claude Code | Viết nháp câu trả lời Part 1–5 | Đọc lại và sửa theo hiểu biết của mình |
