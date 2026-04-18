from ultralytics import YOLO
import cv2

# load model
model = YOLO("models/best.pt")

# load image (use any test image)
img = cv2.imread("uploads/input.jpg")

results = model(img)

print("DETECTIONS:", results[0].boxes)