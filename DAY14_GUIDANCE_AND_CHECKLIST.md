# Day 14 — Hướng dẫn từng bước & Checklist

> Dành cho lab K5: Deployment, Benchmark & Observability. Làm từ trên xuống. Mỗi bước ghi rõ cần mở thư mục nào, chạy gì, và nhìn kết quả nào. Đề bài đầy đủ vẫn ở `CODE_LAB.md`; lưu ý riêng của K5 ở `README.md`.

## Bản đồ nhanh

Hãy tưởng tượng agent là một quầy phục vụ:

- **Part 1–5:** học cách dựng quầy chắc chắn, biết từ chối khách sai quyền và không quá tải.
- **Part 6:** tự dựng một quầy hoàn chỉnh. Script chấm như người kiểm tra checklist.
- **Part 3 / CP6:** đưa quầy lên Internet để người khác gọi được.
- **Part 7:** đo tốc độ/chất lượng và gắn đồng hồ, camera, chuông báo lỗi.
- **Cuối cùng:** nộp repo cùng ảnh và báo cáo chứng minh bạn đã tự chạy.

Đừng nhảy trước khi bước hiện tại có kết quả kiểm tra được. Nếu lệnh báo lỗi, lưu nguyên lỗi vào ghi chú; không đoán số liệu.

### Từ điển nhỏ

- **Agent:** chương trình nhận câu hỏi và trả lời.
- **Endpoint:** địa chỉ cụ thể trong app, ví dụ `/health`.
- **Container:** hộp riêng để chạy app. Docker tạo và quản lý hộp đó.
- **Redis:** nơi lưu dữ liệu dùng chung, để nhiều container cùng đọc được.
- **Benchmark:** bài đo có kiểm soát. **Concurrency** là số request chạy cùng lúc; **RPS** là số request mỗi giây.
- **p95 / p99:** thời gian mà 95% / 99% request hoàn tất trong mức đó. Giúp thấy các request chậm ở đuôi.
- **Trace:** nhật ký hành trình của một request qua các bước. **Span** là một bước trong hành trình.
- **Alert:** chuông báo khi hệ thống vượt ngưỡng đã đặt.

## Trước khi bắt đầu

1. Fork repo đề trên GitHub.
2. Đổi tên theo mẫu trong `SUBMISSION.md`.
3. Clone repo của bạn về máy.
4. Mở terminal ở repo vừa clone.
5. Mở `README.md`, tìm phần **Lưu ý khi làm bài (K5)**. Các lệnh trong file này đã tính theo những lưu ý đó.
6. Trên Windows, mở terminal **WSL2** để chạy Python. Dùng lệnh:
   ```bash
   python --version
   python -c "import os; print(os.name)"
   docker compose version
   docker run --rm hello-world
   ```
   Kết quả mong đợi: Python 3.11 trở lên, dòng Python thứ hai in `posix`, Docker in thông báo hello-world.
7. Nếu Python in `nt`, bạn đang chạy Python Windows. Mở WSL2 rồi thử lại. Nếu Docker chưa chạy, mở Docker Desktop và bật WSL2 integration.
8. Tạo hai file ghi bài ở gốc repo: `MISSION_ANSWERS.md` và `DEPLOYMENT.md`. Tạo `BENCHMARK_REPORT.md` ở bước CP7 từ template. Nếu cần xem cấu trúc mong đợi, mở `DAY14_DELIVERY_CHECKLIST.md`.

> Nếu quá 10 phút ở một checkpoint, ghi lại lỗi và hỏi Lab Coach. Tiếp tục phần sau nếu chưa bị phụ thuộc vào lỗi đó.

## CP1 — So sánh localhost với production

**Mục đích:** thấy vì sao “chạy được trên máy mình” chưa đủ để đưa app cho người khác dùng.

