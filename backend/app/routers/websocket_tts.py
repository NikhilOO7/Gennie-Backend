import json
import asyncio
import base64
from typing import Dict, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect, Depends, status
from datetime import datetime
import uuid
import io
import struct
from sqlalchemy import select
from app.logger import logger
from app.routers.auth import verify_token
from app.models.user import User
from app.services.gemini_service import gemini_service
from app.services.speech_service import speech_service
from app.services.tts_service import tts_service
from app.services.audio_processor import AudioProcessor
from app.models import User, Message
from app.database import get_db

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.voice_sessions: Dict[str, Dict] = {}
        self.audio_processor = AudioProcessor()
        
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        # Clean up voice session if exists
        if user_id in self.voice_sessions:
            del self.voice_sessions[user_id]
            
    async def send_message(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_json(message)
            
    async def send_binary(self, user_id: str, data: bytes):
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_bytes(data)
            
    async def broadcast(self, message: dict, exclude_user: Optional[str] = None):
        for user_id, websocket in self.active_connections.items():
            if user_id != exclude_user:
                await websocket.send_json(message)

manager = ConnectionManager()

async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db = Depends(get_db)
):
    user = await get_current_user_ws(token, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    await manager.connect(websocket, str(user.id))
    
    try:
        while True:
            # Check if it's a binary message (audio) or text (JSON)
            message_type = await websocket.receive()
            
            if "bytes" in message_type:
                # Handle binary audio data
                await handle_audio_data(websocket, user, message_type["bytes"])
            else:
                # Handle JSON messages
                data = json.loads(message_type["text"])
                await handle_json_message(websocket, user, data, db)
                
    except WebSocketDisconnect:
        manager.disconnect(str(user.id))
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(str(user.id))

async def get_current_user_ws(token: str, db):
    """Get user from JWT token for WebSocket"""
    try:
        payload = verify_token(token)
        user_id = int(payload.get("sub"))
        
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        return user if user and user.is_active else None
    except Exception:
        return None

async def handle_json_message(websocket: WebSocket, user: User, data: dict, db):
    """Handle JSON-based WebSocket messages"""
    message_type = data.get("type")
    
    if message_type == "message":
        # Handle text message
        await handle_text_message(websocket, user, data, db)
        
    elif message_type == "voice_stream_start":
        # Initialize voice streaming session
        await handle_voice_stream_start(websocket, user, data)
        
    elif message_type == "voice_stream_end":
        # End voice streaming session
        await handle_voice_stream_end(websocket, user, data)
        
    elif message_type == "audio_response_request":
        # Request TTS for a message
        await handle_audio_response_request(websocket, user, data)
        
    elif message_type == "typing":
        # Handle typing indicator
        await manager.send_message(str(user.id), {
            "type": "typing_indicator",
            "isTyping": data.get("isTyping", False)
        })
        
    else:
        await websocket.send_json({
            "type": "error",
            "message": f"Unknown message type: {message_type}"
        })

async def handle_text_message(websocket: WebSocket, user: User, data: dict, db):
    """Handle regular text messages"""
    content = data.get("content", "").strip()
    if not content:
        return
        
    # Save user message to database
    user_message = Message(
        user_id=user.id,
        content=content,
        is_user=True,
        timestamp=datetime.utcnow(),
        metadata=data.get("metadata", {})
    )
    db.add(user_message)
    db.commit()
    
    # Send acknowledgment
    await websocket.send_json({
        "type": "message_received",
        "message_id": str(user_message.id),
        "timestamp": user_message.timestamp.isoformat()
    })
    
    # Get AI response
    try:
        # Send typing indicator
        await websocket.send_json({
            "type": "ai_typing",
            "isTyping": True
        })
        
        # Get response from Gemini
        response = await gemini_service.get_response(
            content,
            user_id=str(user.id),
            context=data.get("context", [])
        )
        
        # Save AI response to database
        ai_message = Message(
            user_id=user.id,
            content=response,
            is_user=False,
            timestamp=datetime.utcnow()
        )
        db.add(ai_message)
        db.commit()
        
        # Send AI response
        await websocket.send_json({
            "type": "ai_message",
            "content": response,
            "message_id": str(ai_message.id),
            "timestamp": ai_message.timestamp.isoformat()
        })
        
        # If voice mode is enabled, also send audio
        if data.get("voice_enabled", False):
            asyncio.create_task(
                send_audio_response(websocket, user, response, ai_message.id)
            )
            
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": f"Failed to get AI response: {str(e)}"
        })
    finally:
        # Stop typing indicator
        await websocket.send_json({
            "type": "ai_typing",
            "isTyping": False
        })

