from invoke import task
import pypd


@task(name='check-loop')
def check_loop(c):
    # This is how to configure pypd. Meh.
    pypd.api_key = c.pagerduty.api_key
    # TODO:
    # - check PAX public twitter feed
    # - loop
    # - when any public tweet:
    # - send event as below
    # - link to the tweet itself probably
    pypd.Event.create(data={
        'service_key': c.pagerduty.service_key,
        'event_type': 'trigger',
        'description': 'o shit pax tweeted?!',
        'contexts': [
              {
                  'type': 'link',
                  'href': 'http://west.paxsite.com/registration',
                  'text': 'OMGOMGOMG',
              },
        ],
    })
