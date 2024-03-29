#!/usr/bin/python
import cgi
import datetime
import urllib
import webapp2

from google.appengine.ext import db
from google.appengine.api import users


class Greeting(db.Model):
  """Models an individual Guestbook entry with an author, content, and date."""
  author = db.StringProperty()
  content = db.StringProperty(multiline=True)
  date = db.DateTimeProperty(auto_now_add=True)
  
def guestbook_key(guestbook_name=None):
  """Constructs a Datastore key for a Guestbook entity with guestbook_name"""
  return db.Key.from_path('Guestbook', guestbook_name or 'default_guestbook')


class MainPage(webapp2.RequestHandler):
  
  def get(self):
    self.response.out.write('<html><body>')
    guestbook_name=self.request.get('guestbook_name')
    
    # Ancestor Queries, as shown here, are strongly consistent with the High
    # Replication Datastore. Queries that span entity groups are eventually
    # consistent. If we omitted the ancestor from this query there would be a
    # slight chance that the greeting that had just been written would not show
    # up in a query.
    greetings = Greeting.all()
    greetings.ancestor(guestbook_key(guestbook_name))
    greetings.filter("date >",
                     datetime.datetime.now() + datetime.timedelta(days=-7))
    greetings.order("-date")
                            
    for greeting in greetings:
      if greeting.author:
        self.response.out.write(
          '<b>%s</b> wrote:' % greeting.author)
      else:
        self.response.out.write('Some daft old sod wrote:')
      self.response.out.write('<blockquote>%s</blockquote>' %
                              cgi.escape(greeting.content))
                              
    self.response.out.write("""
      <form action="/sign?%s" method="post">
        <div><textarea name="content" rows="3" cols="60"></textarea></div>
        <div><input type="submit" value="Sign Guestbook"></div>
      </form>
      <hr>
      <form>Guestbook name: <input value="%s" name="guestbook_name">
      <input type="submit" value="switch"></form>
      </body>
      </html>""" % (urllib.urlencode({'guestbook_name': guestbook_name}),
                    cgi.escape(guestbook_name)))


class Guestbook(webapp2.RequestHandler):
  
  def post(self):
    # We set the same parent key on the 'Greeting' to ensure each greeting is in
    # the same entity group. Queries across the single entity group will be
    # consistent. However, the write rate to a single entity group should
    # be limited to ~1/second.
    guestbook_name = self.request.get('guestbook_name')
    greeting = Greeting(parent=guestbook_key(guestbook_name))
    
    if users.get_current_user():
      greeting.author = users.get_current_user().nickname()
      
    greeting.content = self.request.get('content')
    # Add the object to the Datastore (or if it exists, update it)
    greeting.put()
    self.redirect('/?' + urllib.urlencode({'guestbook_name': guestbook_name}))
        

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/sign', Guestbook)],
                               debug=True)
