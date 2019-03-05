import moviepy.editor as mpy

import pydub as pdb

import numpy as np
import matplotlib.pyplot as plt
#import cv2

import moviepy.video.fx.all as vfx

from collections import defaultdict

import moviepy.video.fx.all as vfx
import os

# CONSTANTS
PREVIEW_SIZE = (1280, 720)
#PRODUCTION_SIZE = (1024, 768)

def resize_and_fit(origin_clip, video_size):
    new_size = (0, 0) # init the value
    if origin_clip.h >= origin_clip.w: # EH: when the image is square, change it according to video size
        new_size = ((origin_clip.w * video_size[1] / origin_clip.h),video_size[1])
    else:
        new_size = ((video_size[0], origin_clip.h * video_size[0] / origin_clip.w))
    clip = origin_clip.resize(new_size).on_color(video_size)
    return clip

def set_scene_dur(origin_clip, dur, fps=25):
    clip = origin_clip.set_duration(dur).set_fps(fps)
    return clip

def set_img_dur(origin_clip, dur, fps=25):
    clip = origin_clip.set_duration(dur).set_fps(fps)
    return clip

def set_video_dur(origin_clip, dur, fps=25):
    clip = vfx.speedx(origin_clip, final_duration=dur).set_fps(fps)
    return clip

def generate_subtitles_clip(subtitles, fontsize=60, color="white", stroke_width=2, stroke_color="black"):
    '''
    params:
    * subtitles: parse script
    '''
    text_clips = []
    
    for content in subtitles:
        if isinstance(content, SContent):
            text_content = mpy.TextClip(content.text,
                                         color=color,
                                         stroke_color= stroke_color,
                                         stroke_width= stroke_width,
                                         font="ArialUnicode", # TODO: change the font
                                         fontsize=fontsize
                                        )
            text_on_color = text_content.on_color(PREVIEW_SIZE, pos=('center', 'bottom') ,col_opacity=0)
            text_clip = text_on_color.set_duration(content.dur)
            text_clips.append(text_clip)
            # EH: add some spaces between subtitles
        
    return mpy.concatenate_videoclips(text_clips)


class SCommand():
    
    def __init__(self, command_str):
        self.command_str = command_str
        self.command_parsed = defaultdict(list)
        self.parse()
        
    def parse(self):
        command_factors = self.command_str.split()
        command_factors = [factor for factor in command_factors if factor] # Clean blank lines
        
        param_name = "position_args"

        for i in range(len(command_factors)):
            factor = command_factors[i]
            if i == 0:
                self.command_parsed['func'] = factor
            elif factor[0:2] == "--":
                param_name = factor[2:]
            else:
                # Append the param
                if factor.replace(".", "", 1).isdigit(): # check if it is float
                    factor = float(factor)
                elif ":" in factor:
                    if factor.count(":") == 1: # if hour is forgot to be written
                        if len(factor.split(":")[0]) == 1: # if 0 is forgot to be written
                            factor = "00:0" + factor
                        else:
                            factor = "00:" + factor

                self.command_parsed[param_name].append(factor)

class SContent():
    
    def __init__(self, text, audio=0, dur=1.5):
        self.text = text
        self.audio = audio
        self.dur = dur # EH: adjust the dur according to audio

        # EH: change a position to set the text
        if len(self.text) > 18:
            self.text = text[:12] + "\n" + text[12:]

def parse_script(script):
    script_lines = [line for line in script.split("\n") if line]
    
    parsed = []
    for line in script_lines:
        if line[0] == "$":
            parsed.append(SCommand(line[1:]))
        else:
            parsed.append(SContent(line))
    return parsed

def get_scene_transition_schedule(parsed_script):
    # EH: change this into index based method. This method is too ugly.
    '''
    return: a list of tuples like (scene_filename, dur, params)
    '''

    schedule = []
    
    current_scene = ""
    dur = 0
    params = {}
    
    for line in parsed_script:
        if isinstance(line, SCommand):
            
            if line.command_parsed["func"] == "ST":
                if current_scene: # If 'line' is not the first scene, append the previous scene
                    schedule.append((current_scene, dur, params))
                current_scene = line.command_parsed["position_args"][0]
                dur = 0
                # EH: change the way params are added
                params = {"part": line.command_parsed['part'], "crop": line.command_parsed['crop']}
        else:
            if isinstance(line, SContent):
                dur += line.dur
    
    # Add the final scene after all lines are schedule
    schedule.append((current_scene, dur, params))
    
    return schedule

