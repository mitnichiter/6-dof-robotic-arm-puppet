import asyncio
from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager

async def main():
    try:
        manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
        session = manager.get_current_session()
        if session:
            print(f"Session found: {session.source_app_user_model_id}")
            props = await session.try_get_media_properties_async()
            print(f"Playing: {props.title} by {props.artist}")
            
            # Check playback status (4 = playing, 5 = paused)
            info = session.get_playback_info()
            print(f"Status: {info.playback_status}")
        else:
            print("No active media session found.")
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
