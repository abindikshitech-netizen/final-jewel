from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
import base64
import mediapipe as mp
import os
from ultralytics import YOLO

ear_model = YOLO("models/best.pt")

app = FastAPI()

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

# ✅ Serve output + jewellery
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/jewelry", StaticFiles(directory="jewelry"), name="jewelry")

mp_face = mp.solutions.face_mesh
mp_hands = mp.solutions.hands


# ================= BLEND =================
def realistic_blend(bg, fg):
    alpha = fg[:, :, 3] / 255.0
    alpha = np.clip(alpha * 0.9, 0, 1)

    shadow = cv2.GaussianBlur(alpha, (25, 25), 10) * 0.25

    for c in range(3):
        bg[:, :, c] = (1 - shadow) * bg[:, :, c]
        bg[:, :, c] = alpha * fg[:, :, c] + (1 - alpha) * bg[:, :, c]

    return bg.astype(np.uint8)


# ================= ENHANCE =================
def enhance_jewellery(fg):
    rgb = fg[:, :, :3]
    rgb = cv2.convertScaleAbs(rgb, alpha=1.3, beta=10)

    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    rgb = cv2.filter2D(rgb, -1, kernel)

    fg[:, :, :3] = rgb
    return fg


# ================= LANDMARK =================
def get_points(lm, w, h):
    left = lm[234]
    right = lm[454]
    chin = lm[152]

    return (
        (int(left.x * w), int(left.y * h)),
        (int(right.x * w), int(right.y * h)),
        (int(chin.x * w), int(chin.y * h))
    )


# ================= RING HELPERS =================
def rotate_image_with_alpha(image, angle):
    h, w = image.shape[:2]
    center = (w // 2, h // 2)

    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    cos = abs(matrix[0, 0])
    sin = abs(matrix[0, 1])

    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))

    matrix[0, 2] += (new_w / 2) - center[0]
    matrix[1, 2] += (new_h / 2) - center[1]

    rotated = cv2.warpAffine(
        image,
        matrix,
        (new_w, new_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0)
    )

    return rotated


def overlay_alpha(canvas, fg, x, y):
    h, w = canvas.shape[:2]
    fh, fw = fg.shape[:2]

    if x >= w or y >= h or x + fw <= 0 or y + fh <= 0:
        return canvas

    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(w, x + fw)
    y2 = min(h, y + fh)

    fg_x1 = max(0, -x)
    fg_y1 = max(0, -y)
    fg_x2 = fg_x1 + (x2 - x1)
    fg_y2 = fg_y1 + (y2 - y1)

    roi = canvas[y1:y2, x1:x2]
    fg_crop = fg[fg_y1:fg_y2, fg_x1:fg_x2]

    if fg_crop.shape[2] < 4:
        return canvas

    alpha = fg_crop[:, :, 3] / 255.0

    for c in range(4):
        if c < 3:
            roi[:, :, c] = alpha * fg_crop[:, :, c] + (1 - alpha) * roi[:, :, c]
        else:
            roi[:, :, c] = np.maximum(roi[:, :, c], fg_crop[:, :, c])

    canvas[y1:y2, x1:x2] = roi
    return canvas


# ================= NECKLACE =================
def place_necklace(img, necklace, left, right, chin, offset_x=0, offset_y=0, scale=1.0, rotation=0):
    h, w, _ = img.shape

    # Original necklace placement logic + slider adjustment
    face_width = abs(right[0] - left[0])
    width = int(face_width * 1.25 * scale)
    width = max(width, 20)

    necklace = cv2.resize(
        necklace,
        (width, int(width * necklace.shape[0] / necklace.shape[1]))
    )

    necklace = enhance_jewellery(necklace)

    cx = (left[0] + right[0]) // 2

    x = cx - necklace.shape[1] // 2 + int(offset_x)
    y = chin[1] + int(h * 0.015) + int(offset_y)

    drop = int(necklace.shape[0] * 0.08)

    rows, cols = necklace.shape[:2]
    for i in range(cols):
        shift = int(drop * (1 - abs((i - cols / 2) / (cols / 2))))
        necklace[:, i] = np.roll(necklace[:, i], shift, axis=0)

    alpha = necklace[:, :, 3]
    alpha = cv2.GaussianBlur(alpha, (9, 9), 5)
    necklace[:, :, 3] = alpha

    if abs(rotation) > 0.01:
        necklace = rotate_image_with_alpha(necklace, rotation)
        x = cx - necklace.shape[1] // 2 + int(offset_x)
        y = chin[1] + int(h * 0.015) + int(offset_y)

    canvas = np.zeros((h, w, 4), dtype=np.uint8)
    canvas = overlay_alpha(canvas, necklace, x, y)

    return canvas


