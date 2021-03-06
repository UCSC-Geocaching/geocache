"""
This file defines actions, i.e. functions the URLs are mapped into
The @action(path) decorator exposed the function at URL:

    http://127.0.0.1:8000/{app_name}/{path}

If app_name == '_default' then simply

    http://127.0.0.1:8000/{path}

If path == 'index' it can be omitted:

    http://127.0.0.1:8000/

The path follows the bottlepy syntax.

@action.uses('generic.html')  indicates that the action uses the generic.html template
@action.uses(session)         indicates that the action uses the session
@action.uses(db)              indicates that the action uses the db
@action.uses(T)               indicates that the action uses the i18n & pluralization
@action.uses(auth.user)       indicates that the action requires a logged in user
@action.uses(auth)            indicates that the action requires the auth object

session, db, T, auth, and tempates are examples of Fixtures.
Warning: Fixtures MUST be declared with @action.uses({fixtures}) else your app will result in undefined behavior
"""

import json
from unittest import result
from webbrowser import get
from requests import delete
from py4web import action, request, abort, redirect, URL
from yatl.helpers import A
from .common import (
    db,
    session,
    T,
    cache,
    auth,
    logger,
    authenticated,
    unauthenticated,
    flash,
)
from py4web.utils.url_signer import URLSigner
from .models import get_user_email

from datetime import date, datetime, timedelta


url_signer = URLSigner(session)

# Login Controllers--------------------------------------------------
@action("login")
@action("register")
@action("request_reset_password")
@action("index")
@action.uses("index.html", auth, url_signer)
def index():
    if auth.is_logged_in:
        redirect(URL("map"))
    return {
        "base_url": URL(),
        "add_user_url": URL("add_user", signer=url_signer),
    }


@action("custom_auth/reset_password")
@action.uses("reset_pw.html", auth)
def resetpw():
    return {"base_url": URL()}


# Profile Page Controllers-------------------------------------------
@action("profile", method="GET")
@action.uses("profile.html", db, auth.user)
def profile():
    return dict(
        load_profile_url=URL("load_profile_details"),
        load_activity_url=URL("load_activity"),
        load_hidden_caches_url=URL("load_hidden_caches"),
        go_to_pending_url=URL("pending", signer=url_signer),
    )


@action("load_profile_details", method="GET")
@action.uses(db, auth.user)
def load_profile_details():
    user = auth.get_user()
    profile = db(db.users.user_id == user["id"]).select().first()
    # Attach admin status
    status = db(db.admins.user == profile["id"]).select().first()
    if status == None:
        status = False
    else:
        status = True
    profile["admin"] = status
    return dict(profile=profile)


@action("load_activity", method="GET")
@action.uses(db, auth.user)
def load_activity():
    activities = []
    # First user is from auth_user table
    user = auth.get_user()
    assert user is not None
    # This user is from Users table
    user = db(db.users.user_id == user["id"]).select().first()
    assert user is not None

    activities = db(db.logs.logger == user["id"]).select().as_list()
    # Attach the cache names and hrefs
    for activity in activities:
        cache = db.caches[activity["cache"]]
        activity["cache_name"] = cache.cache_name
        activity["href"] = URL("cache_info", cache["id"])
    return dict(activities=activities)


@action("load_hidden_caches", method="GET")
@action.uses(db, auth.user)
def load_hidden_caches():
    caches = []
    # First user is from auth_user table
    user = auth.get_user()
    assert user is not None
    # This user is from Users table
    user = db(db.users.user_id == user["id"]).select().first()
    assert user is not None

    # Get caches that are by the user and valid
    caches = (
        db((db.caches.author == user["id"]) & (db.caches.valid == True))
        .select()
        .as_list()
    )
    # Attach hrefs to caches
    for cache in caches:
        cache["href"] = URL("cache_info", cache["id"])
    return dict(caches=caches)


# Map Page Controllers-----------------------------------------------
@action("map")
@action.uses("map.html", db, auth, auth.user, url_signer)
def map():
    return dict(
        loadGeoCachesURL=URL("loadGeoCaches", signer=url_signer),
        searchURL=URL("search", signer=url_signer),
        generateCacheURL=URL("generateCacheURL", signer=url_signer),
    )


@action("loadGeoCaches")
@action.uses(db)
def getCaches():
    rows = db(db.caches).select().as_list()
    return dict(caches=rows)


