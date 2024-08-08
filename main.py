from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from requests import HTTPError, Timeout, TooManyRedirects, RequestException
from sqlalchemy.exc import NoResultFound, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, desc
import requests

from tmdb_info import TMDB_API_KEY, TMDB_TOKEN, TMDB_URL

from forms import EditMovieForm, AddMovieForm

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)


# CREATE DB
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///top-movies.db"
# Create the extension
db = SQLAlchemy(model_class=Base)
# Initialise the app with the extension
db.init_app(app)


# CREATE TABLE
class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(500), nullable=True)
    img_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Optional: this will allow each book object to be identified by its title when printed.
    def __repr__(self):
        return f'<Movie {self.title}>'


# Create table schema in the database. Requires application context.
with app.app_context():
    db.create_all()


@app.route("/")
def home():
    ordered_movies = Movie.query.order_by(Movie.rating.desc()).all()
    i = 1
    for movie in ordered_movies:
        movie.ranking = i
        i += 1
    db.session.commit()

    return render_template("index.html", all_movies=ordered_movies)


@app.route("/add", methods=['GET', 'POST'])
def add():
    add_form = AddMovieForm()

    if request.method == 'POST':
        if add_form.validate_on_submit():
            new_movie = add_form.movie_title.data
            # print(new_movie)
            try:
                url = f"{TMDB_URL}/3/search/movie"
                headers = {
                    'Authorization': f'Bearer {TMDB_TOKEN}',
                    'accept': 'application/json',
                }
                params = {
                    'query': f'{new_movie}',
                    'include_adult': 'true',
                    'language': 'en-US',
                    'page': 1,
                }

                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    # Print the JSON response
                    movies = response.json()['results']
                    # print(movies)
                    return render_template('select.html', movies=movies)
                else:
                    # Print an error message if the request was not successful
                    print(f"Error: {response.status_code} - {response.text}")
                    message = f"Something was wrong, try again"
                    return render_template('add.html', add_form=add_form, message=message)

            except HTTPError as http_err:
                print(f'HTTP error occurred: {http_err}')
            except ConnectionError as conn_err:
                print(f'Connection error occurred: {conn_err}')
            except Timeout as timeout_err:
                print(f'Request timed out: {timeout_err}')
            except TooManyRedirects as redirect_err:
                print(f'Too many redirects: {redirect_err}')
            except RequestException as req_err:
                print(f'Request exception occurred: {req_err}')
            except Exception as err:
                print(f'Other error occurred: {err}')

            message = f"Something was wrong, try again"
            return render_template('add.html', add_form=add_form, message=message)
        else:
            message = f"Something was wrong, try again"
            return render_template("add.html", add_form=add_form, message=message)

    else:
        return render_template("add.html", add_form=add_form)


# TODO: route to edit entries, it must load a register by id then update it
@app.route("/edit/<int:movie_id>", methods=['GET', 'POST'])
def edit(movie_id):
    edit_form = EditMovieForm()
    # print(movie_id)
    with app.app_context():
        # Fetch the book to update from the database
        movie_to_update = db.session.execute(db.select(Movie).where(Movie.id == movie_id)).scalar()

        if edit_form.validate_on_submit():
            new_rate = edit_form.rate.data
            new_review = edit_form.review.data

            if new_rate and new_review:
                try:
                    # Convert the new rate to float
                    new_rate = float(new_rate)
                except ValueError:
                    print("The rating must be a number")
                    message = "The rate must be a number"
                    return render_template('edit.html', edit_form=edit_form,
                                           movie_to_update=movie_to_update, message=message)

                if new_rate and 0 <= new_rate <= 10:
                    movie_to_update.rating = new_rate
                    movie_to_update.review = new_review
                    db.session.commit()  # Commit the changes to the database
                    message = "Movie updated successfully"
                    return render_template('edit.html', edit_form=edit_form,
                                           movie_to_update=movie_to_update, message=message)
                else:
                    message = "The rate must be between 0 and 10"
                    return render_template('edit.html', edit_form=edit_form,
                                           movie_to_update=movie_to_update, message=message)

        return render_template('edit.html', edit_form=edit_form, movie_to_update=movie_to_update)


@app.route("/select/<int:movie_id>", methods=['GET', 'POST'])
def select(movie_id):
    if movie_id:
        # print(f"WORKS {movie_id}")
        url = f"{TMDB_URL}/3/movie/{movie_id}"

        headers = {
            'Authorization': f'Bearer {TMDB_TOKEN}',
            'accept': 'application/json',
        }
        params = {
            'language': 'en-US',
        }

        try:
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                # Print the JSON response
                movie = response.json()
                title = movie['original_title']
                # https://image.tmdb.org/t/p/original[poster_path]
                img_url = f"https://image.tmdb.org/t/p/original{movie['poster_path']}"
                description = movie['overview']
                year = movie['release_date']
                mo_id = movie['id']
                new_movie = Movie(id=mo_id, title=title, img_url=img_url, description=description, year=year)
                # print(new_movie)

                try:
                    with app.app_context():
                        db.session.add(new_movie)
                        db.session.commit()
                        print(f"Movie added successfully! {movie_id}")

                        # Render edit.html with movie_id and any other required movie details
                        return redirect(url_for('edit', movie_id=movie_id))

                except Exception as e:
                    # Rollback the session in case of error
                    db.session.rollback()
                    print(f"Error adding movie: {e}")
                    # Optionally handle the error or redirect to an error page
                    add_form = AddMovieForm()
                    message = "Oops, there was an error, try again"
                    return render_template('add.html', add_form=add_form, message=message)

            else:
                # Print an error message if the request was not successful
                print(f"Error: {response.status_code} - {response.text}")
                return render_template('error.html', error=f"Error: {response.status_code} - {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return render_template('error.html', error=f"An error occurred: {e}")

    return render_template("select.html")


@app.route("/delete/<int:movie_id>", methods=['GET', 'POST'])
def delete(movie_id):
    if movie_id:
        try:
            movie_to_delete = db.session.execute(db.select(Movie).where(Movie.id == movie_id)).scalar()
            if movie_to_delete:
                db.session.delete(movie_to_delete)
                db.session.commit()
            else:
                raise NoResultFound("No movie found with the given ID")
        except NoResultFound as e:
            db.session.rollback()
            print(f"Error: {e}")
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"SQLAlchemy error: {e}")
        except Exception as e:
            db.session.rollback()
            print(f"An unexpected error occurred: {e}")

    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
