# async_client.py
import asyncio
import aiohttp
import http.server
import random
import time
from typing import Dict,Any
from functools import lru_cache
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
import threading
import logging
# from enum import Enum
from videoLogger import logger
from src.videotranslation.server import run_server,VideoTranslationStatus

# Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

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
            logger.debug(f"key is in cache")
            value,tstamp = self._cache[key]
            if time.time()-tstamp <= self._ttl:
                logger.debug(f"Key {key} is within ttl")
                return value
            else:
                logger.debug(f"Key {key} is outside ttl, deleting it")
                del self._cache[key]
                return None

    def set(self, key:str,value:Any):
        self._cache[key] = (value,time.time())


class CircuitBreaker:
    def __init__(self,failure_threshold: int = 5,reset_timeout: int=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time = 0
        self.state = "closed"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            logger.error(f"Error threshold is broken, system is faulty")
            self.state = "open"

    def record_success(self):
        if self.state == "half-open":
            self.state = "closed"
        self.failure_count = 0

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time >= self.reset_timeout:
                self.state = "half-open"
                return True
        return self.state == "half-open"

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
        self.circuit_breaker = CircuitBreaker()
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
    def _add_jitter(self, delay: float) -> float:
        """Add random jitter to avoid thundering herd problem"""
        logger.debug("Setting up the jitter")
        return delay * (0.5 + random.random())

    @lru_cache(maxsize=1000)
    def _get_cache_key(self,job_id: str) -> str:
        return f"status:{job_id}"
    
    async def _make_request(self, session: aiohttp.ClientSession,job_id: str) -> TranslationResponse:
        start_time = time.time()
        cache_key = self._get_cache_key(job_id)

        cached_response = self.cache.get(cache_key)
        logger.debug(f"Cached Response: {cached_response}")
        if cached_response:
            return cached_response
        
        if not self.circuit_breaker.can_execute():
            return TranslationResponse(
                status=VideoTranslationStatus.ERROR,
                error=f"CircuitBreaker is in open state, system is faulty" 
            )
        """Make async HTTP request with error handling"""
        async with self.semaphore:  # Limit concurrent requests
            try:
                logger.debug(f"URL: {self.base_url}/status")
                async with session.get(
                    f"{self.base_url}/status",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    print("Make request response: ",response)
                    if response.status != 200:
                        self.circuit_breaker.record_failure()
                        return TranslationResponse(
                            status=VideoTranslationStatus.ERROR,
                            error=f"Server returned status {response.status}"
                        )
                    
                    data = await response.json()
                    logger.debug(f"response data {data}")
                    translation_result = TranslationResponse(
                        status=data["result"]
                    )
                    if translation_result.status != VideoTranslationStatus.PENDING:
                        self.cache.set(cache_key,translation_result)
                    self.circuit_breaker.record_success()
                    return translation_result
            except asyncio.TimeoutError:
                logger.error("Request Timed out")
                return TranslationResponse(
                    status=VideoTranslationStatus.ERROR,
                    error="Request timed out"
                )
            except Exception as e:
                logger.critical(f"Exception: {e}")
                self.circuit_breaker.record_failure()
                return TranslationResponse(
                    status=VideoTranslationStatus.ERROR,
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
                    error_msg = "Timeout waiting for translation completion"
                    logger.critical(f"Exception: {error_msg}")
                    raise Exception(error_msg)
                
                response = await self._make_request(session,job_id)
                logger.debug(response)
                if response.status == "error":
                    consecutive_errors += 1
                    logger.error(f"Incrementing error count to {consecutive_errors}")
                    if consecutive_errors >= 3:
                        if error_callback:
                            
                            await error_callback(response.error)
                        logger.error(f"Multiple consecutive errors: {response.error}")
                        raise Exception(f"Multiple consecutive errors: {response.error}")
                else:
                    consecutive_errors = 0
                
                if progress_callback:
                    logger.debug(f"recording progress for the response {response}")
                    progress_callback(response)
                
                if response.status in ["completed", "error"]:
                    logger.debug(f"Response is either completed or error")
                    return response
                
                # Add jitter and wait
                delay = self._add_jitter(current_delay)
                await asyncio.sleep(delay)
                
                # Increase delay for next iteration
                logger.debug(f"Adding delay to the current delay value")
                current_delay = min(current_delay * 2, self.max_delay)
                logger.debug(f"New Delay Value: {current_delay}")
    
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