from __future__ import print_function
import pickle
import os.path
from sqlalchemy.sql.elements import Null

from sqlalchemy.sql.sqltypes import DateTime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from flask import Flask, render_template, request, flash, redirect, url_for, g, session, make_response, jsonify
from flask_login import (current_user, LoginManager, login_user, logout_user, login_required)
from flask_bootstrap import Bootstrap
from models import UserForm, LoginForm
from flask_sqlalchemy import SQLAlchemy
from flask_mysqldb import MySQL
import json
from sqlalchemy_serializer import SerializerMixin
import os
from werkzeug.utils import secure_filename
from sqlalchemy.orm import relationship
from sqlalchemy import Table, Column, Integer, ForeignKey
import plotly.graph_objects as go
from datetime import datetime



class Config(object):
    SECRET_KEY = '78w0o5tuuGex5Ktk8VvVDF9Pw3jv1MVE'

app = Flask(__name__)
app.config.from_object(Config)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/dashboard_google_sheet'
app.config['SECRET_KEY'] = "3489wfksf93r2k3lf9sdjkfe9t2j3krl"

Bootstrap(app)
# datepicker(app)
db = SQLAlchemy(app)
dir_path = os.path.dirname(os.path.realpath(__file__))

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
current_user = Null

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class User(db.Model, SerializerMixin):  
# class User(db.Model, SerializerMixin):  
    __tablename__ = 'user'

    serialize_only = ('name', 'lastname', 'email', 'password', 'photo', 'company', 'approve', 'authenticated', 'admin')
    
    name =  db.Column(db.String(30), nullable = False) 
    lastname =  db.Column(db.String(30), nullable = False)     
    email = db.Column(db.String(50), nullable = False) 
    password =  db.Column(db.String(30), nullable = False) 
    photo = db.Column(db.String(50), nullable = False) 
    companies = db.Column(db.Text, nullable = False) 
    approve = db.Column(db.Boolean, nullable = False) 
    authenticated = db.Column(db.Boolean, nullable = False) 
    admin = db.Column(db.Boolean, nullable = False) 
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)


    def __init__(self, name, lastname, email, password, photo="", companies="", approve=0, authenticated=0, admin=0):
        self.name = name
        self.lastname = lastname
        self.email = email
        self.password = password                
        self.photo = photo
        self.companies = companies
        self.approve = approve
        self.authenticated = authenticated
        self.admin = admin

    def to_json(self):        
        return {"name": self.name,
                "email": self.email}

    def is_authenticated(self):
        return True

    def is_active(self):   
        return True           

    def is_anonymous(self):
        return False          

    def get_id(self):         
        return str(self.email)
    


class Company(db.Model, SerializerMixin):  
    __tablename__ = 'company'

    serialize_only = ('comp_name', 'cnpj', 'email', 'logo', 'standard_rate', 'improved_rate')
    
    comp_name =  db.Column(db.String(50), nullable = False) 
    cnpj =  db.Column(db.String(30), primary_key=True, nullable = False) 
    email = db.Column(db.String(50), nullable = False) 
    logo = db.Column(db.String(50), nullable = False) 
    standard_rate = db.Column(db.Float, nullable = False) 
    improved_rate = db.Column(db.Float, nullable = False)

    def __init__(self, comp_name, cnpj, email, logo, standard_rate, improved_rate):
        self.comp_name = comp_name
        self.cnpj = cnpj
        self.email = email
        self.logo = logo        
        self.standard_rate = standard_rate
        self.improved_rate = improved_rate


class Tbl(db.Model, SerializerMixin):  
    __tablename__ = 'tbl'

    serialize_only = ('tbl_name', 'description')
    
    tbl_name =  db.Column(db.String(50), nullable = False) 
    description = db.Column(db.Text, nullable = False) 
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    def __init__(self, tbl_name, description):
        self.tbl_name = tbl_name
        self.description = description


class Field(db.Model, SerializerMixin):  
    __tablename__ = 'field'

    serialize_only = ('tbl_id', 'from_', 'to', 'rule', 'field_type')
    
    tbl_id =  db.Column(db.Integer, nullable = False) 
    from_ =  db.Column(db.String(50), nullable = False)     
    to = db.Column(db.String(50), nullable = False) 
    rule =  db.Column(db.Text, nullable = False) 
    field_type = db.Column(db.Integer, db.ForeignKey('field_type.id'))
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    f_type = db.relationship('Field_Type')

    def __init__(self, tbl_id, from_, to, rule, field_type):
        self.tbl_id = tbl_id
        self.from_ = from_
        self.to = to
        self.rule = rule                
        self.field_type = field_type


