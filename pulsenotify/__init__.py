import asyncio
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
event_loop = asyncio.get_event_loop()
