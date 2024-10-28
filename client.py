# async_client.py
import asyncio
import aiohttp
import http.server
import random
import time
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
import threading
from enum import Enum
from server import TranslationServer

@dataclass
class TranslationResponse:
    status: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AsyncTranslationClient:
    def __init__(self, 
                 base_url: str,
                 initial_delay: float = 1.0,
                 max_delay: float = 32.0,
                 timeout: float = 300.0,
                 max_concurrent_requests: int = 3):
        """
        Initialize the async translation client
        
        Args:
            base_url: Server base URL
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            timeout: Maximum total time to wait for completion
            max_concurrent_requests: Maximum number of concurrent requests
        """
        self.base_url = base_url.rstrip('/')
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
    def _add_jitter(self, delay: float) -> float:
        """Add random jitter to avoid thundering herd problem"""
        return delay * (0.5 + random.random())
    
    async def _make_request(self, session: aiohttp.ClientSession) -> TranslationResponse:
        """Make async HTTP request with error handling"""
        async with self.semaphore:  # Limit concurrent requests
            try:
                async with session.get(
                    f"{self.base_url}/status",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return TranslationResponse(
                            status="error",
                            error=f"Server returned status {response.status}"
                        )
                    
                    data = await response.json()
                    return TranslationResponse(
                        status=data["result"]
                    )
                    
            except asyncio.TimeoutError:
                return TranslationResponse(
                    status="error",
                    error="Request timed out"
                )
            except Exception as e:
                return TranslationResponse(
                    status="error",
                    error=str(e)
                )

    async def make_complete_request(self,
                                progress_callback: Optional[Callable] = None,
                                error_callback: Optional[Callable] = None) -> TranslationResponse:
        """
        Asynchronously wait for translation completion
        
        Args:
            progress_callback: Optional async function to receive status updates
            error_callback: Optional async function to receive error notifications
        
        Returns:
            TranslationResponse: Final translation status
            
        Raises:
            Exception: If timeout occurs or maximum retries exceeded
        """
        start_time = time.time()
        current_delay = self.initial_delay
        consecutive_errors = 0
        
        async with aiohttp.ClientSession() as session:
            while True:
                # Check timeout
                if time.time() - start_time > self.timeout:
                    raise Exception("Timeout waiting for translation completion")
                
                response = await self._make_request(session)
                
                if response.status == "error":
                    consecutive_errors += 1
                    if consecutive_errors >= 3:
                        if error_callback:
                            await error_callback(response.error)
                        raise Exception(f"Multiple consecutive errors: {response.error}")
                else:
                    consecutive_errors = 0
                
                if progress_callback:
                    progress_callback(response)
                
                if response.status in ["completed", "error"]:
                    return response
                
                # Add jitter and wait
                delay = self._add_jitter(current_delay)
                await asyncio.sleep(delay)
                
                # Increase delay for next iteration
                current_delay = min(current_delay * 2, self.max_delay)
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

# Example usage
async def main():
    def run_server():
        server = http.server.HTTPServer(('', 8000), TranslationServer)
        server.serve_forever()
    
    # Start server in a thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Give server time to start
    await asyncio.sleep(1)
    
    client = AsyncTranslationClient(
        base_url="http://localhost:8000",
        initial_delay=1.0,
        max_delay=16.0,
        timeout=120.0
    )
    
    async def print_progress(status):
        print(f"Current status: {status.status.value}")
    
    async def print_error(error):
        print(f"Error: {error}")
    
    try:
        # Single job monitoring
        result = await client.make_complete_request(
            progress_callback=print_progress,
            error_callback=print_error
        )
        print(f"Translation finished with status: {result.status.value}")
        

        
    except Exception as e:
        print(f"Failed to get translation status: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())