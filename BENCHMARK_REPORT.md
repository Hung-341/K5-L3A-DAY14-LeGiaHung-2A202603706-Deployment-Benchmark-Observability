# Benchmark & Observability Report — Day 14

**Họ tên:** Le Gia Hung (2A202603706)
**Ngày chạy:** 25/11/2026
**Môi trường:** Laptop Windows 11 Pro, Intel Core i7-9750H (6 nhân / 12 luồng), RAM 15.8 GB; Python 3.11.9; Docker Desktop 29.9.3 (WSL2, VM 12 CPU / 5.8 GB RAM). Agent develop chạy bằng Python Windows, một process uvicorn; `load_test.py` chạy trên cùng máy.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | < 500 ms | Mock LLM mất khoảng 200 ms mỗi câu khi không tải. 500 ms chừa chỗ cho hàng đợi ở tải vừa, và người dùng chat vẫn thấy phản hồi nhanh. Đây cũng là ngưỡng mặc định của `load_test.py`. |
| Error rate `/ask` | < 2 % | Mock LLM tự sinh khoảng 1 % lỗi upstream (`MOCK_ERROR_RATE=0.01`). Ngưỡng 2 % cho phép mức lỗi nền đó nhưng bắt được khi lỗi tăng gấp đôi. |
| Accuracy trên golden dataset | ≥ 100 % (23/23) | Golden dataset nhỏ, mỗi câu là kiến thức bắt buộc của agent. Sai một câu là regression cần sửa trước khi deploy; quality gate cuối chạy với `--min-accuracy 1.0`. |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

Mỗi mức 300 request, `MOCK_SLOW_RATE=0.03` (mặc định). Nguồn: `reports/load_v2_c{1,10,50,100}.json`.

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.31 | 201.3 | 234.1 | 1704.6 | 1.33 % (4 × 503) | PASS |
| 10 | 43.41 | 198.0 | 245.0 | 1685.8 | 1.33 % (4 × 503) | PASS |
| 50 | 83.14 | 218.7 | 864.8 | 1755.0 | 1.33 % (4 × 503) | FAIL (p95) |
| 100 | 37.7 | 1179.0 | 5734.5 | 5956.2 | 1.67 % (5 × 503) | FAIL (p95) |

**Nhận xét:** RPS tăng gần tuyến tính từ concurrency 1 lên 10 (4.31 → 43.41, gấp khoảng 10 lần) vì p50 vẫn giữ quanh 200 ms: mỗi request chủ yếu chờ `asyncio.sleep` của mock LLM, nên một process async xử lý song song được. Từ 10 lên 50, RPS chỉ tăng gấp 1.9 lần (83.14) thay vì gấp 5, và p95 vượt SLO (864.8 ms). Đến 100, RPS giảm còn 37.7 và p50 lên 1179 ms. Agent chỉ có một process uvicorn, còn load generator chạy cùng máy, nên CPU bị chia cho cả hai; khi vượt khả năng xử lý, request phải xếp hàng, thời gian chờ cộng vào latency và throughput giảm. Mức chịu tải an toàn với SLO p95 < 500 ms trên máy này nằm giữa 10 và 50 concurrency. Lỗi 503 ở cả 4 mức là lỗi upstream giả lập của mock LLM, không phải do quá tải.

### 2.2 Tail latency

Mỗi mức 300 request, concurrency 20, agent v2 khởi động lại với từng `MOCK_SLOW_RATE`. Nguồn: `reports/load_v2_slow_{0,0.03,0.1}.json`.

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 210.7 | 471.1 | 513.6 |
| 0.03 (mặc định) | 264.2 | 518.4 | 1711.9 |
| 0.1 | 373.9 | 1700.3 | 1741.2 |

**Nhận xét:** p99 nhạy nhất. Với 3 % request chậm, avg chỉ tăng 25 % (210.7 → 264.2 ms) nhưng p99 tăng hơn 3 lần (513.6 → 1711.9 ms), vì 3 % request chậm (thêm khoảng 1500 ms) nằm đúng trong 1 % đuôi. Khi tỉ lệ chậm lên 10 %, vượt quá 5 %, p95 cũng nhảy lên 1700.3 ms trong khi avg mới là 373.9 ms. Average cộng vài request rất chậm với hàng trăm request nhanh rồi chia đều, nên nó che mất trải nghiệm của những người dùng gặp request chậm. SLO đặt theo p95/p99 cho biết trực tiếp bao nhiêu phần trăm người dùng phải chờ quá ngưỡng.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

