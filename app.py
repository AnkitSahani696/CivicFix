import os
import time
import uuid
import streamlit as st
import folium
from streamlit_folium import st_folium

from model import predict_category, get_priority, find_duplicate
from database import (init_db, add_complaint, get_all_complaints,
                      update_status, add_duplicate_count, get_complaint)

st.set_page_config(page_title="CivicFix", page_icon="🏙️", layout="wide")
init_db()

# ---------------- SPLASH SCREEN ----------------
SPLASH_HTML = """
<style>
.splash {
    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
    background: linear-gradient(135deg, #4F46E5, #7C3AED, #EC4899);
    z-index: 999999;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    color: white; font-family: sans-serif;
}
.splash-logo { font-size: 90px; animation: pulse 1.2s infinite; }
.splash-title { font-size: 52px; font-weight: 800; letter-spacing: 2px; margin-top: 10px; }
.splash-sub { font-size: 18px; opacity: 0.9; margin-top: 8px; }
.splash-bar { width: 260px; height: 6px; background: rgba(255,255,255,0.3);
              border-radius: 10px; margin-top: 35px; overflow: hidden; }
.splash-bar div { height: 100%; width: 0; background: white; border-radius: 10px;
                  animation: load 2.8s ease-in-out forwards; }
@keyframes pulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.15); } }
@keyframes load { to { width: 100%; } }
</style>
<div class="splash">
<div class="splash-logo">🏙️</div>
<div class="splash-title">CivicFix</div>
<div class="splash-sub">AI-Powered Civic Complaint Management</div>
<div class="splash-bar"><div></div></div>
</div>
"""

if "splash_done" not in st.session_state:
    splash = st.empty()
    splash.markdown(SPLASH_HTML, unsafe_allow_html=True)
    time.sleep(3)
    splash.empty()
    st.session_state["splash_done"] = True

