import pyaudio
import numpy as np
import wave
import threading
import time
from win32com.client import Dispatch


class AudioProcessor:
    def __init__(self):
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.is_running = False
        
        self.audio = pyaudio.PyAudio()
        self.tts = Dispatch("SAPI.SpVoice")
        
        self.input_stream = None
        self.output_stream = None
        
    def capture_and_replace(self, tts_text="Hello, this is a test"):
        """
        捕获麦克风音频并替换为TTS声音
        """
        self.input_stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        self.output_stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            output=True,
            frames_per_buffer=self.CHUNK
        )
        
        self.is_running = True
        
        def audio_thread():
            while self.is_running:
                try:
                    data = self.input_stream.read(self.CHUNK, exception_on_overflow=False)
                    
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    
                    if np.abs(audio_data).mean() > 500:
                        # 替换这里: 在此处添加自定义音频处理逻辑
                        # 你可以替换为: 音频特效、变声、混响等
                        pass
                    
                    # 生成TTS音频数据（这里使用静音作为示例）
                    # 替换这里: 在此处替换为自定义TTS音频源
                    # 例如: 使用gTTS、pyttsx3或其他TTS引擎生成的音频
                    silent_chunk = bytes(self.CHUNK * 2)
                    self.output_stream.write(silent_chunk)
                    
                except Exception as e:
                    print(f"Error: {e}")
                    break
        
        def tts_speak_thread():
            """单独线程用于TTS朗读"""
            while self.is_running:
                # 替换这里: 在此处控制TTS的触发条件
                # 可以根据音频能量、关键词检测等方式触发
                self.tts.Speak(tts_text)
                time.sleep(5)
        
        capture_thread = threading.Thread(target=audio_thread, daemon=True)
        tts_thread = threading.Thread(target=tts_speak_thread, daemon=True)
        
        capture_thread.start()
        tts_thread.start()
        
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """停止音频处理"""
        self.is_running = False
        
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        
        self.audio.terminate()
        print("Audio processing stopped")


def main():
    processor = AudioProcessor()
    
    print("Starting audio capture and TTS replacement...")
    print("Press Ctrl+C to stop")
    
    processor.capture_and_replace(
        tts_text="你好，这是一段测试语音"
    )


if __name__ == "__main__":
    main()
