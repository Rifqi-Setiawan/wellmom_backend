"""
Test script untuk chatbot service.
Jalankan dengan: python test_chatbot_service.py
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.chatbot_service import ChatbotService
from app.config import settings


async def test_chatbot():
    """Test chatbot service initialization and basic chat."""
    print("=" * 60)
    print("Testing WellMom Chatbot Service")
    print("=" * 60)
    
    # Check API key
    if not settings.GEMINI_API_KEY:
        print("❌ ERROR: GEMINI_API_KEY tidak ditemukan di environment variables")
        print("   Pastikan file .env berisi: GEMINI_API_KEY=your_key_here")
        return False
    
    print(f"✓ GEMINI_API_KEY ditemukan (length: {len(settings.GEMINI_API_KEY)})")
    
    # Test initialization
    try:
        print("\n1. Testing service initialization...")
        service = ChatbotService()
        print(f"✓ Service initialized successfully")
        print(f"  Model name: {getattr(service, 'model_name', 'unknown')}")
    except Exception as e:
        print(f"❌ Failed to initialize service: {str(e)}")
        return False
    
    # Test basic chat
    try:
        print("\n2. Testing basic chat (no history)...")
        response, input_tokens, output_tokens = await service.chat(
            message="Halo, apa kabar?",
            history=None,
            timeout=30
        )
        print(f"✓ Chat successful")
        print(f"  Response: {response[:100]}...")
        print(f"  Input tokens: {input_tokens}")
        print(f"  Output tokens: {output_tokens}")
    except Exception as e:
        print(f"❌ Chat failed: {str(e)}")
        return False
    
    # Test with history
    try:
        print("\n3. Testing chat with history...")
        history = [
            {"role": "user", "parts": ["Halo"]},
            {"role": "model", "parts": ["Halo! Ada yang bisa saya bantu?"]}
        ]
        response, input_tokens, output_tokens = await service.chat(
            message="Apa saja makanan yang baik untuk ibu hamil?",
            history=history,
            timeout=30
        )
        print(f"✓ Chat with history successful")
        print(f"  Response: {response[:100]}...")
        print(f"  Input tokens: {input_tokens}")
        print(f"  Output tokens: {output_tokens}")
    except Exception as e:
        print(f"❌ Chat with history failed: {str(e)}")
        return False
    
    # Test token counting
    try:
        print("\n4. Testing token counting...")
        test_text = "Ini adalah teks uji untuk menghitung token"
        token_count = service.count_tokens(test_text)
        print(f"✓ Token counting works")
        print(f"  Text: '{test_text}'")
        print(f"  Estimated tokens: {token_count}")
    except Exception as e:
        print(f"❌ Token counting failed: {str(e)}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_chatbot())
    sys.exit(0 if success else 1)
