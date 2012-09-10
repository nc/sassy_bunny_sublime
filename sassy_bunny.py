import sublime, sublime_plugin, functools, re, threading, websocket, json;

class ThreadedFilePoster(threading.Thread):
  host = "localhost:8080"

  def __init__(self, text, project_name, file_name):
    self.text         = text
    self.file_name    = file_name
    self.project_name = project_name 

    threading.Thread.__init__(self)

  def run(self):
    print "Posting file "

    ws = websocket.create_connection("ws://%s" % self.host)

    msg = json.dumps({
      'event' : "update",
      'data' : {
        'text': self.text, 
        'project_name': self.project_name, 
        'file_name': self.file_name
      }
    })

    print "Sending %s" % msg

    ws.send(msg)
    result = json.loads(ws.recv())

    print "Result %s" % result['event']

    ws.close()

    print 'Posted file'

class SassBunny(sublime_plugin.EventListener):
  pending = 0
  extension = re.compile(r'.*\.(.*)$', re.IGNORECASE)
  last_folder = re.compile(r'.*\/(.*)$', re.IGNORECASE)
  supported_file_types = ["css", "scss", "sass", "less"]
  delay = 250
  
  def handle_timeout(self, view):
    self.pending = self.pending - 1
    if self.pending == 0:
      # There are no more queued up calls to handleTimeout, so it must have
      # been 1000ms since the last modification
      self.on_idle(view)

  def on_modified(self, view):
    self.pending = self.pending + 1
    # Ask for handleTimeout to be called in 1000ms
    sublime.set_timeout(functools.partial(self.handle_timeout, view), self.delay)

  def file_extension(self, file_name):
    return re.search(self.extension, file_name).group(1) 

  def project_folder(self, path):
    return re.search(self.last_folder, path).group(1)

  def post_changes(self, view):
    extension = self.file_extension(view.file_name())

    if extension in self.supported_file_types:
      text         = view.substr(sublime.Region(0, view.size()))  
      project_name = self.project_folder(view.window().folders()[0])
      file_name    = view.file_name()

      thread = ThreadedFilePoster(text, project_name, file_name)
      thread.start()

  def on_save(self, view):
    print 'Saved file'

    self.post_changes(view)

  def on_idle(self, view):
    print "No activity in the past %sms" % self.delay
  
    self.post_changes(view)

  def on_delete(self, view):
    print 'TODO: Sublime Text 2 doesn\'t have an API for deleted files, implement by storing files / dir tree and tracking missing files every so often'

    self.delete_file(view)