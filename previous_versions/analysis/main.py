
import cv2
import numpy as np

def count_objects(image_path):
    """
    Counts the number of bikes, cars, and people in an image.

    Args:
        image_path: The path to the image file.

    Returns:
        A dictionary with the counts of bikes, cars, and people.
    """

    # Load YOLO model
    net = cv2.dnn.readNet("/Users/zouf/code/bike-crowding/count/yolov3.weights", "/Users/zouf/code/bike-crowding/count/yolov3.cfg")
    classes = []
    with open("/Users/zouf/code/bike-crowding/count/coco.names", "r") as f:
        classes = [line.strip() for line in f.readlines()]

    layer_names = net.getLayerNames()
    output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

    # Load image
    img = cv2.imread(image_path)
    height, width, channels = img.shape

    # Detecting objects
    blob = cv2.dnn.blobFromImage(img, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)

    # Showing information on the screen
    class_ids = []
    confidences = []
    boxes = []
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.5:
                # Object detected
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)

                # Rectangle coordinates
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)

                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)

    counts = {"bike": 0, "car": 0, "person": 0}
    for i in range(len(boxes)):
        if i in indexes:
            label = str(classes[class_ids[i]])
            if label in counts:
                counts[label] += 1

    return counts

if __name__ == "__main__":
    # Example usage
    image_path = "/Users/zouf/code/bike-crowding/collect/downloaded_images/data/Central_Park___72nd_St_Post_3/2024/11/02/16/image.jpg"
    counts = count_objects(image_path)
    print(counts)
