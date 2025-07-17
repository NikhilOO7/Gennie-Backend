def generate_silent_wav(duration_ms=100, sample_rate=44100):
    """
    Generate a silent WAV file as bytes
    """
    import struct
    
    num_samples = int((duration_ms / 1000) * sample_rate)
    num_channels = 1
    bits_per_sample = 16
    
    # Calculate sizes
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    data_size = num_samples * block_align
    
    # Create WAV header
    wav_header = bytearray()
    
    # RIFF header
    wav_header.extend(b'RIFF')
    wav_header.extend(struct.pack('<I', 36 + data_size))  # File size - 8
    wav_header.extend(b'WAVE')
    
    # fmt chunk
    wav_header.extend(b'fmt ')
    wav_header.extend(struct.pack('<I', 16))  # fmt chunk size
    wav_header.extend(struct.pack('<H', 1))   # Audio format (1 = PCM)
    wav_header.extend(struct.pack('<H', num_channels))
    wav_header.extend(struct.pack('<I', sample_rate))
    wav_header.extend(struct.pack('<I', byte_rate))
    wav_header.extend(struct.pack('<H', block_align))
    wav_header.extend(struct.pack('<H', bits_per_sample))
    
    # data chunk
    wav_header.extend(b'data')
    wav_header.extend(struct.pack('<I', data_size))
    
    # Create silence (zeros)
    audio_data = bytearray(data_size)
    
    return bytes(wav_header + audio_data)


def generate_beep_wav(frequency=440, duration_ms=100, sample_rate=44100):
    """
    Generate a simple beep sound as WAV
    """
    import struct
    import math
    
    num_samples = int((duration_ms / 1000) * sample_rate)
    num_channels = 1
    bits_per_sample = 16
    
    # Calculate sizes
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    data_size = num_samples * block_align
    
    # Create WAV header
    wav_header = bytearray()
    
    # RIFF header
    wav_header.extend(b'RIFF')
    wav_header.extend(struct.pack('<I', 36 + data_size))
    wav_header.extend(b'WAVE')
    
    # fmt chunk
    wav_header.extend(b'fmt ')
    wav_header.extend(struct.pack('<I', 16))
    wav_header.extend(struct.pack('<H', 1))
    wav_header.extend(struct.pack('<H', num_channels))
    wav_header.extend(struct.pack('<I', sample_rate))
    wav_header.extend(struct.pack('<I', byte_rate))
    wav_header.extend(struct.pack('<H', block_align))
    wav_header.extend(struct.pack('<H', bits_per_sample))
    
    # data chunk
    wav_header.extend(b'data')
    wav_header.extend(struct.pack('<I', data_size))
    
    # Generate sine wave
    audio_data = bytearray()
    amplitude = 32767 * 0.3  # 30% volume
    
    for i in range(num_samples):
        t = i / sample_rate
        value = int(amplitude * math.sin(2 * math.pi * frequency * t))
        audio_data.extend(struct.pack('<h', value))
    
    return bytes(wav_header + audio_data)