@action("search")
@action.uses()
def search():
    rows = db(db.caches).select().as_list()
    return dict(caches=rows)


@action("generateCacheURL")
@action.uses(db, url_signer, url_signer.verify())
def generateCacheURL():
    cache_id = int(request.params.get("cache_id"))
    return dict(url=URL("cache_info", cache_id, signer=url_signer))


# Bookmarks Page Controllers-----------------------------------------
@action("bookmarks", method="GET")
@action.uses("bookmarks.html", db, auth.user, url_signer)
def bookmarks():
    return dict(get_bookmarks_url=URL("get_bookmarks", signer=url_signer))


@action("get_bookmarks", method="GET")
@action.uses(db, auth.user, url_signer.verify())
def get_bookmarks():
    # First user is from auth_user table
    bookmarks = []
    user = auth.get_user()
    assert user is not None
    # This user is from Users table
    user = db(db.users.user_id == user["id"]).select().first()
    assert user is not None
    tmp_bookmarks = db(db.bookmarks.user == user["id"]).select().as_list()
    for bookmark in tmp_bookmarks:
        cache = db.caches[bookmark["cache"]]
        cache["href"] = URL("cache_info", cache.id, signer=url_signer)
        bookmarks.append(cache)

    return dict(bookmarks=bookmarks)


# Cache Info Page Controllers----------------------------------------
@action("cache_info/<cache_id:int>")
@action.uses("cache_info.html", db, auth.user, url_signer)
def cache_info(cache_id=None):
    # Don't show invalid caches
    valid = db.caches[cache_id].valid
    if not valid:
        redirect(URL("map"))

    return dict(
        getCacheURL=URL("getCache", cache_id, signer=url_signer),
        getUserURL=URL("getUser", signer=url_signer),
        setBookmarkedURL=URL("setBookmarked", cache_id, signer=url_signer),
        getBookmarkedURL=URL("getBookmarked", cache_id, signer=url_signer),
        logCacheURL=URL("logCache", cache_id, signer=url_signer),
        getLogsURL=URL("getLogs", cache_id),
        checkTimerURL=URL("checkTimer", cache_id, signer=url_signer),
    )


@action("getCache/<cache_id:int>")
@action.uses(db)
def getCache(cache_id=None):
    cache = db(db.caches._id == cache_id).select().first()
    assert cache is not None
    user = db.users[cache["author"]]
    assert user is not None
    # Attach name to cache
    cache["first_name"] = user["first_name"]
    cache["last_name"] = user["last_name"]
    return dict(cache=cache)


@action("setBookmarked/<cache_id:int>", method="PUT")
@action.uses(db, auth, url_signer.verify())
def setBookmarked(cache_id=None):
    # First user is from auth_user table
    bookmarked = False
    user = auth.get_user()
    assert user is not None
    # This user is from Users table
    user = db(db.users.user_id == user["id"]).select().first()
    assert user is not None
    assert cache_id is not None
    bookmark = (
        db((db.bookmarks.user == user["id"]) & (db.bookmarks.cache == cache_id))
        .select()
        .first()
    )
    if bookmark is None:
        db.bookmarks.update_or_insert(user=user["id"], cache=cache_id)
        bookmarked = True
    else:
        del db.bookmarks[bookmark["id"]]
        bookmarked = False
    return dict(bookmarked=bookmarked)


@action("getBookmarked/<cache_id:int>", method="GET")
@action.uses(db, auth, url_signer.verify())
def getBookmarked(cache_id=None):
    # First user is from auth_user table
    user = auth.get_user()
    assert user is not None
    # This user is from Users table
    user = db(db.users.user_id == user["id"]).select().first()
    assert user is not None
    assert cache_id is not None
    bookmark = (
        db((db.bookmarks.user == user["id"]) & (db.bookmarks.cache == cache_id))
        .select()
        .first()
    )
    if bookmark is None:
        bookmarked = False
    else:
        bookmarked = True
    return dict(bookmarked=bookmarked)


