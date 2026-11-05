
from pathlib import Path
import re
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Canada AI Adoption Explorer",
    page_icon="🇨🇦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.block-container {
    padding-top: 1.5rem;
    max-width: 1500px;
}
div[data-testid="stMetric"] {
    border: 1px solid #e6eaf0;
    padding: 14px;
    border-radius: 12px;
    background: white;
}
.insight {
    border-left: 4px solid #2d7199;
    padding: 12px;
    background: #f3f7fb;
    border-radius: 5px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

ROOT = Path(__file__).resolve().parent

CANDIDATE_FILES = [
    ROOT / "data" / "processed" / "ai_adoption_clean_final.csv",
    ROOT / "data" / "processed" / "ai_adoption_model_ready.csv",
    ROOT / "data" / "processed" / "ai_adoption_numeric.csv",
    ROOT / "data" / "ai_adoption.csv",
]

@st.cache_data
def load_dataset():
    for path in CANDIDATE_FILES:
        if path.exists():
            df = pd.read_csv(path)
            if not df.empty:
                return df, str(path.relative_to(ROOT))
    return pd.DataFrame(), None

def clean_name(name):
    return re.sub(
        r"[^a-z0-9]+", "_", str(name).strip().lower()
    ).strip("_")

def find_column(columns, candidates):
    lookup = {clean_name(c): c for c in columns}

    for candidate in candidates:
        key = clean_name(candidate)
        if key in lookup:
            return lookup[key]

    for key, original in lookup.items():
        if any(clean_name(c) in key for c in candidates):
            return original

    return None

df, source_file = load_dataset()

st.title("🇨🇦 Canada AI Adoption Explorer")
st.caption(
    "An interactive analysis of AI adoption across Canadian industries "
    "using Statistics Canada data."
)

if df.empty:
    st.error("Dataset not found. Please check your data folder.")
    st.stop()

df.columns = [str(c).strip() for c in df.columns]

industry_col = find_column(
    df.columns, ["industry", "category", "group"]
)

adoption_col = find_column(
    df.columns,
    ["ai_adoption", "ai adoption", "ai_adoption_rate", "adoption"]
)

if industry_col is None:
    industry_col = df.columns[0]

if adoption_col is None:
    st.error("Could not identify the AI adoption column.")
    st.write("Columns found:", list(df.columns))
    st.stop()

df[adoption_col] = pd.to_numeric(
    df[adoption_col].astype(str)
    .str.replace("%", "", regex=False)
    .str.replace(",", "", regex=False),
    errors="coerce"
)

df[industry_col] = df[industry_col].astype(str).str.strip()
df = df.dropna(subset=[adoption_col]).copy()

aggregate = df[industry_col].str.contains(
    "all industries|NAICS.*all",
    case=False,
    regex=True,
    na=False
)

industry_df = df[~aggregate].copy()

if industry_df.empty:
    industry_df = df.copy()

# Identify technology columns
tech_aliases = {
    "Data analytics": ["data_analytics", "data analytics"],
    "Large language models (LLMs)": [
        "llm", "large_language_models", "large language models"
    ],
    "Chatbots": ["chatbots", "chatbot"],
    "Machine learning": ["machine_learning", "machine learning"],
    "Natural language processing": [
        "nlp", "natural_language_processing",
        "natural language processing"
    ],
    "Speech AI": ["speech_ai", "speech ai", "speech recognition"],
    "Recommendation AI": [
        "recommendation_ai", "recommendation ai",
        "recommendation systems"
    ],
    "Marketing automation": [
        "marketing_automation", "marketing automation"
    ],
    "Text analytics": ["text_analytics", "text analytics"],
}

tech_columns = {}

for label, aliases in tech_aliases.items():
    col = find_column(industry_df.columns, aliases)

    if col and col not in [industry_col, adoption_col]:
        values = pd.to_numeric(
            industry_df[col].astype(str)
            .str.replace("%", "", regex=False)
            .str.replace(",", "", regex=False),
            errors="coerce"
        )

        if values.notna().sum() > 0:
            industry_df[col] = values
            tech_columns[label] = col

# Sidebar
with st.sidebar:
    st.header("Explore the data")
    st.caption(f"Dataset: {source_file}")

    all_industries = sorted(
        industry_df[industry_col].dropna().unique().tolist()
    )

    selected_industries = st.multiselect(
        "Industries",
        all_industries,
        default=all_industries
    )

    st.divider()
    st.markdown("**About this project**")
    st.write(
        "A portfolio analysis using public Statistics Canada data "
        "to compare AI adoption across industries and explore "
        "which AI technologies are being used."
    )
    st.caption(
        "Figures describe the source dataset and should not be "
        "interpreted as causal evidence."
    )

filtered = industry_df[
    industry_df[industry_col].isin(selected_industries)
].copy()

if filtered.empty:
    filtered = industry_df.copy()

# KPI calculations
avg_adoption = industry_df[adoption_col].mean()
top_idx = industry_df[adoption_col].idxmax()
top_industry = str(industry_df.loc[top_idx, industry_col])
top_value = float(industry_df.loc[top_idx, adoption_col])
min_value = float(industry_df[adoption_col].min())
spread = top_value - min_value

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "Industries analysed",
    f"{industry_df[industry_col].nunique():,}"
)
m2.metric("Average AI adoption", f"{avg_adoption:.1f}%")
m3.metric("Highest adoption", f"{top_value:.1f}%")
m4.metric("Range across industries", f"{spread:.1f} pp")