1. Mở `CODE_LAB.md`, tìm **Part 1**.
2. Mở đồng thời:
   - `01-localhost-vs-production/develop/app.py`
   - `01-localhost-vs-production/production/app.py`
3. Đọc Exercise 1.1–1.3. Tìm ít nhất 5 điểm nguy hiểm hoặc thiếu trong bản develop. Ví dụ: secret ghi thẳng trong code, thiếu health check, thiếu xử lý tắt an toàn.
4. Chạy hai bản theo lệnh trong Part 1. Dừng bản đầu bằng `Ctrl+C` trước khi chạy bản kế tiếp vì cả hai dùng port 8000.
5. Với bản develop, gửi câu hỏi bằng query string:
   ```bash
   curl -X POST "http://localhost:8000/ask?question=Hello"
   ```
   Không gửi JSON ở bước này; bản develop của bài không đọc kiểu payload đó.
6. Ghi vào `MISSION_ANSWERS.md`:
   - 5 anti-pattern, mỗi ý kèm lý do nó gây vấn đề.
   - Một bảng develop/production.
   - Một ví dụ chỉ rõ file hoặc dòng code đã sửa vấn đề.
7. **Xong khi:** có ít nhất 5 ý cụ thể và bạn giải thích được vì sao hardcoded secret nguy hiểm, health check để làm gì.

## CP2 — Docker

**Mục đích:** đóng gói app vào container để chạy giống nhau trên các máy khác nhau.

1. Trong `CODE_LAB.md`, mở **Part 2** và làm Exercise 2.1–2.4.
2. Khi có lệnh `docker build`, chạy từ **gốc repo**, không đổi vào thư mục `02-docker/`. Ví dụ:
   ```bash
   docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
   docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
   ```
3. Nếu Compose báo thiếu `.env.local`, tạo file rỗng đúng chỗ:
   ```bash
   touch 02-docker/production/.env.local
   ```
   Lệnh `touch` chạy trong WSL2. File rỗng đủ cho bài mock.
4. Chạy container/stack theo CODE_LAB. Gửi test request qua Nginx theo bài. Lưu lại output.
5. Đo image size, đừng chép số từ README:
   ```bash
   docker images my-agent
   ```
   Ghi dung lượng develop và production. Tính phần trăm giảm: `(develop - production) / develop × 100`.
6. Ghi 4 câu trả lời Exercise 2.1, số đo, sơ đồ service đơn giản và kết quả test vào `MISSION_ANSWERS.md`.
7. **Xong khi:** bạn nói được multi-stage Dockerfile bỏ phần build thừa ra sao và vì sao copy file requirements trước source giúp tận dụng cache.

## CP3 — API security

**Mục đích:** thử 3 cửa bảo vệ: ai được gọi, gọi nhanh đến đâu, và tiêu tối đa bao nhiêu.

1. Mở **Part 4** trong `CODE_LAB.md`.
2. Bản develop cần API key khi khởi động. Dừng server cũ, rồi chạy:
   ```bash
   cd 04-api-gateway/develop
   AGENT_API_KEY=secret-key-123 python app.py
   ```
3. Mở terminal thứ hai. Thử request không key rồi có key. Thêm `-i` để thấy status code:
   ```bash
   curl -i -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"Hello"}'
   curl -i -X POST http://localhost:8000/ask -H "X-API-Key: secret-key-123" -H "Content-Type: application/json" -d '{"question":"Hello"}'
   ```
   Không key phải bị từ chối; có key phải được xử lý.
4. Dừng develop bằng `Ctrl+C`. Chuyển sang production theo Exercise 4.2–4.3. Cấu hình production của bài dùng:
   - token endpoint: `POST /auth/token`
   - username: `student`
   - password: `demo123`
   
   Hướng dẫn gốc có vài URL/tài khoản không khớp với code mẫu; dùng các giá trị K5 này.
5. Trong terminal server, chuyển vào thư mục production, cài gói và bật app:
   ```bash
   cd ../production
   pip install -r requirements.txt
   python app.py
   ```
