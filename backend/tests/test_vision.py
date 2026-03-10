import os
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(
    api_key=os.environ['GEMINI_API_KEY'],
    http_options={'api_version': 'v1alpha'}
)

async def test_vision():
    model = "models/gemini-2.0-flash-exp"
    
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

    try:
        async with client.aio.live.connect(model=model, config=types.LiveConnectConfig()) as session:
            print("Connected.")
            # Send 15 frames over 7 seconds
            for i in range(15):
                print(f"Sending frame {i+1}...")
                await session.send_realtime_input(
                    [{"mime_type": "image/jpeg", "data": valid_jpeg}]
                )
                await asyncio.sleep(0.5)
            
            print("Successfully sent 15 valid frames.")
            await session.send(input="What do you see?", end_of_turn=True)
            async for r in session.receive():
                if r.text:
                    print(r.text)
                if r.server_content and r.server_content.turn_complete:
                    break
                    
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_vision())
