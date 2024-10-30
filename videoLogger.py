import logging

# Create a logger for your API library
# logging.basicConfig(filename='test.log',filemode='w',level=logging.DEBUG,format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger('video_translation_api_library')
logger.setLevel(logging.DEBUG)  # Set the desired logging level

# Create a handler to output logs to the console
handler = logging.FileHandler(filename='logs/test.log',mode='w')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s %(funcName)20s- %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)