6. Mở terminal thứ hai. Lấy token; copy giá trị `access_token` từ JSON response:
   ```bash
   curl -i -X POST http://localhost:8000/auth/token -H "Content-Type: application/json" -d '{"username":"student","password":"demo123"}'
   ```
7. Dán token vào lệnh dưới, rồi gửi 20 request. Request thứ 11 trở đi sẽ bị giới hạn:
   ```bash
   TOKEN="paste_access_token_here"
   for i in $(seq 1 20); do
     curl -s -i -X POST http://localhost:8000/ask -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"question":"Hello"}'
   done
   ```
8. Khi số request vượt giới hạn, cần thấy `429`. `401` nghĩa là chưa có quyền; `429` nghĩa là gọi quá nhanh. Che token trước khi dán output vào bài.
9. Ghi output 401, 200, 429 và giải thích cost guard vào `MISSION_ANSWERS.md`. Rate limit chặn tốc độ; cost guard chặn hóa đơn vượt budget.
10. **Xong khi:** tự tạo được một request 429 và biết tại sao hai lớp bảo vệ trên không thay thế nhau.

## CP4 — Scaling và reliability

**Mục đích:** nhiều bản agent cùng phục vụ nhưng vẫn nhớ dữ liệu chung; tắt server không cắt ngang request.

1. Mở **Part 5** trong `CODE_LAB.md`. Chạy Exercise 5.1–5.5 theo thứ tự.
2. Khi tạo file env rỗng cho Compose:
   ```bash
   touch 05-scaling-reliability/production/.env.local
   ```
3. Bản production dùng port **8080** và endpoint **`POST /chat`**. Không dùng port 80 hay `/ask` ở bài này.
4. Chạy ba instance bằng tên Compose riêng:
   ```bash
   cd 05-scaling-reliability/production
   docker compose -p k5-day14-scaling up -d --build --scale agent=3
   docker compose -p k5-day14-scaling ps
   python test_stateless.py
   ```
   Chờ các service hiện trạng thái running/healthy rồi chạy script. Script gửi nhiều câu và kiểm tra lịch sử dùng chung.
5. Khi xong, dọn stack:
   ```bash
   docker compose -p k5-day14-scaling down
   ```
   Luôn dùng đúng `-p k5-day14-scaling` cho các lệnh của bài này. Nếu bỏ tên project, Docker có thể nhầm stack với bài khác.
6. Ghi kết quả và câu trả lời Part 5 vào `MISSION_ANSWERS.md`.
7. **Xong khi:** giải thích được `/health` là “process còn sống không?”, `/ready` là “đã sẵn sàng nhận việc chưa?”, và vì sao dữ liệu dùng chung cần nằm ngoài RAM của một instance.

## CP5 — Tự hoàn thiện agent production

**Đây là phần trọng điểm.** Làm trong `06-lab-complete/`; không copy code ra thư mục khác.

1. Mở `06-lab-complete/README.md`. Đọc bảng “Script chấm dựa vào những tiêu chí dưới đây”. Bảng đó là hợp đồng: script sẽ gọi đúng endpoint và kiểm status code đã nêu.
2. Mở file có TODO theo thứ tự gợi ý trong README:
   1. `app/main.py`: endpoint và luồng request.
   2. `app/config.py`: đọc config từ env.
   3. JSON log.
   4. `app/auth.py`: API key.
   5. `app/redis_client.py`: kết nối Redis và readiness.
   6. `app/rate_limiter.py`: giới hạn tốc độ.
   7. `app/cost_guard.py`: giới hạn chi phí.
   8. graceful shutdown.
   9. `Dockerfile`, `.dockerignore`.
   10. `docker-compose.yml`, `railway.toml` hoặc `render.yaml`, `.env.example`.
