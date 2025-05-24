import cv2
import time
import os
from helmet_detection_pipeline import process_video_for_violations
import threading

VIDEO_DIR = "recorded_videos"
PROCESSED_LIST_FILE = "processed_videos.txt"
MAX_VIDEO_LENGTH = 15  # seconds
LOCATION = "Hà Nội"

os.makedirs(VIDEO_DIR, exist_ok=True)

def is_file_stable(file_path, wait_time=2):
    """Kiểm tra file có kích thước không đổi trong wait_time giây"""
    if not os.path.exists(file_path):
        return False
    initial_size = os.path.getsize(file_path)
    time.sleep(wait_time)
    new_size = os.path.getsize(file_path)
    return initial_size == new_size and initial_size > 0

def record_single_video(file_index):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Cannot open camera")
        return None

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_path = os.path.join(VIDEO_DIR, f"video_{int(time.time())}_{file_index}.mp4")

    out = None
    start_time = time.time()

    print(f"Start recording: {video_path}")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Can't receive frame from camera")
            break

        if out is None:
            height, width = frame.shape[:2]
            out = cv2.VideoWriter(video_path, fourcc, 20.0, (width, height))

        out.write(frame)

        # Show camera output
        cv2.imshow('Camera', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Recording stopped by user.")
            break

        if (time.time() - start_time) > MAX_VIDEO_LENGTH:
            break

    if out:
        out.release()
    cap.release()
    cv2.destroyAllWindows()
    print(f"Recorded video saved: {video_path}")
    return video_path

def video_recording_loop():
    file_index = 0
    while True:
        file_index += 1
        video_path = record_single_video(file_index)
        if video_path is None:
            print("Recording failed, retrying...")
            time.sleep(1)
            continue
        # Sau khi ghi xong 1 video, đợi 1 giây rồi tiếp tục ghi video khác
        time.sleep(1)

def is_video_processed(video_path):
    if not os.path.exists(PROCESSED_LIST_FILE):
        return False
    with open(PROCESSED_LIST_FILE, 'r') as f:
        processed_videos = f.read().splitlines()
    return os.path.basename(video_path) in processed_videos

def mark_video_processed(video_path):
    with open(PROCESSED_LIST_FILE, 'a') as f:
        f.write(os.path.basename(video_path) + '\n')

def video_processing_loop(location):
    while True:
        all_videos = os.listdir(VIDEO_DIR)
        videos_to_process = [os.path.join(VIDEO_DIR, v) for v in all_videos if not is_video_processed(os.path.join(VIDEO_DIR, v)) and v.endswith('.mp4')]

        for video_path in videos_to_process:
            if not is_file_stable(video_path):
                print(f"File {video_path} chưa ổn định, bỏ qua lần này.")
                continue

            print(f"Processing video: {video_path}")
            try:
                process_video_for_violations(video_path, location)
                mark_video_processed(video_path)
                print(f"Finished processing and marked: {video_path}")
            except Exception as e:
                print(f"Error processing {video_path}: {e}")

        time.sleep(5)  # tránh vòng lặp chạy quá nhanh

if __name__ == "__main__":
    try:
        t_record = threading.Thread(target=video_recording_loop, daemon=True)
        t_process = threading.Thread(target=video_processing_loop, args=(LOCATION,), daemon=True)

        t_record.start()
        t_process.start()

        t_record.join()
        t_process.join()
    except KeyboardInterrupt:
        print("Stopping program...")