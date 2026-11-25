# Benchmark & Observability Report — Day 14

**Họ tên:** Le Gia Hung (2A202603706)
**Ngày chạy:** 25/11/2026
**Môi trường:** Laptop Windows 11 Pro, Intel Core i7-9750H (6 nhân / 12 luồng), RAM 15.8 GB; Python 3.11.9; Docker Desktop 29.9.3 (WSL2, VM 12 CPU / 5.8 GB RAM)

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | < 500 ms | Mock LLM mất khoảng 200 ms mỗi câu khi không tải; 500 ms chừa chỗ cho hàng đợi ở tải vừa mà người dùng chat vẫn thấy phản hồi nhanh. |
| Error rate `/ask` | < 2 % | Mock LLM tự sinh khoảng 1 % lỗi upstream (`MOCK_ERROR_RATE=0.01`); ngưỡng 2 % chấp nhận mức lỗi nền này nhưng bắt được khi lỗi tăng gấp đôi. |
| Accuracy trên golden dataset | ≥ 100 % (23/23) | Golden dataset nhỏ và mỗi câu là kiến thức bắt buộc của agent, nên sai một câu là regression cần sửa trước khi deploy. |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.31 | 201.3 | 234.1 | 1704.6 | 1.33 % | PASS |
| 10 | 43.41 | 198.0 | 245.0 | 1685.8 | 1.33 % | PASS |
| 50 | 83.14 | 218.7 | 864.8 | 1755.0 | 1.33 % | FAIL |
| 100 | 37.7 | 1179.0 | 5734.5 | 5956.2 | 1.67 % | FAIL |

**Nhận xét:** RPS có tăng tuyến tính theo concurrency không? Vì sao?

RPS không tăng tuyến tính theo concurrency. Từ 1 lên 10, RPS tăng gần 10 lần (4.31 → 43.41) vì p50 vẫn giữ quanh 200 ms: mỗi request chủ yếu chờ mock LLM trả lời, nên một process async xử lý song song được. Từ 10 lên 50, RPS chỉ tăng 1.9 lần (83.14) và p95 vượt SLO (864.8 ms). Ở 100, RPS giảm còn 37.7 và p50 lên 1179 ms. Agent chỉ có một process uvicorn và load generator chạy cùng máy, nên khi vượt khả năng xử lý, request phải xếp hàng, thời gian chờ cộng vào latency và throughput giảm. Lỗi 503 ở cả 4 mức là lỗi upstream giả lập của mock LLM, không phải do quá tải.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 210.7 | 471.1 | 513.6 |
| 0.03 (mặc định) | 264.2 | 518.4 | 1711.9 |
| 0.1 | 373.9 | 1700.3 | 1741.2 |

**Nhận xét:** Chỉ số nào nhạy nhất với request chậm? Vì sao SLO không nên đặt theo average?

p99 nhạy nhất với request chậm. Với 3 % request chậm, avg chỉ tăng 25 % (210.7 → 264.2 ms) nhưng p99 tăng hơn 3 lần (513.6 → 1711.9 ms), vì 3 % request chậm thêm khoảng 1500 ms nằm đúng trong 1 % đuôi. Khi tỉ lệ chậm lên 10 %, vượt quá 5 %, p95 cũng nhảy lên 1700.3 ms trong khi avg mới là 373.9 ms. SLO không nên đặt theo average vì average chia đều vài request rất chậm cho hàng trăm request nhanh, nên che mất trải nghiệm của những người dùng phải chờ lâu; p95/p99 cho biết trực tiếp bao nhiêu phần trăm người dùng chờ quá ngưỡng.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.3 % (1/23) | 91.3 % (21/23) | 100 % (23/23) |
| Avg tokens / câu | 57.5 | 108.7 | 113.7 |
| Tổng cost (USD) | 0.00041 | 0.000756 | 0.000791 |
| Cost / câu đúng (USD) | 0.00040995 | 0.00003599 | 0.0000344 |
| Quality gate | FAIL | PASS | PASS |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| security-02 | `token`, `hết hạn`, `chữ ký` | Câu hỏi về JWT không khớp từ khoá nào trong `KNOWLEDGE_BASE` nên v2 trả câu chung chung. Thêm mục từ khoá `["jwt"]`, nội dung nêu API key là chuỗi cố định không tự hết hạn, còn JWT là token có chữ ký số và thời điểm hết hạn. |
| scaling-03 | `cpu`, `memory`, `custom metrics` | Thêm mục từ khoá `["hpa", "kubernetes", "autoscal"]`, nội dung nêu HPA scale số pod theo CPU, memory hoặc custom metrics. |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**

