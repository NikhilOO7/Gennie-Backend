# app/services/__init__.py
"""
Services Package - Business logic and external service integrations
COMPLETE VERSION with enhanced voice processing capabilities and full backward compatibility
"""

import logging

logger = logging.getLogger(__name__)

# Import core services (always available)
from app.services.gemini_service import gemini_service
from app.services.emotion_service import emotion_service
from app.services.personalization import personalization_service

# Try to import enhanced services first (preferred)
try:
    from app.services.enhanced_speech_service import enhanced_speech_service
    from app.services.enhanced_tts_service import enhanced_tts_service
    
    # Use enhanced services as primary
    speech_service = enhanced_speech_service
    tts_service = enhanced_tts_service
    
    ENHANCED_VOICE_AVAILABLE = True
    logger.info("✅ Enhanced voice services loaded successfully")
    
except ImportError as e:
    logger.warning(f"Enhanced voice services not available: {str(e)}")
    
    # Fallback to original services
    try:
        from app.services.speech_service import speech_service
        from app.services.tts_service import tts_service
        ENHANCED_VOICE_AVAILABLE = False
        logger.info("✅ Original voice services loaded as fallback")
    except ImportError as e2:
        logger.warning(f"Original voice services also not available: {str(e2)}")
        # If no voice services available, create placeholder
        speech_service = None
        tts_service = None
        ENHANCED_VOICE_AVAILABLE = False

# Try to import RAG service (enhanced or basic)
try:
    from app.services.enhanced_rag_service import enhanced_rag_service as rag_service
    ENHANCED_RAG_AVAILABLE = True
    logger.info("✅ Enhanced RAG service loaded")
except ImportError:
    try:
        from app.services.rag_service import rag_service
        ENHANCED_RAG_AVAILABLE = False
        logger.info("✅ Original RAG service loaded as fallback")
    except ImportError:
        rag_service = None
        ENHANCED_RAG_AVAILABLE = False
        logger.warning("❌ No RAG service available")

# Try to import prompt service
try:
    from app.services.prompt_service import prompt_service
    logger.info("✅ Prompt service loaded")
except ImportError:
    prompt_service = None
    logger.warning("❌ Prompt service not available")

# Try to import additional services
try:
    from app.services.audio_processor import audio_processor
    logger.info("✅ Audio processor loaded")
except ImportError:
    audio_processor = None
    logger.warning("❌ Audio processor not available")

try:
    from app.services.vector_service import vector_service
    logger.info("✅ Vector service loaded")
except ImportError:
    vector_service = None
    logger.warning("❌ Vector service not available")

try:
    from app.services.topics_service import topics_service
    logger.info("✅ Topics service loaded")
except ImportError:
    topics_service = None
    logger.warning("❌ Topics service not available")

try:
    from app.services.voice_streaming_service import voice_streaming_service
    logger.info("✅ Voice streaming service loaded")
except ImportError:
    voice_streaming_service = None
    logger.warning("❌ Voice streaming service not available")

# Export services based on availability
__all__ = [
    "gemini_service",
    "emotion_service", 
    "personalization_service"
]

# Add voice services if available
if speech_service is not None:
    __all__.extend(["speech_service"])
if tts_service is not None:
    __all__.extend(["tts_service"])

# Add enhanced services if available
if ENHANCED_VOICE_AVAILABLE:
    __all__.extend(["enhanced_speech_service", "enhanced_tts_service"])

# Add RAG service if available
if rag_service is not None:
    __all__.append("rag_service")

# Add prompt service if available
if prompt_service is not None:
    __all__.append("prompt_service")

# Add additional services if available
if audio_processor is not None:
    __all__.append("audio_processor")
if vector_service is not None:
    __all__.append("vector_service")
if topics_service is not None:
    __all__.append("topics_service")
if voice_streaming_service is not None:
    __all__.append("voice_streaming_service")

# Feature flags for other modules to check
FEATURES = {
    "enhanced_voice": ENHANCED_VOICE_AVAILABLE,
    "enhanced_rag": ENHANCED_RAG_AVAILABLE,
    "basic_voice": speech_service is not None and tts_service is not None,
    "rag": rag_service is not None,
    "prompts": prompt_service is not None,
    "audio_processing": audio_processor is not None,
    "vector_search": vector_service is not None,
    "topic_analysis": topics_service is not None,
    "voice_streaming": voice_streaming_service is not None
}

def get_available_services():
    """Get a dictionary of available services"""
    services = {
        "gemini": gemini_service,
        "emotion": emotion_service,
        "personalization": personalization_service
    }
    
    if speech_service is not None:
        services["speech"] = speech_service
    if tts_service is not None:
        services["tts"] = tts_service
    if rag_service is not None:
        services["rag"] = rag_service
    if prompt_service is not None:
        services["prompt"] = prompt_service
    if audio_processor is not None:
        services["audio_processor"] = audio_processor
    if vector_service is not None:
        services["vector"] = vector_service
    if topics_service is not None:
        services["topics"] = topics_service
    if voice_streaming_service is not None:
        services["voice_streaming"] = voice_streaming_service
    
    return services

def get_feature_status():
    """Get the status of enhanced features"""
    return FEATURES.copy()