# ================= EARRINGS () =================
def place_earrings_ai(img, earring, offset_x=0, offset_y=0, scale=1.0, rotation=0):
    h, w, _ = img.shape

    results = ear_model(img)[0]
    canvas = np.zeros((h, w, 4), dtype=np.uint8)

    earlobes = []

    for box in results.boxes:
        cls = int(box.cls[0])

        if cls == 0:
            x1, y1, x2, y2 = box.xyxy[0]

            cx = int((x1 + x2) / 2)
            cy = int(y2)

            earlobes.append((cx, cy))

    earlobes = sorted(earlobes, key=lambda x: x[0])

    size = int(w * 0.07 * scale)
    size = max(size, 10)

    ear = cv2.resize(
        earring,
        (size, int(size * earring.shape[0] / earring.shape[1]))
    )

    ear = enhance_jewellery(ear)

    if abs(rotation) > 0.01:
        ear = rotate_image_with_alpha(ear, rotation)

    for i, (cx, cy) in enumerate(earlobes):

        x = cx - ear.shape[1] // 2 + int(offset_x)
        y = cy - int(ear.shape[0] * 0.1) + int(offset_y)

        if i == 1:
            ear_use = cv2.flip(ear, 1)
        else:
            ear_use = ear

        canvas = overlay_alpha(canvas, ear_use, x, y)

    return canvas


# ================= RING =================
def place_ring(img, ring, offset_x=0, offset_y=0, scale=1.0, rotation=0):
    h, w, _ = img.shape
    canvas = np.zeros((h, w, 4), dtype=np.uint8)

    with mp_hands.Hands(
        static_image_mode=True,
        max_num_hands=2,
        min_detection_confidence=0.5
    ) as hands:
        results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        if not results.multi_hand_landmarks:
            return canvas

        # Original ring logic + slider adjustment
        hand_landmarks = results.multi_hand_landmarks[0].landmark

        p1 = hand_landmarks[13]
        p2 = hand_landmarks[14]

        x1, y1 = int(p1.x * w), int(p1.y * h)
        x2, y2 = int(p2.x * w), int(p2.y * h)

        cx = (x1 + x2) // 2 + int(offset_x)
        cy = (y1 + y2) // 2 + int(offset_y)

        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1)) + float(rotation)

        finger_len = int(np.hypot(x2 - x1, y2 - y1))
        finger_len = max(finger_len, 20)

        ring_width = int(finger_len * 1.8 * scale)
        ring_width = max(ring_width, 10)
        ring_height = int(ring_width * ring.shape[0] / ring.shape[1])

        ring_resized = cv2.resize(ring, (ring_width, ring_height))
        ring_resized = enhance_jewellery(ring_resized)

        ring_rotated = rotate_image_with_alpha(ring_resized, angle)

        x = cx - ring_rotated.shape[1] // 2
        y = cy - ring_rotated.shape[0] // 2

        canvas = overlay_alpha(canvas, ring_rotated, x, y)

    return canvas


