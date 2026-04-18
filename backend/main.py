from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
import base64
import mediapipe as mp
import os
from ultralytics import YOLO

# ✅ AI IMPORTS
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet
import torch

# ================= MODEL =================
ear_model = YOLO("models/best.pt")

app = FastAPI()

# ================= AI ENHANCER =================
print("🔄 Loading RealESRGAN model...")

model = RRDBNet(
    num_in_ch=3,
    num_out_ch=3,
    num_feat=64,
    num_block=23,
    num_grow_ch=32,
    scale=2,
)

device = "cuda" if torch.cuda.is_available() else "cpu"

enhancer = RealESRGANer(
    scale=2,
    model_path="weights/RealESRGAN_x2plus.pth",
    model=model,
    tile=0,
    tile_pad=10,
    pre_pad=0,
    half=False,
    device=device,
)

print("✅ RealESRGAN loaded successfully")

# ================= CORS =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= FOLDERS =================
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/jewelry", StaticFiles(directory="jewelry"), name="jewelry")

mp_face = mp.solutions.face_mesh


# ================= SAFE RGBA =================
def ensure_rgba(img):
    if img is None:
        return None
    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
    if img.shape[2] == 3:
        alpha = np.ones((img.shape[0], img.shape[1]), dtype=np.uint8) * 255
        return np.dstack((img, alpha))
    return img


# ================= ENHANCE =================
def enhance_jewellery(fg):
    rgb = fg[:, :, :3].astype(np.float32)

    gray = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_BGR2GRAY)

    bright_mask = gray > 180
    dark_mask = gray <= 180

    rgb[dark_mask] *= 1.25
    rgb[dark_mask] += 10

    rgb[bright_mask] *= 1.05

    rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    rgb = cv2.filter2D(rgb, -1, kernel)

    fg[:, :, :3] = rgb
    return fg


