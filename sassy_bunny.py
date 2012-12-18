import sublime, sublime_plugin, functools, httplib, urllib, re, threading, websocket, json, Queue, traceback;

class Postman(): 
  host = "localhost:48626"
  ws = None
  retry_count = 0

  def process_msg(self, msg):
    msg_json = json.dumps(msg)

    try:
      self.socket().send(msg_json)

      result = self.socket().recv()

      if result == None:
        print 'Postman connection down'
        self.ws = None
      else:
        self.retry_count = 0

    except:
      print 'No connection'
      self.ws = None

      print self.retry_count

      if (self.retry_count < 2):
        self.retry_count = self.retry_count + 1

        self.process_msg(msg)

  def worker(self):
    while True:
      msg = queue.get()

      # empty the queue if we have processed the last item
      with queue.mutex:
          while (len(queue.queue) > 0):
            queue.queue.pop()

      self.process_msg(msg)

      queue.task_done()

  def start(self):
    thread = threading.Thread(target=self.worker)
    thread.daemon = True
    thread.start()

  def reconnect(self):
    print 'Postman reconnecting'

    self.ws = websocket.create_connection("ws://%s" % self.host)

    if self.ws != None:
      print 'Postman connected' 
      self.socket().send(json.dumps({'event' : 'identify'}))


  def socket(self):
    try:
      if self.ws == None:
        self.reconnect()

    except websocket.WebSocketConnectionClosedException:
      self.reconnect()

    except:
      self.ws = None

    return self.ws

queue = Queue.LifoQueue()
postman = Postman()
postman.start()

class SassBunny(sublime_plugin.EventListener):
  pending = 0
  extension = re.compile(r'.*\.(.*)$', re.IGNORECASE)
  last_folder = re.compile(r'.*\/(.*)$', re.IGNORECASE)
  supported_file_types = ["css", "scss", "sass", "less"]
  current_window = None
  
  def handle_timeout(self, view):
    self.pending = self.pending - 1
    if self.pending == 0:
      # There are no more queued up calls to handleTimeout, so it must have
      # been 1000ms since the last modification
      self.on_idle(view)

  def on_modified(self, view):
    extension = self.file_extension(view.file_name())

    if extension in self.supported_file_types:
      self.post_changes(view)

  def file_extension(self, file_name):
    return re.search(self.extension, file_name).group(1) 

  def project_folder(self, path):
    return re.search(self.last_folder, path).group(1)

  def post_changes(self, view):
    extension = self.file_extension(view.file_name())

    if view.window() == None: 
      self.current_window = view.active_window()
    else:
      self.current_window = view.window()

    text         = view.substr(sublime.Region(0, view.size()))  
    project_name = self.project_folder(self.current_window.folders()[0])
    file_name    = view.file_name() 

    queue.put({
      'event' : "update",
      'data' : {
        'text': text,   
        'project_name': project_name, 
        'file_name': file_name
      }
    })
    
    sublime.status_message("[SASSY BUNNY] %s" % file_name)

      
  def on_save(self, view):
    print 'Saved file'

    self.post_changes(view)

  def on_idle(self, view):
    print "No activity in the past %sms" % self.delay
  
    self.post_changes(view)