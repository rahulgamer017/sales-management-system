import os
from datetime import date, datetime
from decimal import Decimal
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-before-deploying')
db_url = os.environ.get('DATABASE_URL', 'sqlite:///sales.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(180))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    sku = db.Column(db.String(80), unique=True)
    price = db.Column(db.Float, nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    paid = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default='Pending')
    sale_date = db.Column(db.Date, default=date.today)
    customer = db.relationship('Customer')
    product = db.relationship('Product')
    @property
    def due(self): return max(0, round(self.total - self.paid, 2))

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapped

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email','').strip().lower()).first()
        if user and check_password_hash(user.password_hash, request.form.get('password','')):
            session['user_id'] = user.id
            session['user_name'] = user.name
            return redirect(url_for('dashboard'))
        flash('Incorrect email or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def home():
    return redirect(url_for('dashboard' if session.get('user_id') else 'login'))

@app.route('/dashboard')
@login_required
def dashboard():
    sales = Sale.query.order_by(Sale.id.desc()).limit(5).all()
    return render_template('dashboard.html',
        revenue=db.session.query(db.func.coalesce(db.func.sum(Sale.total),0)).scalar() or 0,
        order_count=Sale.query.count(), product_count=Product.query.count(),
        customer_count=Customer.query.count(), due_total=sum(s.due for s in Sale.query.all()), recent=sales)

@app.route('/customers', methods=['GET','POST'])
@login_required
def customers():
    if request.method == 'POST':
        name=request.form.get('name','').strip()
        phone=request.form.get('phone','').strip()
        email=request.form.get('email','').strip() or None
        if not name or not phone:
            flash('Customer name and contact number are required.', 'error')
        else:
            db.session.add(Customer(name=name, phone=phone, email=email))
            db.session.commit()
            flash('Customer added.', 'success')
        return redirect(url_for('customers'))
    records=Customer.query.order_by(Customer.name).all()
    dues={c.id: round(sum(s.due for s in Sale.query.filter_by(customer_id=c.id).all()),2) for c in records}
    return render_template('customers.html', customers=records, dues=dues)

@app.route('/customers/<int:id>/delete', methods=['POST'])
@login_required
def delete_customer(id):
    customer=Customer.query.get_or_404(id)
    if Sale.query.filter_by(customer_id=id).first():
        flash('Cannot delete a customer with sales. Keep the record for invoice history.', 'error')
    else:
        db.session.delete(customer); db.session.commit(); flash('Customer deleted.', 'success')
    return redirect(url_for('customers'))

@app.route('/products', methods=['GET','POST'])
@login_required
def products():
    if request.method=='POST':
        name=request.form.get('name','').strip(); sku=request.form.get('sku','').strip() or None
        try: price=float(request.form.get('price','0')); stock=int(request.form.get('stock','0'))
        except ValueError: price=-1; stock=-1
        if not name or price < 0 or stock < 0:
            flash('Enter a product name, non-negative price and stock.', 'error')
        elif sku and Product.query.filter_by(sku=sku).first():
            flash('That SKU already exists.', 'error')
        else:
            db.session.add(Product(name=name,sku=sku,price=price,stock=stock)); db.session.commit()
            flash('Product added.', 'success')
        return redirect(url_for('products'))
    return render_template('products.html', products=Product.query.order_by(Product.name).all())

@app.route('/products/<int:id>/delete', methods=['POST'])
@login_required
def delete_product(id):
    p=Product.query.get_or_404(id)
    if Sale.query.filter_by(product_id=id).first(): flash('Cannot delete a product used in sales history.', 'error')
    else: db.session.delete(p); db.session.commit(); flash('Product deleted.', 'success')
    return redirect(url_for('products'))

@app.route('/sales', methods=['GET','POST'])
@login_required
def sales():
    if request.method=='POST':
        try:
            customer=Customer.query.get(int(request.form['customer_id']))
            product=Product.query.get(int(request.form['product_id']))
            qty=int(request.form['quantity']); paid=float(request.form.get('paid','0'))
        except (ValueError, KeyError, TypeError):
            customer=product=None; qty=0; paid=-1
        if not customer or not product or qty<1 or qty>product.stock or paid<0:
            flash('Check customer, product, quantity and amount paid. Quantity must be in stock.', 'error')
        else:
            total=round(product.price*qty,2)
            if paid>total: flash('Amount paid cannot exceed sale total.', 'error')
            else:
                product.stock-=qty
                status='Paid' if paid==total else ('Partial' if paid>0 else 'Pending')
                db.session.add(Sale(customer_id=customer.id,product_id=product.id,quantity=qty,unit_price=product.price,total=total,paid=paid,status=status))
                db.session.commit(); flash('Sale recorded and stock updated.', 'success')
        return redirect(url_for('sales'))
    return render_template('sales.html', sales=Sale.query.order_by(Sale.id.desc()).all(),
                           customers=Customer.query.order_by(Customer.name).all(), products=Product.query.filter(Product.stock>0).order_by(Product.name).all())

@app.route('/sales/<int:id>/payment', methods=['POST'])
@login_required
def payment(id):
    sale=Sale.query.get_or_404(id)
    try: amount=float(request.form.get('amount','0'))
    except ValueError: amount=0
    if amount<=0 or amount>sale.due: flash('Enter a valid payment amount.', 'error')
    else:
        sale.paid=round(sale.paid+amount,2)
        sale.status='Paid' if sale.due==0 else 'Partial'
        db.session.commit(); flash('Payment recorded.', 'success')
    return redirect(url_for('sales'))

@app.route('/invoices')
@login_required
def invoices():
    return render_template('invoices.html', sales=Sale.query.order_by(Sale.id.desc()).all())

@app.route('/reports')
@login_required
def reports():
    all_sales=Sale.query.order_by(Sale.sale_date.desc()).all()
    return render_template('reports.html', sales=all_sales, revenue=sum(s.total for s in all_sales), collected=sum(s.paid for s in all_sales), pending=sum(s.due for s in all_sales))

@app.route('/settings', methods=['GET','POST'])
@login_required
def settings():
    if request.method=='POST':
        user=User.query.get(session['user_id'])
        name=request.form.get('name','').strip()
        password=request.form.get('password','')
        if name: user.name=name; session['user_name']=name
        if password: user.password_hash=generate_password_hash(password)
        db.session.commit(); flash('Settings saved.', 'success')
        return redirect(url_for('settings'))
    return render_template('settings.html')

@app.cli.command('init-db')
def init_db():
    db.create_all()
    if not User.query.filter_by(email='admin@example.com').first():
        db.session.add(User(name='Demo Admin',email='admin@example.com',password_hash=generate_password_hash('Admin@123')))
        db.session.commit()
    print('Database initialized. Demo login: admin@example.com / Admin@123')

with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@example.com').first():
        db.session.add(User(name='Demo Admin',email='admin@example.com',password_hash=generate_password_hash('Admin@123')))
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
