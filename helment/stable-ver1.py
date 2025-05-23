import os
import cv2
import time
import math
from datetime import datetime
from pathlib import Path
from ultralytics import YOLO
# 
from cloudinary_uploader import upload_image_to_cloudinary
from tele import send_violation_alert
# --- Cấu hình ---
helmet_model_path = r"C:\Work\Leanring\Helmet-rider-license_plate\best.pt"
plate_model_path = r"C:\Work\Leanring\Helmet-rider-license_plate\license_plate_detector.pt"
video_path = r"C:\Work\Leanring\Helmet-rider-license_plate\6628004790825.mp4"

output_dir = 'violations_2'
temp_frames_dir = 'temp_frames_2'
location = 'HaNoi'
frame_interval = 0.5  # giây
distance_threshold = 100  # ngưỡng tránh trùng Rider

# Tạo thư mục
def clear_directory(dir_path):
    p = Path(dir_path)
    p.mkdir(parents=True, exist_ok=True)  # Tạo thư mục nếu chưa có
    for item in p.iterdir():
        if item.is_dir():
            import shutil
            shutil.rmtree(item)
        else:
            item.unlink()

# Tạo và làm sạch thư mục output và temp frames
clear_directory(output_dir)
clear_directory(temp_frames_dir)

# Load model
helmet_model = YOLO(helmet_model_path)
plate_model = YOLO(plate_model_path)
helmet_class_names = helmet_model.names

# Hàm tạo ID vi phạm
def generate_violation_id():
    now = datetime.now()
    date_prefix = now.strftime("%Y-%m")
    id_file = f"{output_dir}/id_{date_prefix}.txt"
    if os.path.exists(id_file):
        with open(id_file, 'r+') as f:
            current_id = int(f.read().strip()) + 1
            f.seek(0)
            f.write(str(current_id))
    else:
        current_id = 1
        with open(id_file, 'w') as f:
            f.write(str(current_id))
    return current_id

# --- Bước 1: Trích xuất frame ---
def extract_frames(video_path, output_folder, interval=0.5):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_skip = int(fps * interval)
    count = 0
    saved = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if count % frame_skip == 0:
            frame_path = os.path.join(output_folder, f"frame_{saved:05d}.jpg")
            cv2.imwrite(frame_path, frame)
            saved += 1
        count += 1

    cap.release()
    print(f"✅ Đã trích xuất {saved} frame.")

def enhance_image(image):
    # 1. Chuyển sang không gian màu YCrCb để cải thiện độ tương phản
    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    y_eq = cv2.equalizeHist(y)
    ycrcb_eq = cv2.merge((y_eq, cr, cb))
    image_eq = cv2.cvtColor(ycrcb_eq, cv2.COLOR_YCrCb2BGR)

    # 2. Làm nét bằng bộ lọc Laplacian hoặc unsharp masking
    gaussian = cv2.GaussianBlur(image_eq, (0, 0), 3)
    sharpened = cv2.addWeighted(image_eq, 1.5, gaussian, -0.5, 0)

    return sharpened

def resize_keep_aspect(image, max_size=640):
    h, w = image.shape[:2]
    if max(h, w) <= max_size:
        return image  # Không resize nếu nhỏ hơn hoặc bằng 640

    scale = max_size / max(h, w)
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(image, (new_w, new_h))
    return resized

# --- Bước 3: Gửi ảnh lên Cloudinary và gửi cảnh báo ---
def send_tele_and_upload_rider_and_plate(rider_img_path, plate_img_path):
    rider_url = None
    plate_url = None

    if rider_img_path is not None and os.path.exists(rider_img_path):
        with open(rider_img_path, "rb") as f:
            rider_url = upload_image_to_cloudinary(f)
    else:
        print(f"⚠️ File rider không tồn tại: {rider_img_path}")

    if plate_img_path is not None and os.path.exists(plate_img_path):
        with open(plate_img_path, "rb") as f:
            plate_url = upload_image_to_cloudinary(f)
    else:
        print(f"⚠️ File plate không tồn tại: {plate_img_path}")

    send_violation_alert('Hà Nội', rider_url, plate_url)



