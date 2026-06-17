import os
import cv2
import numpy as np

os.makedirs('templates/bings', exist_ok=True)
os.makedirs('templates/bongs', exist_ok=True)
os.makedirs('templates/ratings', exist_ok=True)

def create_mock_template(path, text, bg_color, text_color, size=(400, 400)):
    # Create an image filled with bg_color
    img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    img[:] = bg_color
    
    # Add text
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    thickness = 2
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    
    text_x = (size[0] - text_size[0]) // 2
    text_y = (size[1] + text_size[1]) // 2
    
    cv2.putText(img, text, (text_x, text_y), font, font_scale, text_color, thickness, cv2.LINE_AA)
    cv2.imwrite(path, img)

# Create mock images
create_mock_template('templates/bings/ps_logo.png', 'PS LOGO', (150, 0, 0), (255, 255, 255))
create_mock_template('templates/bongs/standard.png', 'BONG STANDARD', (0, 0, 150), (255, 255, 255))
create_mock_template('templates/bongs/french.png', 'BONG FRENCH', (0, 0, 150), (255, 255, 255))
create_mock_template('templates/ratings/esrb_teen.png', 'ESRB T', (255, 255, 255), (0, 0, 0), size=(200, 300))

print("Mock templates created.")
