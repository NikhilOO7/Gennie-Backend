# app/routers/websocket.py
"""
WebSocket Router with enhanced voice streaming capabilities
Maintains backward compatibility while adding enhanced real-time features
"""

import asyncio
import json
import logging
import base64
import time
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database import get_db, get_redis
from app.models.user import User
from app.routers.auth import get_current_user_ws

# Import enhanced services if available
try:
    from app.services.enhanced_speech_service import enhanced_speech_service
    from app.services.enhanced_tts_service import enhanced_tts_service
    ENHANCED_SERVICES_AVAILABLE = True
except ImportError:
    ENHANCED_SERVICES_AVAILABLE = False

# Fallback to original services
if ENHANCED_SERVICES_AVAILABLE:
    speech_service = enhanced_speech_service
    tts_service = enhanced_tts_service
else:
    from app.services.speech_service import speech_service
    from app.services.tts_service import tts_service

from app.services.gemini_service import gemini_service
from app.services.emotion_service import emotion_service

# Try to import enhanced RAG service
try:
    from app.services.enhanced_rag_service import enhanced_rag_service as rag_service
except ImportError:
    try:
        from app.services.rag_service import rag_service
    except ImportError:
        rag_service = None

logger = logging.getLogger(__name__)

from fastapi import APIRouter

# Create the FastAPI router that was missing
router = APIRouter()

class VoiceStreamingManager:
    """Enhanced voice streaming session manager with backward compatibility"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.connection_pool: Dict[str, WebSocket] = {}
        
    def create_session(self, user_id: str, session_config: Dict[str, Any]) -> str:
        """Create a new voice streaming session"""
        session_id = str(uuid.uuid4())
        
        self.active_sessions[session_id] = {
            'user_id': user_id,
            'session_id': session_id,
            'created_at': time.time(),
            'config': session_config,
            'audio_buffer': bytearray(),
            'transcription_buffer': '',
            'is_recording': False,
            'is_processing': False,
            'audio_queue': asyncio.Queue(),
            'response_queue': asyncio.Queue(),
            'enhanced_features': ENHANCED_SERVICES_AVAILABLE,
            'stats': {
                'audio_chunks_received': 0,
                'audio_bytes_processed': 0,
                'transcriptions_completed': 0,
                'responses_generated': 0,
                'average_latency_ms': 0.0
            }
        }
        
        logger.info(f"Created voice session {session_id} for user {user_id} (enhanced: {ENHANCED_SERVICES_AVAILABLE})")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        return self.active_sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """Remove session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.connection_pool:
            del self.connection_pool[session_id]
        logger.info(f"Removed voice session {session_id}")
    
    def add_connection(self, session_id: str, websocket: WebSocket):
        """Add WebSocket connection to pool"""
        self.connection_pool[session_id] = websocket

# Global manager instance
voice_manager = VoiceStreamingManager()

async def handle_voice_websocket(websocket: WebSocket, token: str, db: AsyncSession):
    """Enhanced WebSocket handler for voice streaming with backward compatibility"""
    
    # Authenticate user
    try:
        user = await get_current_user_ws(token, db)
        if not user:
            await websocket.close(code=1008, reason="Authentication failed")
            return
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        await websocket.close(code=1008, reason="Authentication error")
        return
    
    await websocket.accept()
    session_id = None
    
    try:
        # Wait for session configuration
        config_data = await websocket.receive_json()
        
        if config_data.get('type') != 'start_session':
            await websocket.send_json({
                'type': 'error',
                'error': 'Expected session configuration'
            })
            return
        
        # Create streaming session with enhanced features
        session_config = {
            'language_code': config_data.get('language_code', 'en-US'),
            'sample_rate': config_data.get('sample_rate', 16000),
            'interim_results': config_data.get('interim_results', True),
            'voice_name': config_data.get('voice_name', 'en-US-Neural2-F'),
            'audio_format': config_data.get('audio_format', 'mp3'),
            'enable_emotion_detection': config_data.get('enable_emotion_detection', True),
            'enable_rag': config_data.get('enable_rag', True),
            'enhancement_level': config_data.get('enhancement_level', 'high'),
            'model_type': config_data.get('model_type', 'conversation'),
            'enable_enhancement': config_data.get('enable_enhancement', ENHANCED_SERVICES_AVAILABLE)
        }
        
        session_id = voice_manager.create_session(str(user.id), session_config)
        voice_manager.add_connection(session_id, websocket)
        
        # Send session started confirmation
        await websocket.send_json({
            'type': 'session_started',
            'session_id': session_id,
            'config': session_config,
            'enhanced_features': ENHANCED_SERVICES_AVAILABLE,
            'available_features': {
                'voice_activity_detection': ENHANCED_SERVICES_AVAILABLE,
                'audio_preprocessing': ENHANCED_SERVICES_AVAILABLE,
                'smart_ssml': ENHANCED_SERVICES_AVAILABLE,
                'emotion_based_voices': ENHANCED_SERVICES_AVAILABLE,
                'streaming_synthesis': ENHANCED_SERVICES_AVAILABLE
            }
        })
        
        # Start processing tasks
        tasks = [
            asyncio.create_task(audio_processor(websocket, session_id, user, db)),
            asyncio.create_task(transcription_processor(session_id, user, db)),
            asyncio.create_task(response_processor(websocket, session_id, user, db))
        ]
        
        # Handle incoming messages
        await message_handler(websocket, session_id, user, db)
        
    except WebSocketDisconnect:
        logger.info(f"Voice WebSocket disconnected for user {user.id}")
    except Exception as e:
        logger.error(f"Voice WebSocket error: {str(e)}")
        try:
            await websocket.send_json({
                'type': 'error',
                'error': str(e)
            })
        except:
            pass
    finally:
        # Cleanup
        if session_id:
            voice_manager.remove_session(session_id)
        
        # Cancel tasks
        for task in locals().get('tasks', []):
            task.cancel()

