# Day 14 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

File: `01-localhost-vs-production/develop/app.py`

1. **Secret ghi thẳng trong code** (dòng 17–18: `OPENAI_API_KEY`, `DATABASE_URL` có mật khẩu). Push lên GitHub là lộ key; muốn đổi key phải sửa code và deploy lại.
2. **Log ra secret và dùng `print()`** (dòng 33–38, có dòng `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")`). Khi chạy, log in nguyên văn `sk-hardcoded-fake-key-never-do-this`. Ai đọc được log là có key; `print()` cũng không có level, không parse được trong log aggregator.
3. **Không có health check.** Gọi `GET /health` trả `404`. Platform không biết process còn sống hay đã treo để restart.
4. **Port và host cố định** (`host="localhost"`, `port=8000`). Trong container, `localhost` chỉ nhận kết nối từ chính container; Railway/Render cấp port qua biến `PORT` nên app không nhận được traffic.
5. **Bật `reload=True` và `DEBUG = True` cố định.** Reload theo dõi file và tốn tài nguyên, không dùng cho production; config không đổi được theo môi trường.
6. **Không xử lý shutdown.** Khi platform gửi SIGTERM, request đang chạy có thể bị cắt ngang và không có bước dọn dẹp kết nối.

Kết quả chạy bản develop (`POST /ask?question=Hello`):

```text
[dev-ask#1] POST http://localhost:8000/ask?question=Hello -> 200 {"answer":"Đây là câu trả lời từ AI agent (mock). ..."}
[dev-health#1] GET http://localhost:8000/health -> 404 {"detail":"Not Found"}
```

Log server của bản develop:

```text
[DEBUG] Got question: Hello
[DEBUG] Using key: sk-hardcoded-fake-key-never-do-this
```

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config | Hardcode trong `app.py` | Đọc env qua `config.py` (`os.getenv("PORT")`, `AGENT_API_KEY`, `LLM_MODEL`…) | Đổi config theo môi trường mà không sửa code; secret không nằm trong git |
| Secret | Ghi thẳng và in ra log | Đọc từ env, log chỉ ghi `question_length`, `client_ip` | Tránh lộ key qua repo và log |
| Health check | Không có (`/health` → 404) | `GET /health` (liveness) và `GET /ready` (readiness) đều trả 200 | Platform dùng để restart container hỏng và quyết định route traffic |
| Logging | `print()` | JSON qua `logging` (`{"event": "agent_request", ...}`) | Log aggregator lọc và đếm được theo field |
| Shutdown | Đột ngột | `lifespan` đặt `is_ready = False` rồi dọn dẹp; có handler SIGTERM | Request đang xử lý được trả xong trước khi tắt |
| Host/Port | `localhost:8000` | `0.0.0.0` và `PORT` từ env | Chạy được trong container và trên cloud |
| Reload/Debug | Luôn bật | Chỉ bật khi `DEBUG=true` | Production không chạy chế độ dev |

Kết quả chạy bản production:

```text
[prod-health#1] GET http://localhost:8000/health -> 200 {"status":"ok","uptime_seconds":2.6,"version":"1.0.0","environment":"development",...}
[prod-ready#1] GET http://localhost:8000/ready -> 200 {"ready":true}
[prod-ask#1] POST http://localhost:8000/ask -> 200 {"question":"Hello","answer":"Tôi là AI agent được deploy lên cloud. ...","model":"gpt-4o-mini"}
```

Ví dụ chỗ đã sửa: secret ở dòng 17 bản develop được thay bằng `api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", ""))` trong `01-localhost-vs-production/production/config.py`.

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

File: `02-docker/develop/Dockerfile`

1. **Base image:** `python:3.11`, bản Python đầy đủ (Debian kèm compiler và nhiều thư viện hệ thống).
2. **Working directory:** `/app`.
3. **Vì sao COPY requirements.txt trước:** Docker cache theo từng layer. Requirements ít đổi nên layer `pip install` được dùng lại; khi chỉ sửa `app.py`, Docker chỉ build lại các layer sau lệnh `COPY app.py`, không cài lại dependencies.
4. **CMD vs ENTRYPOINT:** `CMD` là lệnh mặc định, bị thay thế khi truyền lệnh khác vào `docker run <image> <cmd>`. `ENTRYPOINT` là lệnh cố định của container; tham số truyền vào `docker run` được nối thêm vào sau nó. Thường dùng `ENTRYPOINT` cho file thực thi và `CMD` cho tham số mặc định.