class Field_Type(db.Model, SerializerMixin):  
    __tablename__ = 'field_type'

    serialize_only = ('field_type')
    
    field_type =  db.Column(db.String(10), nullable = False)     
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    field = db.relationship('Field', backref='field_type_', lazy=True)

    def __init__(self, field_type):
        self.field_type = field_type
        

@login_manager.user_loader
def user_loader(user_id):
    return User.query.filter_by(id=user_id).first()


@app.route('/', methods=['GET', 'POST'])
def admin():
    if 'connected' in request.cookies:
        print("connected = " + request.cookies.get('connected'))
        if request.cookies.get('connected') == "true" :
            return render_template('main.html')
    return redirect(url_for("login"))

@app.route('/login', methods = ['POST', 'GET'])
def login():    
    resp = make_response(render_template('auth-login.html'))
    if request.cookies.get('email'):
        print("cookie  email: " + request.cookies.get('email'))
    if request.method == 'POST':
        print("remember = " + request.form['remember'])
        for i in request.form:
            print(str(i))
        print(request.form['email'] + "::::::" + request.form['password'])
        if os.environ.get('ADMIN_EMAIL') == request.form['email'] and os.environ.get('ADMIN_PASSWORD') == request.form['password']:
            session['email'] = request.form['email']
            return redirect(url_for('admin'))
        else:
            user = User.query.filter_by(email=request.form['email']).first()
            if user :
                if user.password == request.form['password'] :
                    user.authenticated = True
                    db.session.add(user)
                    db.session.commit()
                    current_user = user
                    print("admin = " + str(user.admin))
                    print("approve = " + str(user.approve))
                    resp = make_response(redirect(url_for('admin')))
                    resp.set_cookie('email', request.form['email'])
                    resp.set_cookie('password', request.form['password'])
                    resp.set_cookie('remember', request.form['remember'])
                    resp.set_cookie('photo', user.photo)
                    resp.set_cookie('user_name', user.name)
                    resp.set_cookie('user_lastname', user.lastname)
                    # resp.set_cookie('approve', user.approve)
                    if user.admin:
                        resp.set_cookie('admin', '1')
                    else:
                        resp.set_cookie('admin', '0')
                    resp.set_cookie('connected', 'true')
                    login_user(user, remember=True)
                    return resp
                else:
                    return render_template('auth-login.html', msg='Password is incorrect.')
                
            else:
                return render_template('auth-login.html', msg='Not a registered user.')
    else:
        if 'remember' in request.cookies:
            if request.cookies.get('remember') == "true" :
                return render_template('auth-login.html', email=request.cookies.get('email'), password=request.cookies.get('password'))
    return resp

@app.route("/logout", methods=["GET"])
# @login_required
def logout():
    print("logout")
    """Logout the current user."""
    # user = current_user
    # user.authenticated = False
    # db.session.add(user)
    # db.session.commit()
    resp = make_response(redirect(url_for("login")))
    print("1")
    if 'connected' in request.cookies:
        print("ok")
        resp.set_cookie('connected', 'false')
    logout_user()
    return resp
    

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = db.session.query(User).filter_by(email=request.form['email']).first()
        if not user:
            user = User(request.form['name'], request.form['lastname'], request.form['email'], request.form['password'])
            db.session.add(user)
            db.session.commit()
            return redirect(url_for("login"))

    return render_template('auth-register.html')


@app.route('/users', methods=['GET', 'POST'])
def users():
    users = User.query.order_by(User.id)
    return render_template('user.html', users=users)


@app.route('/remove_user/<string:user_id>', methods=['GET', 'POST'])
def remove_user(user_id):
    db.session.query(User).filter_by(id=user_id).delete()
    db.session.commit()
    return redirect(url_for('users'))


@app.route('/company', methods=['GET', 'POST'])
def company():
    # if not 'username' in session:
    #     return redirect(url_for("login"))
    if request.method == 'POST':
        f = request.files['logo']
        if f.filename != '':
            f.save(dir_path + "\\static\\app-assets\\images\\company_logo\\" + secure_filename(f.filename))
        if request.form['cur_cnpj'] == "---":
            comp = Company(request.form['comp_name'], request.form['cnpj'], request.form['email'], f.filename, request.form['standard_rate'], request.form['improved_rate'])
            db.session.add(comp)
        else:
            db.session.query(Company).filter_by(cnpj = request.form['cur_cnpj']).update({Company.comp_name:request.form['comp_name'], Company.cnpj:request.form['cnpj'], Company.email:request.form['email'], Company.logo:f.filename, Company.standard_rate:request.form['standard_rate'], Company.improved_rate:request.form['improved_rate']}, synchronize_session = False)
            
        db.session.commit()
    companies = Company.query.order_by(Company.comp_name)
    return render_template('company.html', comps=companies)


