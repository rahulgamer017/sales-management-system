# Sellwise — Sales Management System

A Flask web app for small physical shops to manage products, stock, customers, sales, invoices and reports.

## Features in this update
- Modern responsive blue-and-white interface with dark navigation sidebar.
- Cashier / point-of-sale page with multi-product cart and quantity controls.
- Walk-in checkout without requiring a customer account; customer name and phone are optional.
- Payment method selection for Cash, UPI, Card, Bank transfer or Other.
- Full, partial and zero-payment checkout; unpaid balances remain visible as dues.
- Stock decreases when a sale is recorded, with server-side quantity validation.
- Invoice reference shared by all items in one checkout.
- Additive startup migration for `invoice_no` and `payment_method` columns on existing deployments.
- Existing product, customer, reports and invoice pages retained.

## Run locally
1. Install Python 3.10+.
2. Create and activate a virtual environment.
3. Run `pip install -r requirements.txt`.
4. Run `python app.py`.
5. Open `http://127.0.0.1:5000`.

Demo login: `admin@example.com` / `Admin@123`

**Security note:** change the demo admin password and set a strong `SECRET_KEY` environment variable before using this app with real customer data. Configure a persistent PostgreSQL database for a hosted deployment; local SQLite data on ephemeral hosting may not persist.

## Deployment
The included `Procfile` starts the app with Gunicorn. Set `DATABASE_URL` to a persistent PostgreSQL connection string and set `SECRET_KEY` in the hosting service environment. The app attempts a small additive migration on startup for the new sale fields.

## Validation notes
The Python source was checked with `py_compile`, and template comparisons were scanned for HTML-escaped operators inside Jinja templates. Full Flask route/browser integration tests could not be run in this environment because Flask dependencies could not be installed without network access. Test the app in a local environment before deploying.