Test container develop:

```text
$ docker run -p 8000:8000 my-agent:develop
$ curl -X POST "http://localhost:8000/ask?question=What%20is%20Docker"
HTTP/1.1 200 OK
{"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
```

### Exercise 2.3: Multi-stage build

- **Stage 1 (`builder`):** từ `python:3.11-slim`, cài `gcc`, `libpq-dev` và chạy `pip install --user` để có các package đã build.
- **Stage 2 (`runtime`):** image `python:3.11-slim` mới, chỉ copy `/root/.local` (package đã cài) và source code, tạo user `appuser` non-root, có `HEALTHCHECK`.
- **Vì sao nhỏ hơn:** image cuối không chứa compiler, apt cache, file build tạm; base `slim` cũng nhỏ hơn nhiều so với `python:3.11` đầy đủ.

### Exercise 2.3: Image size comparison

Đo bằng `docker image inspect my-agent:develop my-agent:advanced --format "{{.RepoTags}} {{.Size}}"`:

- Develop (`my-agent:develop`): 1667.8 MB (1 667 792 373 bytes)
- Production (`my-agent:advanced`): 239.8 MB (239 811 355 bytes)
- Difference: (1667.8 − 239.8) / 1667.8 × 100 ≈ **85.6%** nhỏ hơn

### Exercise 2.4: Docker Compose stack

```text
Client ──HTTP──▶ nginx (cổng 80 trong container)
                    │  proxy_pass http://agent_backend (agent:8000), limit_req 10r/s
                    ▼
                 agent (FastAPI, uvicorn 2 workers)
                    │                    │
                    ▼                    ▼
              redis:6379           qdrant:6333
        (session, rate limit)      (vector DB cho RAG)

Tất cả nằm trong network bridge `internal`; chỉ nginx mở port ra host.
```

Services được start: `agent`, `redis`, `qdrant`, `nginx`. Agent chờ `redis` và `qdrant` healthy (`depends_on: condition: service_healthy`) rồi mới chạy. Các service gọi nhau bằng tên service qua DNS nội bộ của Docker.

Máy chạy lab có port 80 đã bị một project khác dùng, nên nginx được map ra port 8088 bằng file override (`ports: !override ["8088:80"]`). Kết quả:

```text
agent running Up 5 minutes (healthy)
nginx running Up 7 seconds
qdrant running Up 6 minutes (healthy)
redis running Up 6 minutes (healthy)

$ curl -i http://localhost:8088/health
HTTP/1.1 200 OK
Server: nginx
{"status":"ok","uptime_seconds":101.1,"version":"2.0.0","timestamp":"2026-11-25T10:32:33.848841"}

$ curl -i -X POST http://localhost:8088/ask -H "Content-Type: application/json" -d '{"question":"Explain microservices"}'
HTTP/1.1 200 OK
Server: nginx
{"answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- URL: `https://agent-production-801fc1a9.up.railway.app`
- Screenshot: [dashboard](screenshots/dashboard.png), [running](screenshots/running.png), [test](screenshots/test.png)
- Chi tiết lệnh kiểm tra và biến môi trường: [DEPLOYMENT.md](DEPLOYMENT.md)

### Exercise 3.2: So sánh `railway.toml` và `render.yaml`

So sánh hai file trong `06-lab-complete/`:

| Điểm | `railway.toml` | `render.yaml` |
|---|---|---|
| Định dạng | TOML, chỉ mô tả service hiện tại | YAML Blueprint, mô tả nhiều service trong một file |
| Build | `[build] builder = "DOCKERFILE"` | `runtime: docker`, `rootDir: 06-lab-complete`, `dockerfilePath` |
| Health check | `healthcheckPath = "/health"`, `healthcheckTimeout = 300` | `healthCheckPath: /health` |
| Restart | `restartPolicyType = "ON_FAILURE"`, tối đa 10 lần | Render tự restart, không khai báo trong file |
| Redis | Không khai báo; tạo Redis service riêng trong project rồi gán `REDIS_URL` | Khai báo service `keyvalue` và lấy `REDIS_URL` bằng `fromService ... property: connectionString` |
| Secret | Đặt trong tab Variables của Railway | `sync: false`: Render hỏi giá trị khi tạo Blueprint, không lưu trong git |
| Region, plan | Chọn trên dashboard | Khai báo `plan: free`, `region: singapore` |