# ================= ROI AI ENHANCE =================
def ai_enhance_roi(img, x, y, w, h):
    try:
        print("🚀 AI ROI enhancement running...")

        # Clamp
        x = max(0, x)
        y = max(0, y)
        w = min(w, img.shape[1] - x)
        h = min(h, img.shape[0] - y)

        if w <= 0 or h <= 0:
            return img

        roi = img[y:y+h, x:x+w]

        # Resize small (speed boost)
        roi_small = cv2.resize(roi, (max(64, w//2), max(64, h//2)))

        output, _ = enhancer.enhance(roi_small, outscale=1)

        output = cv2.resize(output, (w, h))

        img[y:y+h, x:x+w] = output

        print("✅ AI ROI enhancement done")
        return img

    except Exception as e:
        print("❌ AI ERROR:", e)
        return img


# ================= BLEND =================
def realistic_blend(bg, fg):
    if fg is None or fg.shape[2] < 4:
        return bg

    alpha = fg[:, :, 3] / 255.0
    alpha = np.clip(alpha, 0, 1)

    shadow = cv2.GaussianBlur(alpha, (25, 25), 10) * 0.2

    for c in range(3):
        bg[:, :, c] = bg[:, :, c] * (1 - shadow)
        bg[:, :, c] = alpha * fg[:, :, c] + (1 - alpha) * bg[:, :, c]

    return np.clip(bg, 0, 255).astype(np.uint8)


# ================= LANDMARK =================
def get_points(lm, w, h):
    left = lm[234]
    right = lm[454]
    chin = lm[152]

    return (
        (int(left.x*w), int(left.y*h)),
        (int(right.x*w), int(right.y*h)),
        (int(chin.x*w), int(chin.y*h))
    )


# ================= NECKLACE =================
def place_necklace(img, necklace, left, right, chin):
    print("📿 Processing necklace...")

    h, w, _ = img.shape

    necklace = ensure_rgba(necklace)
    if necklace is None:
        return np.zeros((h, w, 4), dtype=np.uint8)

    face_width = abs(right[0] - left[0])
    width = int(face_width * 1.25)

    necklace = cv2.resize(
        necklace,
        (width, int(width * necklace.shape[0] / necklace.shape[1]))
    )

    necklace = enhance_jewellery(necklace)

    cx = (left[0] + right[0]) // 2
    x = cx - necklace.shape[1] // 2
    y = chin[1] + int(h * 0.02)

    rows, cols = necklace.shape[:2]
    drop = int(rows * 0.06)

    for i in range(cols):
        t = (i - cols / 2) / (cols / 2)
        shift = int(drop * (1 - t**2))

        if shift > 0:
            necklace[shift:, i] = necklace[:-shift, i]
            necklace[:shift, i] = 0

    canvas = np.zeros((h, w, 4), dtype=np.uint8)

    x = max(0, min(x, w - necklace.shape[1]))
    y = max(0, min(y, h - necklace.shape[0]))

    canvas[y:y+necklace.shape[0], x:x+necklace.shape[1]] = necklace

    return canvas


# ================= EARRINGS (UNCHANGED) =================
def place_earrings_ai(img, earring):
    print("💎 Processing earrings...")

    h, w, _ = img.shape
    results = ear_model(img)[0]

    canvas = np.zeros((h, w, 4), dtype=np.uint8)
    earlobes = []

    for box in results.boxes:
        if int(box.cls[0]) == 0:
            x1, y1, x2, y2 = box.xyxy[0]
            cx = int((x1 + x2) / 2)
            cy = int(y2)
            earlobes.append((cx, cy))

    earlobes = sorted(earlobes, key=lambda x: x[0])

    size = int(w * 0.07)

    ear = cv2.resize(
        earring,
        (size, int(size * earring.shape[0] / earring.shape[1]))
    )

    ear = enhance_jewellery(ear)

    for i, (cx, cy) in enumerate(earlobes):
        x = cx - ear.shape[1] // 2
        y = cy - int(ear.shape[0] * 0.1)

        ear_use = cv2.flip(ear, 1) if i == 1 else ear

        if 0 <= x < w - ear_use.shape[1] and 0 <= y < h - ear_use.shape[0]:
            canvas[y:y+ear_use.shape[0], x:x+ear_use.shape[1]] = ear_use

    return canvas


# ================= API =================
@app.post("/tryon")
async def tryon(data: dict):
    try:
        print("📥 Request:", data["type"])

        img_bytes = base64.b64decode(data["image"])

        with open("uploads/input.jpg", "wb") as f:
            f.write(img_bytes)

        img = cv2.imread("uploads/input.jpg")
        original = img.copy()

        h, w, _ = img.shape

        with mp_face.FaceMesh(static_image_mode=True) as face:
            res = face.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

            if not res.multi_face_landmarks:
                return {"error": "No face detected"}

            lm = res.multi_face_landmarks[0].landmark

            jewellery = cv2.imread(
                f"jewelry/{data['item']}.png",
                cv2.IMREAD_UNCHANGED
            )

            jewellery = ensure_rgba(jewellery)

            if data["type"] == "necklace":
                left, right, chin = get_points(lm, w, h)
                placed = place_necklace(img, jewellery, left, right, chin)

            elif data["type"] == "earring":
                placed = place_earrings_ai(img, jewellery)

            else:
                return {"error": "Invalid type"}

            img = realistic_blend(img, placed)

            # 🔥 ONLY NECKLACE → AI
            if data["type"] == "necklace":
                x = left[0] - 50
                y = chin[1]
                w_roi = abs(right[0] - left[0]) + 100
                h_roi = int(h * 0.25)

                img = ai_enhance_roi(img, x, y, w_roi, h_roi)

        output = cv2.resize(img, (original.shape[1], original.shape[0]))
        cv2.imwrite("outputs/output.jpg", output)

        print("✅ Output generated")

        return {"output": "outputs/output.jpg"}

    except Exception as e:
        print("❌ API ERROR:", e)
        return {"error": str(e)}