Nguồn: `reports/eval_v1.json`, `reports/eval_v2.json`, `reports/eval_v2_fixed.json`.

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.3 % (1/23) | 91.3 % (21/23) | 100.0 % (23/23) |
| Avg tokens / câu | 57.5 | 108.7 | 113.7 |
| Tổng cost (USD) | 0.00041 | 0.000756 | 0.000791 |
| Cost / câu đúng (USD) | 0.00040995 | 0.00003599 | 0.0000344 |
| Quality gate | FAIL (ngưỡng 80 %) | PASS (ngưỡng 80 %, so với baseline v1) | PASS (ngưỡng 100 %, so với baseline v2, 0 regression) |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| security-02 | `token`, `hết hạn`, `chữ ký` | Câu hỏi "JWT khác gì API key" không khớp từ khoá nào trong `KNOWLEDGE_BASE`, nên v2 trả câu chung chung. Thêm mục từ khoá `["jwt"]` vào `utils/mock_llm.py`, nội dung nêu API key là chuỗi cố định không tự hết hạn, JWT là token có chữ ký số và thời điểm hết hạn. |
| scaling-03 | `cpu`, `memory`, `custom metrics` | Thêm mục từ khoá `["hpa", "kubernetes", "autoscal"]`, nội dung nêu HPA scale số pod theo CPU, memory hoặc custom metrics. |

Không sửa `eval/golden_dataset.jsonl`. Lần chạy cuối:

```text
python eval/run_eval.py --url http://localhost:8002 --min-accuracy 1.0 --baseline reports/eval_v2.json --out reports/eval_v2_fixed.json
Accuracy      : 100.0%  (23/23)
Accuracy                     91.3%      100.0%     +8.7 điểm %
⚠️  Câu bị regression : 0
Quality gate (accuracy ≥ 100%, không regression): ✅ PASS
```

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**

v2 thêm bước retrieval và đưa tài liệu vào prompt, nên số token mỗi câu tăng khoảng 1.9 lần (57.5 → 108.7) và tổng cost tăng 1.84 lần. Latency eval cũng tăng: p50 của v1 là 155.8 ms, của v2 là 201.4 ms, do thêm khoảng 20 ms gọi knowledge base và prompt dài hơn. Đổi lại, accuracy tăng từ 4.3 % lên 91.3 %, nên cost cho mỗi câu đúng giảm khoảng 11 lần (0.00041 → 0.000036 USD). Với agent hỏi đáp, câu trả lời sai không có giá trị, nên chỉ số cần so là cost trên câu đúng chứ không phải cost trên request. Sau khi sửa KB, token tăng nhẹ (113.7) vì hai câu trước đây không có context nay có context.

**Dùng exit code của eval để chặn merge:** `run_eval.py` trả exit code 1 khi accuracy dưới `--min-accuracy` hoặc có câu regression so với `--baseline`. CI chạy agent v2 rồi chạy eval trong một job; exit code khác 0 làm job fail. Đặt job này là required status check trong branch protection thì PR không merge được khi chất lượng giảm.

```yaml
# .github/workflows/eval.yml
name: quality-gate
on: [pull_request]
jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Run agent + eval
        working-directory: 06-lab-complete/benchmark-observability/develop
        run: |
          pip install -r requirements.txt
          AGENT_VERSION=v2 MOCK_ERROR_RATE=0 python app.py &
          sleep 3
          python eval/run_eval.py --url http://localhost:8000 --min-accuracy 0.85 --baseline reports/eval_v2_fixed.json
```

---

## 4. Observability stack (production)

Stack chạy bằng `docker compose -p k5-day14-observability` trong `06-lab-complete/benchmark-observability/production/`. Dockerfile của agent được thêm `ENV PYTHONUSERBASE=/home/agent/.local`; thiếu dòng này, user `agent` (home là `/app`) không thấy package đã cài và container crash với `No module named 'uvicorn'`.

### 4.1 Screenshot

