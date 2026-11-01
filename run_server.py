# -*- coding: utf-8 -*-
"""Script khởi chạy Backend Server an toàn & thân thiện cho người dùng."""
import os
import sys
import time
import socket
import webbrowser
from pathlib import Path

# Đảm bảo UTF-8 cho console Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Kiểm tra xem cổng đã bị tiến trình khác chiếm dụng chưa."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0


def main():
    print("=" * 60)
    print("      KMS TỬ VI — KHỞI ĐỘNG HỆ THỐNG BACKEND SERVER")
    print("=" * 60)

    port = 8000
    host = "127.0.0.1"

    # Kiểm tra cổng
    if is_port_in_use(port, host):
        print(f"\n⚠️  CẢNH BÁO: Cổng {port} hiện đang có một ứng dụng khác sử dụng!")
        print(f"👉 Vui lòng tắt ứng dụng đang dùng cổng {port} hoặc đóng server cũ trước khi chạy lại.")
        print("\nNhấn Enter để thoát...")
        input()
        return

    docs_url = f"http://{host}:{port}/docs"
    print(f"\n[1/3] Đang chuẩn bị môi trường...")
    print(f"[2/3] Địa chỉ API Docs (Swagger UI): {docs_url}")
    print(f"[3/3] Đang khởi động Uvicorn Server tại http://{host}:{port} ...")
    print("\n💡 HƯỚNG DẪN:")
    print(f"  • Mở trình duyệt và truy cập: {docs_url}")
    print(f"  • Để dừng Server: Nhấn tổ hợp phím [Ctrl + C]\n")
    print("-" * 60)

    # Mở trình duyệt sau 1.5 giây sau khi server bắt đầu
    import threading
    def open_browser():
        time.sleep(1.8)
        try:
            webbrowser.open(docs_url)
        except Exception:
            pass

    threading.Thread(target=open_browser, daemon=True).start()

    # Khởi chạy uvicorn
    import uvicorn
    from backend.app.main import app

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()

