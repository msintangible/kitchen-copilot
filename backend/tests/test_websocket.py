import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

import asyncio
import json
import httpx
import websockets

async def test_backend():
    print("1. Requesting session token...")
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8002/session/token")
        response.raise_for_status()
        data = response.json()
        token = data["token"]
        session_id = data["session_id"]
        print(f"   Got token for session: {session_id}")

    ws_url = f"ws://localhost:8002/ws?token={token}"
    print(f"2. Connecting to WebSocket at {ws_url}...")
    
    try:
        async with websockets.connect(ws_url) as ws:
            print("   Connected!")
            
            async def send_fake_audio():
                print("   [Streaming fake microphone audio...]")
                chunk = bytes([0x00]) + (b"\x00" * 8192)
                
                # A mathematically perfect 1x1 black JPEG
                valid_jpeg = bytes.fromhex(
                    "ffd8ffe000104a46494600010100000100010000ffdb00430003020202"
                    "0202030202020303030304060404040404080606050609080a0a0908"
                    "09090a0c0f0c0a0b0e0b09090d110d0e0f101011100a0c1213111012"
                    "0f101010ffdb00430103030304030408040408100b090b1010101010"
                    "10101010101010101010101010101010101010101010101010101010"
                    "10101010101010101010101010101010ffc000110800010001030122"
                    "00021101031101ffc4001f0000010501010101010100000000000000"
                    "000102030405060708090a0bffc400b5100002010303020403050504"
                    "040000017d01020300041105122131410613516107227114328191a1"
                    "082342b1c11552d1f02433627282090a161718191a25262728292a34"
                    "35363738393a434445464748494a535455565758595a636465666768"
                    "696a737475767778797a838485868788898a92939495969798999aa2"
                    "a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3"
                    "d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faff"
                    "c4001f01000301010101010101010100000000000001020304050607"
                    "08090a0bffc400b51100020102040403040705040400010277000102"
                    "031104052131061241510761711322328108144291a1b1c109233352"
                    "f0156272d10a162434e125f11718191a262728292a35363738393a43"
                    "4445464748494a535455565758595a636465666768696a7374757677"
                    "78797a82838485868788898a92939495969798999aa2a3a4a5a6a7a8"
                    "a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9"
                    "dae2e3e4e5e6e7e8e9eaf2f3f4f5f6f7f8f9faffda000c0301000211"
                    "0311003f00f9ffe5ffd9"
                )
                fake_vid = bytes([0x01]) + valid_jpeg
                
                count = 0
                while True:
                    await ws.send(chunk)
                    count += 1
                    
                    if count % 10 == 0:
                        print(f"   [Injecting valid JPEG Video frame #{count//10}...]")
                        await ws.send(fake_vid)
                        
                    await asyncio.sleep(0.25)
            
            asyncio.create_task(send_fake_audio())
            
            while True:
                message = await ws.recv()
                if isinstance(message, str):
                    print(f"   [JSON received]: {message}")
                elif isinstance(message, bytes):
                    print(f"   [Audio received]: {len(message)} bytes of PCM audio")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"\nConnection closed by server: {e}")

    except Exception as e:
        print(f"\nConnection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_backend())