# Four dashboard tabs
tab_overview, tab_tech, tab_data, tab_chat = st.tabs([
    "Overview",
    "Technology mix",
    "Explore data",
    "Ask the data"
])

# OVERVIEW
with tab_overview:
    left, right = st.columns([1.65, 1])

    with left:
        chart_df = filtered.sort_values(
            adoption_col, ascending=True
        )

        fig = px.bar(
            chart_df,
            x=adoption_col,
            y=industry_col,
            orientation="h",
            title="Planned AI adoption by industry",
            text=adoption_col,
            color=adoption_col,
            color_continuous_scale="Blues",
            labels={
                adoption_col: "Businesses planning to use AI (%)",
                industry_col: "Industry"
            }
        )

        fig.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside",
            cliponaxis=False
        )

        fig.update_layout(
            height=max(480, 30 * len(chart_df)),
            coloraxis_showscale=False,
            margin=dict(l=8, r=55, t=60, b=30),
            yaxis_title=None,
            xaxis=dict(
                range=[
                    0,
                    max(60, float(chart_df[adoption_col].max()) * 1.18)
                ],
                ticksuffix="%"
            )
        )

        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Key findings")

        st.markdown(
            f'<div class="insight"><b>Leading industry</b><br>'
            f'{top_industry}: {top_value:.1f}% planned AI adoption.</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            f'<div class="insight"><b>Industry average</b><br>'
            f'{avg_adoption:.1f}% across '
            f'{industry_df[industry_col].nunique()} industries.</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            f'<div class="insight"><b>Variation</b><br>'
            f'The gap between the highest and lowest industries '
            f'is {spread:.1f} percentage points.</div>',
            unsafe_allow_html=True
        )

        st.subheader("Top 5 industries")

        top5 = industry_df.nlargest(
            5, adoption_col
        )[[industry_col, adoption_col]].copy()

        top5 = top5.sort_values(
            adoption_col, ascending=False
        )

        top5.columns = ["Industry", "AI adoption (%)"]

        top5["AI adoption (%)"] = top5[
            "AI adoption (%)"
        ].map(lambda x: f"{x:.1f}%")

        st.dataframe(
            top5,
            hide_index=True,
            use_container_width=True
        )

# TECHNOLOGY MIX
with tab_tech:
    st.subheader("AI technology mix")

    if not tech_columns:
        st.warning(
            "Technology columns were not detected in the selected CSV."
        )
    else:
        tech_labels = list(tech_columns.keys())

        chosen_tech = st.multiselect(
            "Technologies to compare",
            tech_labels,
            default=tech_labels[:min(5, len(tech_labels))]
        )

        if chosen_tech:
            tech_df = filtered[
                [industry_col] +
                [tech_columns[t] for t in chosen_tech]
            ].copy()

            tech_df = tech_df.rename(
                columns={
                    tech_columns[t]: t for t in chosen_tech
                }
            )

            long_df = tech_df.melt(
                id_vars=industry_col,
                var_name="Technology",
                value_name="Rate (%)"
            ).dropna(subset=["Rate (%)"])

            fig2 = px.bar(
                long_df,
                x="Technology",
                y="Rate (%)",
                color="Technology",
                barmode="group",
                hover_data=[industry_col],
                title="Reported technology rates by industry"
            )

            fig2.update_layout(
                height=470,
                xaxis_title=None,
                yaxis_ticksuffix="%",
                legend_title=None
            )

            st.plotly_chart(fig2, use_container_width=True)

        summary_rows = []

        for label, col in tech_columns.items():
            values = pd.to_numeric(
                industry_df[col], errors="coerce"
            ).dropna()

            if not values.empty:
                best_idx = values.idxmax()

                summary_rows.append({
                    "Technology": label,
                    "Average rate (%)": round(values.mean(), 1),
                    "Highest industry": str(
                        industry_df.loc[best_idx, industry_col]
                    ),
                    "Highest rate (%)": round(float(values.max()), 1)
                })

        if summary_rows:
            st.subheader("Technology summary")

            summary = pd.DataFrame(summary_rows).sort_values(
                "Average rate (%)", ascending=False
            )

            st.dataframe(
                summary,
                hide_index=True,
                use_container_width=True
            )

