# Ghi chú phân tích · Day 04

Họ và tên: Lê Quang Vinh
MSSV: 2A202603363

## 1. Case được chọn

- ID case: H7
- Câu trả lời của agent:
  - Lần 1: Khi tool Cloudflare trả `TimeoutError`, agent vẫn kết luận Cloudflare Spectrum `operational`.
  - Lần 2: Agent nói trạng thái Cloudflare chưa xác định do timeout; đồng thời báo trạng thái GitHub dựa trên kết quả tool thành công.
- Điểm H7: lần 1 **45/100**, lần 2 **100/100** (LLM judge).

## 2. Bằng chứng trong trace

Trace H7 cho thấy tool Cloudflare lỗi, không có bằng chứng về trạng thái:

```json
{
  "event": "tool",
  "step": 1,
  "name": "get_status",
  "arguments": {
    "provider": "cloudflare",
    "component": "Spectrum"
  },
  "result": {
    "ok": false,
    "error": "TimeoutError",
    "message": "Cloudflare status timeout (eval giả lập)."
  }
}
```

Ở lần 1, câu trả lời vẫn gọi Cloudflare là `operational`, trái với trace và expected. Ở lần 2, agent nêu rõ không thể xác nhận trạng thái do timeout và không suy đoán.

## 3. Thay đổi đã thực hiện

- Sửa `SYSTEM_PROMPT` trong `agent.py`: yêu cầu chỉ xác nhận trạng thái dựa trên kết quả tool thành công; khi tool lỗi/timeout thì báo trạng thái chưa xác định, không suy ra `operational` hay outage; lỗi của một provider không phủ nhận kết quả từ provider khác.
- Thêm test trong `tests/test_validation.py` để xác nhận model nhận được chính sách này cùng kết quả GitHub thành công và Cloudflare timeout.
- Kiểm tra: `python -m unittest discover -s tests -v` — **41 tests passed**.

## 4. So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---:|---:|
| Điểm tổng | Chưa có (11/22 case được chấm) | Chưa có (15/22 case được chấm) |
| Trung bình tạm thời trên case đã chấm | 94.82/100 | 94.00/100 |
| Điểm case H7 | 45/100 | 100/100 |
| Số agent model calls được ghi nhận | 47 | 46 |
| Tokens agent / judge được ghi nhận | 42,820 / 19,523 | 49,309 / 26,120 |
| Chi phí | Không có trong file kết quả | Không có trong file kết quả |

Hai trung bình tạm thời không thể so sánh trực tiếp vì số lượng và danh sách case được chấm khác nhau. Lần 1 còn các case E3, E4, A1, A3, A6, A7, A8, H1, H2, H4, H5 chưa chấm; lần 2 còn A1, A3, A4, A7, A8, H4, H5 chưa chấm. Các lỗi HTTP 503 khiến kết quả chưa đủ để tính điểm tổng theo rubric.

- Lỗi đã giải quyết trong H7: không còn kết luận Cloudflare `operational` khi tool timeout; vẫn giữ thông tin từ GitHub có bằng chứng.
- Lỗi còn lại: một số case chưa chấm do HTTP 503; cần chạy lại để có đủ kết quả trước khi kết luận điểm tổng.

## 5. Giới hạn

- Điểm judge do LLM tạo ra, có thể sai lệch; trong lần chạy này agent và judge cùng dùng Gemini `gemini-3.5-flash-lite`.
- Eval dùng snapshot cố định và có scenario lỗi giả lập; không đại diện hoàn toàn cho API live.
- Hai lần chạy đơn lẻ không chứng minh độ ổn định. Các trung bình trên chỉ là thống kê của những case đã chấm, không phải điểm tổng hợp hợp lệ.