Lý do khác nhau: Railway cấu hình hạ tầng chủ yếu trên dashboard/CLI, file `railway.toml` chỉ giữ phần build và deploy của một service. Render Blueprint là infrastructure-as-code, nên một file mô tả cả web service, Redis và cách nối biến môi trường giữa chúng. Cả hai đều cấp biến `PORT`, nên Dockerfile dùng `--port ${PORT:-8000}`.

### Exercise 3.3: Cloud Run CI/CD

Đọc `03-cloud-deployment/production-cloud-run/cloudbuild.yaml` và `service.yaml`:

1. Cloud Build chạy pipeline khi có commit: bước `test` dùng `python:3.11-slim` cài requirements và chạy `pytest`.
2. Bước `build` dùng `gcr.io/cloud-builders/docker` build image, gắn tag `$COMMIT_SHA` và `latest`, dùng `--cache-from` image `latest` để tận dụng layer cache.
3. Bước `push` đẩy image lên Container Registry `gcr.io/$PROJECT_ID/ai-agent`.
4. Bước `deploy` chạy `gcloud run deploy` với image theo `$COMMIT_SHA`, region `asia-southeast1`, lấy `OPENAI_API_KEY` từ Secret Manager. Các bước chạy tuần tự nhờ `waitFor`.
5. Tài nguyên bị giới hạn ở `--memory=512Mi --cpu=1 --max-instances=10` trong `cloudbuild.yaml`, và trong `service.yaml` là `limits: cpu "1", memory 512Mi`, `containerConcurrency: 80`, `maxScale: "10"`, `minScale: "1"` để tránh cold start. `livenessProbe` gọi `/health`, `startupProbe` gọi `/ready`.

## Part 4: API Security

### Exercise 4.1: API key authentication

File: `04-api-gateway/develop/app.py`

- **Check ở đâu:** hàm `verify_api_key` (dùng `APIKeyHeader(name="X-API-Key", auto_error=False)`), gắn vào `/ask` bằng `Depends(verify_api_key)`. Key so với `AGENT_API_KEY` đọc từ env.
- **Sai key:** thiếu header trả `401`, có header nhưng sai trả `403`.
- **Rotate key:** đổi biến môi trường `AGENT_API_KEY` trên platform rồi restart/redeploy; code không đổi. Muốn rotate không downtime thì cho phép tạm thời 2 key (cũ và mới) rồi bỏ key cũ khi client đã chuyển.

Server chạy bằng `AGENT_API_KEY=secret-key-123 python app.py`:

```text
[no-key#1]    POST http://localhost:8000/ask -> 401 {"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
[wrong-key#1] POST http://localhost:8000/ask -> 403 {"detail":"Invalid API key."}
[good-key#1]  POST http://localhost:8000/ask -> 200 {"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock). ..."}
```

### Exercise 4.2: JWT authentication

File: `04-api-gateway/production/auth.py`. Client gửi `POST /auth/token` với username/password; server kiểm tra trong `DEMO_USERS`, tạo JWT ký HS256 chứa `sub`, `role`, `iat`, `exp` (hết hạn sau 60 phút). Các request sau gửi `Authorization: Bearer <token>`; `verify_token` kiểm chữ ký và hạn dùng mà không cần tra database. Thiếu token trả 401, token hết hạn trả 401, token sai chữ ký trả 403.

### Exercise 4.3: Rate limiting

