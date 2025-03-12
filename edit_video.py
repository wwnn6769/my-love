# D:\Assistant\src\video\edit_video.py
import cv2
import os

def clip_video(input_path, output_path, start_time, end_time):
    """
    從指定的影片中剪輯出一段區間，並存儲為新影片。
    
    :param input_path: 原始影片的完整路徑
    :param output_path: 剪輯後影片的輸出路徑
    :param start_time: 剪輯開始時間（秒）
    :param end_time: 剪輯結束時間（秒）
    :return: 剪輯成功則返回 True，否則返回 False
    """
    # 檢查輸入檔案是否存在
    if not os.path.exists(input_path):
        print("錯誤：找不到影片素材檔案：", input_path)
        return False

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print("無法開啟影片：", input_path)
        return False

    # 讀取影片參數
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps)
    if start_frame < 0 or start_frame >= total_frames:
        print("錯誤：開始時間不在影片範圍內")
        cap.release()
        return False
    if end_frame > total_frames:
        end_frame = total_frames

    # 設定影片編碼格式與 VideoWriter 寫入器
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    current_frame = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if start_frame <= current_frame <= end_frame:
            out.write(frame)
        if current_frame > end_frame:
            break
        current_frame += 1

    cap.release()
    out.release()
    print("影片剪輯完成，輸出檔案：", output_path)
    return True

if __name__ == "__main__":
    # 測試用固定參數：您可以根據需要修改這裡
    input_video = r"E:\VideoMaterials\sample_video.avi"
    output_video = r"I:\EditedVideos\edited_sample_video.avi"
    start_time = 2
    end_time = 5
    
    if not os.path.exists(r"E:\VideoMaterials"):
        print("影片素材目錄不存在，請確認 E:\\VideoMaterials 存在。")
    elif not os.path.exists(r"I:\EditedVideos"):
        print("剪輯後影片目錄不存在，請確認 I:\\EditedVideos 存在。")
    else:
        clip_video(input_video, output_video, start_time, end_time)