async def handle_audio_data(websocket: WebSocket, user: User, audio_data: bytes):
    """Handle binary audio data for streaming transcription"""
    user_id = str(user.id)
    
    # Check if there's an active voice session
    if user_id not in manager.voice_sessions:
        await websocket.send_json({
            "type": "error",
            "message": "No active voice session. Start a session first."
        })
        return
        
    session = manager.voice_sessions[user_id]
    
    # Add audio chunk to buffer
    session["audio_buffer"].extend(audio_data)
    
    # Process when buffer reaches threshold
    if len(session["audio_buffer"]) >= session["chunk_size"]:
        # Extract chunk
        chunk = bytes(session["audio_buffer"][:session["chunk_size"]])
        session["audio_buffer"] = session["audio_buffer"][session["chunk_size"]:]
        
        # Add to processing queue
        await session["audio_queue"].put(chunk)

async def handle_voice_stream_start(websocket: WebSocket, user: User, data: dict):
    """Initialize a voice streaming session"""
    user_id = str(user.id)
    session_id = str(uuid.uuid4())
    
    # Create voice session
    session = {
        "session_id": session_id,
        "language_code": data.get("language_code", "en-US"),
        "interim_results": data.get("interim_results", True),
        "single_utterance": data.get("single_utterance", False),
        "sample_rate": data.get("sample_rate", 16000),
        "audio_format": data.get("audio_format", "linear16"),
        "chunk_size": data.get("chunk_size", 4096),
        "audio_buffer": bytearray(),
        "audio_queue": asyncio.Queue(),
        "transcription_task": None,
    }
    
    manager.voice_sessions[user_id] = session
    
    # Start transcription task
    session["transcription_task"] = asyncio.create_task(
        process_audio_stream(websocket, user, session)
    )
    
    # Send confirmation
    await websocket.send_json({
        "type": "voice_stream_started",
        "session_id": session_id,
        "config": {
            "language_code": session["language_code"],
            "sample_rate": session["sample_rate"],
            "audio_format": session["audio_format"],
            "chunk_size": session["chunk_size"],
        }
    })

async def handle_voice_stream_end(websocket: WebSocket, user: User, data: dict):
    """End a voice streaming session"""
    user_id = str(user.id)
    
    if user_id not in manager.voice_sessions:
        return
        
    session = manager.voice_sessions[user_id]
    
    # Process remaining audio in buffer
    if session["audio_buffer"]:
        await session["audio_queue"].put(bytes(session["audio_buffer"]))
        
    # Signal end of stream
    await session["audio_queue"].put(None)
    
    # Wait for transcription to complete
    if session["transcription_task"]:
        await session["transcription_task"]
        
    # Clean up session
    del manager.voice_sessions[user_id]
    
    # Send confirmation
    await websocket.send_json({
        "type": "voice_stream_ended",
        "session_id": session["session_id"]
    })

async def process_audio_stream(websocket: WebSocket, user: User, session: dict):
    """Process audio stream and send transcription updates"""
    audio_chunks = []
    
    async def audio_generator():
        while True:
            chunk = await session["audio_queue"].get()
            if chunk is None:
                break
            yield chunk
            audio_chunks.append(chunk)
    
    try:
        # Perform streaming transcription
        async for result in speech_service.streaming_transcribe(
            audio_stream=audio_generator(),
            sample_rate=session["sample_rate"],
            language_code=session["language_code"],
            interim_results=session["interim_results"],
            single_utterance=session["single_utterance"],
        ):
            # Send transcription update
            await websocket.send_json({
                "type": "transcription_update",
                "transcript": result["transcript"],
                "is_final": result["is_final"],
                "confidence": result.get("confidence"),
                "stability": result.get("stability"),
            })
            
            # If final result, process as message
            if result["is_final"] and result["transcript"].strip():
                # Combine all audio chunks
                complete_audio = b''.join(audio_chunks)
                audio_chunks.clear()
                
                # Send as message
                await handle_text_message(
                    websocket,
                    user,
                    {
                        "type": "message",
                        "content": result["transcript"],
                        "voice_enabled": True,
                        "metadata": {
                            "source": "voice",
                            "confidence": result.get("confidence", 0),
                            "audio_size": len(complete_audio),
                        }
                    },
                    session.get("db")
                )
                
    except Exception as e:
        await websocket.send_json({
            "type": "transcription_error",
            "error": str(e)
        })

async def handle_audio_response_request(websocket: WebSocket, user: User, data: dict):
    """Handle request to synthesize audio for a message"""
    message_id = data.get("message_id")
    text = data.get("text", "")
    voice_name = data.get("voice_name")
    
    if not text:
        return
        
    await send_audio_response(websocket, user, text, message_id, voice_name)