3. Sau một nhóm TODO, chạy kiểm tra tĩnh:
   ```bash
   cd 06-lab-complete
   python check_production_ready.py --static-only
   ```
   Dùng kết quả để biết mục nào còn thiếu. Không sửa file script chấm.
4. Khi static check tốt, cài dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Chạy stack local để kiểm tra Docker và Redis:
   ```bash
   cp .env.example .env
   docker compose up --build
   ```
   Mở terminal khác để gọi endpoint. Sau khi kiểm tra xong, quay lại terminal đang chạy Compose và nhấn `Ctrl+C` để dừng stack. Checker ở bước kế tiếp cần tự khởi động app/container, nên đừng để stack này giữ port 8000.
6. Chạy bài chấm đầy đủ:
   ```bash
   python check_production_ready.py
   ```
   Nếu có ❌ hoặc ⚠️, quay lại dòng tương ứng trong README, sửa rồi chạy lại. Chỉ qua CP6 khi kết quả là **`PASS 12/12`**.
7. Các status cần nhớ:
   - Redis chết nhưng process còn chạy: `GET /health` vẫn 200.
   - Redis chưa kết nối: `GET /ready` trả 503.
   - Thiếu/sai `X-API-Key`: 401.
   - Gọi vượt giới hạn: 429.
   - Vượt budget: 402.
8. Copy phần `📋 Checklist Deliverable` từ output checker vào `MISSION_ANSWERS.md`.
9. **Xong khi:** checker đầy đủ báo PASS 12/12 và code vẫn nằm trong đúng `06-lab-complete/`.

## CP6 — Deploy agent lên Internet

**Mục đích:** có một URL public để người khác kiểm tra agent của bạn.

1. Chọn Railway **hoặc** Render. K5 deploy chính agent trong `06-lab-complete/`, không deploy app mẫu ở `03-cloud-deployment/`.
2. Tạo Redis service trên cùng platform. Copy connection URL của Redis vào biến `REDIS_URL` trong settings của agent.
3. Tạo secret `AGENT_API_KEY` trực tiếp trong settings của platform. Không dán key vào code, report, screenshot hay git.
4. Deploy theo hướng dẫn trong `03-cloud-deployment/` và config bạn đã tạo (`railway.toml` hoặc `render.yaml`). Railway CLI cần Node.js. Chờ deploy hoàn tất.
5. Tạo `DEPLOYMENT.md` ở gốc repo. Ghi platform, public URL, tên các env đã đặt, và lệnh test; không ghi giá trị secret.
   Nếu chưa có thư mục ảnh, tạo một lần bằng `mkdir -p screenshots`.
6. Kiểm tra 4 trường hợp. Trong WSL2, thay URL và key bằng giá trị của bạn trong terminal (đừng commit biến shell hay ghi key ra file):
   ```bash
   export BASE="https://your-service.example"
   export AGENT_API_KEY="your-secret"
   curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
   curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
   curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
   curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
   ```
   Kết quả lần lượt: 200, 200, 401, 200. Nếu `/ready` lỗi, kiểm tra Redis URL trước.
7. Chụp ảnh dashboard deploy, service running, và kết quả test. Lưu vào `screenshots/`.
8. Trong `MISSION_ANSWERS.md`, ghi public URL và so sánh `06-lab-complete/railway.toml` với `06-lab-complete/render.yaml`. Để lấy điểm Cloud Run, mở `03-cloud-deployment/production-cloud-run/cloudbuild.yaml` và `service.yaml`, rồi viết 3–5 dòng: code được build ở đâu, image được lưu ở đâu, service deploy bằng gì, và cấu hình nào giới hạn tài nguyên.
9. **Xong khi:** người khác mở URL được, 4 status code đúng, ảnh nằm trong repo, không lộ key.

## CP7 — Đo benchmark local

**Mục đích:** biết agent nhanh đến đâu và trả lời đúng bao nhiêu. Con số phải do máy bạn đo; đừng lấy ví dụ trong README.

