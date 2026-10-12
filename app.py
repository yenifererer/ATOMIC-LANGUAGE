import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from deep_translator import GoogleTranslator
import requests
import re
from gtts import gTTS
import io

# Configuración de la página
st.set_page_config(page_title="YouTube Language Learner Pro", layout="wide")

st.title("🎥 YouTube Subtitle & Vocabulary Learner Pro")
st.write("Pega el enlace de un video de YouTube, aprende palabra por palabra con audio nativo y exporta tu vocabulario a Anki.")

# Inicializar lista de vocabulario guardado en la sesión
if 'vocab_list' not in st.session_state:
    st.session_state.vocab_list = []

# 1. Función para extraer el ID de YouTube desde el enlace
def get_youtube_id(url):
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(regex, url)
    return match.group(1) if match else None

# 2. Función para obtener la información de una palabra
def get_word_info(word):
    clean_word = re.sub(r'[^\w\s]', '', word).lower()
    translated_word = GoogleTranslator(source='auto', target='es').translate(clean_word)
    
    phonetic = "No disponible"
    examples = []
    
    try:
        response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{clean_word}")
        if response.status_code == 200:
            data = response.json()[0]
            phonetic = data.get('phonetic', 'No disponible')
            
            for meaning in data.get('meanings', []):
                for definition in meaning.get('definitions', []):
                    if 'example' in definition:
                        examples.append(definition['example'])
                        if len(examples) >= 3:
                            break
    except Exception:
        pass

    return {
        "word": clean_word,
        "translation": translated_word,
        "phonetic": phonetic,
        "examples": examples if examples else ["No se encontraron ejemplos específicos."]
    }

# 3. Función para generar audio de pronunciación con gTTS
def play_audio(text):
    tts = gTTS(text=text, lang='en', slow=False)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    st.audio(fp, format='audio/mp3')

# ----------------- INTERFAZ DE USUARIO -----------------

youtube_url = st.text_input("Enlace del vídeo de YouTube:", placeholder="https://www.youtube.com/watch?v=...")

if youtube_url:
    video_id = get_youtube_id(youtube_url)
    
    if video_id:
        st.video(f"https://www.youtube.com/watch?v={video_id}")
        
        st.subheader("📜 Transcripción y Traducción")
        
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US'])
            translator = GoogleTranslator(source='auto', target='es')
            
            col_transcript, col_dictionary = st.columns([2, 1])
            
            with col_transcript:
                for entry in transcript_list[:30]: # Límite para prueba rápida
                    original_text = entry['text']
                    translated_text = translator.translate(original_text)
                    
                    st.markdown("---")
                    st.markdown(f"**Original:** {original_text}")
                    st.markdown(f"**Traducción (ES):** *{translated_text}*")
            
            with col_dictionary:
                st.sidebar.header("🔍 Diccionario Interactivo")
                selected_word = st.sidebar.text_input("Escribe una palabra para analizar:")
                
                if selected_word:
                    info = get_word_info(selected_word)
                    st.sidebar.subheader(f"📌 {info['word'].capitalize()}")
                    
                    # Audio de pronunciación
                    st.sidebar.write("**Pronunciación nativa:**")
                    play_audio(info['word'])
                    
                    st.sidebar.write(f"**Traducción:** {info['translation']}")
                    st.sidebar.write(f"**Fonética:** `{info['phonetic']}`")
                    
                    st.sidebar.write("**Ejemplos de uso:**")
                    for ex in info['examples']:
                        st.sidebar.write(f"- *{ex}*")
                    
                    # Botón para guardar en Anki
                    if st.sidebar.button("➕ Guardar palabra para Anki"):
                        card_data = {
                            "word": info['word'],
                            "translation": info['translation'],
                            "phonetic": info['phonetic'],
                            "example": info['examples'][0] if info['examples'] else ""
                        }
                        if card_data not in st.session_state.vocab_list:
                            st.session_state.vocab_list.append(card_data)
                            st.sidebar.success(f"¡'{info['word']}' guardada!")
                        else:
                            st.sidebar.warning("Esta palabra ya está en tu lista.")

                # Sección de Exportación a Anki en la barra lateral
                st.sidebar.markdown("---")
                st.sidebar.header("📦 Exportar a Anki")
                if st.session_state.vocab_list:
                    st.sidebar.write(f"Palabras guardadas: **{len(st.session_state.vocab_list)}**")
                    
                    # Generar texto plano separado por tabulaciones (Formato estándar para importar en Anki)
                    anki_export_text = ""
                    for item in st.session_state.vocab_list:
                        # Formato: Palabra [TAB] Traducción [TAB] Fonética / Ejemplo
                        anki_export_text += f"{item['word']}\t{item['translation']}\t{item['phonetic']} | Ejemplo: {item['example']}\n"
                    
                    st.sidebar.download_button(
                        label="📥 Descargar archivo para Anki (.txt)",
                        data=anki_export_text,
                        file_name="vocabulario_youtube_anki.txt",
                        mime="text/plain"
                    )
                    
                    if st.sidebar.button("🗑️ Limpiar lista"):
                        st.session_state.vocab_list = []
                        st.rerun()
                else:
                    st.sidebar.info("Guarda palabras desde el diccionario para poder exportarlas aquí.")
                        
        except Exception as e:
            st.error("No se pudieron cargar los subtítulos para este video. Asegúrate de que tenga subtítulos activados.")
    else:
        st.warning("Por favor introduce una URL válida de YouTube.")