v2 thêm bước retrieval và đưa tài liệu vào prompt, nên số token mỗi câu tăng khoảng 1.9 lần (57.5 → 108.7) và tổng cost tăng 1.84 lần. Latency cũng tăng: p50 của v1 là 155.8 ms, của v2 là 201.4 ms, do thêm bước gọi knowledge base và prompt dài hơn. Đổi lại, accuracy tăng từ 4.3 % lên 91.3 %, nên cost cho mỗi câu đúng giảm khoảng 11 lần (0.00041 → 0.000036 USD). Với agent hỏi đáp, câu trả lời sai không có giá trị, nên chỉ số cần so là cost trên câu đúng chứ không phải cost trên request.

`run_eval.py` trả exit code 1 khi accuracy dưới `--min-accuracy` hoặc có câu regression so với `--baseline`. CI chạy agent rồi chạy eval trong một job; exit code khác 0 làm job fail. Đặt job này là required status check trong branch protection thì PR không merge được khi chất lượng giảm.

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

### 4.1 Screenshot

- [x] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals): [grafana-dashboard.png](screenshots/grafana-dashboard.png)
- [x] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian): [jaeger-slow-trace.png](screenshots/jaeger-slow-trace.png)
- [x] Một trace lỗi trong Jaeger (có event `exception`): [jaeger-error-trace.png](screenshots/jaeger-error-trace.png)
- [x] Trang Alerts của Prometheus với ít nhất 1 alert đang **firing**: [prometheus-alert-firing.png](screenshots/prometheus-alert-firing.png)

**Exercise 7.4** (Locust 100 user):

1. Với 1 instance, p95 là 298.6 ms và avg là 233.9 ms, chênh khoảng 65 ms vì phần lớn request mất 190–220 ms. Khoảng cách lớn nằm ở p99 (1817.6 ms): 3 % request chậm thêm khoảng 1.5 giây, ít hơn 5 % nên chưa đẩy p95 lên nhưng làm p99 gấp 8 lần avg.
2. Với 3 instance, panel "Requests/s theo instance" cho 20.45, 20.49 và 20.67 req/s, nên Nginx chia gần đều theo round-robin.
3. Input tokens/s (4504.5) lớn gần gấp đôi output tokens/s (2391.6) vì input gồm system prompt, tài liệu retrieval và câu hỏi, còn output chỉ là câu trả lời ngắn.
4. `curl http://localhost:8080/metrics` trả 404 vì `nginx.conf` chặn `location = /metrics`, để không lộ thông tin route, lưu lượng và hệ thống ra ngoài; Prometheus scrape thẳng từng agent trong mạng nội bộ.

### 4.2 Thí nghiệm "phá hệ thống"

