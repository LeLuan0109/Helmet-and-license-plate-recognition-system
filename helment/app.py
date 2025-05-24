import os
import time
from helmet_detection_pipeline import process_video_for_violations

VIDEO_PATH = r"E:\dataset\Train-data\1\Helmet-and-license-plate-recognition-system-master\6616427026658.mp4"
LOCATION = "Hà Nội"

def is_file_stable(file_path, wait_time=2):
    """Kiểm tra file có ổn định (không thay đổi kích thước trong vài giây)"""
    if not os.path.exists(file_path):
        return False
    initial_size = os.path.getsize(file_path)
    time.sleep(wait_time)
    new_size = os.path.getsize(file_path)
    return initial_size == new_size and initial_size > 0

if __name__ == "__main__":
    if not os.path.exists(VIDEO_PATH):
        print(f"File không tồn tại: {VIDEO_PATH}")
    elif not is_file_stable(VIDEO_PATH):
        print(f"File {VIDEO_PATH} chưa ổn định. Hãy thử lại sau.")
    else:
        print(f"Bắt đầu xử lý video: {VIDEO_PATH}")
        try:
            process_video_for_violations(VIDEO_PATH, LOCATION)
            print("✅ Xử lý hoàn tất.")
        except Exception as e:
            print(f"❌ Lỗi khi xử lý video: {e}")
