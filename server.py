# import http.server
from fastapi import FastAPI, HTTPException
import uvicorn
import json
import time
import random
from typing import Dict
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


app = FastAPI()
jobs: Dict[str, TranslationJob] = {}

@app.get("/status")
async def get_status():
    if len(jobs) == 1:
        jkey = list(jobs.keys())[0]
        status = jobs[jkey].get_status()
        return {"result":status}

def run_server():
    """Start the translation status server"""
    # server_address = ('', 8000)
    # httpd = http.server.HTTPServer(server_address, TranslationServer)
    jobs["job_one"] = TranslationJob(expected_duration=60)
    uvicorn.run(app,host="127.0.0.1",port=8000)
    print("Server running on port 8000...")
    # httpd.serve_forever()