from PIL import Image
import hashlib

def get_hash(image):
    '''

    '''
    return hashlib.md5(Image.open(image).tobytes()).hexdigest()