async def message_handler(websocket: WebSocket, session_id: str, user: User, db: AsyncSession):
    """Handle incoming WebSocket messages"""
    session = voice_manager.get_session(session_id)
    if not session:
        return
    
    try:
        while True:
            try:
                # Receive message (binary for audio, text for commands)
                message = await asyncio.wait_for(websocket.receive(), timeout=30.0)
                
                if 'bytes' in message:
                    # Audio data
                    audio_data = message['bytes']
                    await handle_audio_chunk(session, audio_data)
                    
                elif 'text' in message:
                    # Command message
                    data = json.loads(message['text'])
                    await handle_command(websocket, session, data, user, db)
                    
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_json({'type': 'keepalive'})
                continue
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Message handler error: {str(e)}")

async def handle_audio_chunk(session: Dict[str, Any], audio_data: bytes):
    """Handle incoming audio chunk"""
    try:
        # Update stats
        session['stats']['audio_chunks_received'] += 1
        session['stats']['audio_bytes_processed'] += len(audio_data)
        
        # Add to audio queue for processing
        await session['audio_queue'].put(audio_data)
        
    except Exception as e:
        logger.error(f"Audio chunk handling error: {str(e)}")

async def handle_command(websocket: WebSocket, session: Dict[str, Any], 
                        data: Dict[str, Any], user: User, db: AsyncSession):
    """Handle command messages"""
    try:
        command = data.get('type')
        
        if command == 'start_recording':
            session['is_recording'] = True
            await websocket.send_json({
                'type': 'recording_started',
                'session_id': session['session_id']
            })
            
        elif command == 'stop_recording':
            session['is_recording'] = False
            await websocket.send_json({
                'type': 'recording_stopped',
                'session_id': session['session_id']
            })
            
        elif command == 'get_stats':
            await websocket.send_json({
                'type': 'session_stats',
                'stats': session['stats'],
                'enhanced_features': session['enhanced_features']
            })
            
        elif command == 'update_config':
            # Update session configuration
            new_config = data.get('config', {})
            session['config'].update(new_config)
            await websocket.send_json({
                'type': 'config_updated',
                'config': session['config']
            })
            
        elif command == 'ping':
            await websocket.send_json({
                'type': 'pong',
                'timestamp': time.time()
            })
            
    except Exception as e:
        logger.error(f"Command handling error: {str(e)}")
        await websocket.send_json({
            'type': 'command_error',
            'error': str(e)
        })