# EXPLORE DATA
with tab_data:
    st.subheader("Explore the dataset")

    st.caption(
        f"Showing {len(filtered)} rows after applying the industry filter."
    )

    display_df = filtered.copy()

    display_df = display_df.rename(
        columns={
            industry_col: "Industry",
            adoption_col: "AI adoption (%)"
        }
    )

    st.dataframe(
        display_df,
        hide_index=True,
        use_container_width=True
    )

    csv_bytes = display_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download filtered data (CSV)",
        csv_bytes,
        "canada_ai_adoption_filtered.csv",
        "text/csv"
    )

# DATASET QUESTION ANSWERING
def answer_question(question):
    q = question.lower().strip()
    d = industry_df.copy()

    if any(word in q for word in [
        "top", "highest", "leader", "most adoption", "leading"
    ]):
        match = re.search(r"\btop\s+(\d+)", q)
        n = min(int(match.group(1)), 10) if match else 5

        top = d.nlargest(
            n, adoption_col
        )[[industry_col, adoption_col]].sort_values(
            adoption_col, ascending=False
        )

        return "Here are the leading industries:\n\n" + "\n".join(
            f"{i+1}. **{row[industry_col]}** — "
            f"{row[adoption_col]:.1f}%"
            for i, (_, row) in enumerate(top.iterrows())
        )

    if any(word in q for word in ["lowest", "least", "bottom"]):
        bottom = d.nsmallest(5, adoption_col)

        return "The five lowest industries are:\n\n" + "\n".join(
            f"- **{row[industry_col]}** — "
            f"{row[adoption_col]:.1f}%"
            for _, row in bottom.iterrows()
        )

    if any(word in q for word in ["average", "mean", "overall"]):
        return (
            f"The average AI adoption rate across "
            f"{d[industry_col].nunique()} industries is "
            f"**{d[adoption_col].mean():.1f}%**."
        )

    if any(word in q for word in [
        "range", "gap", "difference", "spread", "variation"
    ]):
        return (
            f"The gap between the highest and lowest industries "
            f"is **{d[adoption_col].max()-d[adoption_col].min():.1f} "
            f"percentage points**."
        )

    if any(word in q for word in [
        "technology", "technologies", "chatbot", "llm",
        "analytics", "machine learning", "speech"
    ]):
        if not tech_columns:
            return "Technology data is not available in this CSV."

        means = []

        for label, col in tech_columns.items():
            vals = pd.to_numeric(d[col], errors="coerce").dropna()

            if not vals.empty:
                means.append((label, vals.mean()))

        means.sort(key=lambda x: x[1], reverse=True)

        return "Average rates by technology:\n\n" + "\n".join(
            f"- **{label}**: {value:.1f}%"
            for label, value in means
        )

    match = next(
        (
            name for name in d[industry_col].astype(str).tolist()
            if name.lower() in q
        ),
        None
    )

    if match:
        row = d[d[industry_col].astype(str) == match].iloc[0]

        return (
            f"**{match}** has a reported AI adoption rate of "
            f"**{float(row[adoption_col]):.1f}%**."
        )

    return (
        "Try asking: Which industries have the highest AI adoption? "
        "What is the average adoption rate? Which industry has the "
        "lowest rate? Which technology has the highest average rate?"
    )

# ASK THE DATA
with tab_chat:
    st.subheader("Ask the data")

    st.write(
        "Explore the dataset in plain English. Ask about leading "
        "industries, average adoption, gaps, or technology patterns."
    )

    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": (
                "Hi! I'm your Canada AI Adoption data assistant. "
                "Ask me about AI adoption across Canadian industries."
            )
        }]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input(
        "Ask a question about Canada's AI adoption data..."
    )

    if prompt:
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        response = answer_question(prompt)

        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })

        st.rerun()

    c1, c2, c3 = st.columns(3)

    if c1.button("Show top industries", use_container_width=True):
        st.session_state.messages.append({
            "role": "user",
            "content": "Which industries have the highest AI adoption?"
        })
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer_question(
                "Which industries have the highest AI adoption?"
            )
        })
        st.rerun()

    if c2.button("Find the average", use_container_width=True):
        st.session_state.messages.append({
            "role": "user",
            "content": "What is the average AI adoption rate?"
        })
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer_question(
                "What is the average AI adoption rate?"
            )
        })
        st.rerun()

    if c3.button("Explore technology", use_container_width=True):
        st.session_state.messages.append({
            "role": "user",
            "content": "Which technology has the highest average rate?"
        })
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer_question(
                "Which technology has the highest average rate?"
            )
        })
        st.rerun()

st.divider()

st.caption(
    "Source: Statistics Canada, table 33-10-1207-01. "
    "This portfolio dashboard provides descriptive analysis "
    "of the local dataset."
)


