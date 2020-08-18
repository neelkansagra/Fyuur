import dateutil.parser
import babel
from flask import (Flask, render_template,
                   request, Response, flash,
                   redirect, url_for)
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, and_
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
import config
import sys
from models import db, Venue, Artist, Show

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')

migrate = Migrate(app, db, compare_type=True)
db.init_app(app)


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime


@app.route('/')
def index():
    return render_template('pages/home.html')


@app.route('/venues')
def venues():
    current = datetime.now()
    show_venue = []
    list_of_venue = db.session.query(Venue.city, Venue.state).group_by(
        Venue.city, Venue.state).all()
    for items in list_of_venue:
        venue = dict()
        venue["city"] = items.city
        venue["state"] = items.state
        venue_name_and_id = db.session.query(Venue.id, Venue.name).filter(
            and_(Venue.city == items.city, Venue.state == items.state)).all()
        print(venue_name_and_id)
        ans = []
        for i in venue_name_and_id:
            di = {"id": i.id, "name": i.name}
            upcoming_shows = db.session.query(Show).filter(
                Show.venue_id == i.id).filter(
                  Show.start_time > current).count()
            di["num_upcoming_shows"] = upcoming_shows
            ans = sorted(
                ans, key=lambda s: s['num_upcoming_shows'], reverse=True)
            ans.append(di)

        venue["venues"] = ans
        show_venue.append(venue)
    show_venue = sorted(
        show_venue, key=lambda s:
        s['venues'][0]['num_upcoming_shows'], reverse=True)
    print(show_venue)

    return render_template('pages/venues.html', areas=show_venue)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form["search_term"]
    search = "%{}%".format(search_term)
    query = db.session.query(Venue).filter(
        func.lower(Venue.name).like(func.lower(search))).all()
    ans = dict()
    ans['count'] = len(query)
    venue_list = []
    for i in query:
        d = dict()
        d["id"] = i.id
        d["name"] = i.name
        d['num_of_upcoming_shows'] = db.session.query(Show).filter(
            Show.venue_id == i.id).filter(
              Show.start_time > datetime.now()).count()
        venue_list.append(d)
    ans["data"] = venue_list
    print(ans)
    return render_template('pages/search_venues.html', results=ans,
                           search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    current = datetime.now()
    query = Venue.query.filter(Venue.id == venue_id).one_or_none()
    data = dict()
    data["id"] = query.id
    data["name"] = query.name
    data['address'] = query.address
    data['city'] = query.city
    data['state'] = query.state
    data['phone'] = query.phone
    data['website'] = query.website
    data['facebook_link'] = query.facebook_link
    data['image_link'] = query.image_link
    data['seeking_talent'] = query.seeking_talent
    data['seeking_description'] = query.seeking_description

    query2 = db.session.query(Show, Artist).join(
        Artist, Show.artist_id == Artist.id).filter(
        and_(Show.start_time <= current, Show.venue_id == venue_id)).all()
    past_shows = []
    for i in query2:
        past_show = dict()
        past_show["artist_id"] = i[1].id
        past_show["artist_name"] = i[1].name
        past_show["artist_image_link"] = i[1].image_link
        past_show["start_time"] = str(i[0].start_time)
        past_shows.append(past_show)
    data["past_shows"] = past_shows
    query3 = db.session.query(Show, Artist).join(
        Artist, Show.artist_id == Artist.id).filter(
        and_(Show.start_time > current, Show.venue_id == venue_id)).all()
    upcoming_shows = []
    for i in query3:
        upcoming_show = dict()
        upcoming_show["artist_id"] = i[1].id
        upcoming_show["artist_name"] = i[1].name
        upcoming_show["artist_image_link"] = i[1].image_link
        upcoming_show["start_time"] = str(i[0].start_time)
        upcoming_shows.append(upcoming_show)
    data["upcoming_shows"] = upcoming_shows
    print(data)
    return render_template('pages/show_venue.html', venue=data)


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    error = False
    try:
        name = request.form['name']
        city = request.form['city']
        state = request.form['state']
        address = request.form['address']
        phone = request.form['phone']
        genres = request.form.getlist('genres')
        facebook_link = request.form['facebook_link']
        image_link = request.form['image_link']
        website_link = request.form['website_link']
        seeking_talent = True

        if 'seeking_talent' not in request.form:
            seeking_talent = False

        seeking_description = request.form['seeking_description']

        venue = Venue(name=name, city=city, state=state, address=address,
                      phone=phone, image_link=image_link,
                      facebook_link=facebook_link, genres=genres,
                      website=website_link, seeking_talent=seeking_talent,
                      seeking_description=seeking_description)

        db.session.add(venue)
        db.session.commit()

    except:
        db.session.rollback()
        error = True
        print(sys.exc_info())

    finally:
        db.session.close()

    if error:
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be listed.')

    else:
        flash('Venue ' + request.form['name'] + ' was successfully listed!')

    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['POST'])
