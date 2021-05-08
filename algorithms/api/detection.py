from flask import Blueprint, Response, abort
from api.model.video_camera import YoutubeDetectionCamera

detection_api = Blueprint('detection_api', __name__)

model = None


def gen(cam):
    while True:
        frame = cam.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame +
               b'\r\n\r\n')


@detection_api.route('/video_feed/<video_id>')
def video_feed(video_id):
    camera = YoutubeDetectionCamera(model, video_id)
    return Response(gen(camera), mimetype='multipart/x-mixed-replace;boundary=frame')