# ================= BRACELET =================
def place_bracelet(img, bracelet, offset_x=0, offset_y=0, scale=1.0, rotation=0):
    h, w, _ = img.shape
    canvas = np.zeros((h, w, 4), dtype=np.uint8)

    with mp_hands.Hands(
        static_image_mode=True,
        max_num_hands=2,
        min_detection_confidence=0.5
    ) as hands:
        results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        if not results.multi_hand_landmarks:
            return canvas

        hand_landmarks = results.multi_hand_landmarks[0].landmark

        wrist = hand_landmarks[0]
        p1 = hand_landmarks[5]
        p2 = hand_landmarks[17]

        x0, y0 = int(wrist.x * w), int(wrist.y * h)
        x1, y1 = int(p1.x * w), int(p1.y * h)
        x2, y2 = int(p2.x * w), int(p2.y * h)

        cx_palm = (x1 + x2) // 2
        cy_palm = (y1 + y2) // 2

        dx = cx_palm - x0
        dy = cy_palm - y0
        angle = np.degrees(np.arctan2(dy, dx)) + float(rotation)

        cx = int(x0 - dx * 0.3) + int(offset_x)
        cy = int(y0 - dy * 0.3) + int(offset_y)

        wrist_width = int(np.hypot(x2 - x1, y2 - y1))
        wrist_width = max(wrist_width, 40)

        bracelet_width = int(wrist_width * 1.2 * scale)
        bracelet_width = max(bracelet_width, 20)
        bracelet_height = int(bracelet_width * bracelet.shape[0] / bracelet.shape[1])

        bracelet_resized = cv2.resize(bracelet, (bracelet_width, bracelet_height))
        bracelet_resized = enhance_jewellery(bracelet_resized)

        bracelet_rotated = rotate_image_with_alpha(bracelet_resized, angle)

        x = cx - bracelet_rotated.shape[1] // 2
        y = cy - bracelet_rotated.shape[0] // 2

        canvas = overlay_alpha(canvas, bracelet_rotated, x, y)

    return canvas


# ================= API =================
@app.post("/tryon")
async def tryon(data: dict):
    try:
        img_bytes = base64.b64decode(data["image"])

        with open("uploads/input.jpg", "wb") as f:
            f.write(img_bytes)

        img = cv2.imread("uploads/input.jpg")
        if img is None:
            return {"error": "Invalid image"}

        original = img.copy()
        h, w, _ = img.shape

        jewellery = cv2.imread(
            f"jewelry/{data['item']}.png",
            cv2.IMREAD_UNCHANGED
        )

        if jewellery is None:
            return {"error": "Jewellery image not found"}

        if len(jewellery.shape) == 3 and jewellery.shape[2] == 3:
            jewellery = cv2.cvtColor(jewellery, cv2.COLOR_BGR2BGRA)

        offset_x = float(data.get("offset_x", 0))
        offset_y = float(data.get("offset_y", 0))
        scale = float(data.get("scale", 1.0))
        rotation = float(data.get("rotation", 0))

        if data["type"] == "necklace":
            with mp_face.FaceMesh(static_image_mode=True) as face:
                res = face.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

                if not res.multi_face_landmarks:
                    return {"error": "No face detected"}

                lm = res.multi_face_landmarks[0].landmark
                left, right, chin = get_points(lm, w, h)
                placed = place_necklace(
                    img, jewellery, left, right, chin,
                    offset_x=offset_x, offset_y=offset_y, scale=scale, rotation=rotation
                )

        elif data["type"] == "earring":
            with mp_face.FaceMesh(static_image_mode=True) as face:
                res = face.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

                if not res.multi_face_landmarks:
                    return {"error": "No face detected"}

            placed = place_earrings_ai(
                img, jewellery,
                offset_x=offset_x, offset_y=offset_y, scale=scale, rotation=rotation
            )

        elif data["type"] == "ring":
            placed = place_ring(
                img, jewellery,
                offset_x=offset_x, offset_y=offset_y, scale=scale, rotation=rotation
            )

            if placed[:, :, 3].max() == 0:
                return {"error": "No hand detected"}

        elif data["type"] == "bracelet":
            placed = place_bracelet(
                img, jewellery,
                offset_x=offset_x, offset_y=offset_y, scale=scale, rotation=rotation
            )

            if placed[:, :, 3].max() == 0:
                return {"error": "No hand detected"}

        else:
            return {"error": "Invalid type"}

        img = realistic_blend(img, placed)

        output = cv2.resize(img, (original.shape[1], original.shape[0]))
        cv2.imwrite("outputs/output.jpg", output)

        return {"output": "outputs/output.jpg"}

    except Exception as e:
        return {"error": str(e)}