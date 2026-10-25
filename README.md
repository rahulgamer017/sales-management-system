# Sales Management System (Python / Flask)

Responsive college-project web app with login, dashboard, products, customers, sales, invoices, reports, and settings.

## Demo login
- Email: `admin@example.com`
- Password: `Admin@123`

Change the demo password before using real customer information.

## Deploy on Render
1. Push this folder to your GitHub repository.
2. In Render, choose **New → Web Service** and connect the repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. For persistent hosted data, create a Render PostgreSQL database and set the app's `DATABASE_URL` environment variable to its internal connection URL.
6. Set `SECRET_KEY` to a long random secret in Render environment variables.
7. Deploy. Render gives the service a public `onrender.com` URL.

Free Render services may sleep after inactivity; free database availability and limits can change. Review current Render plan details before relying on it for important data.

## Local testing (optional)
`pip install -r requirements.txt` then `python app.py`. This uses a local SQLite file by default. You do not need XAMPP.
