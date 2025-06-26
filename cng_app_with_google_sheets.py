
import streamlit as st
from datetime import datetime
from sklearn.linear_model import LinearRegression
import numpy as np
from fpdf import FPDF
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Setup Google Sheets
def log_to_google_sheets(row_data):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("macro-polymer-464102-u0-51f88b284c8d.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("CNG Maintenance Logs").worksheet("Logs")
    sheet.append_row(row_data)

st.title("🚗 AI-Powered CNG Maintenance & Safety Reminder with Google Sheets Logging")

# --- Session state initialization ---
if 'maintenance_result' not in st.session_state:
    st.session_state.maintenance_result = ""
if 'predicted_next_km' not in st.session_state:
    st.session_state.predicted_next_km = None
if 'risk_result' not in st.session_state:
    st.session_state.risk_result = ""

# --- Maintenance Section ---
st.header("🔧 Maintenance Reminder")

vehicle_name = st.text_input("Vehicle Name or Plate Number")
last_service_km = st.number_input("Last Service Odometer Reading (in KM)", min_value=0)
current_km = st.number_input("Current Odometer Reading (in KM)", min_value=0)
service_interval = st.number_input("Service Interval (in KM)", min_value=1000, value=5000)
last_service_date = st.date_input("Last Service Date")
today = datetime.today().date()
days_since_service = (today - last_service_date).days

if st.button("Check Maintenance Status"):
    km_due = current_km - last_service_km
    km_left = service_interval - km_due

    if km_due >= service_interval:
        st.session_state.maintenance_result = "Service is DUE! Please service your CNG kit."
        st.warning(st.session_state.maintenance_result)
    else:
        st.session_state.maintenance_result = f"Not yet due. You have {km_left} km remaining."
        st.success(st.session_state.maintenance_result)

    st.info(f"Days since last service: {days_since_service} days")

    st.subheader("AI Prediction: Next Service Mileage")

    past_km_inputs = np.array([[0], [5000], [10000], [15000]])
    expected_next_km = np.array([5000, 10000, 15000, 20000])
    model = LinearRegression()
    model.fit(past_km_inputs, expected_next_km)
    st.session_state.predicted_next_km = model.predict([[current_km]])[0]
    st.info(f"Predicted next service: {int(st.session_state.predicted_next_km)} KM")

# --- Safety Risk Assessment Section ---
st.header("CNG Leak / Safety Risk Assessment")

hissing = st.radio("Do you hear a hissing sound near or around the CNG system?", ["No", "Yes"])
smell_rating = st.slider("Rate the smell of gas inside the cabin (0 = None, 5 = Strong)", 0, 5)
check_engine = st.radio("Is the Check Engine Light ON?", ["No", "Yes"])
mileage_drop = st.radio("Has your gas mileage dropped recently?", ["No", "Yes"])
backfiring = st.radio("Has the vehicle backfired recently?", ["No", "Yes"])

if st.button("Assess Safety Risk"):
    risk_score = 0
    if hissing == "Yes": risk_score += 2
    if smell_rating >= 3: risk_score += 2
    if check_engine == "Yes": risk_score += 1
    if mileage_drop == "Yes": risk_score += 1
    if backfiring == "Yes": risk_score += 1

    if risk_score >= 5:
        st.session_state.risk_result = "High Risk – Inspect your CNG system immediately!"
        st.error(st.session_state.risk_result)
    elif risk_score >= 3:
        st.session_state.risk_result = "Moderate Risk – Monitor and consider inspection."
        st.warning(st.session_state.risk_result)
    else:
        st.session_state.risk_result = "Low Risk – No immediate issue detected."
        st.success(st.session_state.risk_result)

# --- PDF Creation ---
def safe_text(text):
    return text.encode("latin1", "ignore").decode("latin1")

def create_pdf(vehicle_name, maintenance_result, predicted_next_km, risk_result):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, safe_text("CNG Maintenance & Safety Report"), ln=True, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, safe_text(f"Vehicle: {vehicle_name}"), ln=True)
    pdf.cell(200, 10, safe_text(f"Date: {datetime.today().strftime('%Y-%m-%d')}"), ln=True)
    pdf.cell(200, 10, safe_text(f"Maintenance Status: {maintenance_result}"), ln=True)
    if predicted_next_km:
        pdf.cell(200, 10, safe_text(f"Predicted Next Service: {int(predicted_next_km)} KM"), ln=True)
    pdf.cell(200, 10, safe_text(f"Safety Risk Assessment: {risk_result}"), ln=True)

    return pdf.output(dest='S').encode('latin1')

# --- PDF Download + Google Sheets Logging ---
if st.button("📄 Download Report as PDF"):
    if vehicle_name and st.session_state.maintenance_result and st.session_state.risk_result:
        pdf_bytes = create_pdf(vehicle_name, st.session_state.maintenance_result, st.session_state.predicted_next_km, st.session_state.risk_result)

        row = [
            datetime.today().strftime("%Y-%m-%d %H:%M:%S"), vehicle_name, last_service_km, current_km,
            service_interval, days_since_service, st.session_state.maintenance_result,
            int(st.session_state.predicted_next_km) if st.session_state.predicted_next_km else "",
            hissing, smell_rating, check_engine, mileage_drop, backfiring, st.session_state.risk_result
        ]
        log_to_google_sheets(row)

        b64 = base64.b64encode(pdf_bytes).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="CNG_Report.pdf">📥 Click here to download your report</a>'
        st.markdown(href, unsafe_allow_html=True)
    else:
        st.error("Please complete both the maintenance and safety check first.")