Các thí nghiệm chạy với 2 instance và Locust 15 user. Ở 30 user, cấu hình mặc định đã tốn $2.21/giờ, vượt ngưỡng $2/giờ của `LLMCostBurnRateHigh`, nên alert này firing trước cả khi đổi cấu hình.

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` | 85 s | Error rate |
| B | `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` | 145 s | Latency /ask — p50 / p95 / p99 |
| C | `LLM_MODEL=mock-llm-large` | `LLMCostBurnRateHigh` | 160 s | Cost burn rate (USD/giờ) |
| D | `docker pause` 1 instance | `AgentInstanceDown` | 45 s | Instances up |
| E | `AGENT_VERSION=v1` | Không có | — | Phiên bản đang chạy, Retrieval hit ratio |

Thời gian tới lúc firing phụ thuộc cửa sổ `rate(...)` và điều kiện `for:` của rule. A có `for: 1m` nên firing sau 85 s. B có `for: 2m` nên chậm hơn (145 s). C dùng `rate(...[5m])` nhưng chi phí tăng 16 lần nên vượt $2/giờ sau 40 s, rồi thêm `for: 2m`. D nhanh nhất vì `up == 0` đổi ngay ở lần scrape đầu tiên và rule chỉ có `for: 30s`.

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

v1 vẫn trả 200 nhanh và rẻ hơn, nên latency, error rate và cost đều bình thường; chỉ có câu trả lời sai. Loại sự cố này cần kiểm tra chất lượng:

- Chạy eval golden dataset trong CI/CD làm quality gate: v1 cho accuracy 4.3 % và exit code 1, nên bản deploy bị chặn trước khi lên production.
- Sau deploy, chạy eval định kỳ với một tập câu hỏi cố định trên môi trường thật, đẩy accuracy thành metric và đặt alert khi giảm.
- Theo dõi tín hiệu gián tiếp như retrieval hit ratio về 0, tokens/câu giảm mạnh, phiên bản đổi ngoài lịch deploy, hoặc phản hồi tiêu cực của người dùng.

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất bạn tìm được:

- `trace_id`: `7f80737f0edb94204e6b113691a43ac7`
- Tổng thời gian: 1690.0 ms
- Span chiếm nhiều thời gian nhất: `chat mock-llm-small` (1661.5 ms, 98.3 %). `agent.retrieve_context` chỉ mất 25.3 ms, nên cần tối ưu hoặc đặt timeout ở bước gọi LLM, không phải ở retrieval.
- Dòng log tương ứng (grep theo `trace_id`):

```json
{"ts": "2026-11-25T14:41:50.900020+00:00", "level": "INFO", "service": "observable-agent", "instance": "6c86a7f6e350", "event": "llm_call", "trace_id": "7f80737f0edb94204e6b113691a43ac7", "span_id": "400afd9bee11b910", "request_id": "16c6b836c451", "model": "mock-llm-small", "agent_version": "v2", "input_tokens": 74, "output_tokens": 37, "cost_usd": 3.3e-05, "llm_ms": 1660.5}
{"ts": "2026-11-25T14:41:50.901078+00:00", "level": "INFO", "service": "observable-agent", "instance": "6c86a7f6e350", "event": "http_request", "trace_id": "7f80737f0edb94204e6b113691a43ac7", "span_id": "400afd9bee11b910", "request_id": "16c6b836c451", "method": "POST", "route": "/ask", "status": 200, "ms": 1689.1}
```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 59.83 | 190 | 350 | 1700 | 67 (0.94 %) |
| 3 | 59.62 | 190 | 240 | 1700 | 64 (0.90 %) |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

Scale lên 3 instance cải thiện p95 một ít (350 → 240 ms), còn RPS, p50 và p99 gần như không đổi. RPS do phía tải quyết định: mỗi user Locust chờ 0.5–2 giây giữa hai request, nên 100 user chỉ tạo khoảng 60 req/s dù agent nhanh hay chậm, và ở mức tải này một instance chưa bão hoà. Nút thắt nằm ở bước gọi LLM: p95 của LLM khoảng 198 ms ở cả hai lần và không giảm khi thêm instance, còn p99 1700 ms đến từ 3 % request chậm của mock LLM. p95 giảm nhẹ nhờ hàng đợi ở mỗi instance ngắn hơn (in-flight 16 với 1 instance, 11 với 3 instance).

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. Average che mất tail latency: với 3 % request chậm, avg chỉ tăng 25 % nhưng p99 tăng hơn 3 lần, nên SLO phải đặt theo p95/p99.
  2. Metric hạ tầng không bắt được lỗi chất lượng: chuyển sang v1 làm accuracy giảm còn 4.3 % mà không có alert nào, nên cần eval với golden dataset làm quality gate.
  3. Điều kiện đo quyết định ý nghĩa con số: Locust có thời gian chờ giữa các request nên RPS bị giới hạn bởi số user, và số instance thực tế phải được kiểm tra trước khi so sánh kết quả scale.
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?

Thêm synthetic check từ bên ngoài và metric ở tầng nginx (tỉ lệ 502/504, upstream response time), vì lỗi xảy ra ở load balancer không hiện trong metric của agent. Thêm alert theo error budget burn rate thay vì ngưỡng tức thời. Chạy eval định kỳ trên mẫu traffic thật, đẩy accuracy thành metric và alert khi giảm. Thêm alert khi retrieval hit ratio giảm đột ngột, vì đây là dấu hiệu sớm của sự cố kiểu thí nghiệm E.
