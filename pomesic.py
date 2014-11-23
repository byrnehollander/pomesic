#!/usr/bin/env python
# -*- coding: utf-8 -*-

#tutorial from http://www.dototot.com/how-to-write-a-twitter-bot-with-python-and-tweepy/

import tweepy, time, sys, Queue, pprint, argparse, copy
from linguistics import hard_string_similarity, make_rhyme, make_same_syl_count, normalize_word

class Request:
    ''' class to store the parameters for the poem, and actually construct the poem '''
    def __init__(self, status_object, api):
        self.BAD_QUERY = False
        try:
            print 'here! here!'
            print status_object.text
            parser = argparse.ArgumentParser()
            parser.add_argument('-query', type=str, help='what do you want to search', required=True)
            args = parser.parse_args(split_ignore_quotes(status_object.text)[1:])

            self.sender = status_object.author.screen_name
            self.query = args.query

            # Download the tweets
            print 'searching english tweets...'
            self.searches = {}
            for result in api.search(self.query, lang='en'):
                self.searches[str(result.id)] = result.text.split()

            print '...searched'
            print 'removing tweets that are too long...'
            self.cut()
            print '...removed'

        except:
            self.BAD_QUERY = True

    def cut(self):
        ''' Removes all @xxxx from tweets, and then removes all tweets over 70 characters 
            keeps hashtags '''
        to_delete = set()
        for tweet in self.searches:
            no_ats = []
            for word in self.searches[tweet]:
                if 'http://':
                    no_ats += [word]
            self.searches[tweet] = no_ats
            if len(' '.join(self.searches[tweet])) > 70:
                to_delete.add(tweet)
        for tweet in to_delete:
            del self.searches[tweet]

    def get_poem(self):
        if self.BAD_QUERY:
            return '''BAD QUERY - request must be in the format: \n (AT)PomeSic -query "query", where "query" must be in quotes'''

        pairs = []
        for one in self.searches:
            for two in self.searches:
                if one != two:
                    if self.searches[one] != self.searches[two]:
                        pairs.append((self.searches[one], self.searches[two]))
        scores = [None] * len(pairs)
        for i in range(len(pairs)):
            scores[i] = (pairs[i], hard_string_similarity(pairs[i][0], pairs[i][1]))
        scores.sort(key = lambda x: x[1], reverse = True)

        for i in range(len(scores)):
            tweet1 = scores[i][0][0]
            tweet2 = scores[i][0][1]

            print 'trying to compose a poem from:'
            print '\ttweet1: ' + ' '.join(tweet1)
            print '\ttweet2: ' + ' '.join(tweet2)

            normalization_dict = {}

            for i in range(len(tweet1)):
                normalized = normalize_word(tweet1[i])
                normalization_dict[tweet1[i]] = normalized
                tweet1[i] = normalized

            for i in range(len(tweet2)):
                normalized = normalize_word(tweet2[i])
                normalization_dict[tweet2[i]] = normalized
                tweet2[i] = normalized

            reverse_normalization = dict((v,k) for k, v in normalization_dict.iteritems())

            # Normalization may have added additional words
            tweet1 = ' '.join(tweet1).split()
            tweet2 = ' '.join(tweet2).split()

            print 'post normalization:'
            print '\ttweet1: ' + ' '.join(tweet1)
            print '\ttweet2: ' + ' '.join(tweet2)

            try:
                print 'before rhyming changes:'
                print '\ttweet1: ' + ' '.join(tweet1)
                print '\ttweet2: ' + ' '.join(tweet2)

                tweet1, tweet2 = make_rhyme(tweet1, tweet2)

                print 'after rhyming changes, before syllable changes:'
                print '\ttweet1: ' + ' '.join(tweet1)
                print '\ttweet2: ' + ' '.join(tweet2)

                tweet1, tweet2 = make_same_syl_count(tweet1, tweet2)

                print 'after syllable:'
                print '\ttweet1: ' + ' '.join(tweet1)
                print '\ttweet2: ' + ' '.join(tweet2)

                for i in range(len(tweet1)):
                    if tweet1[i] in reverse_normalization:
                        tweet1[i] = reverse_normalization[tweet1[i]]
                for i in range(len(tweet2)):
                    if tweet2[i] in reverse_normalization:
                        tweet2[i] = reverse_normalization[tweet2[i]]

                print 'after de-normalization:'
                print '\ttweet1: ' + ' '.join(tweet1)
                print '\ttweet2: ' + ' '.join(tweet2)

                return '@' + self.sender + '\n' + ' '.join(tweet1) + '\n' + ' '.join(tweet2)

            except Exception, e:
                print 'exception:', str(e)
                print 'moving to next pair of tweets'

    # String representation of the instance variables relevant to the query
    def __repr__(self):
        return '@' + self.sender + ' query: ' + self.query + '\nlines: ' + self.lines + '\nscheme: ' + self.scheme + '\nflex: ' + str(self.flex)

def split_ignore_quotes(text):
    ''' splits on spaces except treats things in quotes as one item - used to allow for multiple word queries in quotes
        returns None if there are no quotes, in which case the program should inform the user '''
    result = text.split('''"''')
    if len(result) == 1: return None
    result = result[0].split() + [result[1]] + result[2].split()
    return result
    
def main():
    CONSUMER_KEY = 'p9OxRifkkzauMPUuh9CogQDu3'
    CONSUMER_SECRET = 'REDACTED'
    ACCESS_TOKEN = '2826481127-MxZGiWMGBoWhkC9acHFKPBbbm4aFMczaeWM6ctU'
    ACCESS_SECRET = 'REDACTED'
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)
    api = tweepy.API(auth) 
    # Open the file containing the tweets already processed
    try:
        seen_file = open('SEEN', 'r')
    except:
        open('SEEN','w').close()
        seen_file = open('SEEN', 'r')
    # Store it in processed_tweets
    processed_tweets = [line.strip() for line in seen_file]
    seen_file.close()

    q = Queue.Queue() # tweets that need to be processed
    done = set()      # tweets that have been processed, must be added to seen_file

    print 'checking for queries...'
    mentions = api.mentions_timeline(count=1) # get tweets to process
    # If we haven't processed / responded to them yet, add it to the queue
    for mention in mentions:
        if not str(mention.id) in processed_tweets and mention != None:
            q.put(mention)

    if not q.empty():
        print '...found some'
    else:
        print '...no new tweets to reply to'

    # Process q
    while not q.empty():
        m = q.get()
        r = Request(m, api)
        print 'composing poem...'
        poem = r.get_poem()
        print '...poem composed:'
        print poem
        print 'tweeting back...'
        api.update_status(poem) # will need to be changed to get_poem or whatever
        print '...done'
        done.add(m.id)
    # Update the seen file
    seen_file = open('SEEN', 'a')
    for processed in done:
        seen_file.write(str(processed) + '\n')

    seen_file.close()

if __name__ == '__main__':
    main()
