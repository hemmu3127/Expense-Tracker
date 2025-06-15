# src/export_manager.py
import pandas as pd
from io import BytesIO
from fpdf import FPDF
from datetime import datetime

class ExportManager:
    """Handles exporting data to various formats like CSV, Excel, and PDF."""

    def export_to_csv(self, df: pd.DataFrame) -> bytes:
        """Exports a DataFrame to a CSV file in memory. No changes needed."""
        return df.to_csv(index=False).encode('utf-8')

    def export_to_excel(self, df: pd.DataFrame) -> BytesIO:
        """Exports a DataFrame to an Excel file in memory. No changes needed."""
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Expenses')
        return output

    # --- MODIFIED FUNCTION ---
    def export_to_pdf(self, df: pd.DataFrame, user: dict, wallet_balances: dict) -> bytes:
        """Creates a formatted PDF expense report including a wallet summary."""
        pdf = FPDF()
        pdf.add_page()

        # Header
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Expense Report', 0, 1, 'C')
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f"User: {user['username']}", 0, 1, 'C')
        pdf.cell(0, 10, f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1, 'C')
        pdf.ln(5)

        # Transaction Summary
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Transaction Summary', 0, 1, 'L')
        total_expenses = df['amount'].sum()
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 8, f"Total Expenses: ${total_expenses:,.2f}", 0, 1)
        pdf.cell(0, 8, f"Total Transactions: {len(df)}", 0, 1)
        pdf.ln(5)

        # --- NEW: WALLET SUMMARY SECTION ---
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Current Wallet Balances', 0, 1, 'L')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 8, f"UPI Balance: ${wallet_balances.get('upi_balance', 0):,.2f}", 0, 1)
        pdf.cell(0, 8, f"Cash Balance: ${wallet_balances.get('cash_balance', 0):,.2f}", 0, 1)
        pdf.ln(10)

        # Table Header
        pdf.set_font('Arial', 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        # Added payment method, adjusted widths
        col_widths = [25, 30, 65, 25, 25] 
        headers = ['Date', 'Category', 'Title', 'Amount', 'Method']
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, 1, 0, 'C', 1)
        pdf.ln()

        # Table Rows
        pdf.set_font('Arial', '', 9)
        for _, row in df.iterrows():
            pdf.cell(col_widths[0], 10, row['date'].strftime('%Y-%m-%d'), 1)
            pdf.cell(col_widths[1], 10, str(row['category']), 1)
            
            x_before, y_before = pdf.get_x(), pdf.get_y()
            pdf.multi_cell(col_widths[2], 10, str(row['title']), 1, 'L')
            pdf.set_xy(x_before + col_widths[2], y_before) # Reset position
            
            pdf.cell(col_widths[3], 10, f"${row['amount']:,.2f}", 1, 0, 'R')
            pdf.cell(col_widths[4], 10, str(row.get('payment_method', 'N/A')), 1, 0, 'C')
            pdf.ln()

        return bytes(pdf.output())