### A. Chuẩn bị

1. Từ gốc repo tạo báo cáo từ template (chạy một lần, không ghi đè file đã điền):
   ```bash
   cp -n 06-lab-complete/benchmark-observability/BENCHMARK_REPORT_TEMPLATE.md BENCHMARK_REPORT.md
   ```
2. Mở terminal 1, chạy v1:
   ```bash
   cd 06-lab-complete/benchmark-observability/develop
   pip install -r requirements.txt
   mkdir -p reports
   AGENT_VERSION=v1 PORT=8001 python app.py
   ```
3. Mở terminal 2. Chuyển terminal đó vào cùng thư mục rồi chạy v2:
   ```bash
   cd 06-lab-complete/benchmark-observability/develop
   AGENT_VERSION=v2 PORT=8002 python app.py
   ```
4. Mở terminal 3 và giữ nguyên thư mục `develop/` để chạy các phép đo.

### B. Đo tốc độ ở 4 mức tải

1. Trong terminal 3, chạy từng lệnh:
   ```bash
   python load_test.py --url http://localhost:8002 --requests 300 --concurrency 1 --out reports/load_v2_c1.json
   python load_test.py --url http://localhost:8002 --requests 300 --concurrency 10 --out reports/load_v2_c10.json
   python load_test.py --url http://localhost:8002 --requests 300 --concurrency 50 --out reports/load_v2_c50.json
   python load_test.py --url http://localhost:8002 --requests 300 --concurrency 100 --out reports/load_v2_c100.json
   ```
2. Mỗi lần lệnh chạy xong, report sẽ in RPS, p50, p95, p99, error rate và SLO. Exit code 1 nghĩa là SLO fail; file JSON vẫn được lưu.
3. Ghi các con số từ 4 JSON vào bảng 2.1 trong `BENCHMARK_REPORT.md`. Không tự làm tròn trước khi chép.

### C. Đo tác động của request chậm

1. Dừng v2 bằng `Ctrl+C` ở terminal 2.
2. Chạy lại v2 với từng mức `MOCK_SLOW_RATE`. Mỗi mức là một lần khởi động mới:
   ```bash
   MOCK_SLOW_RATE=0 AGENT_VERSION=v2 PORT=8002 python app.py
   ```
3. Trong terminal 3, đo rồi lưu kết quả:
   ```bash
   python load_test.py --url http://localhost:8002 --requests 300 --concurrency 20 --out reports/load_v2_slow_0.json
   ```
4. Dừng v2, rồi chạy từng mức sau. Với mỗi mức: khởi động lệnh ở terminal 2, chờ app chạy, chạy lệnh đo ở terminal 3, sau đó dừng app bằng `Ctrl+C` trước mức kế tiếp:
   - Terminal 2:
   ```bash
   MOCK_SLOW_RATE=0.03 AGENT_VERSION=v2 PORT=8002 python app.py
   ```
   - Terminal 3:
   ```bash
   python load_test.py --url http://localhost:8002 --requests 300 --concurrency 20 --out reports/load_v2_slow_0.03.json
   ```
   Dừng v2 bằng `Ctrl+C`, rồi lặp lại với mức 0.1:
   - Terminal 2:
   ```bash
   MOCK_SLOW_RATE=0.1 AGENT_VERSION=v2 PORT=8002 python app.py
   ```
   - Terminal 3:
   ```bash
   python load_test.py --url http://localhost:8002 --requests 300 --concurrency 20 --out reports/load_v2_slow_0.1.json
   ```
   Sau lệnh cuối, quay lại terminal 2 và nhấn `Ctrl+C` để dừng v2 trước khi qua phần D.
5. Ghi avg, p95, p99 vào bảng 2.2. Giải thích vì sao một ít request rất chậm có thể làm p99 tăng mạnh dù average nhìn vẫn ổn.

### D. So sánh chất lượng v1/v2 và sửa knowledge base