- [x] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals): [grafana-dashboard.png](screenshots/grafana-dashboard.png). Locust 15 user, 2 instance: 9.0 req/s, error rate 1.01 %, p95 296.63 ms.
- [x] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian): [jaeger-slow-trace.png](screenshots/jaeger-slow-trace.png). Trace `7f80737`, chi tiết ở mục 4.3.
- [x] Một trace lỗi trong Jaeger (có event `exception`): [jaeger-error-trace.png](screenshots/jaeger-error-trace.png). Trace `12ec433`, chi tiết ở mục 4.3.
- [x] Trang Alerts của Prometheus với ít nhất 1 alert đang **firing**: [prometheus-alert-firing.png](screenshots/prometheus-alert-firing.png). Đặt cùng lúc `MOCK_ERROR_RATE=0.2` và `MOCK_SLOW_RATE=0.3` lúc 21:44:44: `AgentHighErrorRate` firing lúc 21:46:10, `AgentHighLatencyP95` firing lúc 21:47:12, ảnh có cả hai alert.

Bốn ảnh chụp bằng Chromium headless (Playwright) trong lần chạy stack lúc 21:41–21:47 ngày 25/11/2026.

**Exercise 7.4.** Số đọc từ các query của dashboard trên Prometheus, khi Locust chạy 100 user (25/11/2026, 20:12 và 20:14):

1. Với 1 instance, p95 là 298.6 ms và avg là 233.9 ms; p99 là 1817.6 ms. p95 chỉ cao hơn avg khoảng 65 ms vì phần lớn request mất 190–220 ms. Khoảng cách lớn nằm ở p99: 3 % request bị chậm thêm khoảng 1.5 giây, ít hơn 5 % nên chưa đẩy p95 lên nhưng làm p99 gấp 8 lần avg. Avg không cho thấy nhóm người dùng phải chờ gần 2 giây này.
2. Với 3 instance, panel "Requests/s theo instance" cho 20.45, 20.49 và 20.67 req/s. Nginx chia gần đều (lệch dưới 1.1 %), đúng với cơ chế round-robin.
3. Input tokens/s (4504.5) lớn gần gấp đôi output tokens/s (2391.6) vì input gồm system prompt, tài liệu retrieval của v2 và câu hỏi, còn output chỉ là câu trả lời ngắn.
4. `curl http://localhost:8080/metrics` trả `404 Not Found` từ nginx. `nginx.conf` có `location = /metrics { return 404; }` để không lộ metric (route, lưu lượng, thông tin hệ thống) ra ngoài; Prometheus scrape thẳng từng agent qua mạng nội bộ `obs_net`, không đi qua nginx.

### 4.2 Thí nghiệm "phá hệ thống"

Cách làm: 2 instance agent, Locust chạy nền 15 user. Với mỗi thí nghiệm, script đổi đúng một biến trong `.env`, chạy `docker compose -p k5-day14-observability up -d --scale agent=2`, rồi hỏi `GET /api/v1/alerts` của Prometheus mỗi 5 giây. Thời gian tính từ lúc chạy lệnh `up -d` (hoặc `docker pause`) tới lúc alert chuyển sang `firing`. Sau mỗi thí nghiệm `.env` được trả về như `.env.example` và chờ mọi alert tắt rồi mới làm thí nghiệm tiếp. Giờ ghi theo GMT+7, ngày 25/11/2026.

