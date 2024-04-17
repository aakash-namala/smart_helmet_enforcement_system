pip install Ultralytics

from ultralytics import YOLO
model = "yolov8l.pt"
data = "dataset/data.yaml"
epochs = 100
imgsz = 640

yolo = YOLO()

yolo.train(
    task="detect",
    mode="train",
    model=model,
    data=data,
    epochs=epochs,
    imgsz=imgsz,
)
