import secrets
import os
from flask import Flask, render_template, redirect, request, session, url_for, flash,jsonify
from pymongo import MongoClient
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin,current_user
from bson import ObjectId
import cgi
from datetime import datetime,timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


app = Flask(__name__)

#sdfshh
# Generate a secure secret key
secret_key = secrets.token_hex(16)

# Set the secret key securely from environment variable or fallback to a default value
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secret_key)

client = MongoClient('mongodb://localhost:27017/')
db = client['MovieMania']
movies = db['movies']
users = db['users']
adminl = db['admin']
booking = db['bookings']

login_manager = LoginManager()
login_manager.init_app(app)

def int_to_str(value):
    return str(value)

def str_to_int(value):
    return int(value)

app.jinja_env.filters['int_to_str'] = int_to_str
app.jinja_env.filters['str_to_int'] = str_to_int

class User(UserMixin):
    def __init__(self, username):
        self.username = username
    def get_id(self):
        return str(self.username)    

# Load user from database
@login_manager.user_loader
def load_user(username):
    a = adminl.find_one({'username': username})
    if a:
        return User(a['username'])
    
    user_data = users.find_one({'username': username})
    if user_data:
        return User(user_data['username'])
    else:
        return None
    

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        mobile = request.form['mobile']

        

        if users.find_one({'username': username}):
            flash('Username already taken. Please choose a different username.', 'error')
            return redirect(url_for('signup'))

        new_user = {
            'firstname': firstname,
            'lastname': lastname,
            'username': username,
            'email': email,
            'password': password,
            'mobile': mobile
        }
        users.insert_one(new_user)
        flash('Signup successful. You can now login.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        a = adminl.find_one({'username':username,
                             'password':password
                             })
        
        if a:
            print('login successful')
            user = User(a['username'])
            login_user(user)
            print(user)
            return redirect(url_for('admin'))
        
        user_data = users.find_one({'username': username, 'password': password})

        if user_data:
            user = User(user_data['username'])
            
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password. Please try again.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/',methods=['GET','POST'])
def first():
    return render_template('login.html')

@app.route('/index',methods=['GET','POST'])
def home():
    if current_user.is_authenticated:  # Check if the user is authenticated
        # user_data = users.find_one({'username': current_user.username})

        movie_record = movies.find()
        print(movie_record)
        
        cdf = datetime.now().strftime("%Y%m%d")


        cdf = int(cdf)
        # for i in movie_record:
            
        #     print(i)
        
        return render_template('index.html', movie_record=movie_record,cdf=cdf)

    return render_template('index.html')

@app.route('/seatbooking',methods=['GET','POST'])
def seatbooking():
    if current_user.is_authenticated:  # Check if the user is authenticated
        form = cgi.FieldStorage()
        movie_id = request.form['movie_id']
        print(movie_id)
        movie_details = movies.find_one({'movie_id':movie_id})

        print(movie_details)
        return render_template('seatbooking.html', movie_details=movie_details)

    return render_template('seatbooking.html')