- **Algorithm:** sliding window log. Mỗi user có một `deque` timestamp; request cũ hơn 60 giây bị bỏ khỏi đầu deque, rồi đếm số còn lại.
- **Limit:** user thường 10 request/phút (`rate_limiter_user`), admin 100 request/phút (`rate_limiter_admin`).
- **Bypass cho admin:** `app.py` chọn limiter theo role trong JWT (`limiter = rate_limiter_admin if role == "admin" else rate_limiter_user`). Đăng nhập bằng tài khoản role `admin` sẽ dùng limiter 100 req/phút.

Kết quả 20 request với token của `student` (token đã che):

```text
[no-token#1] POST /ask -> 401 {"detail":"Authentication required. Include: Authorization: Bearer <token>"}
[login#1]    POST /auth/token -> 200 {"access_token":"<JWT>","token_type":"bearer",...}
[ask#1]  POST /ask -> 200 {... "usage":{"requests_remaining":9, ...}}
...
[ask#10] POST /ask -> 200 {... "usage":{"requests_remaining":0, ...}}
[ask#11] POST /ask -> 429 {"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":39}}
...
[ask#20] POST /ask -> 429 {"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":20}}
[usage#1] GET /me/usage -> 200 {"user_id":"student","requests":10,"input_tokens":40,"output_tokens":296,"cost_usd":0.000184,"budget_usd":1.0,...}
```

`401` nghĩa là chưa xác thực; `429` nghĩa là đã xác thực nhưng gọi quá nhanh. Request 11–20 bị chặn và không được tính vào usage (vẫn 10 request).

### Exercise 4.4: Cost guard implementation

Bản mẫu `04-api-gateway/production/cost_guard.py` lưu usage trong RAM: mỗi user $1/ngày, toàn hệ thống $10/ngày, cảnh báo ở 80%. Vượt budget user trả `402`, vượt budget global trả `503`.

Bản trong `06-lab-complete/app/cost_guard.py` chuyển state sang Redis để nhiều instance dùng chung:

- `check_budget()` gọi trước LLM: đọc key `agent:cost:daily:<YYYY-MM-DD>`; tổng `>= DAILY_BUDGET_USD` thì trả `402`.
- `record_cost()` gọi sau LLM: tính `(input_tokens × 0.00015 + output_tokens × 0.0006) / 1000`, cộng vào Redis bằng `INCRBYFLOAT`, đặt `EXPIRE` tới nửa đêm UTC để budget tự reset mỗi ngày.
- Redis lỗi thì trả `503` thay vì cho request đi qua mà không đếm chi phí.

Rate limit và cost guard không thay thế nhau. Rate limit chặn tốc độ gọi (số request/phút). Cost guard chặn tổng tiền: một client gọi chậm nhưng mỗi câu tốn nhiều token vẫn có thể làm vượt budget mà không chạm rate limit.

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

`GET /health` là liveness: process còn sống không. Nó không phụ thuộc Redis, vì nếu Redis chết mà `/health` trả lỗi thì platform sẽ restart agent liên tục mà không sửa được gì. `GET /ready` là readiness: instance đã sẵn sàng nhận traffic chưa (Redis kết nối được, không đang tắt). Load balancer bỏ instance có `/ready` = 503 ra khỏi pool.

Chạy `05-scaling-reliability/develop`:

```text
[health#1] GET /health -> 200 {"status":"degraded","uptime_seconds":5.6,...,"checks":{"memory":{"status":"degraded","used_percent":94.2}}}
[ready#1]  GET /ready  -> 200 {"ready":true,"in_flight_requests":1}
[ask#1]    POST /ask?question=Hello -> 200 {"answer":"Tôi là AI agent được deploy lên cloud. ..."}
```

`/health` báo `degraded` vì RAM của máy chạy lab lúc đó dùng 94.2%, nhưng vẫn trả 200 do process còn chạy.

### Exercise 5.2: Graceful shutdown

Handler SIGTERM trong `develop/app.py` chỉ ghi log rồi để uvicorn xử lý: uvicorn ngừng nhận kết nối mới, chờ request đang chạy xong, chạy phần shutdown của `lifespan`, rồi thoát. Kiểm tra bằng `docker stop` một instance trong stack production:

```text
$ docker stop k5-day14-scaling-agent-1
exit=0
INFO:     Waiting for application shutdown.
INFO:app:Instance instance-072d95 shutting down
INFO:     Application shutdown complete.
INFO:     Finished server process [1]
```