@action("logCache/<cache_id:int>", method="PUT")
@action.uses(db, auth.user, url_signer.verify())
def logCache(cache_id=None):
    # First user is from auth_user table
    auth_user_data = auth.get_user()
    assert auth_user_data is not None
    # This user is from Users table
    user = db(db.users.user_id == auth_user_data["id"]).select().first()
    discover_date = datetime.now()
    assert user is not None
    assert cache_id is not None
    assert discover_date is not None

    # Check the timer before logging
    newest_log = (
        db((db.logs.cache == cache_id) & (db.logs.logger == user["id"])).select().last()
    )
    result = checkLogTimer(newest_log)
    if result["disabled"]:
        return dict(log=None)

    # Add the log
    log_id = db.logs.insert(logger=user.id, cache=cache_id, discover_date=discover_date)
    log = db.logs[log_id]
    log["first_name"] = auth_user_data["first_name"]
    log["last_name"] = auth_user_data["last_name"]

    return dict(log=log)


@action("getLogs/<cache_id:int>", method="GET")
@action.uses(db, auth.user)
def getLogs(cache_id=None):
    logs = db(db.logs.cache == cache_id).select().as_list()
    # Add name attributes to logs
    for log in logs:
        user = db(db.users.id == log["logger"]).select().first()
        auth_user_data = db(db.auth_user.id == user["user_id"]).select().first()
        log["first_name"] = auth_user_data["first_name"]
        log["last_name"] = auth_user_data["last_name"]
    # Figure out how to query only last 10 logs.
    # logs = db(db.executesql('SELECT * FROM logs order by id desc limit 10;'))
    return dict(logs=logs)


@action("checkTimer/<cache_id:int>", method="GET")
@action.uses(db, auth.user, url_signer.verify())
def checkTimer(cache_id=None):
    # First user is from auth_user table
    auth_user_data = auth.get_user()
    assert auth_user_data is not None
    # This user is from Users table
    user = db(db.users.user_id == auth_user_data["id"]).select().first()
    assert user is not None
    newest_log = (
        db((db.logs.cache == cache_id) & (db.logs.logger == user["id"])).select().last()
    )
    result = checkLogTimer(newest_log)
    return dict(
        disabled=result["disabled"],
        refresh_time=result["refresh_time"],
    )


# Suggest Page Controllers-------------------------------------------
@action("suggest")
@action.uses("suggest.html", db, auth.user, url_signer)
def suggest():
    return dict(
        addCacheURL=URL("addCache", signer=url_signer),
        loadGeoCachesURL=URL("loadGeoCaches", signer=url_signer),
    )


@action("addCache", method="POST")
@action.uses(db, auth, url_signer.verify())
def addCache():
    # First user is from auth_user table
    auth_user_data = auth.get_user()
    assert auth_user_data is not None
    # This user is from Users table
    user = db(db.users.user_id == auth_user_data["id"]).select().first()
    assert user is not None

    db.caches.insert(
        cache_name=request.json.get("cache_name"),
        lat=request.json.get("lat"),
        long=request.json.get("long"),
        description=request.json.get("description"),
        hint=request.json.get("hint"),
        author=user["id"],
        creation_date=datetime.now(),
        difficulty=request.json.get("difficulty"),
        terrain=request.json.get("terrain"),
        size=request.json.get("size"),
        valid=False,
    )
    return "OK"


@action("pending", method="GET")
@action.uses("pending.html", db, auth.user, url_signer)
def pending():
    # First user is from auth_user table
    auth_user_data = auth.get_user()
    assert auth_user_data is not None
    # This user is from Users table
    user = db(db.users.user_id == auth_user_data["id"]).select().first()
    assert user is not None

    check = db(db.admins.user == user["id"]).select().first()

    if check is None:  # if user is not an admin
        redirect(URL("map"))
    return dict(
        loadGeoCachesURL=URL("loadGeoCaches", signer=url_signer),
        deleteCacheURL=URL("deleteCache", signer=url_signer),
        approveCacheURL=URL("approveCache", signer=url_signer),
        getUserURL=URL("getUser", signer=url_signer),
    )


@action("deleteCache", method="POST")
@action.uses(db, auth.user, url_signer.verify())
def deleteCache():
    id = request.json.get("id")
    assert id is not None
    db(db.caches.id == id).delete()
    return dict()


@action("approveCache", method="POST")
@action.uses(db, auth.user, url_signer.verify())
def approveCache():
    id = request.json.get("id")
    assert id is not None
    # print(db(db.caches.id == id).select().first())
    db(db.caches.id == id).update(valid=True)  # update cache submitted
    return dict()


