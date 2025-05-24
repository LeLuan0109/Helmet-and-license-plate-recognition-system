from django.shortcuts import render
from .forms import VideoUploadForm
import os
import uuid
from django.conf import settings
import subprocess
import threading

from main.helmet.helmet_detection_pipeline import process_video_for_violations
def ensure_media_folder():
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

def process_video(input_path, output_path):
    try:
       print("Processing video:", input_path)
       process_video_for_violations(input_path)
    except subprocess.CalledProcessError as e:
        print("Error during video processing:", e.stderr)
        raise

def upload_video(request):
    ensure_media_folder()

    uploaded_video_url = None
    video_evidence_url = None
    form = VideoUploadForm()

    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video = request.FILES['video']
            video_name = f"{uuid.uuid4()}.mp4"
            input_path = os.path.join(settings.MEDIA_ROOT, video_name)

            # Lưu video đầu vào
            with open(input_path, 'wb+') as destination:
                for chunk in video.chunks():
                    destination.write(chunk)

            uploaded_video_url = settings.MEDIA_URL + video_name
            video_evidence_url = process_video_for_violations(input_path, "Hà Nội")
            print("Video evidence URL:", video_evidence_url)
            print("Uploaded video URL:", uploaded_video_url)
    return render(request, 'index.html', {
        'form': form,
        'uploaded_video_url': uploaded_video_url,
        'video_evidence_url': video_evidence_url,
    })


def media_select(request):
    
    media_path = settings.MEDIA_ROOT
    video_files = [f for f in os.listdir(media_path) if f.endswith('.mp4') or f.endswith('.avi')]

    if request.method == 'POST':
        video_name = request.POST.get('video_path')
        input_path = os.path.join(media_path, video_name)
        output_name = f"processed_{video_name}"
        output_path = os.path.join(media_path, output_name)

        try:
            process_video(input_path, output_path)
        except Exception as e:
            return render(request, 'media_select.html', {
                'video_files': video_files,
                'error': 'Xử lý video thất bại. Kiểm tra server logs.'
            })

        if os.path.exists(output_path):
            return render(request, 'media_select.html', {
                'video_files': video_files,
                'processed_video_url': settings.MEDIA_URL + output_name
            })
        else:
            return render(request, 'media_select.html', {
                'video_files': video_files,
                'error': 'Không tìm thấy video sau xử lý.'
            })

    return render(request, 'media_select.html', {'video_files': video_files})