def scheduled_time_scene_transition(schedule, resource_folder_name="res"):
    '''
    params:
    - schedule: a list of tuples of (file name, dur)
    '''
    clips = []
    print(schedule)#DEBUG
    for res, dur, params in schedule:
        # EH: use a better way to detect the type of a file
        file_name = os.path.join(resource_folder_name, res)
        if not os.path.exists(file_name):
            print("File not found! {}".format(file_name))
            raise FileNotFoundError()
        file_type = res.split(".")[-1]
        if file_type in ["mov", "mp4", "avi", "flv"]:
            origin_video_clip = mpy.VideoFileClip(os.path.join(resource_folder_name, res), audio=False)
            if params["part"]:
                #print(params["part"])
                parts = params["part"]
                origin_video_clip = origin_video_clip.subclip(parts[0], parts[1])
            if params["crop"]:
                w = origin_video_clip.w
                h = origin_video_clip.h
                rect = params["crop"]
                origin_video_clip = vfx.crop(origin_video_clip, w*rect[0], h*rect[1], w*rect[2], h*rect[3])
            clips.append(set_video_dur(resize_and_fit(origin_video_clip, PREVIEW_SIZE), dur))
        elif file_type in ["jpg", "png", "jpeg"]:
            origin_img_clip = mpy.ImageClip(os.path.join(resource_folder_name, res))
            if params["crop"]:
                w = origin_img_clip.w
                h = origin_img_clip.h
                rect = params["crop"]
                #print("Crop", w, h, rect, rect[0]*w)
                origin_img_clip = vfx.crop(origin_img_clip, w*rect[0], h*rect[1], w*rect[2], h*rect[3])
            clips.append(set_img_dur(resize_and_fit(origin_img_clip, PREVIEW_SIZE), dur))
        elif file_type in ["txt"]:
            print(res)
            print(os.path.join(resource_folder_name, res))
            origin_txt_clip = mpy.TextClip(
                open(os.path.join(resource_folder_name, res)).read(),
                color="white",
                font="ArialUnicode",
                fontsize=100
                ).on_color(PREVIEW_SIZE).set_position("center")
            clips.append(set_scene_dur(resize_and_fit(origin_txt_clip, PREVIEW_SIZE), dur))
            
    return mpy.concatenate_videoclips(clips)

def get_chunks(audio):
    chunks = pdb.silence.split_on_silence(audio.normalize(), min_silence_len=1000, silence_thresh=-40, keep_silence=250)

    new_chunks = []
    for chunk in chunks:
        dur = round(chunk.duration_seconds, 1) + 0.1
        new_chunk = (chunk + pdb.AudioSegment.silent())[:dur*1000]
        new_chunks.append(new_chunk)
    return new_chunks

def match_audio(parsed_script, chunks):
    
    # EH: normalize the volume of audio at first and then divide it into chunks
    
    for line in parsed_script:
        if isinstance(line, SContent) and chunks:
            line.audio = chunks.pop(0) # Get the main audio before chunks are removed
            line.dur = line.audio.duration_seconds

def generate_video():

    # Parse script
    script = ""
    with open("script.txt", "r") as f:
        script = f.read()

    parsed_script = parse_script(script)
    print("Script parsed.")

    # Generate audio
    if "audio.wav" in os.listdir("."):
        print("Audio detected.")
        chunks = get_chunks(pdb.AudioSegment.from_wav("audio.wav"))
        print("Audio chunks generated.")
        sum(chunks).export("audio_track.wav", "wav")
        # Export to file first, then match
        match_audio(parsed_script, chunks)
    
    # Generate subtitles
    subtitle_clip = generate_subtitles_clip(parsed_script)
    print("Subtitles generated.")

    # Generate scenes
    schedule = get_scene_transition_schedule(parsed_script)
    video_clip = scheduled_time_scene_transition(schedule)
    print("Scene generated.")

    # Generate the video
    main_clip = mpy.CompositeVideoClip([video_clip, subtitle_clip])

    # Add the audio track
    if "audio_track.wav" in os.listdir("."):
        audio_clip = mpy.AudioFileClip('audio_track.wav')
        if "BGM.mp3" in os.listdir(".") or "BGM.flac" in os.listdir("."):
            audio_clip = mpy.CompositeAudioClip([mpy.AudioFileClip('audio_track.wav'), mpy.AudioFileClip("BGM.mp3").volumex(0.15)])
        main_clip = main_clip.set_audio(audio_clip.set_duration(main_clip.duration))

    # Write the video
    main_clip.write_videofile("output.mp4")

if __name__ == "__main__":
    generate_video()