Tải nền chọn 15 user thay vì 30 user như README. Ở 30 user (khoảng 18.7 req/s), cấu hình mặc định đã tốn $2.21/giờ, vượt ngưỡng $2/giờ của `LLMCostBurnRateHigh`, nên alert này firing ngay cả khi chưa đổi gì và thí nghiệm C không đo được.

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` (giá trị lúc firing 18.8 %) | 85 s (đổi 20:28:47, pending sau 25 s, firing 20:30:16) | Error rate |
| B | `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` (p95 = 1.92 s) | 145 s (đổi 20:31:08, pending sau 25 s, firing 20:33:36) | Latency /ask — p50 / p95 / p99 |
| C | `LLM_MODEL=mock-llm-large` | `LLMCostBurnRateHigh` ($8.35/giờ) | 160 s (đổi 20:34:39, pending sau 40 s, firing 20:37:22) | Cost burn rate (USD/giờ) |
| D | `docker pause` 1 instance (`k5-day14-observability-agent-1`) | `AgentInstanceDown` | 45 s (pause 20:42:15, pending sau 15 s, firing 20:43:00) | Instances up |
| E | `AGENT_VERSION=v1` | Không có (kiểm tra sau 240 s) | — | Phiên bản đang chạy (hiện `v1`), Retrieval hit ratio (không còn dữ liệu), Tokens/s (input còn 338.5 tok/s) |

**Phân tích:** Thời gian tới lúc firing gồm ba phần: thời gian để metric thay đổi đủ trong cửa sổ `rate(...[1m])` hoặc `[5m]`, chu kỳ scrape/evaluate, và điều kiện `for:` của rule. A có `for: 1m` nên firing sau 85 s, tức khoảng 25 s để error rate vượt 5 % cộng 60 s chờ. B có `for: 2m` nên chậm hơn (145 s). C dùng `rate(...[5m])` nhưng chi phí tăng 16 lần nên vượt $2/giờ chỉ sau 40 s, rồi thêm `for: 2m`. D nhanh nhất vì `up == 0` đổi ngay ở lần scrape đầu tiên sau khi container bị pause và rule chỉ có `for: 30s`.

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

v1 vẫn trả 200 nhanh và rẻ hơn, nên latency, error rate và cost đều "khoẻ"; chỉ có câu trả lời sai. Loại lỗi này cần kiểm tra chất lượng:

- Chạy eval golden dataset trong CI/CD như quality gate: `run_eval.py` của v1 cho accuracy 4.3 % và exit code 1, nên bản deploy này bị chặn trước khi lên production.
- Sau deploy, chạy eval định kỳ (canary/synthetic) với một tập câu hỏi cố định lên môi trường thật, đẩy accuracy thành metric và đặt alert khi giảm.
- Theo dõi tín hiệu gián tiếp: retrieval hit ratio về 0, tokens/câu giảm mạnh, panel phiên bản đổi ngoài lịch deploy, phản hồi tiêu cực của người dùng (thumbs down), hoặc LLM-as-judge chấm một phần traffic.

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất bạn tìm được (trace chậm nhất trong 221 trace của service `observable-agent` ở lần chạy chụp ảnh; đây là trace trong `jaeger-slow-trace.png`):

- `trace_id`: `7f80737f0edb94204e6b113691a43ac7`
- Tổng thời gian: 1690.0 ms
- Span chiếm nhiều thời gian nhất: `chat mock-llm-small` (1661.5 ms, 98.3 %). `agent.retrieve_context` chỉ mất 25.3 ms (1.5 %). Request này rơi vào nhóm "slow" của mock LLM (`MOCK_SLOW_RATE=0.03`), nên cần tối ưu hoặc đặt timeout ở bước gọi LLM, không phải ở retrieval.
- Dòng log tương ứng (grep theo `trace_id`):

```json
{"ts": "2026-11-25T14:41:50.900020+00:00", "level": "INFO", "service": "observable-agent", "instance": "6c86a7f6e350", "event": "llm_call", "trace_id": "7f80737f0edb94204e6b113691a43ac7", "span_id": "400afd9bee11b910", "request_id": "16c6b836c451", "model": "mock-llm-small", "agent_version": "v2", "input_tokens": 74, "output_tokens": 37, "cost_usd": 3.3e-05, "llm_ms": 1660.5}
{"ts": "2026-11-25T14:41:50.901078+00:00", "level": "INFO", "service": "observable-agent", "instance": "6c86a7f6e350", "event": "http_request", "trace_id": "7f80737f0edb94204e6b113691a43ac7", "span_id": "400afd9bee11b910", "request_id": "16c6b836c451", "method": "POST", "route": "/ask", "status": 200, "ms": 1689.1}
```

Trace lỗi trong `jaeger-error-trace.png`: `trace_id` `12ec433e5ab982a2cbe7e16680ef3753`, tổng 125.6 ms, status 503. Span `agent.run` (114.8 ms) và `chat mock-llm-small` (90.4 ms) có event `exception` với `exception.type = utils.mock_llm.LLMError`, `exception.message = Upstream LLM error: 503 Service Unavailable (mock)`. Log tương ứng:

```json
{"ts": "2026-11-25T14:41:51.993092+00:00", "level": "INFO", "service": "observable-agent", "instance": "6c86a7f6e350", "event": "llm_error", "trace_id": "12ec433e5ab982a2cbe7e16680ef3753", "span_id": "844e80e1ce7d0ec7", "request_id": "9694d1426225", "error": "Upstream LLM error: 503 Service Unavailable (mock)"}
{"ts": "2026-11-25T14:41:51.993907+00:00", "level": "INFO", "service": "observable-agent", "instance": "6c86a7f6e350", "event": "http_request", "trace_id": "12ec433e5ab982a2cbe7e16680ef3753", "span_id": "844e80e1ce7d0ec7", "request_id": "9694d1426225", "method": "POST", "route": "/ask", "status": 503, "ms": 123.9}
```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

Nguồn: `benchmark-results/scale_1_stats.csv`, `benchmark-results/scale_3_stats.csv`, dòng `POST /ask`. Locust chạy bằng `docker compose run --rm --no-deps locust ...`. Thiếu `--no-deps`, lệnh `run` tự đưa service agent về `replicas: 2` khai báo trong compose, nên lần chạy "1 instance" thực tế có 2 instance.

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 59.83 | 190 | 350 | 1700 | 67 / 7152 (0.94 %, đều là 503) |
| 3 | 59.62 | 190 | 240 | 1700 | 64 / 7081 (0.90 %, đều là 503) |

Tính cả `GET /health` (dòng Aggregated), RPS là 65.71 với 1 instance và 65.73 với 3 instance.

**Giải thích kết quả:** Scale lên 3 instance không làm tăng RPS và p50, p99 giữ nguyên; p95 giảm từ 350 xuống 240 ms. RPS do phía tải quyết định: mỗi user Locust chờ `between(0.5, 2)` giây giữa hai request, nên 100 user chỉ tạo khoảng 65 req/s dù agent trả lời nhanh hay chậm. Ở mức tải này một instance chưa bão hoà: Prometheus đo p95 phía server 298.6 ms với 1 instance và 295.6 ms với 3 instance. Phần lớn latency nằm ở bước gọi LLM (p95 của LLM khoảng 198 ms ở cả hai lần), mà bước này không nhanh hơn khi thêm instance. p95 phía client giảm nhẹ nhờ hàng đợi ở mỗi instance ngắn hơn (in-flight 16 với 1 instance, 11 với 3 instance). p99 1700 ms do 3 % request "slow" của mock LLM, scale không xử lý được. Lỗi 503 là lỗi upstream giả lập (`MOCK_ERROR_RATE=0.01`), xuất hiện ở cả hai lần với tỉ lệ như nhau. Muốn thấy lợi ích của scale cần tăng tải tới khi 1 instance bão hoà (in-flight tăng, p50 tăng), hoặc giảm `wait_time` của Locust.

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. Average che mất tail latency. Với 3 % request chậm, avg chỉ tăng 25 % nhưng p99 tăng hơn 3 lần, nên SLO phải đặt theo p95/p99.
  2. Metric hạ tầng không bắt được lỗi chất lượng. Đổi sang agent v1 làm accuracy giảm từ 100 % xuống 4.3 % mà không có alert nào; cần eval với golden dataset làm quality gate trước deploy.
  3. Cách đo quyết định ý nghĩa con số. Locust có `wait_time` nên RPS bị giới hạn bởi số user, và `docker compose run` thiếu `--no-deps` âm thầm đổi số instance; phải kiểm tra điều kiện đo (số instance, máy có bị ngủ/quá tải) trước khi tin vào kết quả.
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?

Thêm synthetic check từ bên ngoài và metric ở tầng nginx (tỉ lệ 502/504, upstream response time), vì lỗi xảy ra ở load balancer không hiện trong metric của agent. Thêm alert theo error budget burn rate (nhiều cửa sổ 5 phút và 1 giờ) thay vì ngưỡng tức thời. Chạy eval định kỳ trên mẫu traffic thật và đẩy accuracy thành metric `agent_eval_accuracy` có alert khi giảm. Thêm alert khi retrieval hit ratio giảm đột ngột, vì đây là dấu hiệu sớm của lỗi kiểu thí nghiệm E. Theo dõi cost theo ngày so với budget và alert khi dự báo vượt budget trong ngày.