1. Sau CP7-C, v2 đã dừng. Bật lại v2 ở terminal 2 với config mặc định:
   ```bash
   AGENT_VERSION=v2 PORT=8002 python app.py
   ```
2. Dùng terminal 3:
   ```bash
   python eval/run_eval.py --url http://localhost:8001 --out reports/eval_v1.json
   python eval/run_eval.py --url http://localhost:8002 --out reports/eval_v2.json
   ```
3. Mở report eval để thấy câu nào sai và keyword nào bị thiếu.
4. Mở `utils/mock_llm.py`; chỉ thêm/sửa mục tương ứng trong `KNOWLEDGE_BASE`. Không sửa `eval/golden_dataset.jsonl`.
5. Dừng v2 bằng `Ctrl+C`, rồi bật lại để app nạp code mới:
   ```bash
   AGENT_VERSION=v2 PORT=8002 python app.py
   ```
6. Chạy quality gate cuối:
   ```bash
   python eval/run_eval.py --url http://localhost:8002 --min-accuracy 1.0 --baseline reports/eval_v2.json --out reports/eval_v2_fixed.json
   ```
7. Mong đợi thấy `Quality gate ... PASS` và accuracy 100%. Nếu FAIL, đọc câu sai trong report, sửa knowledge base, restart v2 và chạy lại.
8. Điền các bảng trong `BENCHMARK_REPORT.md` từ JSON thật. Thêm nhận xét trade-off chất lượng, cost, latency. Ghi cách CI dùng exit code của eval để chặn merge nếu quality giảm.
9. **Xong khi:** có 7 load JSON, 3 eval JSON trong `develop/reports/` và quality gate cuối PASS.

## CP8 — Grafana, Jaeger và alert (sau giờ lab)

**Mục đích:** tạo tải thật lên stack local, nhìn biểu đồ, lần theo một request, và xem chuông báo lỗi.

### A. Bật stack và tạo tải

1. Mở terminal trong `06-lab-complete/benchmark-observability/production/`.
2. Bật một agent cùng các dịch vụ quan sát:
   ```bash
   docker compose -p k5-day14-observability up -d --build --scale agent=1
   docker compose -p k5-day14-observability ps
   ```
3. Chờ service chạy. Mở:
   - Grafana: http://localhost:3000 (user `admin`, password `admin`)
   - Prometheus: http://localhost:9090
   - Jaeger: http://localhost:16686
   - Locust: http://localhost:8089
4. Tạo tải và lưu CSV:
   ```bash
   docker compose -p k5-day14-observability run --rm locust -f /mnt/locust/locustfile.py --host http://nginx --headless -u 100 -r 10 -t 2m --csv /mnt/results/scale_1
   ```
5. Chụp dashboard Grafana khi biểu đồ đã có dữ liệu. Lưu thành `screenshots/grafana-dashboard.png`.

### B. So sánh 1 agent với 3 agent

1. Scale stack lên 3:
   ```bash
   docker compose -p k5-day14-observability up -d --scale agent=3
   ```
2. Đợi khoảng 15 giây để Prometheus/Nginx nhận instance mới.
3. Chạy đúng cùng bài Locust:
   ```bash
   docker compose -p k5-day14-observability run --rm locust -f /mnt/locust/locustfile.py --host http://nginx --headless -u 100 -r 10 -t 2m --csv /mnt/results/scale_3
   ```
4. Ghi RPS, latency và failures từ CSV. Chụp ảnh so sánh nếu cần. Sau này copy hai file `scale_1_stats.csv`, `scale_3_stats.csv` ra thư mục `benchmark-results/` ở gốc repo.

### C. Tìm trace chậm và trace lỗi

