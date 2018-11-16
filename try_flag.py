import argparse
import moviepy.editor as mpy
import datetime

parser = argparse.ArgumentParser()

parser.add_argument(
    "filename",
    action="store",
    help="The name of the video file",
    type=str,
)

parser.add_argument(
    "-s",
    "--subclip",
    action="store",
    dest="subclip_duration",
    help="Specify the subclip duration in seconds.",
    nargs=2,
    type=float,
    default=[0, -1],
    )

results = parser.parse_args()
video = mpy.VideoFileClip(results.filename)
video = video.subclip(
        results.subclip_duration[0],
        results.subclip_duration[1]
    )
video.write_videofile(results.filename[:-4]
        +"_trimmed_"
        +datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        +".mp4"
    )

