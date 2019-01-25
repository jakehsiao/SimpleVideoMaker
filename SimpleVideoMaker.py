
# coding: utf-8

# In[41]:


import moviepy.editor as mpy


# In[42]:


import pydub as pdb


# In[43]:


import numpy as np
import matplotlib.pyplot as plt
import cv2


# In[44]:


# CONSTANTS
PREVIEW_SIZE = (400, 300)
PRODUCTION_SIZE = (1024, 768)


# In[45]:


import moviepy.video.fx.all as vfx
import os


# In[46]:


def resize_and_fit(origin_clip, video_size):
    new_size = (0, 0) # init the value
    if origin_clip.h > origin_clip.w:
        new_size = ((origin_clip.w * video_size[1] / origin_clip.h),video_size[1])
    else:
        new_size = ((video_size[0], origin_clip.h * video_size[0] / origin_clip.w))
    clip = origin_clip.resize(new_size).on_color(video_size)
    return clip


# In[47]:


def set_scene_dur(origin_clip, dur, fps=25):
    clip = origin_clip.set_duration(dur).set_fps(fps)
    return clip


# In[48]:


def set_img_dur(origin_clip, dur, fps=25):
    clip = origin_clip.set_duration(dur).set_fps(fps)
    return clip


# In[49]:


def set_video_dur(origin_clip, dur, fps=25):
    clip = vfx.speedx(origin_clip, final_duration=dur).set_fps(fps)
    return clip


# In[50]:


def fixed_time_scene_transition(resources):
    '''
    params:
    - resources: a list of file names of resources in order
    '''
    clips = []
    for res in resources:
        # EH: use a better way to detect the type of a file
        file_type = res[-3:]
        if file_type in ["mov", "mp4", "avi", "flv"]:
            clips.append(set_video_dur(resize_and_fit(mpy.VideoFileClip(res), PREVIEW_SIZE), 2))
        elif file_type in ["jpg", "png"]:
            clips.append(set_img_dur(resize_and_fit(mpy.ImageClip(res), PREVIEW_SIZE), 2))
            
    return mpy.concatenate_videoclips(clips)


# In[51]:


test_resources = sorted(os.listdir("TestResources/"))


# ## Scripting

# In[52]:


def generate_subtitles_clip(subtitles, fontsize=40, color="white", stroke_width=1, stroke_color="black"):
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
                                         font="Helvetica", # TODO: change the font
                                         fontsize=fontsize
                                        )
            text_on_color = text_content.on_color(PREVIEW_SIZE, pos=('center', 'bottom') ,col_opacity=0)
            text_clip = text_on_color.set_duration(content.dur)
            text_clips.append(text_clip)
            # EH: add some spaces between subtitles
        
    return mpy.concatenate_videoclips(text_clips)


# In[53]:


test_script = '''
$ST Umbrella.jpg --crop 0.25 0.25 0.75 0.75
This is a script.
Each sentence's duration is 2 seconds.
That is quite cool.
$ST 10.mp4 --part 0 4
This is the next scene.
That is so cool.
'''


# In[74]:


from collections import defaultdict

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
                if factor.replace(".", "", 1).isdigit():
                    factor = float(factor)
                self.command_parsed[param_name].append(factor)


# In[75]:


class SContent():
    
    def __init__(self, text, audio=0, dur=2):
        self.text = text
        self.audio = audio
        self.dur = dur # EH: adjust the dur according to audio


# In[76]:


script_lines = [line for line in test_script.split("\n") if line]


# In[77]:


script_lines


# In[78]:


def parse_script_lines(script_lines):
    parsed = []
    for line in script_lines:
        if line[0] == "$":
            parsed.append(SCommand(line[1:]))
        else:
            parsed.append(SContent(line))
    return parsed


# In[79]:


parsed_script = parse_script_lines(script_lines)


# In[80]:


test_cmd = parsed_script[0]


# In[81]:


