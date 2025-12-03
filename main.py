import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import tempfile
import os

# --- CONFIGURATIE ---
# LET OP: Zet je API key hieronder tussen de haakjes!
api_key = "AIzaSyC9o4qtyqQhRaRlUPTQn9Fy-Oni2L3xINI"

genai.configure(api_key=api_key)

# Instellingen voor de pagina (zodat het op mobiel past)
st.set_page_config(layout="wide", page_title="Gonk Scanner")

# CSS om de knop ENORM te maken (zodat je neefje niet kan missen)
st.markdown("""
<style>
    /* Maak de camera input en knop onzichtbaar maar wel klikbaar of positioneer ze */
    .stCameraInput {
        width: 100%;
    }
    div[data-testid="stCameraInput"] button {
        height: 300px; /* Enorme knop */
        width: 100%;
        background-color: transparent;
        border: 2px solid red; /* Tijdelijk rood om te mikken, later weg */
        color: transparent;
    }
    /* Verberg header en footer */
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# --- FUNCTIES ---

def get_c3po_analysis(image_data):
    """Stuurt foto naar Gemini en vraagt om C-3PO response + prijs."""
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = """
    Je bent C-3PO uit Star Wars. Je bent beleefd maar altijd een beetje bezorgd.
    Bekijk deze Pokémon kaart. 
    1. Identificeer de Pokémon en de kaart set.
    2. Schat de waarde in Euro's (schatting is prima).
    3. Geef antwoord als C-3PO tegen een jong kind. Zeg iets over de 'power level' of dat de kaart zeldzaam is.

    Houd het kort (maximaal 3 zinnen). Begin met een typische C-3PO uitspraak.
    Eindig met de geschatte waarde duidelijk te noemen.
    """

    try:
        # Streamlit camera input geeft een BytesIO object
        import PIL.Image
        img = PIL.Image.open(image_data)

        response = model.generate_content([prompt, img])
        return response.text
    except Exception as e:
        return f"Oh dear, my sensors are malfunctioning. Error: {e}"


def speak_text(text):
    """Zet tekst om naar spraak (C-3PO stem benadering is lastig, we doen gewoon NL/EN)."""
    try:
        # We gebruiken 'en' voor een Engels accent, of 'nl' als je wilt dat hij NL spreekt.
        # C-3PO spreekt vaak Engels, maar voor je neefje is NL misschien leuker?
        # Laten we NL doen met een 'robot' sausje is lastig, gTTS is vrij standaard.
        tts = gTTS(text=text, lang='nl')

        # Tijdelijk bestand
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            return fp.name
    except Exception as e:
        st.error(f"Audio error: {e}")
        return None


# --- MAIN APP ---

# Omdat het scherm kapot is, bouwen we een 'blinde' interface.
# De app wacht eigenlijk alleen op de camera input.

img_file_buffer = st.camera_input("SCANNER_ACTIVATED", label_visibility="hidden")

if img_file_buffer is not None:
    # 1. Feedback dat hij bezig is (voor jou via scrcpy te zien)
    st.write("Processing artifact...")

    # 2. AI Analyse
    result_text = get_c3po_analysis(img_file_buffer)

    # 3. Print resultaat (voor debug)
    st.success(result_text)

    # 4. Spreek resultaat uit
    audio_file = speak_text(result_text)
    if audio_file:
        # Autoplay proberen we te forceren
        st.audio(audio_file, format="audio/mp3", autoplay=True)
        # Clean up file later
        os.unlink(audio_file)