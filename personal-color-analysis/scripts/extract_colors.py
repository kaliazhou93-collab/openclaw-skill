#!/usr/bin/env python3
"""
extract_colors.py — 从自拍照自动提取4个区域的 hex 颜色值
用于个人色彩分析（Personal Color Analysis）

依赖：pip install mediapipe opencv-python pillow numpy

用法：
    python3 extract_colors.py <图片路径> [--glasses] [--dyed-hair]

输出 JSON：
    {
      "highlight": "#eccbc4",
      "shadow": "#866552",
      "hair": "#1b1615",
      "eye": "#301c1d",
      "white_balance_corrected": true,
      "warnings": ["戴眼镜，眼色取样跳过"]
    }
"""

import sys
import json
import argparse
import numpy as np
from PIL import Image


def hex_from_rgb(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(int(r), int(g), int(b))


def correct_white_balance(img_array):
    """
    灰世界白平衡校正：将图片整体偏色做补偿
    减少室内黄灯/暖光造成的 R 值虚高
    """
    result = img_array.astype(np.float32)
    mean_r = result[:, :, 0].mean()
    mean_g = result[:, :, 1].mean()
    mean_b = result[:, :, 2].mean()
    mean_all = (mean_r + mean_g + mean_b) / 3

    scale_r = mean_all / mean_r if mean_r > 0 else 1.0
    scale_g = mean_all / mean_g if mean_g > 0 else 1.0
    scale_b = mean_all / mean_b if mean_b > 0 else 1.0

    result[:, :, 0] = np.clip(result[:, :, 0] * scale_r, 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] * scale_g, 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] * scale_b, 0, 255)
    return result.astype(np.uint8)