@app.route('/remove_company/<string:cnpj>', methods=['GET', 'POST'])
def remove_company(cnpj):
    db.session.query(Company).filter_by(cnpj=cnpj).delete()
    db.session.commit()
    return redirect(url_for('company'))


@app.route('/table', methods=['GET', 'POST'])
def table_():
    # if not 'username' in session:
    #     return redirect(url_for("login"))
    if request.method == 'POST':
        if request.form['cur_id'] == "---":
            comp = Tbl(request.form['tbl_name'], request.form['description'])
            db.session.add(comp)
        else:
            db.session.query(Tbl).filter_by(id = request.form['cur_id']).update({Tbl.tbl_name:request.form['tbl_name'], Tbl.description:request.form['description']}, synchronize_session = False)            
        db.session.commit()
    tbls = Tbl.query.order_by(Tbl.id)
    return render_template('table.html', tbls=tbls)


@app.route('/remove_table/<string:table_id>', methods=['GET', 'POST'])
def remove_table(table_id):
    db.session.query(Tbl).filter_by(id=table_id).delete()
    db.session.commit()
    return redirect(url_for('table_'))

@app.route('/field', methods=['GET', 'POST'])
def field():
    # if not 'username' in session:
    #     return redirect(url_for("login"))
    tbls = Tbl.query.order_by(Tbl.id)
    tbl_id = -1
    if len(tbls.all()) > 0:
        tbl_id = tbls.first().id
        print("tbl_id = " + str(tbl_id))
        return redirect(url_for('field_of_table', tbl_id=tbl_id))
    else:
        return render_template('field.html', tbl_id=tbl_id)

@app.route('/field/<int:tbl_id>', methods=['GET', 'POST'])
def field_of_table(tbl_id):
    # if not 'username' in session:
    #     return redirect(url_for("login"))
    if request.method == 'POST':
        if request.form['cur_id'] == "---":
            comp = Field(request.form['tbl_id'], request.form['from'], request.form['to'], "", request.form['field_type'])
            db.session.add(comp)
        else:
            print(str(request.form['cur_id']))
            db.session.query(Field).filter_by(id = request.form['cur_id']).update({Field.from_:request.form['from'], Field.to:request.form['to'], Field.field_type:request.form['field_type']}, synchronize_session = False)            
        db.session.commit()
    field_types = Field_Type.query.order_by(Field_Type.id)
    tbls = Tbl.query.order_by(Tbl.id)
    # fields = Field.query.order_by(Field.id)
    fields = Field.query.join(Field_Type, Field.field_type==Field_Type.id).add_columns(Field.id, Field.tbl_id, Field.from_, Field.to, Field_Type.field_type).filter(Field.tbl_id==tbl_id)
   
    return render_template('field.html', fields=fields, tbls=tbls, field_types=field_types, tbl_id=tbl_id)


@app.route('/remove_field/<int:field_id>', methods=['GET', 'POST'])
def remove_field(field_id):
    db.session.query(Field).filter_by(id=field_id).delete()
    db.session.commit()
    return redirect(url_for('field'))


@app.route('/rule', methods=['GET', 'POST'])
def rule():
    # if not 'username' in session:
    #     return redirect(url_for("login"))
    tbls = Tbl.query.order_by(Tbl.id)
    tbl_id = -1
    if len(tbls.all()) > 0:
        tbl_id = tbls.first().id
        print("tbl_id = " + str(tbl_id))
        return redirect(url_for('rule_of_table', tbl_id=tbl_id))
    else:
        return render_template('rule.html', tbl_id=tbl_id)

@app.route('/rule/<int:tbl_id>', methods=['GET', 'POST'])
def rule_of_table(tbl_id):
    # if not 'username' in session:
    #     return redirect(url_for("login"))
    if request.method == 'POST':
        db.session.query(Field).filter_by(id = request.form['cur_id']).update({Field.to:request.form['to'], Field.rule:request.form['rule']}, synchronize_session = False)            
        db.session.commit()
    tbls = Tbl.query.order_by(Tbl.id)
    rules = Field.query.order_by(Field.id).filter(Field.from_=="", Field.tbl_id==tbl_id)
    fields = Field.query.order_by(Field.id).filter(Field.tbl_id==tbl_id)
    # fields = Field.query.join(Field_Type, Field.field_type==Field_Type.id).add_columns(Field.id, Field.tbl_id, Field.from_, Field.to, Field_Type.field_type).filter(Field.tbl_id==tbl_id)
   
    return render_template('rule.html', rules=rules, fields=fields, tbls=tbls, tbl_id=tbl_id)


