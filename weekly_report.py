import smtplib
import requests
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os

# Secrets loaded from GitHub environment
GUMROAD_TOKEN = os.getenv("GUMROAD_TOKEN")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

def fetch_sales():
    url = "https://api.gumroad.com/v2/sales"
    params = {"access_token": GUMROAD_TOKEN}
    response = requests.get(url, params=params)
    return response.json().get("sales", [])

def fetch_products():
    url = "https://api.gumroad.com/v2/products"
    params = {"access_token": GUMROAD_TOKEN}
    response = requests.get(url, params=params)
    return response.json().get("products", [])

def build_email_body(sales, products):
    this_week = datetime.utcnow() - timedelta(days=7)
    weekly_sales = [
        s for s in sales if datetime.strptime(s["created_at"], "%Y-%m-%dT%H:%M:%SZ") > this_week
    ]

    body = f"📊 Weekly Report - {datetime.utcnow().strftime('%Y-%m-%d')}\n\n"
    body += f"🛒 Total Sales: {len(weekly_sales)}\n\n"
    
    sales_by_product = {}
    for sale in weekly_sales:
        pid = sale["product_id"]
        sales_by_product[pid] = sales_by_product.get(pid, 0) + 1

    for product in products:
        count = sales_by_product.get(product["id"], 0)
        body += f"- {product['name']}: {count} sale(s)\n"

    return body

def send_email(body):
    msg = MIMEText(body)
    msg["Subject"] = "📬 Weekly Gumroad Report"
    msg["From"] = "noreply@thattemplateplace.com"
    msg["To"] = "weeklyreport@thattemplateplace.com"

    with smtplib.SMTP("smtp-relay.brevo.com", 587) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(msg["From"], [msg["To"]], msg.as_string())

if __name__ == "__main__":
    sales = fetch_sales()
    products = fetch_products()
    email_body = build_email_body(sales, products)
    send_email(email_body)
