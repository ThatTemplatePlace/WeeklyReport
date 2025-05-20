import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os

# Secrets loaded from GitHub environment
GUMROAD_TOKEN = os.getenv("GUMROAD_TOKEN")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
TO_EMAIL = os.getenv("TO_EMAIL")

# Constants
FROM_EMAIL = "noreply@thattemplateplace.com"
REPLY_TO_EMAIL = "hello@thattemplateplace.com"

# Gumroad API URLs
GUMROAD_SALES_URL = "https://api.gumroad.com/v2/sales"
GUMROAD_PRODUCTS_URL = "https://api.gumroad.com/v2/products"


def fetch_sales(token, from_date_str, to_date_str):
    sales = []
    page_key = None

    from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
    to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()

    while True:
        params = {
            'access_token': token,
            'from': from_date_str,
            'to': to_date_str
        }
        if page_key:
            params['page_key'] = page_key

        response = requests.get(
            GUMROAD_SALES_URL,
            params=params
        )

        data = response.json()
        if 'sales' not in data:
            print(f"❌ Failed to fetch sales: {data}")
            return []

        # Filter out sales outside the strict 7-day window
        for sale in data['sales']:
            sale_date = datetime.strptime(sale['created_at'], '%Y-%m-%dT%H:%M:%SZ').date()
            if from_date <= sale_date <= to_date:
                # Normalize price by dividing by 100
                sale['price'] = float(sale['price']) / 100
                sales.append(sale)

        page_key = data.get('next_page_key')
        if not page_key:
            break

    print(f"🧾 Filtered {len(sales)} sales from {from_date_str} to {to_date_str}")
    return sales


def fetch_products():
    url = GUMROAD_PRODUCTS_URL
    params = {"access_token": GUMROAD_TOKEN}
    response = requests.get(url, params=params)
    return response.json().get("products", [])

def build_email_body(sales, products):
    product_names = {product['id']: product['name'] for product in products}

    sales_by_product = {}
    earnings_by_product = {}
    total_sales = 0
    total_earnings = 0

    for sale in sales:
        pid = sale["product_id"]
        price = float(sale["price"]) / 100  # Convert from cents to dollars
        sales_by_product[pid] = sales_by_product.get(pid, 0) + 1
        earnings_by_product[pid] = earnings_by_product.get(pid, 0) + price
        total_sales += 1
        total_earnings += price

    email_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        body {{
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          background-color: #f3f2f1;
          margin: 0;
          padding: 40px;
        }}
        .email-container {{
          max-width: 600px;
          margin: 0 auto;
          background-color: #ffffff;
          border-radius: 8px;
          box-shadow: 0 2px 6px rgba(0,0,0,0.05);
          overflow: hidden;
        }}
        .header {{
          background-color: #ffffff;
          text-align: center;
          padding: 24px;
          border-bottom: 1px solid #e0e0e0;
        }}
        .header img {{
          max-height: 60px;
        }}
        .content {{
          padding: 32px;
        }}
        .content h1 {{
          font-size: 20px;
          margin-bottom: 8px;
        }}
        .content p {{
          margin: 16px 0;
          line-height: 1.6;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
          margin-top: 20px;
          background: #fafafa;
          border-radius: 4px;
          overflow: hidden;
        }}
        thead {{
          background-color: #f3f2f1;
        }}
        th {{
          text-align: left;
          padding: 12px 16px;
          font-weight: 600;
          color: #333;
        }}
        td {{
          border-top: 1px solid #e6e6e6;
          color: #444;
        }}
        .footer {{
          font-size: 12px;
          color: #888;
          padding: 24px;
          text-align: center;
          background-color: #fafafa;
          border-top: 1px solid #e0e0e0;
        }}
      </style>
    </head>
    <body>
      <div class="email-container">
        <div class="header">
          <img src="https://www.thattemplateplace.com/logo.png" alt="ThatTemplatePlace Logo">
        </div>
        <div class="content">
          <h1>Weekly Gumroad Sales Report</h1>
          <p>Here is your <strong>weekly Gumroad sales report</strong> for <strong>{datetime.utcnow().strftime('%B %d, %Y')}</strong>.</p>
          <p><strong>Total Sales:</strong> {total_sales}</p>
          <p><strong>Total Earnings:</strong> ${total_earnings:.2f}</p>

          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th style="text-align:right;">Sales</th>
                <th style="text-align:right;">Earnings</th>
              </tr>
            </thead>
            <tbody>
    """

    for product in products:
        if 'id' not in product or 'name' not in product:
            continue

        product_id = product['id']
        product_name = product['name']
        sales_count = sales_by_product.get(product_id, 0)
        earnings = earnings_by_product.get(product_id, 0)
        email_body += f"""
              <tr>
                <td style="padding: 12px 16px;">{product_name}</td>
                <td style="padding: 12px 16px; text-align:right;">{sales_count}</td>
                <td style="padding: 12px 16px; text-align:right;">${earnings:.2f}</td>
              </tr>
        """

    email_body += f"""
            </tbody>
          </table>

          <p style="margin-top: 30px;">Best regards,<br>ThatTemplatePlace</p>
        </div>
        <div class="footer">
          Note that this email is sent from an unmonitored inbox. Do not reply. If unsure where to direct questions, email hello@thattemplateplace.com <br> 
          © {datetime.utcnow().year} ThatTemplatePlace. All rights reserved.
        </div>
      </div>
    </body>
    </html>
    """
    return email_body

def send_email(body):
    msg = MIMEMultipart()
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    msg["Reply-To"] = REPLY_TO_EMAIL
    msg["Subject"] = f"📬 Weekly Gumroad Report - {datetime.utcnow().strftime('%B %d, %Y')}"

    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP("smtp-relay.brevo.com", 587) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(msg["From"], [msg["To"]], msg.as_string())
            print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

if __name__ == "__main__":
    to_date = datetime.utcnow().strftime('%Y-%m-%d')
    from_date = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')

    sales = fetch_sales(GUMROAD_TOKEN, from_date, to_date)
    products = fetch_products()
    email_body = build_email_body(sales, products)
    send_email(email_body)