1. Gọi agent vài lần (hoặc chạy Locust) để tạo request.
2. Mở Jaeger, chọn service `observable-agent`, bấm **Find Traces**.
3. Trace chậm: sắp xếp **Longest First**, mở trace đầu tiên, tìm span mất nhiều ms nhất. Chụp ảnh thành `screenshots/jaeger-slow-trace.png`.
4. Trace lỗi: lọc tag `error=true`, mở trace có exception. Chụp ảnh thành `screenshots/jaeger-error-trace.png`.
5. Tìm cùng `trace_id` trong log:
   ```bash
   docker compose -p k5-day14-observability logs agent
   ```
   Chép dòng JSON có cùng ID vào phần “Debug bằng trace” trong report.
6. **Dấu hiệu đúng:** trace và dòng log có cùng `trace_id`; report nêu span chậm nhất và thời gian của nó.

### D. Làm cho ít nhất hai alert kêu

1. Mở `06-lab-complete/benchmark-observability/production/.env.example`, xem tên các biến. Tạo file cấu hình local:
   ```bash
   cp .env.example .env
   ```
2. Với mỗi thí nghiệm A–E trong phần 2.6 của `06-lab-complete/benchmark-observability/README.md`:
   - đổi đúng biến trong `.env`;
   - ghi giờ bắt đầu;
   - áp dụng lại config bằng `docker compose -p k5-day14-observability up -d`;
   - giữ tải Locust chạy;
   - chờ trạng thái alert thành **firing** trong Prometheus;
   - ghi giờ alert firing và chụp ảnh nếu cần;
   - trả biến về mặc định trước thí nghiệm kế tiếp.
3. Thử đúng các giá trị mẫu: A đặt `MOCK_ERROR_RATE=0.2`; B đặt `MOCK_SLOW_RATE=0.3`; C đặt `LLM_MODEL=mock-llm-large`; D tìm tên container bằng `docker compose -p k5-day14-observability ps`, rồi chạy `docker pause <tên-container>`; E đặt `AGENT_VERSION=v1`. Sau thí nghiệm D, chạy `docker unpause <tên-container>`. Trước mỗi bài tiếp theo, khôi phục các biến đã đổi về giá trị ban đầu trong `.env` và chạy lại Compose.
4. Cần ít nhất **2 alert cùng firing** trong ảnh cuối. Chụp trang Alerts của Prometheus thành `screenshots/prometheus-alert-firing.png`.
5. Ghi vào report alert nào kêu và mất bao lâu. Bài E có thể không làm alert hạ tầng kêu: câu trả lời sai cần eval quality phát hiện.
6. **Xong khi:** đủ 4 ảnh Grafana/Jaeger/Prometheus và report có trace ID, alert name, alert timing.

### E. Dọn dịch vụ

Chỉ dọn sau khi đã chụp ảnh và lấy log:
```bash
docker compose -p k5-day14-observability down -v
```
Lệnh có `-v` xoá cả volume dữ liệu local của stack; các report CSV đã mount ra thư mục vẫn cần kiểm tra còn nguyên.

## Đóng gói bài nộp

1. Tạo các thư mục ở gốc repo:
   ```bash
   mkdir -p reports benchmark-results screenshots
   ```
2. Copy kết quả benchmark vào nơi người chấm mong đợi:
   ```bash
   cp -r 06-lab-complete/benchmark-observability/develop/reports/. reports/
   cp -r 06-lab-complete/benchmark-observability/production/benchmark-results/. benchmark-results/
   ```
3. Kiểm tra có đủ:
   - `MISSION_ANSWERS.md`
   - `DEPLOYMENT.md`
   - `BENCHMARK_REPORT.md`
   - `reports/`: 4 concurrency JSON, 3 slow-rate JSON, 3 eval JSON.
   - `benchmark-results/`: `scale_1_stats.csv`, `scale_3_stats.csv`.
   - `screenshots/`: 3 ảnh deploy (dashboard, running, test) và 4 ảnh observability (Grafana, trace chậm, trace lỗi, Prometheus alerts).
   - `06-lab-complete/`: code cuối đạt PASS 12/12.
