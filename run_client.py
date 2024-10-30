from src.videotranslation.client import AsyncTranslationClient
import asyncio
from src.videotranslation.server import job_one

client = AsyncTranslationClient("http://localhost:8000")

async def handle_progress(status):
    print(f"Status: {status.status}")

# result = await client.make_complete_request(
#     progress_callback=handle_progress
# )

asyncio.run(client.make_complete_request(
    progress_callback=handle_progress,
    job_id = job_one
))

print("video process")