def get_scene_transition_schedule(parsed_script):
    # EH: change this into index based method. This method is too ugly.
    
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


# In[86]:


def scheduled_time_scene_transition(schedule, resource_folder_name="res"):
    '''
    params:
    - schedule: a list of tuples of (file name, dur)
    '''
    clips = []
    for res, dur, params in schedule:
        # EH: use a better way to detect the type of a file
        file_type = res[-3:]
        if file_type in ["mov", "mp4", "avi", "flv"]:
            origin_video_clip = mpy.VideoFileClip(resource_folder_name+"/"+res)
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
        elif file_type in ["jpg", "png"]:
            origin_img_clip = mpy.ImageClip(resource_folder_name+"/"+res)
            if params["crop"]:
                w = origin_img_clip.w
                h = origin_img_clip.h
                rect = params["crop"]
                #print("Crop", w, h, rect, rect[0]*w)
                origin_img_clip = vfx.crop(origin_img_clip, w*rect[0], h*rect[1], w*rect[2], h*rect[3])
            clips.append(set_img_dur(resize_and_fit(origin_img_clip, PREVIEW_SIZE), dur))
            
    return mpy.concatenate_videoclips(clips)


# In[87]:


mpy.CompositeVideoClip([scheduled_time_scene_transition(get_scene_transition_schedule(parsed_script), resource_folder_name="TestResources"), generate_subtitles_clip(parsed_script, fontsize=40, color='white', stroke_width=1.5)]).ipython_display()


# ## Audio
# Analysis the silence, then get a list of (audio, dur), then match it with scripts, then generate the audio using generate_audio(parsed_script), then match it with the scene transitions.

# In[43]:


test_audio = pdb.AudioSegment.from_wav("audio.wav")


# In[44]:


test_audio


# In[85]:


chunks = pdb.silence.split_on_silence(test_audio, min_silence_len=500, silence_thresh=-50, keep_silence=500)


# In[86]:


chunks


# In[98]:


def adjust_chunk_time(chunks):
    new_chunks = []
    for chunk in chunks:
        dur = round(chunk.duration_seconds, 1) + 0.1
        new_chunk = (chunk + pdb.AudioSegment.silent())[:dur*1000]
        new_chunks.append(new_chunk)
    return new_chunks


# In[107]:


new_chunks = adjust_chunk_time(chunks)


# In[57]:


test_script_with_audio = '''
$ST 01.png
Gaige chunfeng flow the ground
Chinese are so awesome
This world......
$ST 07.mp4
Forget the plots
$ST Umbrella.jpg
How to make children love study
'''


# In[59]:


def parse_script(script):
    script_lines = [line for line in script.split("\n") if line]
    
    parsed = []
    for line in script_lines:
        if line[0] == "$":
            parsed.append(SCommand(line[1:]))
        else:
            parsed.append(SContent(line))
    return parsed


# In[60]:


parsed_script = parse_script(test_script_with_audio)


# In[61]:


parsed_script


# In[63]:


def match_audio(parsed_script, chunks):
    
    # EH: normalize the volume of audio at first and then divide it into chunks
    
    for line in parsed_script:
        if isinstance(line, SContent):
            line.audio = chunks.pop(0) # Get the main audio before chunks are removed
            line.dur = line.audio.duration_seconds


# In[109]:


sum(new_chunks).export("audio_track.wav", "wav")


# In[110]:


match_audio(parsed_script, new_chunks)


# In[111]:


subtitle_clip = generate_subtitles_clip(parsed_script)


# In[112]:


schedule = get_scene_transition_schedule(parsed_script)


# In[113]:


video_clip = scheduled_time_scene_transition(schedule, "TestResources")


# In[114]:


main_clip = mpy.CompositeVideoClip([video_clip, subtitle_clip])


# In[115]:


main_clip.set_audio(mpy.AudioFileClip('audio_track.wav')).ipython_display()


# In[120]:


parsed_script[2].audio

