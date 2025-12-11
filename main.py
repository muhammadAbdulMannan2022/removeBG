from rembg import remove
from PIL import Image

input_path = "j.png"
output_path = "output2.png"

img = Image.open(input_path)
result = remove(img)

result.save(output_path)

print("🔥 HQ background removed:", output_path)