4. Mở `BENCHMARK_REPORT.md` lần cuối. So từng số với JSON/CSV tương ứng. Đừng chép số ví dụ trong tài liệu.
5. Tìm secret trước khi commit:
   ```bash
   git status --short
   git log --all --oneline -- '*.env' '.env'
   ```
   Không commit `.env`, API key, token deploy. Nếu đã commit secret, phải thu hồi key và báo Lab Coach; xoá file không xoá secret khỏi lịch sử.
6. Kiểm tra repo public và mở URL bằng cửa sổ ẩn danh. Commit trước deadline rồi nộp **link repo** lên LMS.

### Checklist cuối

- [ ] Part 1–5 có câu trả lời và bằng chứng trong `MISSION_ANSWERS.md`.
- [ ] Checker Part 6 báo `PASS 12/12`.
- [ ] `DEPLOYMENT.md` có URL đang chạy; 4 status code đúng.
- [ ] Report có số đo thật; các JSON/CSV nguồn đã copy ra thư mục gốc.
- [ ] Có 3 ảnh deploy + 4 ảnh observability.
- [ ] Không có `.env`, API key hay token trong file hoặc lịch sử commit.
- [ ] Repo public, commit trước deadline, link đã nộp trên LMS.

## Học cách dùng agent đúng (Harness)

Harness là bộ biển chỉ đường và bài kiểm tra quanh agent. Khi agent làm sai, đừng chỉ nhắc lại bằng prompt:

1. Hỏi “agent thiếu thông tin hay công cụ nào?”
2. Ghi chỉ dẫn vào đúng README/checkpoint để lần sau agent đọc thấy.
3. Nếu lỗi có thể kiểm tra bằng máy, thêm script/test/CI thay vì chỉ viết rule bằng lời.
4. Giữ tiêu chí rõ: ví dụ status code phải là 401 hoặc checker phải PASS 12/12.
5. Người vẫn review các quyết định ảnh hưởng security, dữ liệu và chất lượng. Benchmark phải lấy từ máy chạy thật.

## Nếu bị kẹt

- Cổng 8000 đang bận: tìm terminal/server cũ và nhấn `Ctrl+C`; nếu là container, dừng stack bằng đúng `docker compose -p <tên-project> down`.
- Request Part 1/2 bị 422: dùng query `?question=Hello`, không gửi JSON cho app develop.
- Compose chạy nhầm bài: dùng project name cố định `-p k5-day14-scaling` hoặc `-p k5-day14-observability` xuyên suốt bài đó.
- Checker báo graceful shutdown fail trên Windows: chạy Python từ WSL2; xác nhận `os.name` là `posix`.
- Eval dùng nhầm agent: truyền `--url http://localhost:8001` cho v1, `--url http://localhost:8002` cho v2.
- Eval/load report không được lưu: thêm `--out reports/<ten-file>.json`.
- Screenshot thiếu trace/alert: tạo request và giữ Locust chạy; chờ dữ liệu/alert trước khi chụp.
- Đừng sửa checker hoặc golden dataset. Xem `TROUBLESHOOTING.md`, rồi hỏi Lab Coach nếu vẫn kẹt.

## Tài liệu gốc cần mở

- `README.md`: lưu ý K5 và cách bắt đầu.
- `CODE_LAB.md`: câu hỏi và bài tập từng Part.
- `CHECKPOINTS.md`: thời lượng và deliverable từng checkpoint.
- `06-lab-complete/README.md`: hợp đồng Part 6 và cách chạy checker.
- `06-lab-complete/benchmark-observability/README.md`: hướng dẫn Grafana/Jaeger/Locust.
- `SUBMISSION.md`, `RUBRIC.md`, `RULES.md`: nộp bài, điểm và quy định.
- Ghi chú workshop Harness Engineering: `../../vault/Vin20/Sessions/Day 14 harness engineering workshop.md`.

