from PIL import Image
import os

def check_ico(ico_path):
    try:
        # Open the ICO file
        img = Image.open(ico_path)
        # Print all sizes contained in the ICO
        print(f"Icon sizes found: {img.info.get('sizes', 'No sizes info found')}")
        return True
    except Exception as e:
        print(f"Error reading icon: {e}")
        return False

# Test the icon file
ico_path = 'metalsnake.ico'
if os.path.exists(ico_path):
    print(f"Icon file found at {os.path.abspath(ico_path)}")
    check_ico(ico_path)
else:
    print("Icon file not found!")