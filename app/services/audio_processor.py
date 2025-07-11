import numpy as np
import io
import wave
import struct
from typing import Optional, Tuple, List
import scipy.signal as signal
from scipy.io import wavfile
import audioop

class AudioProcessor:
    def __init__(self):
        self.supported_formats = ['wav', 'raw', 'pcm']
        self.target_sample_rate = 16000  # Target sample rate for speech recognition
        
    def validate_audio_format(self, audio_data: bytes, format: str) -> Tuple[bool, Optional[str]]:
        """
        Validate audio data format
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if format not in self.supported_formats:
            return False, f"Unsupported format: {format}"
            
        if format == 'wav':
            try:
                with io.BytesIO(audio_data) as audio_io:
                    with wave.open(audio_io, 'rb') as wav_file:
                        # Check basic WAV properties
                        channels = wav_file.getnchannels()
                        sample_width = wav_file.getsampwidth()
                        framerate = wav_file.getframerate()
                        
                        if channels > 2:
                            return False, f"Too many channels: {channels}. Maximum 2 channels supported."
                        
                        if sample_width not in [1, 2, 3, 4]:
                            return False, f"Invalid sample width: {sample_width}"
                            
                        return True, None
                        
            except Exception as e:
                return False, f"Invalid WAV file: {str(e)}"
                
        return True, None
    
    def resample_audio(
        self,
        audio_data: bytes,
        original_rate: int,
        target_rate: int,
        format: str = 'wav'
    ) -> bytes:
        """
        Resample audio to target sample rate
        
        Args:
            audio_data: Audio data bytes
            original_rate: Original sample rate
            target_rate: Target sample rate
            format: Audio format
            
        Returns:
            Resampled audio data
        """
        if original_rate == target_rate:
            return audio_data
            
        if format == 'wav':
            # Read WAV data
            with io.BytesIO(audio_data) as audio_io:
                rate, data = wavfile.read(audio_io)
                
            # Resample using scipy
            num_samples = int(len(data) * target_rate / original_rate)
            resampled = signal.resample(data, num_samples)
            
            # Convert back to int16
            if data.dtype == np.int16:
                resampled = resampled.astype(np.int16)
            
            # Write back to WAV
            output_io = io.BytesIO()
            wavfile.write(output_io, target_rate, resampled)
            output_io.seek(0)
            
            return output_io.read()
            
        elif format in ['raw', 'pcm']:
            # For raw PCM data, use audioop
            # Assuming 16-bit mono PCM
            resampled, _ = audioop.ratecv(
                audio_data,
                2,  # sample width in bytes (16-bit)
                1,  # number of channels
                original_rate,
                target_rate,
                None
            )
            return resampled
            
        return audio_data
    
    def apply_noise_reduction(
        self,
        audio_data: bytes,
        format: str = 'wav',
        noise_floor: float = 0.02
    ) -> bytes:
        """
        Apply basic noise reduction
        
        Args:
            audio_data: Audio data bytes
            format: Audio format
            noise_floor: Noise floor threshold (0-1)
            
        Returns:
            Processed audio data
        """
        if format == 'wav':
            # Read WAV data
            with io.BytesIO(audio_data) as audio_io:
                rate, data = wavfile.read(audio_io)
                
            # Convert to float for processing
            if data.dtype == np.int16:
                data_float = data.astype(np.float32) / 32768.0
            else:
                data_float = data.astype(np.float32)
                
            # Apply simple noise gate
            mask = np.abs(data_float) > noise_floor
            data_float = data_float * mask
            
            # Apply smoothing to reduce artifacts
            window_size = int(rate * 0.01)  # 10ms window
            data_float = signal.medfilt(data_float, kernel_size=min(window_size, 5))
            
            # Convert back to original format
            if data.dtype == np.int16:
                data_processed = (data_float * 32768).astype(np.int16)
            else:
                data_processed = data_float.astype(data.dtype)
                
            # Write back to WAV
            output_io = io.BytesIO()
            wavfile.write(output_io, rate, data_processed)
            output_io.seek(0)
            
            return output_io.read()
            
        return audio_data
    
    def chunk_audio_stream(
        self,
        audio_data: bytes,
        chunk_duration_ms: int = 100,
        sample_rate: int = 16000,
        sample_width: int = 2
    ) -> List[bytes]:
        """
        Split audio data into chunks for streaming
        
        Args:
            audio_data: Audio data bytes
            chunk_duration_ms: Duration of each chunk in milliseconds
            sample_rate: Sample rate
            sample_width: Sample width in bytes
            
        Returns:
            List of audio chunks
        """
        # Calculate chunk size in bytes
        chunk_size = int(sample_rate * chunk_duration_ms / 1000) * sample_width
        
        # Split into chunks
        chunks = []
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            
            # Pad last chunk if necessary
            if len(chunk) < chunk_size and i + chunk_size >= len(audio_data):
                chunk += b'\x00' * (chunk_size - len(chunk))
                
            chunks.append(chunk)
            
        return chunks
    
    def merge_audio_chunks(self, chunks: List[bytes]) -> bytes:
        """
        Merge audio chunks back into continuous stream
        
        Args:
            chunks: List of audio chunks
            
        Returns:
            Merged audio data
        """
        return b''.join(chunks)
    
    def convert_stereo_to_mono(self, audio_data: bytes, format: str = 'wav') -> bytes:
        """
        Convert stereo audio to mono
        
        Args:
            audio_data: Audio data bytes
            format: Audio format
            
        Returns:
            Mono audio data
        """
        if format == 'wav':
            with io.BytesIO(audio_data) as audio_io:
                with wave.open(audio_io, 'rb') as wav_in:
                    params = wav_in.getparams()
                    
                    if params.nchannels == 1:
                        return audio_data  # Already mono
                        
                    frames = wav_in.readframes(params.nframes)
                    
            # Convert stereo to mono using audioop
            mono_frames = audioop.tomono(frames, params.sampwidth, 0.5, 0.5)
            
            # Write mono WAV
            output_io = io.BytesIO()
            with wave.open(output_io, 'wb') as wav_out:
                wav_out.setparams((
                    1,  # mono
                    params.sampwidth,
                    params.framerate,
                    params.nframes,
                    params.comptype,
                    params.compname
                ))
                wav_out.writeframes(mono_frames)
                
            output_io.seek(0)
            return output_io.read()
            
        return audio_data
    
    def normalize_audio_level(
        self,
        audio_data: bytes,
        format: str = 'wav',
        target_dBFS: float = -20.0
    ) -> bytes:
        """
        Normalize audio level to target dBFS
        
        Args:
            audio_data: Audio data bytes
            format: Audio format
            target_dBFS: Target level in dBFS
            
        Returns:
            Normalized audio data
        """
        if format == 'wav':
            # Read WAV data
            with io.BytesIO(audio_data) as audio_io:
                rate, data = wavfile.read(audio_io)
                
            # Convert to float
            if data.dtype == np.int16:
                data_float = data.astype(np.float32) / 32768.0
            else:
                data_float = data.astype(np.float32)
                
            # Calculate current RMS level
            rms = np.sqrt(np.mean(data_float**2))
            current_dBFS = 20 * np.log10(rms) if rms > 0 else -96.0
            
            # Calculate gain needed
            gain_dB = target_dBFS - current_dBFS
            gain_linear = 10**(gain_dB / 20)
            
            # Apply gain with limiting
            data_normalized = data_float * gain_linear
            data_normalized = np.clip(data_normalized, -1.0, 1.0)
            
            # Convert back
            if data.dtype == np.int16:
                data_processed = (data_normalized * 32768).astype(np.int16)
            else:
                data_processed = data_normalized.astype(data.dtype)
                
            # Write back to WAV
            output_io = io.BytesIO()
            wavfile.write(output_io, rate, data_processed)
            output_io.seek(0)
            
            return output_io.read()
            
        return audio_data
    
    def detect_silence(
        self,
        audio_data: bytes,
        format: str = 'wav',
        threshold_dB: float = -40.0,
        min_silence_duration_ms: int = 300
    ) -> List[Tuple[float, float]]:
        """
        Detect silence periods in audio
        
        Args:
            audio_data: Audio data bytes
            format: Audio format
            threshold_dB: Silence threshold in dB
            min_silence_duration_ms: Minimum silence duration
            
        Returns:
            List of (start_time, end_time) tuples for silence periods
        """
        if format == 'wav':
            # Read WAV data
            with io.BytesIO(audio_data) as audio_io:
                rate, data = wavfile.read(audio_io)
                
            # Convert to float
            if data.dtype == np.int16:
                data_float = data.astype(np.float32) / 32768.0
            else:
                data_float = data.astype(np.float32)
                
            # Calculate frame energy
            frame_size = int(rate * 0.02)  # 20ms frames
            threshold_linear = 10**(threshold_dB / 20)
            
            silence_periods = []
            current_silence_start = None
            
            for i in range(0, len(data_float) - frame_size, frame_size):
                frame = data_float[i:i + frame_size]
                rms = np.sqrt(np.mean(frame**2))
                
                if rms < threshold_linear:
                    if current_silence_start is None:
                        current_silence_start = i / rate
                else:
                    if current_silence_start is not None:
                        silence_duration = (i / rate) - current_silence_start
                        if silence_duration >= min_silence_duration_ms / 1000:
                            silence_periods.append((
                                current_silence_start,
                                i / rate
                            ))
                        current_silence_start = None
                        
            # Check for trailing silence
            if current_silence_start is not None:
                silence_duration = (len(data_float) / rate) - current_silence_start
                if silence_duration >= min_silence_duration_ms / 1000:
                    silence_periods.append((
                        current_silence_start,
                        len(data_float) / rate
                    ))
                    
            return silence_periods
            
        return []

# Create singleton instance
audio_processor = AudioProcessor()