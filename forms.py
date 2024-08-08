from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, FloatField
from wtforms.validators import DataRequired, Email, Length, NumberRange


class EditMovieForm(FlaskForm):
    rate = FloatField('Rate', validators=[DataRequired(), NumberRange(min=0.0, max=10.0)])
    review = StringField('Review', validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField('Confirm')


class AddMovieForm(FlaskForm):
    movie_title = StringField('Movie Title', validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField('Add movie')
