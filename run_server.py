import threading
from src.videotranslation.server import run_server

server_thread = threading.Thread(target=run_server)
# server_thread.daemon = True
server_thread.start()

