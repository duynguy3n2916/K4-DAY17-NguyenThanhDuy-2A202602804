# Phân tích kết quả benchmark

Benchmark đã chạy từ thư mục gốc repo; cả bốn test trong `src/test_agents.py` đều pass. Benchmark dùng chế độ offline xác định để có thể lặp lại mà không cần API key. `Response quality` là điểm heuristic dựa trên độ đầy đủ của các fact trong câu trả lời, không phải đánh giá của model judge.

| Bộ dữ liệu | Agent | Recall | Prompt tokens processed | Memory growth | Compactions |
|---|---|---:|---:|---:|---:|
| Standard | Baseline | 0% | 14.241 | 0 bytes | 0 |
| Standard | Advanced | 100% | 20.819 | 252 bytes | 0 |
| Long context | Baseline | 0% | 22.195 | 0 bytes | 0 |
| Long context | Advanced | 100% | 13.296 | 211 bytes | 2 |

## Vì sao Advanced nhớ xuyên phiên?

Baseline giữ các message theo `thread_id`, nên câu hỏi ở thread mới không có thông tin từ hội thoại cũ. Advanced ghi các fact tương đối ổn định (tên, nơi ở, nghề, sở thích, cách trả lời) vào `state/profiles/<user_id>/User.md`. Câu hỏi ở thread mới đọc lại file đó. Khi người dùng đính chính nơi ở hoặc nghề nghiệp, `upsert_fact()` thay giá trị cũ theo cùng một khóa.

## Chi phí của memory

Trong bộ Standard, Advanced xử lý nhiều hơn Baseline 6.578 prompt token, khoảng 46%, vì mỗi lượt mang thêm `User.md`; chưa có lần compact nào. Trong bộ Long context, Advanced xử lý ít hơn 8.899 prompt token, khoảng 40%, sau 2 lần compact. Baseline gửi lại toàn bộ lịch sử ở mỗi lượt; Advanced giữ một số message gần nhất và tóm tắt phần cũ. Vì thế tác dụng chính của compact thể hiện ở `Prompt tokens processed`. `Agent tokens only` đo lượng nội dung người dùng và agent tạo ra theo cùng một heuristic, nên không nên coi nó là chi phí API thực.

`Memory growth (bytes)` chỉ tính độ tăng của file `User.md`. File này có thể tăng khi thêm loại fact mới. Cơ chế ghi theo khóa hạn chế việc lặp lại cùng fact, nhưng trích xuất heuristic vẫn có thể lưu sai nếu câu nói mơ hồ. Summary cũng có thể làm mất chi tiết cũ vì có giới hạn độ dài. Hai rủi ro này cần được kiểm soát bằng confidence threshold, provenance hoặc review trước khi dùng trong hệ thống thật.

## Giới hạn của kết quả

Recall 100% trên dữ liệu mẫu chứng minh các quy tắc offline xử lý được những câu hỏi có sẵn trong benchmark. Nó chưa chứng minh agent sẽ hiểu đúng câu diễn đạt mới, thông tin mơ hồ, hoặc hoạt động tốt với model live. Điểm `Response quality` phụ thuộc mạnh vào recall heuristic, vì vậy không phải phép đánh giá độc lập về độ tự nhiên hay hữu ích của câu trả lời.
