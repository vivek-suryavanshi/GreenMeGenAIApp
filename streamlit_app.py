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

# Define a LangChain prompt template for sustainability recommendations
prompt_template = PromptTemplate(
    input_variables=[
        "name", "location", "household_size", "electricity_emissions",
        "renewable_usage", "water_usage", "travel_emissions", "vehicle_type",
        "waste_generated", "recycling_habits"
    ],
    template="""
    Generate sustainability recommendations for a user named {name}, living in {location}, with a household size of {household_size}. 
    Their electricity usage results in {electricity_emissions} kg of CO2 emissions per month, and {renewable_usage}% of their energy is from renewable sources.
    They consume {water_usage} liters of water monthly. Their travel contributes {travel_emissions} kg of CO2 emissions monthly using a {vehicle_type}.
    They generate {waste_generated} kg of waste weekly and recycle materials such as {recycling_habits}.

    Provide actionable insights to improve sustainability across energy usage, water conservation, transportation, and waste management.
    """
)

# Function to calculate electricity emissions using the Carbon Interface API
def calculate_electricity_emissions(electricity_usage_kwh: float):
    try:
        url = "https://www.carboninterface.com/api/v1/estimates"
        headers = {
            "Authorization": f"Bearer {CARBON_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "type": "electricity",
            "electricity_unit": "kwh",
            "electricity_value": electricity_usage_kwh,
            "country": "US"  # Change to the user's country
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["data"]["attributes"]["carbon_mt"] * 1000  # Convert metric tons to kilograms
    except Exception as e:
        st.error(f"Error fetching electricity emissions: {e}")
        return 0.0

# Set up Streamlit app
st.set_page_config(page_title="Sustainability Insights with AI", layout="wide")
st.title("🌱 Sustainability Insights")

# Sidebar for user inputs
st.sidebar.header("Enter Your Details")
name = st.sidebar.text_input("Name")
location = st.sidebar.text_input("Location")
household_size = st.sidebar.number_input("Household Size", min_value=1, step=1)

st.sidebar.subheader("Energy Consumption")
electricity_usage = st.sidebar.number_input("Monthly Electricity Usage (kWh)", min_value=0.0, step=0.1)
renewable_usage = st.sidebar.slider("Percentage from Renewable Energy", 0, 100)

st.sidebar.subheader("Water Consumption")
water_usage = st.sidebar.number_input("Monthly Water Consumption (liters)", min_value=0.0, step=0.1)

st.sidebar.subheader("Transportation")
travel_kms = st.sidebar.number_input("Average Weekly Travel (km)", min_value=0.0, step=0.1)
vehicle_type = st.sidebar.selectbox("Vehicle Type", ["Petrol", "Diesel", "Electric", "Hybrid", "Public Transport"])

st.sidebar.subheader("Waste Management")
waste_generated = st.sidebar.number_input("Weekly Waste Generated (kg)", min_value=0.0, step=0.1)
recycling_habits = st.sidebar.multiselect("Materials You Recycle", ["Plastic", "Glass", "Paper", "Metal", "Other"])

# Main area for insights
st.header("Your Sustainability Insights")

if st.sidebar.button("Generate Insights"):
    # Calculate emissions
    electricity_emissions = calculate_electricity_emissions(electricity_usage)
    travel_emissions = travel_kms * 0.12  # Example calculation: 0.12 kg CO2 per km

    # Display results in a chart
    st.subheader("Carbon Footprint Breakdown")
    data = {
        "Category": ["Electricity", "Travel"],
        "CO2 Emissions (kg)": [electricity_emissions, travel_emissions]
    }
    df = pd.DataFrame(data)
    st.bar_chart(df.set_index("Category"))

    # Build the chain using LangChain
    llm_chain = LLMChain(llm=llm, prompt=prompt_template)

    # Collect all inputs for the prompt
    inputs = {
        "name": name,
        "location": location,
        "household_size": household_size,
        "electricity_emissions": electricity_emissions,
        "renewable_usage": renewable_usage,
        "water_usage": water_usage,
        "travel_emissions": travel_emissions,
        "vehicle_type": vehicle_type,
        "waste_generated": waste_generated,
        "recycling_habits": ", ".join(recycling_habits) if recycling_habits else "none"
    }

    # Generate recommendations
    try:
        recommendations = llm_chain.run(inputs)
        st.subheader("Recommendations")
        st.write(recommendations)
    except Exception as e:
        st.error(f"Error generating insights: {e}")

else:
    st.info("Enter your details in the sidebar and click 'Generate Insights' to get started!")
