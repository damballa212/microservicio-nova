#!/usr/bin/env python3
"""
Script para migrar API keys desde .env al sistema de credenciales en la base de datos.
Ejecutar una vez para importar las credenciales existentes.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load .env file
load_dotenv()

from src.models.admin import (
    ApiCredentialCreate,
    CredentialProvider,
    admin_repo,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


def migrate_credentials():
    """Migrate credentials from .env to database."""
    
    migrations = []
    
    # 1. OpenRouter (uses OPENAI_API_KEY with OPENAI_BASE_URL pointing to OpenRouter)
    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_base_url = os.environ.get("OPENAI_BASE_URL", "")
    
    if openai_key and "openrouter" in openai_base_url.lower():
        migrations.append(ApiCredentialCreate(
            provider=CredentialProvider.OPENROUTER,
            name="Production (from .env)",
            api_key=openai_key,
            base_url=openai_base_url,
            is_default=True,
        ))
        print(f"✅ Found OpenRouter key: {openai_key[:10]}...{openai_key[-4:]}")
    elif openai_key:
        # It's a direct OpenAI key
        migrations.append(ApiCredentialCreate(
            provider=CredentialProvider.OPENAI,
            name="Production (from .env)",
            api_key=openai_key,
            base_url=openai_base_url or None,
            is_default=True,
        ))
        print(f"✅ Found OpenAI key: {openai_key[:10]}...{openai_key[-4:]}")
    
    # 2. Google Gemini
    google_key = os.environ.get("GOOGLE_API_KEY")
    if google_key:
        migrations.append(ApiCredentialCreate(
            provider=CredentialProvider.GOOGLE,
            name="Production (from .env)",
            api_key=google_key,
            base_url=None,
            is_default=True,
        ))
        print(f"✅ Found Google key: {google_key[:10]}...{google_key[-4:]}")
    
    # 3. Cohere
    cohere_key = os.environ.get("COHERE_API_KEY")
    if cohere_key:
        migrations.append(ApiCredentialCreate(
            provider=CredentialProvider.COHERE,
            name="Production (from .env)",
            api_key=cohere_key,
            base_url=None,
            is_default=True,
        ))
        print(f"✅ Found Cohere key: {cohere_key[:10]}...{cohere_key[-4:]}")
    
    if not migrations:
        print("⚠️  No API keys found in .env to migrate.")
        return
    
    print(f"\n📦 Migrating {len(migrations)} credential(s) to database...\n")
    
    for cred in migrations:
        try:
            # Check if credential already exists for this provider
            existing = admin_repo.list_credentials(cred.provider)
            if existing:
                print(f"⏭️  Skipping {cred.provider.value}: already has {len(existing)} credential(s)")
                continue
            
            credential_id = admin_repo.create_credential(cred)
            if credential_id:
                print(f"✅ Created {cred.provider.value} credential: {cred.name}")
            else:
                print(f"❌ Failed to create {cred.provider.value} credential")
        except Exception as e:
            print(f"❌ Error creating {cred.provider.value}: {e}")
    
    print("\n🎉 Migration complete!")
    print("\n📌 Next steps:")
    print("   1. Go to http://localhost:3000/admin/settings")
    print("   2. Verify credentials in 'API Credentials' section")
    print("   3. Test each credential using the 'Test' button")
    print("   4. (Optional) Remove the keys from .env file")


if __name__ == "__main__":
    migrate_credentials()
