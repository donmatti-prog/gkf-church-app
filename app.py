import streamlit as st
import re
import urllib.request
import json

# Setup page configuration
st.set_page_config(page_title="GKF Connect", page_icon="⛪", layout="centered")

# --- CUSTOM CHURCH BACKGROUND ---
background_image_url = "https://unsplash.com"
st.markdown(
    f"""
    <style>
    .stApp {{
        background: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), url("{background_image_url}");
        background-size: cover; background-position: center; background-attachment: fixed;
    }}
    h1, h2, h3, p, span, label {{ color: #ffffff !important; }}
    [data-testid="stSidebar"] {{ background-color: rgba(30, 41, 59, 0.95); }}
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {{
        background-color: rgba(255, 255, 255, 0.9) !important; color: #1e293b !important;
    }}
    .chord-sheet {{
        font-family: monospace; white-space: pre; background-color: rgba(0, 0, 0, 0.6);
        padding: 15px; border-radius: 5px; color: #ffd700 !important; line-height: 1.6; font-size: 15px; overflow-x: auto;
    }}
    /* Giant text styling for projector screens */
    .projector-text {{
        font-size: 42px; font-weight: bold; color: #ffffff; text-align: center;
        line-height: 1.4; padding: 40px 10px; font-family: 'Helvetica Neue', sans-serif;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.8);
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# --- CHORD TRANSPOSER ENGINE ---
def transpose_ultimate_guitar_text(text, semitones):
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    chord_pattern = re.compile(r"\b([A-G][#b]?)(m|min|maj|min7|maj7|7|sus2|sus4|add9|dim|aug)?(/[A-G][#b]?)?\b")

    def transpose_single_chord(match):
        chord_text = match.group(0)
        parts = chord_text.split('/')
        transposed_parts = []
        for part in parts:
            base_note_match = re.match(r"^[A-G][#b]?", part)
            if base_note_match:
                base_note = base_note_match.group(0)
                suffix = part[len(base_note):]
                if "Db" in base_note:
                    base_note = "C#"
                elif "Eb" in base_note:
                    base_note = "D#"
                elif "Gb" in base_note:
                    base_note = "F#"
                elif "Ab" in base_note:
                    base_note = "G#"
                elif "Bb" in base_note:
                    base_note = "A#"

                if base_note in notes:
                    new_idx = (notes.index(base_note) + semitones) % 12
                    transposed_parts.append(f"{notes[new_idx]}{suffix}")
                else:
                    transposed_parts.append(part)
            else:
                transposed_parts.append(part)
        return "/".join(transposed_parts)

    output_lines = []
    for line in text.split("\n"):
        clean_line = line.rstrip()
        if not clean_line.strip():
            output_lines.append("")
            continue
        words = clean_line.split()
        chord_words_count = sum(1 for w in words if chord_pattern.match(w))
        if len(words) > 0 and chord_words_count / len(words) >= 0.7:
            output_lines.append(chord_pattern.sub(transpose_single_chord, clean_line))
        else:
            output_lines.append(clean_line)
    return "\n".join(output_lines)


# --- LYRICS STRIPPER ---
def get_clean_lyrics_only(text):
    chord_pattern = re.compile(r"\b([A-G][#b]?)(m|min|maj|min7|maj7|7|sus2|sus4|add9|dim|aug)?(/[A-G][#b]?)?\b")
    clean_lines = []
    for line in text.split("\n"):
        words = line.split()
        if len(words) > 0 and (sum(1 for w in words if chord_pattern.match(w)) / len(words)) >= 0.7:
            continue
        clean_lines.append(line)
    return "\n".join(clean_lines)


# --- SMART WEB BIBLE APIS ENGINE ---
import urllib.request
import urllib.parse
import json


def fetch_bible_verse_text(reference, translation_code="web"):
    try:
        # 1. Standardize translation strings for the AO Lab API format
        api_trans = "web" if translation_code.lower() == "web" else "kjv"

        # 2. Parse out book name vs chapters/verses safely (e.g., "John 3:16" -> book="john", chapter=3)
        match = re.match(r"^([0-9]?\s*[a-zA-Z\s]+)\s+([0-9]+):([0-9\-,]+)", reference.strip())
        if not match:
            return None

        book_name = match.group(1).strip().lower().replace(" ", "-")
        chapter_num = match.group(2)
        verse_range = match.group(3)

        # 3. Request the clean, static chapter data array from low-latency global hosting
        url = f"https://helloao.org{api_trans}/books/{book_name}/chapters/{chapter_num}.json"

        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))

            # 4. Filter and piece together only the verses requested
            if "chapter" in data and "verses" in data["chapter"]:
                all_verses = data["chapter"]["verses"]
                compiled_text = []

                # Handle standard single verses vs sequence arrays (e.g. 16 vs 16-18)
                if "-" in verse_range:
                    start_v, end_v = map(int, verse_range.split("-"))
                    target_range = range(start_v, end_v + 1)
                else:
                    target_range = [int(verse_range)]

                for v in all_verses:
                    if "number" in v and int(v["number"]) in target_range:
                        # Extract string elements clean from the paragraph structures
                        verse_str = "".join([t["text"] for t in v.get("content", []) if t.get("type") == "text"])
                        compiled_text.append(f"{v['number']}. {verse_str.strip()}")

                if compiled_text:
                    return " ".join(compiled_text)
    except Exception as e:
        print(f"Bible Backup Engine Error: {e}")
    return None
# --- GLOBAL SERVICE STATE ---
if "playlist" not in st.session_state:
    st.session_state.playlist = [
        {
            "title": "Amazing Grace", "original_key": "G",
            "sheet": "G              C              G\nAmazing grace! How sweet the sound\n               D\nThat saved a wretch like me!",
            "link": ""
        }
    ]
if "sermon_slides" not in st.session_state:
    st.session_state.sermon_slides = [
        "Velkommen til GKF! 🙏\nJessheim Misjonssenter",
        "Dagens tema: Growing in Faith Together",
        "Takk for i dag! Velkommen igjen neste søndag kl. 11:00."
    ]
if "active_slide_index" not in st.session_state: st.session_state.active_slide_index = 0
if "rsvp_count" not in st.session_state: st.session_state.rsvp_count = 0
if "minutes" not in st.session_state: st.session_state.minutes = []
if "logged_in" not in st.session_state: st.session_state.logged_in = False

# --- LOGIN SCREEN ---
if not st.session_state.logged_in:
    st.title("⛪ Gardermoen Kristne Fellesskap")
    st.subheader("GKF Service & Media Suite")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == "member" and password == "church123":
            st.session_state.logged_in, st.session_state.user_role = True, "Member"
        elif username == "band" and password == "music123":
            st.session_state.logged_in, st.session_state.user_role = True, "Band"
        elif username == "leader" and password == "lead123":
            st.session_state.logged_in, st.session_state.user_role = True, "Leadership"
        st.rerun()
else:
    role = st.session_state.user_role
    st.sidebar.title("GKF Control Center")

    tabs = ["🏠 Hjem / Dashboard", "📺 Projector Screen"]
    if role in ["Band", "Leadership"]: tabs.append("🎵 Band Portal")
    if role == "Leadership": tabs.append("Leadership Area Settings")
    choice = st.sidebar.radio("Go to:", tabs)

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- 1. MAIN MEMBER DASHBOARD ---
    if choice == "🏠 Hjem / Dashboard":
        st.title("⛪ GKF Sunday Service")
        st.info("📅 **Next Service:** Sunday at 11:00 AM\n\n📍 **Location:** Jessheim Misjonssenter")

        st.subheader("🎵 Today's Setlist")
        for song in st.session_state.playlist:
            st.write(f"• {song['title']}")

        st.subheader("Attendance Check-in")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ I Will Attend"): st.session_state.rsvp_count += 1; st.success("RSVP registered!")
        with col2:
            if st.button("❌ Cannot Attend"): st.warning("Noted!")
        st.metric("Total Attending", st.session_state.rsvp_count)

    # --- 2. THE MAIN PROJECTOR SCREEN ---
    elif choice == "📺 Projector Screen":
        st.title("🖥️ Main Sanctuary Projection")
        st.caption("Maximize this browser window on your church projector screen.")

        master_slides = list(st.session_state.sermon_slides)
        for song in st.session_state.playlist:
            clean_lyrics = get_clean_lyrics_only(song['sheet'])
            for verse in clean_lyrics.split("\n\n"):
                if verse.strip():
                    master_slides.append(f"🎵 {song['title']}\n\n{verse.strip()}")

        if st.session_state.active_slide_index >= len(master_slides):
            st.session_state.active_slide_index = 0

        current_slide_content = master_slides[st.session_state.active_slide_index]
        formatted_slide = current_slide_content.replace("\n", "<br>")
        st.markdown(f'<div class="projector-text">{formatted_slide}</div>', unsafe_allow_html=True)

        st.components.v1.html(
            """
            <script>
            const doc = window.parent.document;
            doc.onkeydown = function(e) {
                if (e.key === "ArrowRight" || e.key === "PageDown") {
                    window.parent.location.reload();
                }
            };
            </script>
            """, height=0
        )

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("⬅️ Back") and st.session_state.active_slide_index > 0:
                st.session_state.active_slide_index -= 1
                st.rerun()
        with c2:
            st.write(f"<center>Slide {st.session_state.active_slide_index + 1} of {len(master_slides)}</center>",
                     unsafe_allow_html=True)
        with c3:
            if st.button("Next ➡️") and st.session_state.active_slide_index < len(master_slides) - 1:
                st.session_state.active_slide_index += 1
                st.rerun()

    # --- 3. BAND PORTAL ---
    elif choice == "🎵 Band Portal":
        st.title("🎵 Worship Band Portal")

        st.warning("📱 **Stage Phone Remote Control**")
        st.write("Change slides on the sanctuary projector directly from your phone on stage:")

        master_slides_ref = list(st.session_state.sermon_slides)
        for song in st.session_state.playlist:
            for verse in get_clean_lyrics_only(song['sheet']).split("\n\n"):
                if verse.strip():
                    master_slides_ref.append(f"🎵 {song['title']}: {verse.strip()[:30]}...")

        remote_select = st.selectbox("Force Projector Screen to display:", master_slides_ref,
                                     index=st.session_state.active_slide_index)
        if master_slides_ref.index(remote_select) != st.session_state.active_slide_index:
            st.session_state.active_slide_index = master_slides_ref.index(remote_select)
            st.success("Projector updated remote live!")
            st.rerun()

        # REMODELED API BIBLE SEARCH SECTION
        st.markdown("---")
        st.subheader("📖 Quick Stage Bible Finder")
        st.caption("Look up any verse to project it directly onto the main screen:")
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            ref_input = st.text_input("Enter Reference (e.g., John 3:16, Genesis 1:1)", key="band_ref")
        with b_col2:
            version = st.selectbox("Version / Translation", ["WEB (World English Bible)", "KJV (King James Version)"],
                                   key="band_ver")

        if st.button("🌟 Project Verse to Screen", key="band_proj_btn"):
            if ref_input:
                v_code = "web" if "WEB" in version else "kjv"
                clean_text = fetch_bible_verse_text(ref_input, v_code)
                if clean_text:
                    slide_format = f"📖 {ref_input}\n\n\"{clean_text}\""
                    st.session_state.sermon_slides.append(slide_format)
                    st.session_state.active_slide_index = len(st.session_state.sermon_slides) - 1
                    st.success(f"Sent {ref_input} directly to projector!")
                    st.rerun()
                else:
                    st.error("Could not find verse text. Check spelling (e.g., John 3:16).")

        st.markdown("---")
        st.subheader("Add Song from Ultimate Guitar")
        with st.form("song_form"):
            new_title = st.text_input("Song Title")
            new_key = st.selectbox("Starting Key", ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])
            new_sheet = st.text_area("Paste Ultimate Guitar Text Here (Use empty double lines between verses)",
                                     height=150)
            if st.form_submit_button("Save Song") and new_title:
                st.session_state.playlist.append({"title": new_title, "original_key": new_key, "sheet": new_sheet})
                st.rerun()

        st.subheader("Team Chord Sheets")
        keys_list = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        for idx, song_data in enumerate(st.session_state.playlist):
            with st.expander(f"{idx + 1}. {song_data['title']} (Key: {song_data['original_key']})"):
                start_index = keys_list.index(song_data['original_key']) if song_data[
                                                                                'original_key'] in keys_list else 0
                target_key = st.selectbox("Transpose team key to:", keys_list, index=start_index, key=f"trans_{idx}")
                semitones = keys_list.index(target_key) - start_index
                st.markdown(
                    f'<div class="chord-sheet">{transpose_ultimate_guitar_text(song_data["sheet"], semitones)}</div>',
                    unsafe_allow_html=True)

    # --- 4. LEADERSHIP & SERMON SLIDE COMPILER ---
    elif choice == "Leadership Area Settings":
        st.title("💼 Church Leadership Portal")

        # BIBLE VIEWER SECTION
        st.subheader("📖 Pastor's Sermon Bible Search")
        st.caption("Search scripture verses and append them straight into your slide deck database:")
        lead_b1, lead_b2 = st.columns(2)
        with lead_b1:
            l_ref = st.text_input("Enter Citation (e.g., John 1:1, Psalms 23:1)", key="lead_ref")
        with lead_b2:
            l_ver = st.selectbox("Version", ["NIV", "ASV"], key="lead_ver")

        if st.button("➕ Append to Sermon Slide Deck"):
            if l_ref:
                # We make sure the variable is named exactly v_code
                v_code = "web" if "WEB" in l_ver else "kjv"
                clean_text = fetch_bible_verse_text(l_ref, v_code)
                if clean_text:
                    slide_format = f"📖 {l_ref}\n\n\"{clean_text}\""
                    st.session_state.sermon_slides.append(slide_format)
                    st.success(f"Added {l_ref} to slide deck list!")
                    st.rerun()
                else:
                    st.error("Could not load verse. Please verify entry format.")

        st.markdown("---")
        st.subheader("📺 Compile Pastor's Sermon Slides")
        st.caption("Write out sermon points or scriptures. Put each new slide on its own line.")
        sermon_input = st.text_area("Sermon Slides Input Box", value="\n".join(st.session_state.sermon_slides),
                                    height=150)
        if st.button("⚡ Update Service Slides"):
            st.session_state.sermon_slides = [line.strip() for line in sermon_input.split("\n") if line.strip()]
            st.success("Sermon deck synced across all sanctuary screens!")
            st.rerun()

        st.markdown("---")
        st.subheader("📝 Internal Board Minutes")
        with st.form("minutes_form"):
            new_meeting = st.text_area("Enter private meeting minutes:")
            if st.form_submit_button("Archive Minutes") and new_meeting:
                st.session_state.minutes.append(new_meeting)
                st.success("Archived safely.")
                st.rerun()

        for minutes in reversed(st.session_state.minutes):
            st.markdown(f"--- \n {minutes}")

