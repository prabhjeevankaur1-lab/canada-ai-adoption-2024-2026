
import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="Canada AI Adoption Assistant",
    page_icon="🇨🇦",
    layout="wide",
)

st.title("🇨🇦 Canada AI Adoption Assistant")
st.write(
    "Ask questions about AI adoption and AI technologies "
    "across Canadian industries using the dataset."
)

# Change this path if your CSV has a different filename.
CSV_PATH = Path("data/ai_adoption.csv")

# Load the actual dataset.
@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    df["industry"] = df["industry"].astype(str).str.strip()
    return df

try:
    df = load_data(CSV_PATH)
except FileNotFoundError:
    st.error(
        f"Could not find {CSV_PATH}. Check the exact CSV filename "
        "and make sure it is inside the data folder."
    )
    st.stop()

# Match common phrases to CSV columns.
METRICS = {
    "ai_adoption": ["ai adoption", "adoption of ai", "using ai", "overall ai"],
    "machine_learning": ["machine learning"],
    "nlp": ["natural language processing", "nlp"],
    "chatbots": ["chatbots", "chatbot"],
    "speech_ai": ["speech ai", "speech recognition"],
    "recommendation_ai": ["recommendation ai", "recommendation systems"],
    "llm": ["large language models", "large language model", "llm", "llms"],
    "text_analytics": ["text analytics"],
    "data_analytics": ["data analytics"],
    "neural_network": ["neural networks", "neural network"],
    "augmented_reality": ["augmented reality"],
    "ai_decision_making": ["ai decision making", "decision-making ai"],
    "deep_learning": ["deep learning"],
    "image_recognition": ["image recognition"],
    "computer_vision": ["computer vision"],
    "rpa": ["robotic process automation", "rpa"],
    "biometrics": ["biometrics", "biometric ai"],
    "marketing_ai": ["marketing ai", "ai marketing"],
    "other_ai": ["other ai"],
    "no_ai": ["no ai", "not using ai"],
    "unknown": ["unknown"],
}

LABELS = {
    "ai_adoption": "AI adoption",
    "machine_learning": "Machine learning",
    "nlp": "Natural language processing",
    "chatbots": "Chatbots",
    "speech_ai": "Speech AI",
    "recommendation_ai": "Recommendation AI",
    "llm": "Large language models",
    "text_analytics": "Text analytics",
    "data_analytics": "Data analytics",
    "neural_network": "Neural networks",
    "augmented_reality": "Augmented reality",
    "ai_decision_making": "AI decision-making",
    "deep_learning": "Deep learning",
    "image_recognition": "Image recognition",
    "computer_vision": "Computer vision",
    "rpa": "Robotic process automation",
    "biometrics": "Biometrics",
    "marketing_ai": "Marketing AI",
    "other_ai": "Other AI",
    "no_ai": "No AI",
    "unknown": "Unknown",
}

# Put longer phrases first to improve matching.
def find_metric(question):
    q = question.lower()
    matches = []

    for column, phrases in METRICS.items():
        for phrase in phrases:
            if phrase in q:
                matches.append((len(phrase), column))
                break

    if matches:
        return max(matches)[1]

    return "ai_adoption"


def find_industry(question):
    q = question.lower()

    # Match the longest industry name first.
    industries = sorted(
        df["industry"].tolist(),
        key=len,
        reverse=True,
    )

    for industry in industries:
        if industry.lower() in q:
            return industry

    # Recognize a few common shortened names.
    aliases = {
        "professional services":
            "Professional, scientific and technical services",
        "information":
            "Information and cultural industries",
        "transportation":
            "Transportation and warehousing",
        "healthcare":
            "Health care and social assistance",
        "health care":
            "Health care and social assistance",
        "agriculture":
            "Agriculture, forestry, fishing and hunting",
        "accommodation":
            "Accommodation and food services",
    }

    for phrase, industry in aliases.items():
        if phrase in q:
            return industry

    return None


# Identify the overall-industry benchmark row.
benchmark_mask = df["industry"].str.contains(
    "all industries",
    case=False,
    na=False,
)

if benchmark_mask.any():
    benchmark = df.loc[benchmark_mask].iloc[0]
else:
    benchmark = None

industries = df.loc[~benchmark_mask].copy()


def answer_question(question):
    q = question.lower()
    metric = find_metric(question)
    label = LABELS.get(metric, metric.replace("_", " ").title())
    value = pd.to_numeric(df[metric], errors="coerce")
    data = df.assign(_value=value).dropna(subset=["_value"])

    if data.empty:
        return "There are no usable values for that measure."

    # Answer questions about a specific industry.
    industry = find_industry(question)

    if industry:
        row = df[df["industry"].str.lower() == industry.lower()]

        if row.empty:
            return f"I couldn't find {industry} in the dataset."

        result = float(row.iloc[0][metric])
        return f"**{label} in {industry}: {result:.1f}%**"

    # Exclude the overall benchmark when ranking individual industries.
    ranked = data[
        ~data["industry"].str.contains(
            "all industries", case=False, na=False
        )
    ].sort_values("_value", ascending=False)

    if any(word in q for word in ["highest", "most", "top", "largest"]):
        top = ranked.head(5)[["industry", "_value"]].copy()
        top.columns = ["Industry", "Percentage"]
        st.dataframe(top, hide_index=True, use_container_width=True)
        st.bar_chart(top.set_index("Industry"))
        return f"Here are the five highest industries for {label.lower()}."

    if any(word in q for word in ["lowest", "least", "smallest"]):
        bottom = ranked.tail(5).sort_values("_value")[
            ["industry", "_value"]
        ].copy()
        bottom.columns = ["Industry", "Percentage"]
        st.dataframe(bottom, hide_index=True, use_container_width=True)
        st.bar_chart(bottom.set_index("Industry"))
        return f"Here are the five lowest industries for {label.lower()}."

    if any(word in q for word in ["compare", "comparison", "all industries", "across industries", "chart", "graph", "table"]):
        table = ranked[["industry", "_value"]].copy()
        table.columns = ["Industry", "Percentage"]
        st.dataframe(table, hide_index=True, use_container_width=True)
        st.bar_chart(table.set_index("Industry"))
        return f"Here is the industry comparison for {label.lower()}."

    # Overall benchmark questions.
    if benchmark is not None and any(
        phrase in q
        for phrase in ["overall", "national", "all businesses", "all industries", "average"]
    ):
        result = float(benchmark[metric])
        return f"**Overall {label.lower()}: {result:.1f}%** according to the dataset."

    # General summary for the selected measure.
    average = ranked["_value"].mean()
    highest = ranked.loc[ranked["_value"].idxmax()]
    lowest = ranked.loc[ranked["_value"].idxmin()]

    return (
        f"**{label} — dataset summary**\n\n"
        f"- Average across listed industries: {average:.1f}%\n"
        f"- Highest: {highest['industry']} ({highest['_value']:.1f}%)\n"
        f"- Lowest: {lowest['industry']} ({lowest['_value']:.1f}%)\n\n"
        "Try asking for a specific industry, the highest or lowest value, "
        "or a comparison chart."
    )


# Chat history.
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input("Ask a question about Canadian AI adoption...")

if question:
    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        response = answer_question(question)
        st.markdown(response)

    st.session_state.messages.append(
        {"role": "assistant", "content": response}
    )

st.divider()
st.caption(
    "Portfolio project | Answers are calculated from the supplied CSV dataset."
)
source venv/bin/activate

python -m streamlit run app.py
