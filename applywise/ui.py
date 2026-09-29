from pathlib import Path
import streamlit as st


def style():
    st.html("<style>" + (Path(__file__).parent / "styles.css").read_text() + "</style>")


def hero():
    # Static HTML only; user and model text never enter this surface.
    st.html('''<div class="hero"><div class="eyebrow">APPLYWISE / YOUR NEXT CHAPTER</div>
    <h1>Make your experience<br><span>make sense for the role.</span></h1>
    <p>A clearer application starts with the facts. Find your fit, uncover relevant
    experience, and refine only what matters.</p>
    <div class="hero-tags"><span>Evidence before keywords</span><span>Questions only when useful</span><span>You approve every edit</span></div></div>''')


def steps(active):
    columns = st.columns(3)
    for i, label in enumerate(["01 · Add documents", "02 · Find your fit", "03 · Refine & export"]):
        with columns[i]:
            if i == active:
                st.success(label)
            else:
                st.caption(label)


def heading(kicker, title, description=""):
    st.caption(kicker.upper())
    st.subheader(title)
    if description:
        st.write(description)
