import requests

class BrickRecognition:
    def __init__(self):
        pass

    def recognize(self, image_bate_array: bytearray):
        # Prepare files for POST request 
        files = {'query_image': ('image.jpg', image_bate_array.data(), 'image/jpeg')}
        # Make POST request to API
        response = requests.post('https://api.brickognize.com/predict/parts', files=files)
        # Print response
        if response.status_code == 200:
            detectionData = response.json()
            bbleft = int(detectionData['bounding_box']['left'])
            bbright = int(detectionData['bounding_box']['right']) 
            bbupper = int(detectionData['bounding_box']['upper'])
            bblower = int(detectionData['bounding_box']['lower'])

            items = []
            for item in detectionData['items']:
                items.append({
                    "id": item['id'],
                    "name": item['name'],
                    "score": item['score'],
                    "type": item['type'],
                    "img_url": item['img_url']
                })

            return {
                "bb": {
                    "left": bbleft,
                    "right": bbright,
                    "upper": bbupper,
                    "lower": bblower,
                },
                "items": items,
            }
        else:
            print(f"Error: {response.status_code}", response.text)
            return None