# --- Bước 2: Xử lý từng ảnh ---
def process_frames():
    processed_centers = []

    for img_file in sorted(os.listdir(temp_frames_dir)):
        img_path = os.path.join(temp_frames_dir, img_file)
        frame = enhance_image(cv2.imread(img_path))

        results = helmet_model(frame)[0]
        if results.boxes is None or len(results.boxes) == 0:
            continue

        for box in results.boxes:
            class_id = int(box.cls)
            label = helmet_class_names[class_id]

            if label in ['No-Helmet', 'None-helmet']:
                timestamp_10 = int(time.time())  
                nh_x1, nh_y1, nh_x2, nh_y2 = map(int, box.xyxy[0].tolist())
                nh_cx = (nh_x1 + nh_x2) / 2
                nh_cy = (nh_y1 + nh_y2) / 2

                # Tìm Rider gần nhất
                min_dist = float('inf')
                rider_box = None

                for other_box in results.boxes:
                    cls_id = int(other_box.cls)
                    other_label = helmet_class_names[cls_id]
                    if other_label == 'Rider':
                        ox1, oy1, ox2, oy2 = map(int, other_box.xyxy[0].tolist())
                        ocx = (ox1 + ox2) / 2
                        ocy = (oy1 + oy2) / 2
                        dist = math.hypot(nh_cx - ocx, nh_cy - ocy)
                        if dist < min_dist:
                            min_dist = dist
                            rider_box = other_box

                if rider_box is None:
                    continue

                # Kiểm tra tránh trùng Rider đã xử lý
                rx1, ry1, rx2, ry2 = map(int, rider_box.xyxy[0].tolist())
                rcx = (rx1 + rx2) / 2
                rcy = (ry1 + ry2) / 2

                is_duplicate = False
                for (pcx, pcy) in processed_centers:
                    if math.hypot(rcx - pcx, rcy - pcy) < distance_threshold:
                        is_duplicate = True
                        break

                if is_duplicate:
                    continue

                # Đánh dấu đã xử lý
                processed_centers.append((rcx, rcy))

                # Tạo thư mục vi phạm
                violator_id = generate_violation_id()
                folder_name = f"{output_dir}/{violator_id}_{location}"
                os.makedirs(folder_name, exist_ok=True)

                # Lưu ảnh Rider
                crop = frame[ry1:ry2, rx1:rx2]
                crop_resized = resize_keep_aspect(crop, max_size=640)
                rider_path = os.path.join(folder_name, f"rider_{timestamp_10}.jpg")
                rider_img = cv2.imwrite(rider_path, crop_resized)
                if(not rider_img): rider_path = None
                # print(f"🚨 Phát hiện vi phạm: {rider_path}")

                # --- Detect biển số ---
                plate_path = None
                plate_results = plate_model(crop_resized)[0]
                for p_box in plate_results.boxes:
                    p_class = int(p_box.cls)
                    p_label = plate_model.names[p_class]
                    if p_label.lower() in ['license-plate', 'licenseplate']:
                        px1, py1, px2, py2 = map(int, p_box.xyxy[0].tolist())
                        plate_crop = crop_resized[py1:py2, px1:px2]
                        plate_crop = cv2.resize(plate_crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                        plate_path = os.path.join(folder_name, f"plate_{timestamp_10}.jpg")
                        plate_img = cv2.imwrite(plate_path, plate_crop)
                        if(not plate_img): plate_path = None
                        break
                # đẩy ảnh vào Cloudinary
                # send_tele_and_upload_rider_and_plate(rider_path, plate_path)


# --- Chạy toàn bộ ---
extract_frames(video_path, temp_frames_dir, interval=frame_interval)
process_frames()
print("🏁 Hoàn tất.")
