import argparse
import asyncore
import email
import re
import smtpd
import time
import urllib2

from Queue import Queue
from threading import Thread

activation_queue = Queue()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--host', help='Set SMTP server listening host',
                        default='0.0.0.0')
    parser.add_argument('-P', '--port', type=int,
                        help='Set SMTP server listening port', default=25)
                        
    args = parser.parse_args()
    
    return args

class PidgeySMTPServer(smtpd.SMTPServer):
  _expr = re.compile('https://club.pokemon.com/us/pokemon-trainer-club/activated/([\w\d]+)')

  def process_message(self, peer, mailfrom, rcpttos, data):
    print 'You\' ve got mail.'
    
    msg = email.message_from_string(data)
    url = None
    for part in msg.walk():
      if part.get_content_type() in ['text/plain', 'text/html']:
        text = part.get_payload(decode=True)
        
        url = self._expr.search(text)
        if url:
          url = url.group(0)
          break
        
    if url != None:
      activation_queue.put(url)
    else:
      print peer, 'is likely a spammer.'

def worker():
  while True:
    url = activation_queue.get(block=True)
    
    try:
      print 'Fetching %s...' % url
      
      response_code = urllib2.urlopen(url).getcode()
      
      if response_code != 200:
        print response_code, ' Error. Adding back to the end of the queue.'
        activation_queue.put(url)
      else:
        print 'One more successfully activated account!'

      time.sleep(1)
    
    except Exception:
      with open('failed.txt', 'a') as f:
        f.write(url + '\n')
    
    activation_queue.task_done()

    
def main():
  args = parse_args()
  
  server = PidgeySMTPServer((args.host, args.port), None)
  print 'Mail server listening on %s:%i...' % (args.host, args.port)
  
  try:
    t = Thread(target=worker)
    t.daemon = True
    t.start()

    asyncore.loop(timeout=1)
  except KeyboardInterrupt:
    server.close()
  
if __name__ == "__main__":
  main()