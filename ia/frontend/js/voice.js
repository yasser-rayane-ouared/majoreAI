/**
 * StudyFlow AI - Voice Input/Output
 */
let recognition = null;
let isRecording = false;

function initVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      const input = document.getElementById('message-input');
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      if (input) input.value = transcript;
      autoResizeInput();
    };

    recognition.onend = () => {
      isRecording = false;
      updateVoiceBtn();
    };

    recognition.onerror = () => {
      isRecording = false;
      updateVoiceBtn();
    };
  }
}

function toggleVoice() {
  if (!recognition) {
    alert('Speech recognition not supported in this browser.');
    return;
  }
  if (isRecording) {
    recognition.stop();
    isRecording = false;
  } else {
    recognition.start();
    isRecording = true;
  }
  updateVoiceBtn();
}

function updateVoiceBtn() {
  const btn = document.getElementById('voice-btn');
  if (!btn) return;
  btn.classList.toggle('recording', isRecording);
  btn.textContent = isRecording ? '⏹️' : '🎤';
  btn.title = isRecording ? 'Stop recording' : 'Voice input';
}

function speakText(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const clean = text.replace(/[#*`_~\[\]()>|]/g, '').replace(/\n+/g, '. ');
  const utterance = new SpeechSynthesisUtterance(clean.substring(0, 2000));
  utterance.rate = 1;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

document.addEventListener('DOMContentLoaded', initVoice);
