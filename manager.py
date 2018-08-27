import os
import sys
import subprocess
import logging

from flask_script import Manager, Command
import alembic
import alembic.config, alembic.command
from flask_assets import ManageAssets
from flask_rq2.script import RQManager

from call_server.app import create_app
from call_server.extensions import assets, db, cache, rq
from call_server import political_data
from call_server import sync
from call_server.user import User, USER_ADMIN, USER_ACTIVE

log = logging.getLogger(__name__)

app = create_app()
app.db = db
manager = Manager(app)
manager.add_command('rq', RQManager(app.rq))

alembic_config = alembic.config.Config(os.path.realpath(os.path.dirname(__name__)) + "/alembic.ini")
# let the config override the default db location in production
alembic_config.set_section_option('alembic', 'sqlalchemy.url',
                                  app.config.get('SQLALCHEMY_DATABASE_URI'))

manager.add_command("assets", ManageAssets())


def reset_assets():
    """Reset assets named bundles to {} before running command.
    This command should really be run with TestingConfig context"""
    log.info("resetting assets")
    assets._named_bundles = {}


@manager.command
def runserver(external=None):
    """Run web server for local development and debugging
        pass --external for external routing"""
    if external:
        app.config['SERVER_NAME'] = external
        app.config['STORE_DOMAIN'] = "http://" + external # needs to have scheme, so urlparse is fully absolute
        print "serving from %s" % app.config['SERVER_NAME']
    if app.config['DEBUG'] and not cache.get('political_data:us'):
        political_data.load_data(cache)

    host = (os.environ.get('APP_HOST') or '127.0.0.1')
    
    app.jinja_env.cache = None
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    app.run(debug=True, use_reloader=True, host=host)


@manager.command
def loadpoliticaldata():
    """Load political data into persistent cache"""
    try:
        import gevent.monkey
        gevent.monkey.patch_thread()
    except ImportError:
        log.warning("unable to apply gevent monkey.patch_thread")

    log.info("loading political data")
    with app.app_context():
        n = political_data.load_data(cache)
    log.info("done loading %d objects" % n)

@manager.command
def stop_scheduled_calls(campaign_id, date):
    # unsubscribe outgoing recurring calls created before date
    from datetime import datetime
    from call_server.campaign import Campaign
    from call_server.schedule import ScheduleCall
    before_date = datetime.strptime(date, '%Y-%m-%d')
    campaign = Campaign.query.get(campaign_id)
    scheduled_calls = ScheduleCall.query.filter(campaign==campaign, ScheduleCall.created_at <= before_date).all()
    print 'This will stop all {} scheduled calls for campaign {} created before {}'.format(len(scheduled_calls), campaign.name, date)
    confirm = raw_input('Confirm (Y/N): ')
    if confirm == 'Y':
        for sc in scheduled_calls:
            print "canceling job", sc.job_id
            sc.stop_job()
            db.session.add(sc)
        db.session.commit()
        print "done"
    else:
        print "exit"

@manager.command
def restart_scheduled_calls(campaign_id, accept_all=False):
    # rebind outgoing recurring calls
    from call_server.campaign import Campaign
    from call_server.campaign.constants import STATUS_LIVE
    from call_server.schedule import ScheduleCall

    if campaign_id == 'all':
        campaigns = Campaign.query.filter_by(prompt_schedule=True, status_code=STATUS_LIVE).all()
    else:
        campaigns = [Campaign.query.get(campaign_id),]

    print 'This will restart all subscribed scheduled calls for campaign {}'.format(campaign_id)
    if accept_all:
        confirm = 'Y'
    else:
        confirm = raw_input('Confirm (Y/N): ')
    if confirm == 'Y':
        for campaign in campaigns:
            scheduled_calls = ScheduleCall.query.filter_by(campaign=campaign, subscribed=True).all()
            print 'Scheduled calls for {}: {}'.format(campaign.name, len(scheduled_calls))
            rq_scheduler = rq.get_scheduler()
            for sc in scheduled_calls:
                if not sc.job_id in rq_scheduler:
                    print "resetting job", sc.job_id
                    sc.start_job()
                    db.session.add(sc)
            db.session.commit()
            print "done"
        else:
            print "exit"

@manager.command
def crmsync(campaigns='all'):
    print "Sync to CRM"
    if campaigns == 'all':
        campaigns_list = 'all'
    elif ',' in campaigns:
        campaigns_list = campaigns.split(',')
    else:
        campaigns_list = (campaigns,)
    sync.jobs.sync_campaigns(campaigns_list)

@manager.command
def redis_clear():
    print "This will entirely clear the Redis cache"
    confirm = raw_input('Confirm (Y/N): ')
    if confirm == 'Y':
        with app.app_context():
            cache.cache._client.flushdb()
        print "redis cache cleared"
    else:
        print "exit"


@manager.command
def migrate(direction):
    """Migrate db revision up or down"""
    reset_assets()
    print "migrating %s database at %s" % (direction, app.db.engine.url)
    if direction == "up":
        alembic.command.upgrade(alembic_config, "head")
    elif direction == "down":
        alembic.command.downgrade(alembic_config, "-1")
    else:
        app.logger.error('invalid direction. (up/down)')
        sys.exit(-1)


@manager.command
def migration(message):
    """Create migration file"""
    reset_assets()
    alembic.command.revision(alembic_config, autogenerate=True, message=message)


@manager.command
def stamp(revision):
    """Fake a migration to a particular revision"""
    reset_assets()
    alembic.command.stamp(alembic_config, revision)


@manager.command
def createadminuser(username=None, password=None, email=None):
    """Create a new admin user, get password from user input or directly via command line"""

    # first, check to see if exact user already exists
    if username and email and password:
        if User.query.filter_by(name=username).count() == 1:
            print "username %s already exists" % username
            return True

    # else, getpass from raw input
    from getpass import getpass
    from call_server.user.constants import (USERNAME_LEN_MIN, USERNAME_LEN_MAX,
                                            PASSWORD_LEN_MIN, PASSWORD_LEN_MAX)

    while username is None:
        username = raw_input('Username: ')
        if len(username) < USERNAME_LEN_MIN:
            print "username too short, must be at least", USERNAME_LEN_MIN, "characters"
            username = None
            continue
        if len(username) > USERNAME_LEN_MAX:
            print "username too long, must be less than", USERNAME_LEN_MIN, "characters"
            username = None
            continue
        if User.query.filter_by(name=username).count() > 0:
            print "username already exists"
            username = None
            continue

    while email is None:
        email = raw_input('Email: ')
        # email validation necessary?

    while password is None:
        password = getpass('Password: ')
        password_confirm = getpass('Confirm: ')
        if password != password_confirm:
            print "passwords don't match"
            password = None
            continue
        if len(password) < PASSWORD_LEN_MIN:
            print "password too short, must be at least", PASSWORD_LEN_MIN, "characters"
            password = None
            continue
        if len(password) > PASSWORD_LEN_MAX:
            print "password too long, must be less than", PASSWORD_LEN_MAX, "characters"
            password = None
            continue

    admin = User(name=username,
                 email=email,
                 password=password,
                 role_code=USER_ADMIN,
                 status_code=USER_ACTIVE)
    db.session.add(admin)
    db.session.commit()

    print "created admin user", admin.name


if __name__ == "__main__":
    manager.run()