def delete_venue(venue_id):
    error = False
    try:
        show = Show.query.filter(Show.venue_id == venue_id).delete()
        query = Venue.query.filter(Venue.id == venue_id).delete()
        db.session.commit()
    except:
        error = True
        db.session.rollback()
    finally:
        db.session.close()
    if error:
        flash("There was a problem deleting venue.")
    else:
        flash("Venue deleted succesfully!")
    return render_template('pages/home.html')


@app.route('/artists/<artist_id>', methods=['POST'])
def delete_artist(artist_id):
    error = False
    try:
        show = Show.query.filter(Show.artist_id == artist_id).delete()
        query = Artist.query.filter(Artist.id == artist_id).delete()
        db.session.commit()
    except:
        error = True
        db.session.rollback()
    finally:
        db.session.close()
    if error:
        flash("There was a problem deleting artist.")
    else:
        flash("Artist deleted succesfully!")

    return render_template('pages/home.html')


@app.route('/artists')
def artists():
    ans = Artist.query.order_by(Artist.id).all()
    list_of_artists = []
    for i in ans:
        d = {"id": i.id, "name": i.name}
        list_of_artists.append(d)
    print(list_of_artists)
    data = [{
        "id": 4,
        "name": "Guns N Petals",
    }, {
        "id": 5,
        "name": "Matt Quevedo",
    }, {
        "id": 6,
        "name": "The Wild Sax Band",
    }]
    return render_template('pages/artists.html', artists=list_of_artists)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form["search_term"]
    search = "%{}%".format(search_term)
    query = db.session.query(Artist).filter(
        func.lower(Artist.name).like(func.lower(search))).all()
    ans = dict()
    ans['count'] = len(query)
    artist_list = []
    for i in query:
        d = dict()
        d["id"] = i.id
        d["name"] = i.name
        d['num_of_upcoming_shows'] = db.session.query(Show).filter(
            Show.artist_id == i.id).filter(
              Show.start_time > datetime.now()).count()
        artist_list.append(d)
    ans["data"] = artist_list
    print(ans)
    response = {
        "count": 1,
        "data": [{
            "id": 4,
            "name": "Guns N Petals",
            "num_upcoming_shows": 0,
        }]
    }
    return render_template('pages/search_artists.html',
                           results=ans,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):

    current = datetime.now()
    query = Artist.query.filter(Artist.id == artist_id).one_or_none()
    data = dict()
    data["id"] = query.id
    data["name"] = query.name
    data['city'] = query.city
    data['state'] = query.state
    data['phone'] = query.phone
    data['website'] = query.website
    data['facebook_link'] = query.facebook_link
    data['image_link'] = query.image_link
    data['seeking_venue'] = query.seeking_venue
    data['seeking_description'] = query.seeking_description

    query2 = db.session.query(Show, Venue).join(
        Venue, Show.venue_id == Venue.id).filter(
        and_(Show.start_time <= current, Show.artist_id == artist_id)).all()
    past_shows = []
    for i in query2:
        past_show = dict()
        past_show["venue_id"] = i[1].id
        past_show["venue_name"] = i[1].name
        past_show["venue_image_link"] = i[1].image_link
        past_show["start_time"] = str(i[0].start_time)
        past_shows.append(past_show)
    data["past_shows"] = past_shows
    query3 = db.session.query(Show, Venue).join(
        Venue, Show.venue_id == Venue.id).filter(
        and_(Show.start_time > current, Show.artist_id == artist_id)).all()
    upcoming_shows = []
    for i in query3:
        upcoming_show = dict()
        upcoming_show["venue_id"] = i[1].id
        upcoming_show["venue_name"] = i[1].name
        upcoming_show["venue_image_link"] = i[1].image_link
        upcoming_show["start_time"] = str(i[0].start_time)
        upcoming_shows.append(upcoming_show)
    data["upcoming_shows"] = upcoming_shows
    print(data)
    return render_template('pages/show_artist.html', artist=data)


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist2 = Artist.query.get(artist_id)

    form.name.data = artist2.name
    form.city.data = artist2.city
    form.state.data = artist2.state
    form.phone.data = artist2.phone
    form.genres.data = artist2.genres
    form.facebook_link.data = artist2.facebook_link
    form.website_link.data = artist2.website
    form.image_link.data = artist2.image_link
    form.seeking_venue.data = artist2.seeking_venue
    form.seeking_description.data = artist2.seeking_description

    return render_template('forms/edit_artist.html', form=form, artist=artist2)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    error = False
    query = Artist.query.filter(Artist.id == artist_id).one_or_none()
    try:
        query.name = request.form['name']
        query.city = request.form['city']
        query.state = request.form['state']
        query.phone = request.form['phone']
        query.genres = request.form.getlist('genres')
        query.facebook_link = request.form['facebook_link']
        query.image_link = request.form['image_link']
        query.website_link = request.form['website_link']
        query.seeking_venue = True

        if 'seeking_venue' not in request.form:
            query.seeking_venue = False

        query.seeking_description = request.form['seeking_description']
        db.session.commit()
    except:
        db.session.rollback()
        error = True
        print(sys.exc_info())

    finally:
        db.session.close()

    if error:
        flash('An error occurred. Artist ' +
              request.form['name'] + ' could not be edited.')

    else:
        flash('Artist ' + request.form['name'] + ' was successfully edited!')

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue2 = Venue.query.get(venue_id)

    form.name.data = venue2.name
    form.city.data = venue2.city
    form.state.data = venue2.state
    form.address.data = venue2.address
    form.phone.data = venue2.phone
    form.genres.data = venue2.genres
    form.facebook_link.data = venue2.facebook_link
    form.website_link.data = venue2.website
    form.image_link.data = venue2.image_link
    form.seeking_talent.data = venue2.seeking_talent
    form.seeking_description.data = venue2.seeking_description

    return render_template('forms/edit_venue.html', form=form, venue=venue2)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    error = False
    query = Venue.query.filter(Venue.id == venue_id).one_or_none()
    try:
        query.name = request.form['name']
        query.city = request.form['city']
        query.state = request.form['state']
        query.address = request.form['address']
        query.phone = request.form['phone']
        query.genres = request.form.getlist('genres')
        query.facebook_link = request.form['facebook_link']
        query.image_link = request.form['image_link']
        query.website_link = request.form['website_link']
        query.seeking_talent = True

        if 'seeking_talent' not in request.form:
            query.seeking_talent = False

        query.seeking_description = request.form['seeking_description']
        db.session.commit()
    except:
        db.session.rollback()
        error = True
        print(sys.exc_info())

    finally:
        db.session.close()

    if error:
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be edited.')

    else:
        flash('Venue ' + request.form['name'] + ' was successfully edited!')

    return redirect(url_for('show_venue', venue_id=venue_id))


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    error = False
    try:
        name = request.form['name']
        city = request.form['city']
        state = request.form['state']
        phone = request.form['phone']
        genres = request.form.getlist('genres')
        facebook_link = request.form['facebook_link']
        image_link = request.form['image_link']
        website_link = request.form['website_link']
        seeking_venue = True

        if 'seeking_venue' not in request.form:
            seeking_venue = False

        seeking_description = request.form['seeking_description']

        artist = Artist(name=name, city=city, state=state,
                        phone=phone, image_link=image_link,
                        facebook_link=facebook_link, genres=genres,
                        website=website_link, seeking_venue=seeking_venue,
                        seeking_description=seeking_description)

        db.session.add(artist)
        db.session.commit()
    except:
        db.session.rollback()
        error = True
        print(sys.exc_info())

    finally:
        db.session.close()

    if error:
        flash('An error occurred. Artist ' +
              request.form['name'] + ' could not be listed.')

    else:
        flash('Artist ' + request.form['name'] + ' was successfully listed!')

    return render_template('pages/home.html')


@app.route('/shows')
def shows():
    data = []
    query = db.session.query(Venue, Show, Artist).join(
        Show, Show.venue_id == Venue.id).join(
          Artist, Show.artist_id == Artist.id).all()
    for item in query:
        d = dict()
        d["venue_id"] = item[0].id
        d["venue_name"] = item[0].name
        d["artist_id"] = item[2].id
        d["artist_name"] = item[2].name
        d["artist_image_link"] = item[2].image_link
        d["start_time"] = str(item[1].start_time)
        data.append(d)
    print(data)

    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    error = False
    try:
        artist_id = request.form['artist_id']
        venue_id = request.form['venue_id']
        start_time = request.form['start_time']
        show = Show(artist_id=artist_id, venue_id=venue_id,
                    start_time=start_time)
        db.session.add(show)
        db.session.commit()
    except:
        db.session.rollback()
        print(sys.exc_info())
        error = True
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Show could not be listed.')
    else:
        flash('Show was successfully listed!')
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
                  '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
