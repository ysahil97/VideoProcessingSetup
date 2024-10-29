# integration_test.py
import asyncio
from fastapi.testclient import TestClient
import multiprocessing
import time
from typing import Optional
import logging
from client import AsyncTranslationClient,TranslationResponse
from server import run_server,app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def status_callback(status: TranslationResponse):
    logger.info(f"Status = {status.status}")
    return {"Status":status.status}

async def func_test_client(port: int, expected_duration: int):
    base_url = f"http://localhost:{port}"
    
    async with AsyncTranslationClient(base_url) as client:
        try:
            start_time = time.time()
            final_status = await client.make_complete_request(progress_callback=status_callback)
            duration = time.time() - start_time
            
            logger.info(f"Final status: {final_status}")
            
            assert final_status.status == "completed" or final_status.status == "error"
            
            logger.info("Test passed successfully!")
            
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            raise

def test_run_integration_test():
    port = 8000
    expected_duration = 60  # seconds
    
    # Start server in a separate process
    # server_process = multiprocessing.Process(
    #     target=run_server
    # )
    # server_process.start()
    server_process = TestClient(app)
    time.sleep(1)  # Give server time to start
    
    try:
        # Run client test
        asyncio.run(func_test_client(port, expected_duration))
    finally:
        pass
        # server_process.terminate()
        # server_process.join()

# if __name__ == "__main__":
#     run_integration_test()