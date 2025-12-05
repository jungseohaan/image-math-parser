# utils/image.py
"""이미지 처리 유틸리티"""


def crop_image_by_bbox(img, bounding_box):
    """bounding_box 좌표(0-1 비율)를 사용하여 이미지를 크롭합니다.

    Args:
        img: PIL Image 객체
        bounding_box: {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0} 형식의 dict

    Returns:
        크롭된 PIL Image 객체. bounding_box가 없거나 전체 이미지인 경우 원본 반환.
    """
    if not bounding_box:
        return img

    x = bounding_box.get('x', 0)
    y = bounding_box.get('y', 0)
    width = bounding_box.get('width', 1)
    height = bounding_box.get('height', 1)

    # 전체 이미지인 경우 원본 반환
    if x == 0 and y == 0 and width >= 1 and height >= 1:
        return img

    # 이미지 크기 가져오기
    img_width, img_height = img.size

    # 비율 좌표를 픽셀 좌표로 변환
    left = int(x * img_width)
    top = int(y * img_height)
    right = int((x + width) * img_width)
    bottom = int((y + height) * img_height)

    # 범위 체크
    left = max(0, min(left, img_width))
    top = max(0, min(top, img_height))
    right = max(left, min(right, img_width))
    bottom = max(top, min(bottom, img_height))

    # 크롭 영역이 너무 작으면 원본 반환
    if right - left < 10 or bottom - top < 10:
        return img

    return img.crop((left, top, right, bottom))
