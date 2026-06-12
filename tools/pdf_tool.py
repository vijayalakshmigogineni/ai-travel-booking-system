from fpdf import FPDF
import io


def generate_itinerary_pdf(query: str, final_response: str, flight_results: str, hotel_results: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "AI Travel Itinerary", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Your Request", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, query.encode("latin-1", "replace").decode("latin-1"))
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Itinerary & Plan", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, final_response.encode("latin-1", "replace").decode("latin-1"))
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Flight Results", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, (flight_results or "No data").encode("latin-1", "replace").decode("latin-1"))
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Hotel Results", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, (hotel_results or "No data").encode("latin-1", "replace").decode("latin-1"))

    return bytes(pdf.output())