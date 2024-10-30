import asyncio
# from fastapi.testclient import TestClient
import multiprocessing
import time
from typing import Optional
import logging
from src.videotranslation.client import CircuitBreaker

def test_circuit_breaker_near_to_failure():
    circuitBreaker = CircuitBreaker(failure_threshold=3)
    circuitBreaker.record_failure()
    circuitBreaker.record_failure()
    assert circuitBreaker.state == "closed"

def test_circuit_breaker_threshold_cross():
    circuitBreaker = CircuitBreaker(failure_threshold=3)
    circuitBreaker.record_failure()
    circuitBreaker.record_failure()
    circuitBreaker.record_failure()
    assert circuitBreaker.state == "open"

def test_circuit_breaker_success_on_open():
    circuitBreaker = CircuitBreaker(failure_threshold=3)
    circuitBreaker.record_failure()
    circuitBreaker.record_failure()
    circuitBreaker.record_failure()
    circuitBreaker.record_success()
    assert circuitBreaker.state == "open" and circuitBreaker.failure_count == 0


def test_circuit_breaker_timeout_gap():
    circuitBreaker = CircuitBreaker(failure_threshold=3,reset_timeout=60)
    circuitBreaker.record_failure()
    circuitBreaker.record_failure()
    circuitBreaker.record_failure()
    time.sleep(60)
    assert circuitBreaker.can_execute() == True