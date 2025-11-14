import requests


class BrickRecognition:
    def __init__(self):
        pass

    def recognize(
        self, image_bate_array: bytearray, image_width: int, image_height: int
    ):
        # Prepare files for POST request
        files = {"query_image": ("image.jpg", image_bate_array, "image/jpeg")}
        # Make POST request to API
        response = requests.post(
            "https://api.brickognize.com/predict/parts", files=files
        )
        # Print response
        if response.status_code == 200:
            detectionData = response.json()

            if detectionData is None or "bounding_box" not in detectionData:
                return None

            imgW = float(detectionData["bounding_box"]["image_width"])
            imgH = float(detectionData["bounding_box"]["image_height"])

            if imgW == 0 or imgH == 0:
                return None

            bbleft = float(detectionData["bounding_box"]["left"]) / imgW * image_width
            bbright = float(detectionData["bounding_box"]["right"]) / imgW * image_width
            bbupper = (
                float(detectionData["bounding_box"]["upper"]) / imgH * image_height
            )
            bblower = (
                float(detectionData["bounding_box"]["lower"]) / imgH * image_height
            )

            items = []
            for item in detectionData["items"]:
                items.append(
                    {
                        "id": item["id"],
                        "name": item["name"],
                        "score": item["score"],
                        "type": item["type"],
                        "img_url": item["img_url"],
                    }
                )

            return {
                "bb": {
                    "left": int(round(bbleft)),
                    "right": int(round(bbright)),
                    "upper": int(round(bbupper)),
                    "lower": int(round(bblower)),
                },
                "items": items,
            }
        else:
            print(f"Error: {response.status_code}", response.text)
            return None
