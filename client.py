# async_client.py
import asyncio
import aiohttp
import http.server
import random
import time
from typing import Dict,Any
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
import threading
from enum import Enum
from server import run_server

@dataclass
class TranslationResponse:
    status: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CacheManager:
    def __init__(self,ttl_seconds: int = 60):
        self._cache: Dict[str,tuple(Any,float)] = {}
        self._ttl = ttl_seconds

    def get(self,key:str) -> Optional[Any]:
        if key in self._cache:
            value,tstamp = self._cache[key]
            if time.time()-tstamp <= self._ttl:
                return value
            else:
                del self._cache[key]
                return None

    def set(self, key:str,value:Any):
        self._cache[key] = tuple(value,time.time())

class AsyncTranslationClient:
    def __init__(self, 
                 base_url: str,
                 initial_delay: float = 1.0,
                 max_delay: float = 32.0,
                 timeout: float = 300.0,
                 max_concurrent_requests: int = 3,
                 cache_ttl: int = 10):
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
        self.cache = CacheManager(cache_ttl)
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
    def _add_jitter(self, delay: float) -> float:
        """Add random jitter to avoid thundering herd problem"""
        return delay * (0.5 + random.random())

    def _get_cache_key(self,job_id: str) -> str:
        return f"status:{job_id}"
    
    async def _make_request(self, session: aiohttp.ClientSession,job_id: str) -> TranslationResponse:
        start_time = time.time()
        cache_key = self._get_cache_key(job_id)

        cached_response = self.cache.get(cache_key)

        if cached_response:
            return cached_response
        """Make async HTTP request with error handling"""
        async with self.semaphore:  # Limit concurrent requests
            try:
                print(f"{self.base_url}/status")
                async with session.get(
                    f"{self.base_url}/status",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    print("Make request response: ",response)
                    if response.status != 200:
                        return TranslationResponse(
                            status="error",
                            error=f"Server returned status {response.status}"
                        )
                    
                    data = await response.json()
                    translation_result = TranslationResponse(
                        status=data["result"]
                    )
                    if translation_result.status != "pending":
                        self.cache.set(cache_key,translation_result)
                    return translation_result
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
                                error_callback: Optional[Callable] = None,
                                job_id: str = None) -> TranslationResponse:
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
                
                response = await self._make_request(session,job_id)
                print("Response: ",response)
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
    # def run_server():
    #     server = http.server.HTTPServer(('', 8000), TranslationServer)
    #     server.serve_forever()
    
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