# app/routers/enhanced_websocket_voice.py
"""
Enhanced WebSocket Voice Handler - Complete Implementation
Real-time voice streaming with STT, TTS, and AI integration
"""

import asyncio
import json
import logging
import base64
import time
import uuid
from typing import Dict, Any, Optional, List
from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user_ws

# Import enhanced services
try:
    from app.services.enhanced_speech_service import enhanced_speech_service
    from app.services.enhanced_tts_service import enhanced_tts_service
    ENHANCED_SERVICES_AVAILABLE = True
except ImportError:
    from app.services.speech_service import speech_service as enhanced_speech_service
    from app.services.tts_service import tts_service as enhanced_tts_service
    ENHANCED_SERVICES_AVAILABLE = False

from app.services import gemini_service, emotion_service, personalization_service

logger = logging.getLogger(__name__)

class VoiceStreamingManager:
    """Enhanced voice streaming session manager"""
    
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
            'is_recording': False,
            'audio_queue': asyncio.Queue(),
            'transcript_queue': asyncio.Queue(),
            'response_queue': asyncio.Queue(),
            'stats': {
                'audio_chunks_received': 0,
                'audio_bytes_processed': 0,
                'transcriptions_completed': 0,
                'responses_generated': 0,
                'session_duration': 0
            }
        }
        
        logger.info(f"Created voice session {session_id} for user {user_id}")
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
    """Enhanced WebSocket handler for voice streaming"""
    
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
    logger.info(f"Voice WebSocket connected for user {user.id}")
    session_id = None
    tasks = []
    
    try:
        # Send immediate welcome message to confirm connection
        await websocket.send_json({
            'type': 'session_ready',
            'message': 'Voice WebSocket connected. Send start_session to begin.',
            'timestamp': time.time()
        })
        
        # Wait for any initial message (could be ping, start_session, etc.)
        while True:
            try:
                config_data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                
                # Handle different initial message types
                if config_data.get('type') == 'start_session':
                    # This is the session configuration
                    break
                elif config_data.get('type') == 'ping':
                    # Handle ping and wait for next message
                    await websocket.send_json({
                        'type': 'pong',
                        'timestamp': time.time()
                    })
                    continue
                else:
                    # For any other message type, send session_ready and continue waiting
                    await websocket.send_json({
                        'type': 'session_ready',
                        'message': f'Received {config_data.get("type", "unknown")}. Send start_session to begin voice session.',
                        'timestamp': time.time()
                    })
                    continue
                    
            except asyncio.TimeoutError:
                logger.warning(f"No session configuration received for user {user.id}")
                await websocket.send_json({
                    'type': 'error',
                    'error': 'Session configuration timeout. Send start_session message.'
                })
                return
        
        # Create streaming session
        session_config = {
            'language_code': config_data.get('language_code', 'en-US'),
            'sample_rate': config_data.get('sample_rate', 16000),
            'interim_results': config_data.get('interim_results', True),
            'voice_name': config_data.get('voice_name', 'en-US-Neural2-F'),
            'audio_format': config_data.get('audio_format', 'mp3'),
            'enable_emotion_detection': config_data.get('enable_emotion_detection', True),
            'enable_rag': config_data.get('enable_rag', True),
            'enhancement_level': config_data.get('enhancement_level', 'high')
        }
        
        session_id = voice_manager.create_session(str(user.id), session_config)
        voice_manager.add_connection(session_id, websocket)
        
        # Send session started confirmation
        await websocket.send_json({
            'type': 'session_started',
            'session_id': session_id,
            'config': session_config,
            'enhanced': ENHANCED_SERVICES_AVAILABLE
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
        for task in tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

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
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"Message handler error: {str(e)}")

async def handle_audio_chunk(session: Dict[str, Any], audio_data: bytes):
    """Handle incoming audio chunk"""
    try:
        # Update stats
        session['stats']['audio_chunks_received'] += 1
        session['stats']['audio_bytes_processed'] += len(audio_data)
        
        # Add to audio queue for processing
        if session['is_recording']:
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
                'stats': session['stats']
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
            
        else:
            await websocket.send_json({
                'type': 'info',
                'message': f'Received command: {command}'
            })
            
    except Exception as e:
        logger.error(f"Command handling error: {str(e)}")
        await websocket.send_json({
            'type': 'error',
            'error': f'Command processing failed: {str(e)}'
        })

async def audio_processor(websocket: WebSocket, session_id: str, user: User, db: AsyncSession):
    """Process audio chunks for transcription"""
    session = voice_manager.get_session(session_id)
    if not session:
        return
    
    audio_buffer = bytearray()
    buffer_threshold = 8192  # 8KB chunks for processing
    
    try:
        while True:
            try:
                # Get audio chunk from queue
                audio_chunk = await asyncio.wait_for(
                    session['audio_queue'].get(), 
                    timeout=1.0
                )
                
                # Add to buffer
                audio_buffer.extend(audio_chunk)
                
                # Process when buffer is large enough
                if len(audio_buffer) >= buffer_threshold:
                    # Send for transcription
                    await session['transcript_queue'].put(bytes(audio_buffer))
                    audio_buffer.clear()
                    
            except asyncio.TimeoutError:
                # Process remaining buffer if any
                if len(audio_buffer) > 0:
                    await session['transcript_queue'].put(bytes(audio_buffer))
                    audio_buffer.clear()
                continue
                
    except asyncio.CancelledError:
        logger.info(f"Audio processor cancelled for session {session_id}")
    except Exception as e:
        logger.error(f"Audio processor error: {str(e)}")

async def transcription_processor(session_id: str, user: User, db: AsyncSession):
    """Process audio for transcription"""
    session = voice_manager.get_session(session_id)
    if not session:
        return
    
    websocket = voice_manager.connection_pool.get(session_id)
    if not websocket:
        return
    
    try:
        while True:
            try:
                # Get audio data from queue
                audio_data = await asyncio.wait_for(
                    session['transcript_queue'].get(),
                    timeout=5.0
                )
                
                # Transcribe audio
                config = session['config']
                
                if ENHANCED_SERVICES_AVAILABLE:
                    result = await enhanced_speech_service.transcribe_audio(
                        audio_data=audio_data,
                        language_code=config['language_code'],
                        audio_format='webm',
                        enable_automatic_punctuation=True,
                        enable_word_confidence=True
                    )
                else:
                    # Fallback transcription
                    result = {'success': False, 'error': 'Enhanced services not available'}
                
                if result.get('success'):
                    transcript = result.get('transcript', '').strip()
                    confidence = result.get('confidence', 0.0)
                    
                    if transcript:
                        # Update stats
                        session['stats']['transcriptions_completed'] += 1
                        
                        # Send transcript
                        await websocket.send_json({
                            'type': 'transcript',
                            'transcript': transcript,
                            'confidence': confidence,
                            'is_final': True,
                            'session_id': session_id
                        })
                        
                        # Add to response queue for AI processing
                        await session['response_queue'].put({
                            'transcript': transcript,
                            'confidence': confidence,
                            'timestamp': time.time()
                        })
                        
                else:
                    logger.warning(f"Transcription failed: {result.get('error')}")
                    
            except asyncio.TimeoutError:
                continue
                
    except asyncio.CancelledError:
        logger.info(f"Transcription processor cancelled for session {session_id}")
    except Exception as e:
        logger.error(f"Transcription processor error: {str(e)}")

async def response_processor(websocket: WebSocket, session_id: str, user: User, db: AsyncSession):
    """Process transcripts for AI responses"""
    session = voice_manager.get_session(session_id)
    if not session:
        return
    
    try:
        while True:
            try:
                # Get transcript from queue
                transcript_data = await asyncio.wait_for(
                    session['response_queue'].get(),
                    timeout=10.0
                )
                
                transcript = transcript_data['transcript']
                confidence = transcript_data['confidence']
                
                # Skip low confidence transcripts
                if confidence < 0.5:
                    continue
                
                # Generate AI response
                try:
                    response = await gemini_service.generate_chat_response([
                        {"role": "user", "content": transcript}
                    ])
                    
                    if response.get('success'):
                        ai_text = response.get('response', '')
                        
                        # Update stats
                        session['stats']['responses_generated'] += 1
                        
                        # Send text response
                        await websocket.send_json({
                            'type': 'ai_response',
                            'text': ai_text,
                            'session_id': session_id,
                            'original_transcript': transcript
                        })
                        
                        # Generate voice response if enabled
                        config = session['config']
                        if config.get('enable_tts', True):
                            await generate_voice_response(
                                websocket, session_id, ai_text, config
                            )
                            
                    else:
                        await websocket.send_json({
                            'type': 'ai_response_error',
                            'error': response.get('error', 'AI response failed')
                        })
                        
                except Exception as e:
                    logger.error(f"AI response generation error: {str(e)}")
                    await websocket.send_json({
                        'type': 'ai_response_error',
                        'error': str(e)
                    })
                    
            except asyncio.TimeoutError:
                continue
                
    except asyncio.CancelledError:
        logger.info(f"Response processor cancelled for session {session_id}")
    except Exception as e:
        logger.error(f"Response processor error: {str(e)}")

async def generate_voice_response(websocket: WebSocket, session_id: str, 
                                text: str, config: Dict[str, Any]):
    """Generate voice response using TTS"""
    try:
        if ENHANCED_SERVICES_AVAILABLE:
            result = await enhanced_tts_service.synthesize_speech(
                text=text,
                voice_name=config.get('voice_name', 'en-US-Neural2-F'),
                language_code=config.get('language_code', 'en-US'),
                audio_format=config.get('audio_format', 'mp3'),
                enhance_quality=True
            )
        else:
            # Fallback TTS
            result = {'success': False, 'error': 'Enhanced TTS not available'}
        
        if result.get('success'):
            audio_data = result.get('audio_data', '')
            
            await websocket.send_json({
                'type': 'voice_response',
                'audio_data': audio_data,
                'audio_format': config.get('audio_format', 'mp3'),
                'session_id': session_id,
                'text': text
            })
            
        else:
            logger.warning(f"TTS failed: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Voice response generation error: {str(e)}")

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

__all__ = [
    "voice_streaming_endpoint",
    "VoiceStreamingManager", 
    "handle_voice_websocket",
    "voice_manager"
]