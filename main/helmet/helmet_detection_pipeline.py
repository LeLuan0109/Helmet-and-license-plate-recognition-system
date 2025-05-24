import os
import cv2
import time
import math
import shutil
import uuid
import subprocess

from datetime import datetime
from pathlib import Path
from ultralytics import YOLO
from main.helmet.cloudinary_uploader import upload_image_to_cloudinary
from main.helmet.tele import send_violation_alert
from django.conf import settings
from threading import Thread


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, '..', '..', 'model')

HELMET_MODEL_PATH = os.path.join(MODEL_DIR, 'best.pt')
PLATE_MODEL_PATH = os.path.join(MODEL_DIR, 'best.pt')

FRAME_INTERVAL = 0.5  # giây
DISTANCE_THRESHOLD = 100
OUTPUT_DIR = 'violations'
TEMP_FRAMES_DIR = 'temp_frames'
MEDIA_BOUNDING_BOX = 'media-bounding-box'
helmet_model = YOLO(HELMET_MODEL_PATH)
plate_model = YOLO(PLATE_MODEL_PATH)
helmet_class_names = helmet_model.names


def clear_directory(dir_path):
    p = Path(dir_path)
    p.mkdir(parents=True, exist_ok=True)
    for item in p.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def generate_violation_id(location: str):
    now = datetime.now()
    date_prefix = now.strftime("%Y-%m")
    id_file = f"{OUTPUT_DIR}/id_{location}_{date_prefix}.txt"
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
    print(f"✅ Extracted {saved} frames from video.")


def enhance_image(image):
    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    y_eq = cv2.equalizeHist(y)
    ycrcb_eq = cv2.merge((y_eq, cr, cb))
    image_eq = cv2.cvtColor(ycrcb_eq, cv2.COLOR_YCrCb2BGR)

    gaussian = cv2.GaussianBlur(image_eq, (0, 0), 3)
    sharpened = cv2.addWeighted(image_eq, 1.5, gaussian, -0.5, 0)

    return sharpened


def resize_keep_aspect(image, max_size=640):
    h, w = image.shape[:2]
    if max(h, w) <= max_size:
        return image
    scale = max_size / max(h, w)
    return cv2.resize(image, (int(w * scale), int(h * scale)))


def send_tele_and_upload(rider_path, plate_path, location):
    rider_url = None
    plate_url = None

    if rider_path and os.path.exists(rider_path):
        with open(rider_path, "rb") as f:
            rider_url = upload_image_to_cloudinary(f)

    if plate_path and os.path.exists(plate_path):
        with open(plate_path, "rb") as f:
            plate_url = upload_image_to_cloudinary(f)

    send_violation_alert(location, rider_url, plate_url)


def fix_mp4_moov(input_path, output_path):
    subprocess.run([
        'ffmpeg', '-y',
        '-i', input_path,
        '-movflags', 'faststart',
        '-c:v', 'libx264',
        '-preset', 'fast',    # hoặc "ultrafast", "medium"
        '-crf', '23',         # chất lượng (thấp hơn = tốt hơn)
        '-c:a', 'aac',        # audio codec
        output_path
    ], check=True)


