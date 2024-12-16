import streamlit as st
import requests
from langchain.llms import Cohere
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd

# Fetch API keys from Streamlit secrets
CARBON_API_KEY = st.secrets["CARBON_API_KEY"]
COHERE_API_KEY = st.secrets["COHERE_API_KEY"]

# Initialize the Cohere LLM
try:
    llm = Cohere(cohere_api_key=COHERE_API_KEY)
except Exception as e:
    st.error(f"Failed to initialize Cohere LLM: {e}")
    st.stop()

# Define a LangChain prompt template for eco insights
prompt_template = PromptTemplate(
    input_variables=[
        "nickname", "region", "family_size", "energy_emissions",
        "renewable_ratio", "water_consumption", "commute_emissions", "transport_mode",
        "weekly_waste", "recycle_types"
    ],
    template="""
    Generate a detailed sustainability lifestyle report for {nickname}, who resides in {region} with a household of {family_size} members. 
    Their current lifestyle details are:
    - Energy usage contributing to {energy_emissions} kg of CO2 emissions monthly, with {renewable_ratio}% from renewables.
    - Water usage of {water_consumption} liters monthly.
    - Weekly travel of {commute_emissions} km using {transport_mode}, contributing to travel emissions.
    - Waste generation of {weekly_waste} kg weekly, with recycling of {recycle_types}.

    **Provide recommendations to improve their sustainability practices and reduce carbon footprint across:**

    1. **Energy**:
        - Suggest innovative methods to reduce energy emissions and reliance on non-renewables.
    2. **Water**:
        - Provide tips for conserving water and reducing wasteful consumption.
    3. **Transportation**:
        - Highlight actionable strategies to minimize travel emissions considering {transport_mode} and {commute_emissions}.
    4. **Waste Management**:
        - Recommend ways to reduce {weekly_waste} kg of waste and improve recycling of {recycle_types}.

    Ensure that all suggestions are:
    - Context-specific to {nickname}'s household size, region, and current practices.
    - Measurable with clear outcomes (e.g., CO2 savings, cost reductions, or water saved).
    - Balanced in environmental impact and practicality.
    """
)


# Function to calculate electricity emissions
def calculate_emissions(usage_kwh: float, country_code: str = "US"):
    try:
        url = "https://www.carboninterface.com/api/v1/estimates"
        headers = {
            "Authorization": f"Bearer {CARBON_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "type": "electricity",
            "electricity_unit": "kwh",
            "electricity_value": usage_kwh,
            "country": country_code
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["data"]["attributes"]["carbon_mt"] * 1000  # Convert metric tons to kg
    except Exception as e:
        st.error(f"Error fetching emissions data: {e}")
        return 0.0

# Set up Streamlit app
st.set_page_config(page_title="GreenMe", layout="wide")
st.title("🌍 GreenMe - Reduce Your Carbon Footprint")

st.markdown("""
    Welcome to **GreenMe**, your personal eco-assistant.  
    Our goal is to help you understand and **reduce your carbon footprint** while making sustainable choices for a greener future. 🌱  
""")

# Sidebar for user inputs
st.sidebar.header("Enter Your Details")
nickname = st.sidebar.text_input("Nickname")
region = st.sidebar.text_input("Region")
family_size = st.sidebar.number_input("Family Size", min_value=1, step=1)

st.sidebar.subheader("Energy Details")
energy_usage = st.sidebar.number_input("Monthly Energy Use (kWh)", min_value=0.0, step=0.1)
renewable_ratio = st.sidebar.slider("Renewable Energy Usage (%)", 0, 100)

st.sidebar.subheader("Water Usage")
water_consumption = st.sidebar.number_input("Monthly Water Use (liters)", min_value=0.0, step=0.1)

st.sidebar.subheader("Commute Info")
commute_distance = st.sidebar.number_input("Weekly Commute (km)", min_value=0.0, step=0.1)
transport_mode = st.sidebar.selectbox("Mode of Transport", ["Car", "Bike", "Bus", "Train", "Electric Vehicle"])

st.sidebar.subheader("Waste Details")
weekly_waste = st.sidebar.number_input("Weekly Waste (kg)", min_value=0.0, step=0.1)
recycle_types = st.sidebar.multiselect("Recycled Materials", ["Plastic", "Glass", "Paper", "E-waste", "Other"])

# Main area for insights
st.header("Your Eco Insights")

if st.sidebar.button("Generate Tips"):
    # Calculate emissions
    energy_emissions = calculate_emissions(energy_usage)
    commute_emissions = commute_distance * 0.12  # 0.12 kg CO2 per km

    # Display chart
    st.subheader("Carbon Footprint Breakdown")
    data = {
        "Category": ["Energy", "Commute"],
        "CO2 Emissions (kg)": [energy_emissions, commute_emissions]
    }
    df = pd.DataFrame(data)
    st.bar_chart(df.set_index("Category"))

    # LangChain for insights
    llm_chain = LLMChain(llm=llm, prompt=prompt_template)

    inputs = {
        "nickname": nickname,
        "region": region,
        "family_size": family_size,
        "energy_emissions": energy_emissions,
        "renewable_ratio": renewable_ratio,
        "water_consumption": water_consumption,
        "commute_emissions": commute_emissions,
        "transport_mode": transport_mode,
        "weekly_waste": weekly_waste,
        "recycle_types": ", ".join(recycle_types) if recycle_types else "none"
    }

    try:
        insights = llm_chain.run(inputs)
        st.subheader("Eco-Friendly Tips")
        st.write(insights)
    except Exception as e:
        st.error(f"Error generating tips: {e}")

else:
    st.info("Enter details in the sidebar and click 'Generate Tips'!")