@app.route('/bookings',methods=['GET','POST'])
def bookings():
    if current_user.is_authenticated:  # Check if the user is authenticated
        # user_data = users.find_one({'username': current_user.username})

        flag = request.form['booking']
        
        if flag == 'yes':
        
            selected_seats = request.form['selected_seats']
            movie_id = request.form['movie_id']
            
            bs1 = movies.find_one({'movie_id':movie_id})
            bs = bs1['booked_seats']
            ss = selected_seats.split(',')
            
            
            query = {'movie_id': movie_id}
            new_values = {'$set': {'booked_seats': ss+bs}}
            print(selected_seats.split(','))
            print(movie_id)
            movies.update_one(query, new_values)
                    
            print(selected_seats,movie_id)
            
            movie_details = movies.find_one({'movie_id':movie_id})
            
            book = {
                'username':current_user.username,
                'movie_id':movie_id,
                'booked_seats':ss,
                'payment':'online',
                'total':len(ss)*bs1['ticket_price'],
                'show_date':movie_details['show_date'],
                'show_time':movie_details['show_time'],
                'screen':movie_details['screen'],
                'movie_name':movie_details['movie_name']
            }
            booking.insert_one(book)
            
            cus_bookings = booking.find({'username':current_user.username})
            cb = []
            for i in cus_bookings:
                cb.append(i)
            cb.reverse()
            
            sender_email = 'anirudhmane974@gmail.com'
            receiver_email = users.find_one({'username':current_user.username})
            receiver_email = receiver_email['email']
            password = 'rippzqlldzeqseth'

            # Create a message
            message = MIMEMultipart()
            message['From'] = sender_email
            message['To'] = receiver_email
            message['Subject'] = 'Booking Confiramtion'

            # Add body to the email
            u = current_user.username
            body = "Hello {user}, your booking has been confirmed and your confirmed seats are {seats} and the total paid amount: {amount}".format(user=u, seats=selected_seats, amount=book['total'])
            # body = "Hello it's me motherfucker"
            message.attach(MIMEText(body, 'plain'))

            # Connect to Gmail's SMTP server
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, password)
                server.sendmail(sender_email, receiver_email, message.as_string())
                
            return render_template('bookings.html',cb=cb)
        
        else:
            cus_bookings = booking.find({'username':current_user.username})
            cb = []
            for i in cus_bookings:
                cb.append(i)
            cb.reverse()
            return render_template('bookings.html',cb=cb)

    return render_template('bookings.html')

@app.route('/profile',methods=['GET','POST'])
def profile():
    if current_user.is_authenticated:  # Check if the user is authenticated
        # user_data = users.find_one({'username': current_user.username})

        user_details = users.find_one({'username':current_user.username})
        
        return render_template('profile.html', user_details=user_details)

    return render_template('profile.html')

@app.route('/admin',methods=['GET','POST'])
def admin():
    if current_user.is_authenticated:  # Check if the user is authenticated
        # user_data = users.find_one({'username': current_user.username})
        
        return render_template('admin.html')

    return render_template('admin.html')

@app.route('/addmovie',methods=['GET','POST'])
def addmovie():
    # print(current_user.username)
    if current_user.is_authenticated:  # Check if the user is authenticated
        # user_data = users.find_one({'username': current_user.username})
        print('adminl')
        return render_template('addmovie.html')

    return render_template('addmovie.html')

@app.route('/successful',methods=['GET','POST'])
def successful():
    
    if current_user.is_authenticated:  # Check if the user is authenticated
        # user_data = users.find_one({'username': current_user.username})
        movieId = request.form['movieId']
        movieName = request.form['movieName']
        movieDescription = request.form['movieDescription']
        screen = request.form['screen']
        showDate = request.form['showDate']
        showTime = request.form['showTime']
        ticketPrice = int(request.form['ticketPrice'])
        bookedSeats = []
        showDate = showDate[8:]+showDate[5:7]+showDate[0:4]
        showDate = int(showDate)
        movie = {
            'movie_id':movieId,
            'movie_name':movieName,
            'movie_description':movieDescription,
            'screen':screen,
            'show_date':showDate,
            'show_time':showTime,
            'ticket_price':ticketPrice,
            'booked_seats':bookedSeats
        }
        
        exist = movies.find_one({'movie_id':movieId})
        
        print(movie)
        
        if exist:
            flash('Movie id already exists.', 'error')
        else:
            movies.insert_one(movie)
            
        return render_template('successful.html')

    return render_template('successful.html')

@app.route('/searchmovie',methods=['GET','POST'])
def searchmovie():
    
    if current_user.is_authenticated:  # Check if the user is authenticated
        
        return render_template('searchmovie.html')

    return render_template('searchmovie.html')

@app.route('/analysis',methods=['GET','POST'])
def analysis():
    
    if current_user.is_authenticated:  # Check if the user is authenticated
        
        return render_template('analysis.html')

    return render_template('analysis.html')