async def audio_processor(websocket: WebSocket, session_id: str, user: User, db: AsyncSession):
    """Process audio chunks for transcription"""
    session = voice_manager.get_session(session_id)
    if not session:
        return
    
    audio_buffer = bytearray()
    buffer_threshold = 8192  # 8KB threshold
    
    try:
        while True:
            # Get audio chunk from queue
            audio_chunk = await session['audio_queue'].get()
            audio_buffer.extend(audio_chunk)
            
            # Process when buffer reaches threshold or recording stops
            if len(audio_buffer) >= buffer_threshold or not session['is_recording']:
                if len(audio_buffer) > 0:
                    # Transcribe audio buffer
                    transcription_start = time.time()
                    
                    # Use enhanced transcription if available
                    if ENHANCED_SERVICES_AVAILABLE and session['config'].get('enable_enhancement', True):
                        result = await speech_service.transcribe_audio(
                            audio_data=bytes(audio_buffer),
                            audio_format='wav',  # Assume raw PCM
                            language_code=session['config']['language_code'],
                            model_type=session['config'].get('model_type', 'conversation'),
                            enable_automatic_punctuation=True
                        )
                    else:
                        # Original transcription method
                        result = await speech_service.transcribe_audio(
                            audio_data=bytes(audio_buffer),
                            audio_format='wav',
                            language_code=session['config']['language_code'],
                            enable_automatic_punctuation=True,
                            sample_rate=session['config']['sample_rate']
                        )
                    
                    transcription_time = (time.time() - transcription_start) * 1000
                    
                    # Send transcription result
                    if result.get('success') and result.get('transcript', '').strip():
                        await websocket.send_json({
                            'type': 'transcription',
                            'transcript': result['transcript'],
                            'confidence': result.get('confidence', 0.0),
                            'is_final': True,
                            'processing_time_ms': transcription_time,
                            'words': result.get('words', []),
                            'enhanced': ENHANCED_SERVICES_AVAILABLE and session['config'].get('enable_enhancement', True)
                        })
                        
                        # Add to response queue for AI processing
                        await session['response_queue'].put({
                            'transcript': result['transcript'],
                            'confidence': result.get('confidence', 0.0),
                            'timestamp': time.time()
                        })
                        
                        session['stats']['transcriptions_completed'] += 1
                    
                    # Clear buffer
                    audio_buffer.clear()
                    
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Audio processor error: {str(e)}")

async def transcription_processor(session_id: str, user: User, db: AsyncSession):
    """Process transcriptions for AI responses"""
    session = voice_manager.get_session(session_id)
    if not session:
        return
    
    try:
        while True:
            # Wait for transcription
            transcription_data = await session['response_queue'].get()
            transcript = transcription_data['transcript']
            
            if not transcript.strip():
                continue
            
            # Start AI processing
            session['is_processing'] = True
            processing_start = time.time()
            
            try:
                # Emotion detection
                emotion_data = None
                if session['config']['enable_emotion_detection']:
                    emotion_data = await emotion_service.analyze_emotion(transcript)
                
                # RAG context retrieval
                context_data = None
                if session['config']['enable_rag'] and rag_service:
                    context_data = await rag_service.get_context_for_query(
                        query=transcript,
                        user_id=user.id,
                        db=db,
                        limit=5
                    )
                
                # Build AI prompt
                system_prompt = "You are a helpful AI assistant. Respond naturally and conversationally."
                
                if emotion_data and emotion_data.get('primary_emotion'):
                    emotion = emotion_data['primary_emotion']
                    confidence = emotion_data.get('confidence_score', 0)
                    system_prompt += f"\nUser emotion: {emotion} (confidence: {confidence:.2f})"
                
                if context_data and context_data.get('context_text'):
                    system_prompt += f"\nRelevant context: {context_data['context_text']}"
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript}
                ]
                
                # Generate streaming AI response with TTS
                await generate_streaming_voice_response(
                    session_id, messages, user, emotion_data
                )
                
                processing_time = (time.time() - processing_start) * 1000
                session['stats']['average_latency_ms'] = (
                    (session['stats']['average_latency_ms'] + processing_time) / 2
                )
                session['stats']['responses_generated'] += 1
                
            except Exception as e:
                logger.error(f"AI processing error: {str(e)}")
            finally:
                session['is_processing'] = False
                
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Transcription processor error: {str(e)}")

async def response_processor(websocket: WebSocket, session_id: str, user: User, db: AsyncSession):
    """Process and send AI responses"""
    # This is handled in generate_streaming_voice_response
    pass