@app.route('/remove_rule/<int:rule_id>', methods=['GET', 'POST'])
def remove_rule(rule_id):
    db.session.query(Field).filter_by(id=rule_id).delete()
    db.session.commit()
    return redirect(url_for('rule'))

@app.route('/edit_dashboard', methods=['GET', 'POST'])
def edit_dashboard():
    # if not 'username' in session:
    #     return redirect(url_for("login"))
    tbls = Tbl.query.order_by(Tbl.id)
    return render_template('edit_dashboard.html', tbls=tbls)


@app.route('/get_sheet_data/<string:sheet_id>/<string:sheet_name>/<int:sheet_row_count>/<string:sheet_range>/<string:chart_type>', methods=['GET', 'POST'])
def get_sheet_data(sheet_id, sheet_name, sheet_row_count, sheet_range, chart_type):
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=20000)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=sheet_id, range=sheet_name + "!" + sheet_range).execute()
    values = result.get('values', [])

    # Bar Chart (1)
    # fig = go.Figure(data=go.Bar(y=[4, 5, 2, 3, 1]))
    # fig.write_html('static/chart/third_figure.html', auto_open=False)

    # Bar Chart (multi)
    # chart_data = []
    # for row in values:
    #     chart_data.append(go.Bar(name='', x=values[0], y=row))
            
    # fig = go.Figure(data=chart_data)
    # chart_id = str(int(DateTime()))
    # fig.write_html('static/chart/' + chart_id + '.html', auto_open=False)


    # [
    #     go.Bar(name='SF Zoo', x=animals, y=[20, 14, 23]),
    #     go.Bar(name='LA Zoo', x=animals, y=[12, 18, 29])
    # ])
    # Change the bar mode
    # fig.update_layout(barmode='group')
    # fig.show()
    
    resp = ""
    # resp = '<iframe src="/static/chart/' + chart_id + '.html" width="100%" height="600px"></iframe>'
    if values:
        if chart_type == "table":
            resp = "<table border='1' style='margin-left:auto; margin-right:auto'>"
            for row in values:
                resp += "<tr>"
                for cell in row:
                    resp += "<td>" + cell + "</td>"
                resp += "</tr>"
            resp += "</table>"
        else:
            chart_data = []
            x_data = []
            fig = Null
            if chart_type == "columns":
                for row in values:
                    x_data.append(row[0])
                for col in range(1, len(values[0])):
                    chart_data.append(go.Bar(name='', x=x_data[1:], y= [row[col] for row in values[1:]]))
                fig = go.Figure(data=chart_data)
            
            elif chart_type == "bars":
                for row in values:
                    x_data.append(row[0])
                for col in range(1, len(values[0])):
                    chart_data.append(go.Bar(name='', y=x_data[1:], x= [row[col] for row in values[1:]], orientation='h'))
                fig = go.Figure(data=chart_data)
            
            elif chart_type == "lines":
                for row in values:
                    x_data.append(row[0])
                for col in range(1, len(values[0])):
                    chart_data.append(go.Scatter(name='', x=x_data[1:], y= [row[col] for row in values[1:]]))
                fig = go.Figure(data=chart_data)
            
            elif chart_type == "pizza_1":
                for row in values:
                    x_data.append(row[0])
                for col in range(1, len(values[0])):
                    chart_data.append(go.Pie(name='', labels=x_data[1:], values= [row[col] for row in values[1:]]))
                fig = go.Figure(data=chart_data)
            
            elif chart_type == "pizza_2":
                for row in values:
                    x_data.append(row[0])
                for col in range(1, len(values[0])):
                    chart_data.append(go.Pie(name='', labels=x_data[1:], values= [row[col] for row in values[1:]], hole = 0.3))
                fig = go.Figure(data=chart_data)
            
            elif chart_type == "histogram":
                for row in values:
                    x_data.append(row[0])
                for col in range(1, len(values[0])):
                    chart_data.append(go.Histogram(name='', x= [row[col] for row in values[1:]]))
                fig = go.Figure(data=chart_data)

            elif chart_type == "funnel":
                for row in values:
                    x_data.append(row[0])
                fig = go.Figure(go.Funnel(y = x_data[1:], x= [row[1] for row in values[1:]]))
            
            chart_id = str(int(datetime.now().timestamp()))
            fig.write_html('static/chart/' + chart_id + '.html', auto_open=False)
            resp = '<iframe src="/static/chart/' + chart_id + '.html" width="100%" height="600px"></iframe>'
    return resp


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
