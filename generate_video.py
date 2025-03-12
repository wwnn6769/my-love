# D:\Assistant\src\video\generate_video.py
import cv2
import numpy as np
import os

def generate_sample_video(output_path, num_frames=100, width=640, height=480, fps=10):
    """
    生成一個簡單影片，每個影格顯示 "Frame <編號>"。
    
    :param output_path: 輸出影片的完整路徑。
    :param num_frames: 影格數量。
    :param width: 影片寬度。
    :param height: 影片高度。
    :param fps: 每秒影格數。
    """
    # 定義影片編碼格式
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    # 建立影片寫入器
    video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    for i in range(num_frames):
        # 建立一個全白背景的影格
        frame = np.full((height, width, 3), 255, dtype=np.uint8)
        # 在影格上添加文字 "Frame <i+1>"
        cv2.putText(frame, f'Frame {i+1}', (50, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
        # 寫入影格
        video_writer.write(frame)
    
    # 釋放影片寫入器
    video_writer.release()
    print("影片生成完成，存放於：", output_path)

if __name__ == "__main__":
    # 指定輸出影片的檔案名稱，這裡存放在目前工作目錄下
    output_video = os.path.join(os.getcwd(), "sample_video.avi")
    generate_sample_video(output_video)