### Exercise 5.3: Stateless design

`production/app.py` lưu session trong Redis (`session:<id>`, `SETEX` TTL 3600s) thay vì dict trong RAM. Khi chạy nhiều instance, mỗi instance có RAM riêng; nếu lưu history trong RAM thì request sau rơi vào instance khác sẽ mất history, và instance bị restart cũng mất hết dữ liệu.

### Exercise 5.4–5.5: Load balancing và test stateless

Lệnh: `docker compose -p k5-day14-scaling up -d --build --scale agent=3`, rồi `python test_stateless.py` (gọi `POST /chat` qua nginx port 8080).

```text
k5-day14-scaling-agent-1 running Up 22 seconds (healthy)
k5-day14-scaling-agent-2 running Up 21 seconds (healthy)
k5-day14-scaling-agent-3 running Up 21 seconds (healthy)
k5-day14-scaling-nginx-1 running Up 21 seconds
k5-day14-scaling-redis-1 running Up 33 seconds (healthy)

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

Nginx chia request lần lượt cho 3 instance. Sau đó dừng `agent-1` và gửi tiếp 4 request cùng `session_id`:

```text
served_by instance-4bbf73 storage redis
served_by instance-7f7eab storage redis
served_by instance-4bbf73 storage redis
served_by instance-7f7eab storage redis
### history
messages 18
```

Hai instance còn lại phục vụ tiếp, history tăng từ 10 lên 18 tin nhắn (thêm 4 cặp hỏi/đáp), nên state không phụ thuộc instance nào.

## Part 6: Final Project — output `check_production_ready.py`

```text
<DÁN_OUTPUT_CHECKER>
```

## AI log

| Việc | Công cụ AI | AI làm gì | Tôi kiểm tra thế nào |
|---|---|---|---|
| Part 6: code `06-lab-complete/app/`, `Dockerfile`, `docker-compose.yml`, `railway.toml`, `render.yaml`, `.env.example`, `.dockerignore` | Claude Code | Viết code theo các TODO và hợp đồng trong `06-lab-complete/README.md` | Chạy `python check_production_ready.py`; đọc lại từng file để giải thích được luồng `/ask` (auth → rate limit → budget → LLM → record cost) |
| Part 1–5: chạy lệnh và ghi kết quả | Claude Code | Chạy các app mẫu, build image, chạy Compose, gom output vào file này | Đối chiếu output với file nguồn trong repo; số MB lấy từ `docker image inspect` |
| Part 7: chạy `load_test.py`, `run_eval.py`, Locust, sửa `KNOWLEDGE_BASE` | Claude Code | Chạy lệnh đo trên máy local, thêm mục còn thiếu vào `KNOWLEDGE_BASE`, điền `BENCHMARK_REPORT.md` từ JSON/CSV | Mở từng file JSON/CSV trong `reports/`, `benchmark-results/` và so với số trong report |
| Sửa lỗi khi chạy stack observability | Claude Code | Đọc log agent crash (`No module named 'uvicorn'`), thêm `ENV PYTHONUSERBASE=/home/agent/.local` vào `benchmark-observability/production/Dockerfile`; phát hiện `docker compose run locust` tự đưa agent về 2 replica nên thêm `--no-deps` khi đo scaling | Kiểm tra `docker ps` trước và sau mỗi lần đo; số instance trong Prometheus (`sum(up{job="agent"})`) khớp 1 và 3 |
| Deploy Railway và chụp ảnh | Claude Code | Dùng Railway CLI tạo project, Redis, service `agent`, đặt biến môi trường (`AGENT_API_KEY` do Railway tự sinh bằng `${{secret(32)}}`), deploy bằng `railway up`, test 4 status code qua `railway run`; chụp 3 ảnh deploy và 4 ảnh observability | Mở URL public kiểm tra `/health`; xem lại từng ảnh trong `screenshots/` khớp với số trong `DEPLOYMENT.md` và `BENCHMARK_REPORT.md` |
| Soạn câu trả lời | Claude Code | Viết nháp câu trả lời Part 1–5 | Đọc lại, sửa theo hiểu biết của mình |