def process_frames(temp_frames_dir, output_dir, media_bbox_dir, location):
    processed_centers = []
    writer = None
    unique_id = uuid.uuid4()
    raw_video_path = os.path.join(media_bbox_dir, f'{unique_id}_violation_raw.mp4')
    final_video_path = os.path.join(media_bbox_dir, f'{unique_id}_violation.mp4')
    for img_file in sorted(os.listdir(temp_frames_dir)):    
        img_path = os.path.join(temp_frames_dir, img_file)
        frame = enhance_image(cv2.imread(img_path))
        results = helmet_model(frame)[0]

        if writer is None:
            height, width = frame.shape[:2]
            os.makedirs(media_bbox_dir, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*'a', 'v', 'c', '1')  # HTML5 compatible
            writer = cv2.VideoWriter(raw_video_path, fourcc, 10.0, (width, height))
        if not results.boxes:
            continue
        
        for box in results.boxes:
            class_id = int(box.cls)
            label = helmet_class_names[class_id]
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            color = (0, 0, 255) if label.lower() in ['no-helmet', 'none-helmet'] else (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        for box in results.boxes:
            class_id = int(box.cls)
            label = helmet_class_names[class_id]
        
            if label in ['No-Helmet', 'None-helmet']:
                timestamp = int(time.time())
                nh_x1, nh_y1, nh_x2, nh_y2 = map(int, box.xyxy[0].tolist())
                nh_cx = (nh_x1 + nh_x2) / 2
                nh_cy = (nh_y1 + nh_y2) / 2

                rider_box = None
                min_dist = float('inf')

                for other_box in results.boxes:
                    if helmet_class_names[int(other_box.cls)] == 'Rider':
                        ox1, oy1, ox2, oy2 = map(int, other_box.xyxy[0].tolist())
                        ocx = (ox1 + ox2) / 2
                        ocy = (oy1 + oy2) / 2
                        dist = math.hypot(nh_cx - ocx, nh_cy - ocy)
                        if dist < min_dist:
                            min_dist = dist
                            rider_box = other_box

                if not rider_box:
                    continue

                rx1, ry1, rx2, ry2 = map(int, rider_box.xyxy[0].tolist())
                rcx = (rx1 + rx2) / 2
                rcy = (ry1 + ry2) / 2

                if any(math.hypot(rcx - pcx, rcy - pcy) < DISTANCE_THRESHOLD for pcx, pcy in processed_centers):
                    continue

                processed_centers.append((rcx, rcy))
                violator_id = generate_violation_id(location)
                folder = f"{output_dir}/{violator_id}_{location}"
                os.makedirs(folder, exist_ok=True)

                rider_crop = frame[ry1:ry2, rx1:rx2]
                rider_crop_resized = resize_keep_aspect(rider_crop)
                rider_path = os.path.join(folder, f"rider_{timestamp}.jpg")
                if not cv2.imwrite(rider_path, rider_crop_resized):
                    rider_path = None

                plate_path = None
                plate_results = plate_model(rider_crop_resized)[0]
                for p_box in plate_results.boxes:
                    p_label = plate_model.names[int(p_box.cls)].lower()
                    if p_label in ['license-plate', 'licenseplate']:
                        px1, py1, px2, py2 = map(int, p_box.xyxy[0].tolist())
                        plate_crop = rider_crop_resized[py1:py2, px1:px2]
                        plate_crop = cv2.resize(plate_crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                        plate_path = os.path.join(folder, f"plate_{timestamp}.jpg")
                        if not cv2.imwrite(plate_path, plate_crop):
                            plate_path = None
                        break

                Thread(target=send_tele_and_upload, args=(rider_path, plate_path, location)).start()


        writer.write(frame)
    if writer:
        writer.release()
    try:
        fix_mp4_moov(raw_video_path, final_video_path)
        os.remove(raw_video_path)
    except Exception as e:
        print("⚠️ FFmpeg xử lý lỗi:", e)
        final_video_path = raw_video_path  # fallback

    return final_video_path


def process_video_for_violations(video_path: str, location: str):
    clear_directory(OUTPUT_DIR)
    clear_directory(TEMP_FRAMES_DIR)
    
    extract_frames(video_path, TEMP_FRAMES_DIR, interval=FRAME_INTERVAL)
    video_result_path = process_frames(TEMP_FRAMES_DIR, OUTPUT_DIR, MEDIA_BOUNDING_BOX, location)
    print("🏁 Xử lý hoàn tất cho video:", video_path)
    relative_path = os.path.relpath(video_result_path, settings.MEDIA_BOUNDING_BOX_ROOT)
    video_result_url = os.path.join(settings.MEDIA_BOUNDING_BOX_URL, relative_path).replace('\\', '/')
    return video_result_url