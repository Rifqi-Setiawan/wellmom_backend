"""
Script untuk mengecek model Gemini yang tersedia untuk API key Anda.
Jalankan dengan: python check_gemini_models.py
"""

import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

def check_available_models():
    """Check available Gemini models for the API key."""
    print("=" * 70)
    print("Checking Available Gemini Models")
    print("=" * 70)
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY tidak ditemukan di .env file")
        print("   Pastikan file .env berisi: GEMINI_API_KEY=your_key_here")
        return False
    
    print(f"✓ API Key ditemukan (length: {len(api_key)})")
    print(f"  Key preview: {api_key[:10]}...{api_key[-4:]}")
    print()
    
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # List all available models
        print("📋 Fetching available models...")
        print("-" * 70)
        
        models = genai.list_models()
        
        # Filter only generation models (models that support generateContent)
        generation_models = []
        for model in models:
            # Check if model supports generateContent
            if 'generateContent' in model.supported_generation_methods:
                generation_models.append(model)
        
        if not generation_models:
            print("❌ Tidak ada model yang tersedia untuk generateContent")
            print("   Mungkin API key tidak valid atau tidak memiliki akses")
            return False
        
        print(f"✅ Ditemukan {len(generation_models)} model yang tersedia:\n")
        
        # Group by model family
        model_families = {}
        for model in generation_models:
            # Extract family name (e.g., "gemini-1.5-flash" from "models/gemini-1.5-flash")
            name = model.name.replace("models/", "")
            family = name.split("-")[0] + "-" + name.split("-")[1] if "-" in name else name
            
            if family not in model_families:
                model_families[family] = []
            model_families[family].append(name)
        
        # Display models grouped by family
        for family, models_list in sorted(model_families.items()):
            print(f"📦 {family.upper()}:")
            for model_name in sorted(models_list):
                # Mark recommended models
                if "flash" in model_name.lower():
                    print(f"   ⭐ {model_name} (Recommended - Fast & Free)")
                elif "pro" in model_name.lower():
                    print(f"   💎 {model_name} (Pro - More Capable)")
                else:
                    print(f"   • {model_name}")
            print()
        
        # Test specific models
        print("=" * 70)
        print("Testing Model Initialization")
        print("=" * 70)
        
        test_models = [
            'gemini-1.5-flash-latest',
            'gemini-1.5-flash',
            'gemini-1.5-pro-latest',
            'gemini-1.5-pro',
            'gemini-pro',
        ]
        
        working_models = []
        for model_name in test_models:
            try:
                model = genai.GenerativeModel(model_name)
                print(f"✅ {model_name}: OK")
                working_models.append(model_name)
            except Exception as e:
                error_msg = str(e)
                if "404" in error_msg or "not found" in error_msg.lower():
                    print(f"❌ {model_name}: Not Found")
                else:
                    print(f"⚠️  {model_name}: Error - {error_msg[:50]}")
        
        print()
        print("=" * 70)
        print("📊 Summary")
        print("=" * 70)
        print(f"Total models available: {len(generation_models)}")
        print(f"Working models for testing: {len(working_models)}")
        
        if working_models:
            print(f"\n✅ Recommended model to use: {working_models[0]}")
            print(f"\n💡 Update app/services/chatbot_service.py dengan model ini:")
            print(f"   model_names = [")
            for model in working_models:
                print(f"       '{model}',")
            print(f"   ]")
        else:
            print("\n⚠️  Tidak ada model yang berhasil di-test")
            print("   Cek API key dan pastikan memiliki akses ke Gemini API")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nKemungkinan penyebab:")
        print("1. API key tidak valid")
        print("2. API key tidak memiliki akses ke Gemini API")
        print("3. Koneksi internet bermasalah")
        print("4. Google AI API sedang maintenance")
        return False


if __name__ == "__main__":
    success = check_available_models()
    sys.exit(0 if success else 1)