# ---------------- CUSTOM CSS ----------------
CSS = """
<style>
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 1.5rem;}

.hero {
    background: linear-gradient(135deg, #4F46E5, #7C3AED, #EC4899);
    padding: 28px 35px; border-radius: 20px; color: white;
    box-shadow: 0 10px 30px rgba(79,70,229,0.3); margin-bottom: 25px;
}
.hero h1 {margin: 0; font-size: 38px; color: white;}
.hero p {margin: 6px 0 0 0; font-size: 16px; opacity: 0.95;}

.stat-card {
    background: white; padding: 20px; border-radius: 16px;
    text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.07);
}
.stat-icon {font-size: 30px;}
.stat-value {font-size: 34px; font-weight: 800; color: #1F2937;}
.stat-label {font-size: 14px; color: #6B7280;}

.badge {
    display: inline-block; padding: 5px 14px; border-radius: 20px;
    color: white; font-weight: 700; font-size: 14px; margin-right: 8px;
}
.result-box {
    background: white; padding: 20px; border-radius: 16px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.07); margin-top: 15px;
}

.stTabs [data-baseweb="tab-list"] {gap: 10px;}
.stTabs [data-baseweb="tab"] {
    background: white; border-radius: 12px; padding: 10px 22px;
    font-weight: 600; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #4F46E5, #7C3AED); color: white;
}
.stButton > button {
    background: linear-gradient(135deg, #4F46E5, #7C3AED); color: white;
    border: none; border-radius: 12px; padding: 10px 28px; font-weight: 700;
}
.stButton > button:hover {transform: translateY(-2px); color: white;}

.footer {text-align: center; color: #9CA3AF; margin-top: 40px; font-size: 13px;}

html, body, .stMarkdown p, .stMarkdown li { font-size: 19px !important; }
[data-testid="stWidgetLabel"] p { font-size: 20px !important; font-weight: 600; }
.stTextArea textarea { font-size: 21px !important; }
.stTextInput input, .stNumberInput input { font-size: 21px !important; }
div[data-baseweb="select"] { font-size: 20px !important; }
.stTabs [data-baseweb="tab"] p { font-size: 19px !important; }
.stButton > button p { font-size: 19px !important; }
.stAlert p { font-size: 18px !important; }
h3 { font-size: 28px !important; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ---------------- HELPERS ----------------
PRIORITY_COLORS = {"High": "#EF4444", "Medium": "#F59E0B", "Low": "#10B981"}
CATEGORY_ICONS = {"Road": "🛣️", "Garbage": "🗑️", "Water": "💧", "Electricity": "💡"}

AREAS = {
    "Adajan": (21.1959, 72.7933),
    "Vesu": (21.1416, 72.7710),
    "Varachha": (21.2049, 72.8567),
    "Katargam": (21.2290, 72.8300),
    "Udhna": (21.1702, 72.8450),
    "Piplod": (21.1530, 72.7680),
}

os.makedirs("uploads", exist_ok=True)

OFFICER_PASSWORD = "civicfix123"

if "officer_logged_in" not in st.session_state:
    st.session_state["officer_logged_in"] = False


def stat_card(col, icon, label, value, color):
    col.markdown(
        f'<div class="stat-card" style="border-top:4px solid {color}">'
        f'<div class="stat-icon">{icon}</div>'
        f'<div class="stat-value">{value}</div>'
        f'<div class="stat-label">{label}</div></div>',
        unsafe_allow_html=True,
    )


def result_box(category, priority):
    icon = CATEGORY_ICONS.get(category, "📌")
    color = PRIORITY_COLORS.get(priority, "#6B7280")
    st.markdown(
        f'<div class="result-box">'
        f'<b>AI ne detect kiya:</b><br><br>'
        f'<span class="badge" style="background:#4F46E5">{icon} {category}</span>'
        f'<span class="badge" style="background:{color}">Priority: {priority}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------- HEADER ----------------
st.markdown(
    '<div class="hero"><h1>🏙️ CivicFix</h1>'
    '<p>Smart AI system jo shehar ki complaints ko samajhta, sort karta aur solve karwata hai</p></div>',
    unsafe_allow_html=True,
)

tab1, tab_track, tab2, tab3 = st.tabs(
    ["📝 Complaint Karo", "🔍 Status Track", "👮 Officer Dashboard", "🗺️ Map"])

# ---------------- TAB 1: Citizen form ----------------
with tab1:
    left, right = st.columns([3, 2])

    with left:
        st.subheader("Apni complaint likho")
        text = st.text_area("Complaint (Hindi / Hinglish / English)", height=130,
                            placeholder="Jaise: sadak par bada gadha hai, accident ka khatra hai")
        area = st.selectbox("Area", list(AREAS.keys()))
        photo_file = st.file_uploader("📷 Issue ki photo (optional)",
                                      type=["jpg", "jpeg", "png"])
        submit = st.button("🚀 Submit Complaint")

    with right:
        st.subheader("Kaise kaam karta hai?")
        st.markdown(
            "1. Aap complaint likhte ho\n"
            "2. AI category aur priority detect karta hai\n"
            "3. Duplicate complaint merge hoti hai\n"
            "4. Officer ko dashboard par dikhti hai"
        )

    if submit:
        if text.strip() == "":
            st.warning("Pehle complaint likho.")
        else:
            df_all = get_all_complaints()
            same_area = df_all[(df_all["area"] == area) & (df_all["status"] != "Resolved")]
            dup_index = find_duplicate(text, same_area["text"].tolist())

            if dup_index is not None:
                original_id = int(same_area.iloc[dup_index]["id"])
                add_duplicate_count(original_id)
                st.warning(f"Aisi complaint pehle se darj hai (ID {original_id}). "
                           "Humne usse merge kar diya, officer ko extra priority milegi.")
                st.info(f"🔖 Track karne ke liye Complaint ID: **{original_id}**")
            else:
                category = predict_category(text)
                priority = get_priority(text)
                lat, lon = AREAS[area]

                photo_path = None
                if photo_file is not None:
                    ext = photo_file.name.split(".")[-1]
                    photo_path = f"uploads/{uuid.uuid4().hex}.{ext}"
                    with open(photo_path, "wb") as f:
                        f.write(photo_file.getbuffer())

                new_id = add_complaint(text, category, priority, area, lat, lon, photo_path)
                st.success("✅ Complaint darj ho gayi!")
                st.info(f"🔖 Aapki Complaint ID: **{new_id}** (isse Status Track tab mein dalo)")
                result_box(category, priority)

# ---------------- TAB: Status Track ----------------
with tab_track:
    st.subheader("Apni complaint ka status dekho")
    track_id = st.number_input("Complaint ID daalo", min_value=1, step=1)

    if st.button("🔍 Track Karo"):
        result = get_complaint(int(track_id))
        if result.empty:
            st.error("Is ID ki koi complaint nahi mili.")
        else:
            row = result.iloc[0]
            steps = ["Pending", "In Progress", "Resolved"]
            current = steps.index(row["status"])

            html = '<div class="result-box"><b>Progress:</b><br><br>'
            for i, s in enumerate(steps):
                color = "#10B981" if i <= current else "#D1D5DB"
                html += f'<span class="badge" style="background:{color}">{s}</span>'
            html += (f'<br><br><b>Complaint:</b> {row["text"]}<br>'
                     f'<b>Category:</b> {row["category"]}<br>'
                     f'<b>Priority:</b> {row["priority"]}<br>'
                     f'<b>Area:</b> {row["area"]}<br>'
                     f'<b>Darj hui:</b> {row["created_at"]}</div>')
            st.markdown(html, unsafe_allow_html=True)

            if row["photo"] and os.path.exists(row["photo"]):
                st.image(row["photo"], caption="Complaint ki photo", width=400)

# ---------------- TAB 2: Officer dashboard ----------------
with tab2:
    if not st.session_state["officer_logged_in"]:
        st.subheader("🔐 Officer Login")
        pwd = st.text_input("Password daalo", type="password")
        if st.button("Login"):
            if pwd == OFFICER_PASSWORD:
                st.session_state["officer_logged_in"] = True
                st.rerun()
            else:
                st.error("Galat password.")
    else:
        if st.button("🚪 Logout"):
            st.session_state["officer_logged_in"] = False
            st.rerun()

        df = get_all_complaints()

        if df.empty:
            st.info("Abhi koi complaint nahi hai.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            stat_card(c1, "📋", "Total", len(df), "#4F46E5")
            stat_card(c2, "⏳", "Pending", len(df[df["status"] == "Pending"]), "#F59E0B")
            stat_card(c3, "🔥", "High Priority", len(df[df["priority"] == "High"]), "#EF4444")
            stat_card(c4, "✅", "Resolved", len(df[df["status"] == "Resolved"]), "#10B981")

            st.write("")
            st.subheader("Category ke hisaab se complaints")
            st.bar_chart(df["category"].value_counts())

            st.subheader("Saari complaints")
            st.dataframe(df, use_container_width=True)

            csv_data = df.drop(columns=["photo"]).to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Report Download Karo (CSV)",
                data=csv_data,
                file_name="civicfix_report.csv",
                mime="text/csv",
            )

            st.subheader("Complaint photos")
            photo_df = df[df["photo"].notna()]
            if photo_df.empty:
                st.caption("Abhi kisi complaint ke saath photo nahi hai.")
            else:
                cols = st.columns(3)
                for i, (_, r) in enumerate(photo_df.iterrows()):
                    if os.path.exists(r["photo"]):
                        cols[i % 3].image(
                            r["photo"],
                            caption=f"ID {r['id']} - {r['category']} ({r['area']})")

            st.subheader("Status update karo")
            u1, u2 = st.columns(2)
            cid = u1.selectbox("Complaint ID", df["id"].tolist())
            new_status = u2.selectbox("Naya status", ["Pending", "In Progress", "Resolved"])
            if st.button("Update Status"):
                update_status(cid, new_status)
                st.success("Status update ho gaya!")
                st.rerun()

# ---------------- TAB 3: Map ----------------
with tab3:
    st.subheader("Complaint Map")
    df = get_all_complaints()
    m = folium.Map(location=[21.1702, 72.8311], zoom_start=12)

    map_colors = {"High": "red", "Medium": "orange", "Low": "green"}
    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=9 + row["dup_count"] * 3,
            color=map_colors.get(row["priority"], "blue"),
            fill=True,
            popup=f"{row['category']} - {row['priority']}: {row['text']}",
        ).add_to(m)

    st_folium(m, width=1000, height=500)
    st.caption("🔴 High   🟠 Medium   🟢 Low   |   Bada circle = zyada duplicate complaints")

st.markdown('<div class="footer">Made with ❤️ for Hackathon | CivicFix</div>',
            unsafe_allow_html=True)