# Miscellaneous Controllers------------------------------------------
@action("add_user", method="POST")
@action.uses(db, auth, url_signer.verify())
def register_user():
    user = auth.get_user()
    db.users.insert(
        user_id=user["id"],
        first_name=request.json.get("first_name"),
        last_name=request.json.get("last_name"),
        user_email=request.json.get("email"),
    )


@action("getUser", method="POST")
@action.uses(db)
def getUser():
    id = request.json.get("id")
    user = db(db.users._id == id).select().first()
    return dict(user=user)


# TODO: MAKE SURE TO REMOVE FOR PRODUCTION
@action("setup")
@action.uses(db, auth, auth.user)
def setup():
    auth_user = auth.get_user()
    user = db(db.users.user_id == auth_user["id"]).select().first()
    db.caches.insert(
        cache_name="Arboretum",
        lat=36.98267070650899,
        long=-122.05985900885949,
        description="The UCSC Arboretum is a beautiful part of campus full of various trees and wildlife. Even if you can't find the cache, come for the smells alone.",
        hint="Check under this tree from down under!",
        author=user["id"],
        creation_date=datetime.now(),
        difficulty=4,
        terrain=3,
        size=2,
        valid=True,
    )
    db.caches.insert(
        cache_name="Quarry Amphitheater",
        lat=36.9986320770141,
        long=-122.05648938884585,
        description="The Quarry Ampitheater is a great place to watch some great concerts. Check the UCSC website to see what shows are coming up!",
        hint="I guarantee you've never seen a show like this B4",
        author=user["id"],
        creation_date=datetime.now(),
        difficulty=2,
        terrain=1,
        size=1,
        valid=True,
    )
    db.caches.insert(
        cache_name="Jack Baskin",
        lat=37.0005353033127,
        long=-122.06380507461215,
        description="Jack Baskin is home to many of the engineering classes here at UCSC. The buildings are some of the most modern looking buildings on campus.",
        hint="These buildings are the CORNERstone of the engineering classes.",
        author=user["id"],
        creation_date=datetime.now(),
        difficulty=3,
        terrain=3,
        size=2,
        valid=True,
    )
    db.caches.insert(
        cache_name="Porter",
        lat=36.99473025211556,
        long=-122.06554686691216,
        description="Porter Quad is often considered the noisest place on campus at 3am. With two tall towers full of party-loving students, how could it not be?",
        hint="If you can't find it, break a leg and try again.",
        author=user["id"],
        creation_date=datetime.now(),
        difficulty=2,
        terrain=1,
        size=5,
        valid=True,
    )
    db.caches.insert(
        cache_name="East Remote",
        lat=36.99056080000000,
        long=-122.05252790000000,
        description="If you're living off campus, this parking lot is your best friend. You can catch the bus here to the rest of your classes.",
        hint="If you climb over me, you'll be partying with the cows!",
        author=user["id"],
        creation_date=datetime.now(),
        difficulty=5,
        terrain=1,
        size=3,
        valid=True,
    )
    redirect(URL("index"))


# TODO: MAKE SURE TO REMOVE FOR PRODUCTION
@action("clear_db")
@action.uses(db, auth)
def clear_db():
    db.auth_user.truncate()
    db.users.truncate()
    db.caches.truncate()
    db.logs.truncate()
    db.bookmarks.truncate()
    redirect(URL("index"))


# TODO: MAKE SURE TO REMOVE FOR PRODUCTION
@action("make_admin")
@action.uses(db, auth, auth.user)
def make_admin():
    auth_user = auth.get_user()
    user = db(db.users.user_id == auth_user["id"]).select().first()
    db.admins.insert(
        user=user["id"],
    )
    redirect(URL("index"))


# Helper Functions---------------------------------------------------
def checkLogTimer(newest_log=None):
    # No log at this cache for this user
    if newest_log is None:
        return dict(disabled=False, refresh_time=datetime.now())
    # Check if the most recent log is old enough
    log_time = newest_log["discover_date"]
    refresh_time = log_time + timedelta(minutes=15)
    time_now = datetime.now()
    # Now is past the refresh time limit
    if time_now > refresh_time:
        return dict(disabled=False, refresh_time=refresh_time)
    # Is hasn't been enough time yet
    else:
        return dict(disabled=True, refresh_time=refresh_time)