def get_region_color(img_array, x, y, size=15):
    """
    取某坐标周围 size×size 像素的中位数颜色（比均值更抗噪）
    """
    h, w = img_array.shape[:2]
    x1 = max(0, x - size // 2)
    x2 = min(w, x + size // 2)
    y1 = max(0, y - size // 2)
    y2 = min(h, y + size // 2)
    region = img_array[y1:y2, x1:x2]
    if region.size == 0:
        return (128, 128, 128)
    # 用中位数排除极端像素
    r = int(np.median(region[:, :, 0]))
    g = int(np.median(region[:, :, 1]))
    b = int(np.median(region[:, :, 2]))
    return (r, g, b)


def rgb_to_hsv(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    cmax = max(r, g, b)
    cmin = min(r, g, b)
    diff = cmax - cmin
    if cmax == 0:
        s = 0
    else:
        s = diff / cmax
    if diff == 0:
        h = 0
    elif cmax == r:
        h = (60 * ((g - b) / diff) % 360)
    elif cmax == g:
        h = 60 * ((b - r) / diff) + 120
    else:
        h = 60 * ((r - g) / diff) + 240
    v = cmax
    return h, s, v


def detect_face_regions(img_array):
    """
    用 MediaPipe 人脸关键点检测精准定位采样区域
    返回各区域坐标字典，失败返回 None
    """
    try:
        import mediapipe as mp
        import cv2
    except ImportError:
        return None

    h, w = img_array.shape[:2]
    mp_face_mesh = mp.solutions.face_mesh
    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5
    ) as face_mesh:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        results = face_mesh.process(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
        if not results.multi_face_landmarks:
            return None
        lm = results.multi_face_landmarks[0].landmark

        def lm_xy(idx):
            return int(lm[idx].x * w), int(lm[idx].y * h)

        # 额头中央高光（landmark 10）
        highlight_xy = lm_xy(10)
        # 颧骨下阴影（landmark 50 左颧，取双侧均值）
        sh_l = lm_xy(50)
        sh_r = lm_xy(280)
        shadow_xy = ((sh_l[0] + sh_r[0]) // 2, (sh_l[1] + sh_r[1]) // 2)
        # 左眼虹膜（landmark 468，需要 refine_landmarks=True）
        eye_xy = lm_xy(468)
        # 发色：额头上方
        hair_x = int(lm[10].x * w)
        hair_y = max(0, int(lm[10].y * h) - int(h * 0.12))
        hair_xy = (hair_x, hair_y)

        return {
            "highlight": highlight_xy,
            "shadow": shadow_xy,
            "eye": eye_xy,
            "hair": hair_xy
        }


def fallback_regions(img_array):
    """无 MediaPipe 时，基于人脸 bounding box 估算（假设正脸居中）"""
    h, w = img_array.shape[:2]
    # 估算人脸区域（上1/5~下4/5，左右各15%边距）
    face_left = int(w * 0.15)
    face_right = int(w * 0.85)
    face_top = int(h * 0.05)
    face_bottom = int(h * 0.85)
    fw = face_right - face_left
    fh = face_bottom - face_top

    return {
        "highlight": (face_left + fw // 2, face_top + int(fh * 0.18)),
        "shadow":    (face_left + int(fw * 0.35), face_top + int(fh * 0.50)),
        "eye":       (face_left + int(fw * 0.38), face_top + int(fh * 0.38)),
        "hair":      (face_left + fw // 2, face_top - int(h * 0.04))
    }


def extract_colors(image_path, has_glasses=False, dyed_hair=False):
    warnings = []
    img = Image.open(image_path).convert("RGB")
    img_array = np.array(img)

    # 白平衡校正
    corrected = correct_white_balance(img_array)
    wb_applied = True

    # 人脸关键点检测
    regions = detect_face_regions(corrected)
    using_mediapipe = regions is not None
    if not using_mediapipe:
        regions = fallback_regions(corrected)
        warnings.append("未检测到人脸关键点，使用估算坐标（建议发正脸居中照片）")

    # 提取各区域颜色
    highlight = get_region_color(corrected, *regions["highlight"], size=18)
    shadow = get_region_color(corrected, *regions["shadow"], size=14)
    hair = get_region_color(corrected, *regions["hair"], size=22)

    if has_glasses:
        warnings.append("已标注戴眼镜：眼色跳过取样，将用视觉判断补充")
        eye = None
    else:
        eye = get_region_color(corrected, *regions["eye"], size=10)

    if dyed_hair:
        warnings.append("已标注染发：发色仅供参考，请告知自然发色")

    result = {
        "highlight": hex_from_rgb(*highlight),
        "shadow": hex_from_rgb(*shadow),
        "hair": hex_from_rgb(*hair) if not dyed_hair else "需用户提供自然发色",
        "eye": hex_from_rgb(*eye) if eye else "需视觉判断",
        "white_balance_corrected": wb_applied,
        "using_mediapipe": using_mediapipe,
        "warnings": warnings
    }
    return result


def analyze_season(colors):
    """
    从 hex 值推断季型（含置信度）
    使用 HSV 色调辅助 RGB 分析，提升抗光照干扰能力
    """
    def parse_hex(h):
        h = h.lstrip('#')
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def luminance(r, g, b):
        return 0.299 * r + 0.587 * g + 0.114 * b

    # 跳过无效值
    if colors["highlight"].startswith("需") or colors["shadow"].startswith("需"):
        return "无法判断", "数据不足", {}, "low"

    hl_r, hl_g, hl_b = parse_hex(colors["highlight"])
    sh_r, sh_g, sh_b = parse_hex(colors["shadow"])

    hl_lum = luminance(hl_r, hl_g, hl_b)
    sh_lum = luminance(sh_r, sh_g, sh_b)
    contrast = hl_lum - sh_lum

    # --- 冷暖判断（RGB + HSV双重校验）---
    rgb_warm_score = (hl_r - hl_b) * 0.6 + (sh_r - sh_b) * 0.4
    hl_h, hl_s, hl_v = rgb_to_hsv(hl_r, hl_g, hl_b)
    # 黄橙色相区间（暖调）：HSV H 在 20-60 度
    hsv_warm = 1 if (20 <= hl_h <= 60) else (-1 if (180 <= hl_h <= 270) else 0)

    # 综合判断
    is_warm = rgb_warm_score > 20 and hsv_warm >= 0

    # --- 明度 ---
    high_lightness = hl_lum > 175
    low_lightness = hl_lum < 140

    # --- 清浊（饱和度） ---
    max_c = max(hl_r, hl_g, hl_b) / 255
    min_c = min(hl_r, hl_g, hl_b) / 255
    saturation = (max_c - min_c) / max_c if max_c > 0 else 0
    is_clear = saturation > 0.22

    # --- 置信度评估 ---
    confidence_score = abs(rgb_warm_score)
    if confidence_score > 40:
        confidence = "high"
    elif confidence_score > 20:
        confidence = "medium"
    else:
        confidence = "low"

    # --- 季型判断 ---
    if is_warm:
        if high_lightness or (not low_lightness and contrast < 55):
            season = "春（Spring）"
            subtype = "亮春" if (is_clear and hl_lum > 185) else ("淡春" if hl_lum > 170 else "暖春")
        else:
            season = "秋（Autumn）"
            subtype = "深秋" if low_lightness else ("暖秋" if is_clear else "柔秋")
    else:
        if high_lightness or (not low_lightness and contrast < 55):
            season = "夏（Summer）"
            subtype = "淡夏" if hl_lum > 180 else ("冷夏" if is_clear else "柔夏")
        else:
            season = "冬（Winter）"
            subtype = "深冬" if low_lightness else ("亮冬" if is_clear else "冷冬")

    debug = {
        "is_warm": is_warm,
        "rgb_warm_score": round(rgb_warm_score, 1),
        "hsv_h": round(hl_h, 1),
        "saturation": round(saturation, 3),
        "highlight_luminance": round(hl_lum, 1),
        "contrast": round(contrast, 1)
    }

    return season, subtype, debug, confidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="个人色彩分析取色工具")
    parser.add_argument("image", help="图片路径")
    parser.add_argument("--glasses", action="store_true", help="用户戴眼镜")
    parser.add_argument("--dyed-hair", action="store_true", help="用户染发（发色不可用）")
    args = parser.parse_args()

    colors = extract_colors(args.image, has_glasses=args.glasses, dyed_hair=args.dyed_hair)
    season, subtype, debug, confidence = analyze_season(colors)

    output = {
        "colors": colors,
        "season": season,
        "subtype": subtype,
        "confidence": confidence,
        "debug": debug
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