async def generate_and_send_audio(
    text: str,
    message_id: int,
    chat_id: int,
    connection_id: str,
    manager,
    redis_client,
    voice_settings: Optional[Dict] = None
):
    """Generate and send audio response asynchronously"""
    try:
        from app.services.tts_service import tts_service
        
        # Extract voice settings with defaults
        voice_name = None
        speaking_rate = 1.0
        pitch = 0.0
        
        if voice_settings:
            voice_name = voice_settings.get("voice_name")
            speaking_rate = voice_settings.get("speaking_rate", 1.0)
            pitch = voice_settings.get("pitch", 0.0)
        
        logger.info(f"Generating audio for message {message_id} with voice {voice_name}")
        
        # Generate audio
        result = await tts_service.synthesize_speech(
            text=text,
            voice_name=voice_name,
            audio_format="mp3",
            speaking_rate=speaking_rate,
            pitch=pitch
        )
        
        # Store in Redis
        if redis_client:
            audio_key = f"audio:message:{message_id}"
            audio_base64 = base64.b64encode(result['audio_content']).decode()
            await redis_client.set(audio_key, audio_base64, ex=3600)  # Expire in 1 hour
            logger.info(f"Cached audio for message {message_id} in Redis")
        
        # Estimate audio duration
        duration = tts_service.estimate_audio_duration(text, speaking_rate)
        
        # Send audio ready notification
        await manager.send_to_chat({
            "type": "voice_response_ready",
            "message_id": message_id,
            "audio_format": "mp3",
            "voice_name": result.get("voice_name"),
            "duration": duration,
            "audio_url": f"/api/v1/ai/message-audio/{message_id}"
        }, chat_id)
        
        logger.info(f"Voice response ready for message {message_id}, duration: {duration}s")
        
    except Exception as e:
        logger.error(f"TTS generation failed for message {message_id}: {str(e)}", exc_info=True)
        
        # Send error notification
        await manager.send_to_chat({
            "type": "voice_response_error",
            "message_id": message_id,
            "error": str(e)
        }, chat_id)

async def send_audio_response(
    websocket: WebSocket,
    user: User,
    text: str,
    message_id: str,
    voice_name: Optional[str] = None
):
    """Synthesize and send audio response in chunks"""
    try:
        # Start audio response
        await websocket.send_json({
            "type": "audio_response_start",
            "message_id": message_id,
            "format": "mp3",
        })
        
        # Synthesize speech
        result = await tts_service.synthesize_speech(
            text=text,
            voice_name=voice_name,
            audio_format="mp3",
            speaking_rate=1.0,
        )
        
        audio_data = result["audio_content"]
        
        # Send audio in chunks (64KB chunks)
        chunk_size = 65536
        total_chunks = (len(audio_data) + chunk_size - 1) // chunk_size
        
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            chunk_index = i // chunk_size
            
            # Create audio chunk message
            # Format: [1 byte type][4 bytes message_id length][message_id][4 bytes chunk index][4 bytes total chunks][audio data]
            message_id_bytes = message_id.encode('utf-8')
            
            chunk_message = bytearray()
            chunk_message.append(0x01)  # Audio chunk type
            chunk_message.extend(struct.pack('<I', len(message_id_bytes)))
            chunk_message.extend(message_id_bytes)
            chunk_message.extend(struct.pack('<I', chunk_index))
            chunk_message.extend(struct.pack('<I', total_chunks))
            chunk_message.extend(chunk)
            
            await websocket.send_bytes(bytes(chunk_message))
            
            # Small delay to prevent overwhelming the client
            await asyncio.sleep(0.01)
        
        # Send completion message
        await websocket.send_json({
            "type": "audio_response_complete",
            "message_id": message_id,
            "duration": tts_service.estimate_audio_duration(text),
            "voice_name": result["voice_name"],
        })
        
    except Exception as e:
        await websocket.send_json({
            "type": "audio_response_error",
            "message_id": message_id,
            "error": str(e)
        })

# Voice-specific WebSocket endpoint for dedicated voice sessions
async def voice_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str,
    db = Depends(get_db)
):
    """Dedicated WebSocket endpoint for voice streaming"""
    user = await get_current_user_ws(token, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    await websocket.accept()
    
    # Set up voice session with provided config
    session = {
        "session_id": session_id,
        "language_code": "en-US",
        "interim_results": True,
        "sample_rate": 16000,
        "audio_queue": asyncio.Queue(),
    }
    
    try:
        # Process incoming audio stream
        async def audio_generator():
            while True:
                try:
                    audio_data = await websocket.receive_bytes()
                    yield audio_data
                except WebSocketDisconnect:
                    break
                    
        # Perform streaming transcription
        async for result in speech_service.streaming_transcribe(
            audio_stream=audio_generator(),
            sample_rate=session["sample_rate"],
            language_code=session["language_code"],
            interim_results=session["interim_results"],
        ):
            await websocket.send_json(result)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Voice WebSocket error: {e}")
        await websocket.send_json({
            "error": str(e),
            "is_final": True
        })