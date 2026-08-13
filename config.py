from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not API_KEY:
    raise ValueError(
        "GOOGLE_MAPS_API_KEY not found. Make sure you have a .env file "
        "in the project root with GOOGLE_MAPS_API_KEY=your_key_here"
    )


