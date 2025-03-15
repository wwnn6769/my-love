from moviepy.editor import VideoFileClip

def clip_video(input_video: str, output_video: str, start_time: float, end_time: float) -> (bool, str):
    """
    從 input_video 裁剪從 start_time 到 end_time 的片段，存到 output_video
    回傳 (True, process_info) 表示成功，否則 (False, error_message)
    process_info 格式例如："00:00 ~ 00:10 剪輯成功"
    """
    try:
        with VideoFileClip(input_video) as clip:
            new_clip = clip.subclip(start_time, end_time)
            new_clip.write_videofile(output_video, codec="libx264", audio_codec="aac")
        process_info = f"{format_time(start_time)} ~ {format_time(end_time)} 剪輯成功"
        return True, process_info
    except Exception as e:
        return False, f"影片剪輯錯誤：{e}"

def format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

if __name__ == '__main__':
    result, info = clip_video("input.mp4", "output.mp4", 10, 20)
    if result:
        print("影片剪輯成功，過程：", info)
    else:
        print("影片剪輯失敗，訊息：", info)