async def generate_streaming_voice_response(
    session_id: str, 
    messages: list, 
    user: User, 
    emotion_data: Optional[Dict[str, Any]] = None
):
    """Generate streaming AI response with real-time TTS"""
    session = voice_manager.get_session(session_id)
    websocket = voice_manager.connection_pool.get(session_id)
    
    if not session or not websocket:
        return
    
    try:
        # Get voice settings based on emotion
        voice_settings = get_voice_settings_for_emotion(
            emotion_data, session['config']
        )
        
        # Start streaming text generation
        try:
            # Check if gemini_service has streaming method
            if hasattr(gemini_service, 'generate_chat_response_stream'):
                text_stream = gemini_service.generate_chat_response_stream(
                    messages=messages,
                    stream=True
                )
            else:
                # Fallback to regular response and chunk it
                response = await gemini_service.generate_chat_response(
                    messages=messages,
                    stream=False
                )
                async def text_generator():
                    if response.get('success'):
                        text = response.get('content', '')
                        # Split into chunks
                        words = text.split()
                        chunk_size = 5
                        for i in range(0, len(words), chunk_size):
                            chunk = ' '.join(words[i:i+chunk_size])
                            yield chunk
                text_stream = text_generator()
        except Exception as e:
            logger.error(f"Gemini streaming error: {str(e)}")
            text_stream = async_iter_single_item(f"I apologize, but I encountered an error: {str(e)}")
        
        # Stream TTS synthesis
        if ENHANCED_SERVICES_AVAILABLE and session['config'].get('enable_enhancement', True):
            # Use enhanced streaming synthesis
            async for chunk in tts_service.synthesize_streaming(
                text_stream=text_stream,
                voice_name=voice_settings.get('voice_name'),
                audio_format=session['config']['audio_format'],
                chunk_size=50
            ):
                # Send audio chunk to client
                await websocket.send_json({
                    'type': 'ai_response_chunk',
                    'chunk_type': chunk['type'],
                    'chunk_index': chunk.get('chunk_index', 0),
                    'text': chunk.get('text', ''),
                    'audio_data': chunk.get('audio_data', ''),
                    'audio_format': session['config']['audio_format'],
                    'is_final': chunk.get('is_final', False),
                    'synthesis_time_ms': chunk.get('synthesis_time_ms', 0),
                    'enhanced': True
                })
                
                if chunk.get('is_final'):
                    break
        else:
            # Fallback to basic synthesis
            full_text = ""
            async for text_chunk in text_stream:
                full_text += text_chunk + " "
            
            if full_text.strip():
                result = await tts_service.synthesize_speech(
                    text=full_text.strip(),
                    voice_name=voice_settings.get('voice_name'),
                    audio_format=session['config']['audio_format']
                )
                
                if result.get('success'):
                    await websocket.send_json({
                        'type': 'ai_response_chunk',
                        'chunk_type': 'audio_chunk',
                        'chunk_index': 0,
                        'text': full_text.strip(),
                        'audio_data': result['audio_data'],
                        'audio_format': session['config']['audio_format'],
                        'is_final': True,
                        'synthesis_time_ms': result.get('synthesis_time_ms', 0),
                        'enhanced': False
                    })
        
        # Send completion
        await websocket.send_json({
            'type': 'ai_response_complete',
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"Streaming response error: {str(e)}")
        await websocket.send_json({
            'type': 'ai_response_error',
            'error': str(e)
        })

async def async_iter_single_item(item):
    """Helper to create async iterator from single item"""
    yield item

def get_voice_settings_for_emotion(
    emotion_data: Optional[Dict[str, Any]], 
    session_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Get optimized voice settings based on detected emotion"""
    
    base_settings = {
        'voice_name': session_config.get('voice_name', 'en-US-Neural2-F'),
        'speaking_rate': 1.0,
        'pitch': 0.0,
        'emotion': None
    }
    
    if not emotion_data:
        return base_settings
    
    primary_emotion = emotion_data.get('primary_emotion', '').lower()
    confidence = emotion_data.get('confidence_score', 0)
    
    # Only adjust if confidence is high enough
    if confidence < 0.6:
        return base_settings
    
    # Emotion-based adjustments
    emotion_mappings = {
        'joy': {'emotion': 'happy', 'speaking_rate': 1.1, 'pitch': 1.0},
        'excitement': {'emotion': 'excited', 'speaking_rate': 1.15, 'pitch': 2.0},
        'sadness': {'emotion': 'sad', 'speaking_rate': 0.9, 'pitch': -1.0},
        'anger': {'emotion': 'calm', 'speaking_rate': 0.95, 'pitch': -0.5},
        'fear': {'emotion': 'calm', 'speaking_rate': 0.9, 'pitch': -1.0},
        'neutral': {'emotion': 'professional', 'speaking_rate': 1.0, 'pitch': 0.0}
    }
    
    if primary_emotion in emotion_mappings:
        adjustments = emotion_mappings[primary_emotion]
        base_settings.update(adjustments)
    
    return base_settings

# WebSocket endpoint
async def voice_streaming_endpoint(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """Main WebSocket endpoint for enhanced voice streaming"""
    await handle_voice_websocket(websocket, token, db)

# Backward compatibility WebSocket endpoints
async def websocket_endpoint(websocket: WebSocket, token: str):
    """Basic WebSocket endpoint (backward compatibility)"""
    # Get database session
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await handle_voice_websocket(websocket, token, db)

__all__ = ['router']