@app.route('/result',methods=['GET','POST'])
def result():
    if current_user.is_authenticated:  # Check if the user is authenticated
        movieId = request.form['movieId']
        movie_details = movies.find_one({'movie_id':movieId})
        if movie_details:
            l = len(movie_details['booked_seats'])
            return render_template('result.html',movie_details=movie_details,l=l)

    return render_template('nodata.html')

@app.route('/analysisresult',methods=['GET','POST'])
def analysisresult():
    if current_user.is_authenticated:  # Check if the user is authenticated
        # startDate = request.form['startDate']
        # endDate = request.form['endDate']
        # startDate = startDate[8:]+startDate[5:7]+startDate[0:4]
        # startDate = int(startDate)
        # endDate = endDate[8:]+endDate[5:7]+endDate[0:4]
        # endDate = int(endDate)
        # total = 0
        # print(endDate)
        # print(startDate)
        # for i in range(startDate,endDate+1):
        #     temp = movies.find_one({'show_date':i})
        #     for j in temp:
        #         total = j['total']+total
        #         print(j['username'])
        #         print(j['show_date'])
        #         print(j['total'])
        #         # print(i)
        # print(total)
        
        startDate_str = request.form['startDate']
        endDate_str = request.form['endDate']

        # Convert string dates to datetime objects
        startDate = datetime.strptime(startDate_str, '%Y-%m-%d')
        endDate = datetime.strptime(endDate_str, '%Y-%m-%d')

        # Generate dates between startDate and endDate
        dates_between = []
        current_date = startDate
        while current_date <= endDate:
            dates_between.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        print(dates_between)
        total = 0
        list = []
        for d in dates_between:
            d = d[8:]+d[5:7]+d[0:4]
            d = int(d)
            temp = movies.find({'show_date':d})
            for j in temp:
                if temp!=None:
                    total = (len(j['booked_seats'])*j['ticket_price'])+total
                    dict = {
                        'revenue':len(j['booked_seats'])*j['ticket_price'],
                        'movie_name':j['movie_name'],
                        'screen':j['screen'],
                        'show_date':j['show_date'],
                        'show_time':j['show_time'],
                        'ticket_price':j['ticket_price'],
                    }
                    list.append(dict)
            print("\n")
        
        return render_template('analysisresult.html',list=list,total=total)

    return render_template('analysisresult.html')

@app.route('/update',methods=['GET','POST'])
def update():
    
    if current_user.is_authenticated:  # Check if the user is authenticated
        
        return render_template('update.html')

    return render_template('update.html')

@app.route('/deletemovie',methods=['GET','POST'])
def deletemovie():
    
    if current_user.is_authenticated:  # Check if the user is authenticated
        movieId = request.form['movie_id']
        exist = movies.find_one({'movie_id':movieId})
        if exist:
            movies.delete_one({'movie_id':movieId})
            return render_template('deletemovie.html')

    return render_template('deletemovie.html')

@app.route('/successful2',methods=['GET','POST'])
def successful2():
    
    if current_user.is_authenticated:  # Check if the user is authenticated
        # user_data = users.find_one({'username': current_user.username})
        movieId = request.form['movieId']
        movieName = request.form['movieName']
        movieDescription = request.form['movieDescription']
        screen = request.form['screen']
        showDate = request.form['showDate']
        showTime = request.form['showTime']
        ticketPrice = int(request.form['ticketPrice'])
        bookedSeats = []
        showDate = showDate[8:]+showDate[5:7]+showDate[0:4]
        showDate = int(showDate)
        
        movie = {
            'movie_id':movieId,
            'movie_name':movieName,
            'movie_description':movieDescription,
            'screen':screen,
            'show_date':showDate,
            'show_time':showTime,
            'ticket_price':ticketPrice,
            'booked_seats':bookedSeats
        }
        
        exist = movies.find_one({'movie_id':movieId})
        
        print(movie)
        
        if exist:
            movies.update_one({'movie_id': movieId}, {"$set": movie})
            return render_template('successful2.html')
        else:
            return render_template('nodata.html')
            
        

    return render_template('nodata.html')


if __name__ =='__main__':
    app.run(debug=True,port=5001)