def check_voice_capabilities():
    """Check what voice capabilities are available"""
    capabilities = {
        "basic_stt": speech_service is not None,
        "basic_tts": tts_service is not None,
        "enhanced_stt": ENHANCED_VOICE_AVAILABLE,
        "enhanced_tts": ENHANCED_VOICE_AVAILABLE,
        "voice_activity_detection": ENHANCED_VOICE_AVAILABLE,
        "audio_preprocessing": ENHANCED_VOICE_AVAILABLE,
        "smart_ssml": ENHANCED_VOICE_AVAILABLE,
        "emotion_based_voices": ENHANCED_VOICE_AVAILABLE,
        "streaming_synthesis": ENHANCED_VOICE_AVAILABLE,
        "real_time_streaming": ENHANCED_VOICE_AVAILABLE
    }
    
    # Check for optional dependencies
    try:
        import webrtcvad
        capabilities["webrtc_vad"] = True
    except ImportError:
        capabilities["webrtc_vad"] = False
    
    try:
        import pydub
        capabilities["audio_enhancement"] = True
    except ImportError:
        capabilities["audio_enhancement"] = False
    
    try:
        import numpy
        capabilities["numpy_processing"] = True
    except ImportError:
        capabilities["numpy_processing"] = False
    
    return capabilities

def get_service_health():
    """Get health status of all services"""
    health = {
        "core_services": {
            "gemini": {"status": "healthy", "available": True},
            "emotion": {"status": "healthy", "available": True},
            "personalization": {"status": "healthy", "available": True}
        },
        "voice_services": {
            "speech": {"status": "healthy" if speech_service else "unavailable", "available": speech_service is not None, "enhanced": ENHANCED_VOICE_AVAILABLE},
            "tts": {"status": "healthy" if tts_service else "unavailable", "available": tts_service is not None, "enhanced": ENHANCED_VOICE_AVAILABLE}
        },
        "optional_services": {
            "rag": {"status": "healthy" if rag_service else "unavailable", "available": rag_service is not None, "enhanced": ENHANCED_RAG_AVAILABLE},
            "prompt": {"status": "healthy" if prompt_service else "unavailable", "available": prompt_service is not None},
            "audio_processor": {"status": "healthy" if audio_processor else "unavailable", "available": audio_processor is not None},
            "vector": {"status": "healthy" if vector_service else "unavailable", "available": vector_service is not None},
            "topics": {"status": "healthy" if topics_service else "unavailable", "available": topics_service is not None},
            "voice_streaming": {"status": "healthy" if voice_streaming_service else "unavailable", "available": voice_streaming_service is not None}
        }
    }
    
    return health

def initialize_all_services():
    """Initialize all available services"""
    initialized = []
    failed = []
    
    # Initialize core services
    try:
        # These should already be initialized on import
        initialized.extend(["gemini_service", "emotion_service", "personalization_service"])
    except Exception as e:
        failed.append(("core_services", str(e)))
    
    # Initialize voice services
    if speech_service:
        try:
            if hasattr(speech_service, 'initialize'):
                speech_service.initialize()
            initialized.append("speech_service")
        except Exception as e:
            failed.append(("speech_service", str(e)))
    
    if tts_service:
        try:
            if hasattr(tts_service, 'initialize'):
                tts_service.initialize()
            initialized.append("tts_service")
        except Exception as e:
            failed.append(("tts_service", str(e)))
    
    # Initialize optional services
    optional_services = [
        ("rag_service", rag_service),
        ("prompt_service", prompt_service),
        ("audio_processor", audio_processor),
        ("vector_service", vector_service),
        ("topics_service", topics_service),
        ("voice_streaming_service", voice_streaming_service)
    ]
    
    for service_name, service in optional_services:
        if service:
            try:
                if hasattr(service, 'initialize'):
                    service.initialize()
                initialized.append(service_name)
            except Exception as e:
                failed.append((service_name, str(e)))
    
    return {
        "initialized": initialized,
        "failed": failed,
        "total_available": len(initialized),
        "total_failed": len(failed)
    }

# Logging setup for service initialization
logger.info("🔧 Services initialization:")
logger.info(f"   Core services: ✅ Available")
logger.info(f"   Enhanced voice: {'✅ Available' if ENHANCED_VOICE_AVAILABLE else '❌ Not available'}")
logger.info(f"   Enhanced RAG: {'✅ Available' if ENHANCED_RAG_AVAILABLE else '❌ Not available'}")

voice_caps = check_voice_capabilities()
logger.info("🎙️ Voice capabilities:")
for capability, available in voice_caps.items():
    status = "✅" if available else "❌"
    logger.info(f"   {capability}: {status}")

# Log service availability summary
available_services = get_available_services()
logger.info(f"📊 Total services available: {len(available_services)}")
for service_name in available_services.keys():
    logger.info(f"   {service_name}: ✅")

# Export everything for backward compatibility
try:
    # Make enhanced services available under original names for backward compatibility
    if ENHANCED_VOICE_AVAILABLE:
        # Create aliases for backward compatibility
        globals()['enhanced_speech_service'] = speech_service
        globals()['enhanced_tts_service'] = tts_service
except Exception as e:
    logger.warning(f"Failed to create backward compatibility aliases: {str(e)}")

# Final status summary
total_core = 3  # gemini, emotion, personalization
total_voice = 2 if speech_service and tts_service else (1 if speech_service or tts_service else 0)
total_optional = sum(1 for service in [rag_service, prompt_service, audio_processor, vector_service, topics_service, voice_streaming_service] if service is not None)
total_available = total_core + total_voice + total_optional

logger.info(f"🎯 Services Summary: {total_available} total ({total_core} core + {total_voice} voice + {total_optional} optional)")
logger.info(f"🚀 Voice enhancement level: {'Enhanced' if ENHANCED_VOICE_AVAILABLE else 'Basic' if total_voice > 0 else 'None'}")
logger.info("✅ Services package initialization complete!")