import streamlit as st
import google.generativeai as genai
from pokemontcgsdk import Card
from pokemontcgsdk import RestClient
from gtts import gTTS
from pydub import AudioSegment
import tempfile
import os
import json

# --- 1. CONFIGURATIE ---
# Vul hier je keys in!
GOOGLE_API_KEY = "JOUW_GOOGLE_API_KEY_HIER"
TCG_API_KEY = "d26a9544-873c-4f6d-ba7b-37fa05ad47c9"  # Optioneel, mag ook leeg als je geen key hebt, maar beter met.

genai.configure(api_key=GOOGLE_API_KEY)
RestClient.configure(api_key=TCG_API_KEY)

st.set_page_config(layout="wide", page_title="Holocron Scanner")

# CSS: Verberg alles behalve de enorme 'blinde' knop
st.markdown("""
<style>
    .stApp {background-color: black;}
    div[data-testid="stCameraInput"] {width: 100%;}
    div[data-testid="stCameraInput"] button {
        height: 400px; 
        width: 100%; 
        opacity: 0.1; /* Bijna onzichtbaar, maar wel klikbaar */
        border: 5px solid red; /* Handig voor jou om te richten */
    }
    header, footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# --- 2. FUNCTIES ---

def identify_card_with_gemini(image):
    """Gebruikt Vision AI om ALLEEN de naam en het nummer te lezen."""
    model = genai.GenerativeModel('gemini-1.5-flash')

    # We dwingen JSON output af voor stabiliteit
    prompt = """
    Bekijk deze Pokemon kaart. Ik heb de exacte naam en het kaartnummer (bijv. 4/102) nodig.
    Geef antwoord in puur JSON formaat: {"name": "Charizard", "number": "4", "set_id": "base1"}
    Als je het niet ziet, geef {"error": "niet zichtbaar"}.
    """
    try:
        response = model.generate_content([prompt, image])
        # Schoonmaken van de output (soms doet Gemini markdown ```json eromheen)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except:
        return {"error": "Parse error"}


def get_real_price(name, number):
    """Haalt de ECHTE prijs op via de SDK."""
    try:
        # Zoek query: naam en nummer is vaak het nauwkeurigst
        query = f'name:"{name}" number:"{number}"'
        cards = Card.where(q=query)

        if len(cards) > 0:
            # Pak de eerste match
            c = cards[0]
            # Probeer marktprijs te vinden, fallback naar mid prijs
            if c.tcgplayer and c.tcgplayer.prices:
                # Prioriteit: Holofoil -> Normal -> Reverse Holo
                prices = c.tcgplayer.prices
                if hasattr(prices, 'holofoil') and prices.holofoil:
                    return prices.holofoil.market or prices.holofoil.mid, c.name
                if hasattr(prices, 'normal') and prices.normal:
                    return prices.normal.market or prices.normal.mid, c.name
                if hasattr(prices, 'reverseHolofoil') and prices.reverseHolofoil:
                    return prices.reverseHolofoil.market or prices.reverseHolofoil.mid, c.name

            return 0.0, c.name
        else:
            return None, None
    except Exception as e:
        print(f"SDK Error: {e}")
        return None, None


def generate_c3po_speech_text(card_name, price):
    """Laat Gemini de C-3PO tekst verzinnen."""
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Als prijs 0 of None is
    val_text = f"ongeveer {price} euro" if price else "onbekend"

    prompt = f"""
    Je bent C-3PO. Je spreekt NEDERLANDS.
    Je hebt net een kaart gescand: {card_name}. Waarde: {val_text}.

    Opdracht:
    1. Reageer geschrokken of bezorgd (typisch C-3PO).
    2. Noem de Pokémon naam en de waarde.
    3. Zeg tegen 'Meester Jelle's neefje' (noem geen naam) dat hij voorzichtig moet zijn.
    4. Houd het kort (max 3 zinnen).
    """
    response = model.generate_content(prompt)
    return response.text


def make_it_sound_like_c3po(text):
    """Maakt audio en vervormt deze naar robot-achtig."""
    # 1. Basis TTS (Nederlands)
    tts = gTTS(text=text, lang='nl')

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        tts.save(fp.name)
        orig_file = fp.name

    # 2. Audio manipulatie met Pydub (Pitch & Speed)
    sound = AudioSegment.from_mp3(orig_file)

    # C-3PO praat sneller en iets hoger
    # Speedup (hacky way: frame rate manipulatie)
    new_sample_rate = int(sound.frame_rate * 1.25)  # 25% sneller
    sound_speedy = sound._spawn(sound.raw_data, overrides={'frame_rate': new_sample_rate})
    sound_speedy = sound_speedy.set_frame_rate(44100)  # Reset naar standaard

    # Pitch shift (beetje omhoog voor robot effect)
    # Pydub heeft geen native pitch shift zonder speed change,
    # maar de speed change hierboven doet ook pitch omhoog!
    # Dus we zijn er eigenlijk al. 2 vliegen in 1 klap.

    processed_file = orig_file.replace(".mp3", "_c3po.mp3")
    sound_speedy.export(processed_file, format="mp3")

    return processed_file


# --- 3. MAIN APP FLOW ---

# Camera input (onzichtbare knop, schermvullend)
img_buffer = st.camera_input("Scan", label_visibility="hidden")

if img_buffer:
    st.write("Analyseren...")  # Feedback voor jou op scrcpy

    import PIL.Image

    img = PIL.Image.open(img_buffer)

    # Stap 1: Wat is het?
    id_data = identify_card_with_gemini(img)

    if "error" not in id_data:
        name = id_data.get("name")
        number = id_data.get("number")

        # Stap 2: Wat kost het?
        price, full_name = get_real_price(name, number)

        # Stap 3: Wat zegt C-3PO?
        c3po_text = generate_c3po_speech_text(full_name or name, price)
        st.success(c3po_text)  # Tekst feedback

        # Stap 4: Audio genereren
        audio_path = make_it_sound_like_c3po(c3po_text)

        # Stap 5: Afspelen
        st.audio(audio_path, format='audio/mp3', autoplay=True)

    else:
        st.error("Oh jee, mijn sensoren zien niets!")