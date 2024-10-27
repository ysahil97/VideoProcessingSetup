import http.server
import json
import time
import random
from urllib.parse import urlparse

class TranslationJob:
    def __init__(self, expected_duration,error_percentage=0.1):
        self.start_time = time.time()
        self.expected_duration = expected_duration
        self.status = "pending"
        self.error_percentage = error_percentage
        
    def get_status(self):
        if self.status != "pending":
            return self.status
            
        elapsed_time = time.time() - self.start_time
        
        if elapsed_time >= self.expected_duration:
            # 10% chance of error
            self.status = "error" if random.random() < self.error_percentage else "completed"
            
        return self.status

class TranslationServer(http.server.SimpleHTTPRequestHandler):
    # Class variable to store the translation job
    translation_job = TranslationJob(expected_duration=60)  # 60 seconds for testing
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/status":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            status = self.translation_job.get_status()
            response = json.dumps({"result": status})
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

def run_server():
    """Start the translation status server"""
    server_address = ('', 8000)
    httpd = http.server.HTTPServer(server_address, TranslationServer)
    print("Server running on port 8000...")
    httpd.serve_forever()