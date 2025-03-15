def generate_image(prompt: str, output_file: str = "generated_image.png") -> bool:
    """
    基礎生成圖像，示範用。實際可整合圖像生成 API。
    """
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (400, 300), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.text((10, 10), f"Prompt: {prompt}", fill=(255, 255, 0))
        img.save(output_file)
        return True
    except Exception as e:
        print(f"圖像生成錯誤：{e}")
        return False

if __name__ == '__main__':
    if generate_image("測試圖像", "test_image.png"):
        print("圖像生成成功")
    else:
        print("圖像生成失敗")
