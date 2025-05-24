from django import forms

class VideoUploadForm(forms.Form):
    video = forms.FileField(label='Chọn video')
