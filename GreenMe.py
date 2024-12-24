import streamlit as st
import requests
from langchain.llms import Cohere
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client

# Supabase Configuration
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch API keys from Streamlit secrets
CARBON_API_KEY = st.secrets["CARBON_API_KEY"]
COHERE_API_KEY = st.secrets["COHERE_API_KEY"]
# Initialize the Cohere LLM
try:
    llm = Cohere(cohere_api_key=COHERE_API_KEY)
except Exception as e:
    st.error(f"Failed to initialize Cohere LLM: {e}")
    st.stop()

# LangChain Prompt Template
prompt_template = PromptTemplate(
    input_variables=[
        "nickname", "region", "family_size", "energy_emissions",
        "renewable_ratio", "water_consumption", "commute_emissions",
        "weekly_travel", "transport_mode", "weekly_waste", "recycle_types"
    ],
    template="""
    Generate a detailed sustainability lifestyle report for {nickname}, who resides in {region} with a household of {family_size} members. 
    Their current lifestyle details are:
    - Energy usage contributing to {energy_emissions} kg of CO2 emissions monthly, with {renewable_ratio}% from renewables.
    - Water usage of {water_consumption} liters monthly.
    - Weekly travel of {weekly_travel} km using {transport_mode}, contributing to {commute_emissions} kg of CO2 emissions.
    - Waste generation of {weekly_waste} kg weekly, with recycling of {recycle_types}.

    Provide recommendations to improve their sustainability practices and reduce carbon footprint.
    """
)

# Function to track API usage
def track_api_usage():
    try:
        result = supabase.table("api_usage").select("*").execute()
        # Check if the response contains `data` and if it's valid
        if result.data is None:
            st.error("Failed to fetch API usage data.")
            return 0

        # Fetch today's usage count
        today = datetime.utcnow().date()
        today_usage = [record for record in result.data if record["date"] == str(today)]
        return today_usage[0]["count"] if today_usage else 0
    except Exception as e:
        st.error(f"Error reading API usage data: {e}")
        return 0

def increment_api_usage():
    try:
        today = datetime.utcnow().date()
        result = supabase.table("api_usage").select("*").eq("date", str(today)).execute()

        if result.data:  # Check if data exists
            record_id = result.data[0]["id"]
            new_count = result.data[0]["count"] + 1
            supabase.table("api_usage").update({"count": new_count}).eq("id", record_id).execute()
        else:  # If no record exists for today
            supabase.table("api_usage").insert({"date": str(today), "count": 1}).execute()
    except Exception as e:
        st.error(f"Error updating API usage data: {e}")


# Fallback static formula
def static_emissions_formula(usage_kwh):
    return usage_kwh * 0.5  # Simple factor: 0.5 kg CO2 per kWh

# Electricity emissions calculation
def calculate_emissions(usage_kwh: float, country_code: str = "US"):
    api_usage = track_api_usage()
    if api_usage >= 3:  # Limit API usage to 3 calls per day
        st.warning("API limit reached! Using static calculation.")
        return static_emissions_formula(usage_kwh)

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
        increment_api_usage()  # Increment API usage after a successful call
        result = response.json()
        return result["data"]["attributes"]["carbon_mt"] * 1000  # Convert metric tons to kg
    except Exception as e:
        st.error(f"Error fetching emissions data: {e}")
        return static_emissions_formula(usage_kwh)

# Streamlit App
st.set_page_config(page_title="GreenMe", layout="wide")
st.title("🌍 GreenMe - Reduce Your Carbon Footprint")
st.markdown("""
    Welcome to **GreenMe**, your personal eco-assistant.  
    Our goal is to help you understand and **reduce your carbon footprint** while making sustainable choices for a greener future. 🌱  
""")

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

if st.sidebar.button("Generate Tips"):
    energy_emissions = calculate_emissions(energy_usage)
    commute_emissions = commute_distance * 0.12  # Emissions based on distance

    st.subheader("Carbon Footprint Breakdown")
    df = pd.DataFrame({
        "Category": ["Energy", "Commute"],
        "CO2 Emissions (kg)": [energy_emissions, commute_emissions]
    })
    st.bar_chart(df.set_index("Category"))

    llm_chain = LLMChain(llm=llm, prompt=prompt_template)
    inputs = {
        "nickname": nickname,
        "region": region,
        "family_size": family_size,
        "energy_emissions": energy_emissions,
        "renewable_ratio": renewable_ratio,
        "water_consumption": water_consumption,
        "commute_emissions": commute_emissions,  # Pass emissions
        "transport_mode": transport_mode,
        "weekly_travel": commute_distance,  # Pass distance
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
