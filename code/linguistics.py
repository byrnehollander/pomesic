#!/usr/bin/env python
# -*- coding: utf-8 -*-

''' This file is for interacting with nltk, computing semantic similarity measures of sentences, and everything linguistically related '''

import enchant
import nltk
from nltk.corpus import cmudict, wordnet
import gensim
from other import int2word
from nltk.metrics import edit_distance

# ------------------------------------------------- RHYME MANIPULATION -----------------------------------------------------
''' CONSIDER CHANGING HOW RHYMING WORKS, SO THAT YOU GET THE MOST SIMILAR WORDS TO BOTH, AND NAVIGATE DOWN IN THE SIMILAIRTY
    PATH UNTIL YOU HAVE A WORD THAT RHYMES '''

def is_rhyming_pair(phon1, phon2):
    vowel_idx = 1
    while not phon1[-vowel_idx][-1].isdigit():
        vowel_idx += 1
    return phon1[-vowel_idx:] == phon2[-vowel_idx:]

def change_both(word1, word2):
    syns_1 = get_synonyms(word1)
    syns_2 = get_synonyms(word2)
    rhyming_pairs = []
    for syn_1 in syns_1:
        for syn_2 in syns_2:
            if is_rhyming_pair(get_phonemes(syn_1), get_phonemes(syn_2)):
                rhyming_pairs.append((syn_1, syn_2))
    rhyming_pairs = [(pair, (TWITTER_MODEL.similarity(pair[0], word1) + TWITTER_MODEL.similarity(pair[1], word2)) / 2.0) for pair in rhyming_pairs]
    rhyming_pairs.sort(key=lambda x: x[1], reverse = True)
    return rhyming_pairs[0]

def get_rhymes(word):
    ''' Returns a list of words in the twitter corpus rhyming with word "word"
    Two words rhyme when all phonemes, beginning with the last vowel in the word, until the end of the word, are the same
    Idea found here: http://kashthealien.wordpress.com/2013/06/15/213/ - Modified to only search words in twitter corpus '''
    pron_of_word = get_phonemes(word)
    rhymes = set()
    for opt in TWITTER_MODEL.vocab.keys():
        if opt in PHONE_DICT and opt != word:
            pron_of_opt = get_phonemes(opt)
            if is_rhyming_pair(pron_of_word, pron_of_opt):
                rhymes.add(opt)
    return rhymes

def best_rhyme(start, goal):
    ''' Calls get_rhymes(start) and ranks the rhymes by similarity to goal '''
    result = [(goal, word_similarity(goal, start)) for goal in get_rhymes(start)]
    result.sort(reverse=True, key = lambda x: x[1])
    return result[0]

def make_rhyme(tweet1, tweet2):
    ''' Tries to make tweet1 rhyme with tweet2, then tweet2 with tweet1, then both, choses the least 'costly' option
    fails if it is impossible '''
    try: # evaluate the cost of making tweet1 rhyme with tweet2
        chng_second = best_rhyme(tweet1[-1], tweet2[-1]) 
    except: # will fail if there is no rhyming word
        chng_second = (None, 0)
    try: # evaluate the cost of making tweet2 rhyme with tweet1
        chng_first = best_rhyme(tweet2[-1], tweet1[-1])
    except: # if there is no rhyming word, make the cost very high
        chng_first = (None, 0)
    try :
        chng_both = change_both(tweet1[-1], tweet2[-1])
    except:
        chng_both = (None, 0)
    # If changing the first is better, do it.
    if chng_first[1] > chng_second[1]:
        if chng_both[1] > chng_first[1]:
            tweet1[-1] = chng_both[0][0]
            tweet2[-1] = chng_both[0][1]
        else:
            tweet1[-1] = chng_first[0]
    else:
        if chng_both[1] > chng_second[1]:
            tweet1[-1] = chng_both[0][0]
            tweet2[-1] = chng_both[0][1]
        else:
            tweet2[-1] = chng_second[0]
    return (tweet1, tweet2)

# ----------------------------------------------- SYLLABLE MANIPULATION ----------------------------------------------------
def synonym_with_syllables(word, n_syl):
    ''' synonym_with_syllables(word, n_syl), which returns a tuple in the format (alternative, score), that contains
    the semantically closest alternative to word with number of syllables n_syl and the score (semantic distance between them)
    if the word is 1 syllable, it returns (None, float('inf'))
    CHOICES: use wordnet synonyms, or rank similarity using gensim and select first one to have correct number of syllables '''
    if n_syl == 0:
        return (None, 0)
    # print '62,',word
    options = get_synonyms(word)
    works = filter(lambda x: nsyl_word(x) == n_syl, options)
    result = [(opt, word_similarity(word, opt)) for opt in works]
    result.sort(reverse=True, key = lambda x: x[1])
    try:
        return result[0]
    except:
        return (None, float('inf'))

class Syllable_Manipulator:
    ''' changed tweet accessible as sm.sent, score of change accessible as sm.final_score '''
    def __init__(self):
        self.sent = None
        # Keeps track of words seen in self.sent to the result of calling synonym_with_syllables to avoid re-computing
        self.easy_reductions = {}   # maps word to syllable count of word - 1
        self.easy_increases = {}    # maps word to syllable count of word + 1
        # Keeps track of words to syllable counts to avoid recounting
        self.easy_syllables = {}
        # How many syllables I have
        self.current = None
        # How many syllables I want
        self.desired = None
        # To avoid returning anything
        self.final_score = 0

    def reset(self, list_of_words, final_nsyl):
        ''' change the current sentence and goal of the Syllable_Manipulator 
            preferable to reinitializing it because easy_increases/reductions are cached '''
        self.sent = list_of_words
        self.current = self.total_syllable_count()
        self.desired = final_nsyl
        self.final_score = 0

    def progress(self):
        ''' add or subtract a syllable, depending on which is necessary '''
        if self.current < self.desired:
            self.add_syllable()
        elif self.current > self.desired:
            self.subtract_syllable()

    def add_syllable(self):
        ''' consider replacing each word with a word that is one more syllable, perform the least 
            "costly" replacement defined by semantic distance 
            CHOICE: what do i do when all words are one syllable? right now delete first, change to
            delete "unimportant" one '''
        for word in self.sent[:-1]:
            if not word in self.easy_increases:
                self.easy_increases[word] = synonym_with_syllables(word, self.syllable_count_of_word(word) + 1)
        best_increase = None
        best_score = 0
        for word in self.sent[:-1]:
            if self.easy_increases[word][1] > best_score:
                best_increase = word
                best_score = self.easy_increases[word][1]
        if best_increase != None and self.easy_increases[best_increase][0] != None:
            # print '113, sub:', best_increase, 'for', self.easy_increases[best_increase][0]
            self.sent[self.sent.index(best_increase)] = self.easy_increases[best_increase][0]
            self.final_score += 1 - self.easy_increases[best_increase][1]
        else:
            self.final_score = float('inf')

    def subtract_syllable(self):
        ''' consider replacing each word with a word that is one less syllable, perform the least 
            "costly" replacement defined by semantic distance 
            CHOICE: what do i do when all words are one syllable? right now delete first, change to
            delete "unimportant" one '''
        for word in self.sent[:-1]:
            if not word in self.easy_reductions:
                self.easy_reductions[word] = synonym_with_syllables(word, self.syllable_count_of_word(word) - 1)
        best_reduction = None
        best_score = 0
        for word in self.sent[:-1]:
            if self.easy_reductions[word][1] > best_score:
                best_reduction = word
                best_score = self.easy_reductions[word][1]
        if best_reduction != None and self.easy_reductions[best_reduction][0] != None:
            # print '129, sub:', best_reduction, 'for', self.easy_reductions[best_reduction][0]
            self.sent[self.sent.index(best_reduction)] = self.easy_reductions[best_reduction][0]
            self.final_score += 1 - self.easy_reductions[best_reduction][1]
        else:
            self.final_score = 10000
            self.sent = self.sent[1:]

    def syllable_count_of_word(self, word):
        ''' use cached syllable counts or start from scratch to compute number of syllables in "word" '''
        if word in self.easy_syllables:
            return self.easy_syllables[w]
        try:
            return nsyl_word(word)
        except:
            return 1

    def total_syllable_count(self):
        '''' use cached syllable count or recounting syllables to determine the syllables in self.sent '''
        total = 0
        for word in self.sent:
            total += self.syllable_count_of_word(word)
        self.current = total
        return total

def nsyl_word(word):
    ''' found here:http://stackoverflow.com/questions/405161/detecting-syllables-in-a-word '''
    tot = 0
    for x in get_phonemes(word.lower()):
        if x[-1].isdigit():
            tot += 1
    return tot

def nsyl_sent(sent):
    ''' calls nsyl_word on every word in sent '''
    total = 0
    for word in sent:
        try:
            total += nsyl_word(word)
        except:
            total += 1
    return total

def make_same_syl_count(tweet1, tweet2):
    ''' abstracts the usage of Syllable_Manipulator class – continues to add or subtract a syllable
        until they are the same number of syllables '''
    sm1 = Syllable_Manipulator()
    sm1.reset(tweet1, nsyl_sent(tweet2))
    sm2 = Syllable_Manipulator()
    sm2.reset(tweet2, nsyl_sent(tweet1))
    while sm1.total_syllable_count() != sm2.total_syllable_count():
        # print sm1.sent
        # print sm2.sent
        prev_s1 = sm1.sent
        prev_s2 = sm2.sent
        sm1.progress()
        sm2.progress()
        # print sm1.final_score, sm2.final_score
        if sm1.final_score < sm2.final_score:
            sm1.reset(sm1.sent, nsyl_sent(prev_s2))
            sm2.reset(prev_s2, sm1.current)
        else:
            sm1.reset(prev_s1, sm2.current)
            sm2.reset(sm2.sent, nsyl_sent(prev_s1))
        # print sm1.total_syllable_count()
        # print sm2.total_syllable_count()
    return sm1.sent, sm2.sent

# ------------------------------------------------ TWEET NORMALIZATION -----------------------------------------------------
def normalize_word(word):
    ''' if it's a hashtag, get rid of the hashtag and normalize it
        if it's a number, use a function found online to write out the number for phonetic ease
        if it's in the dictionary, just return it
        if it's in the twitter corpus, find a "normal" word that is contextually similar to it
        if it's not in any of the above, spell correct it
        if it can't be spell corrected, return it un-normalized '''
    if word.isdigit():
        return int2word(int(word))
    word = word.lower()
    if word in PHONE_DICT:
        # print 'in phone dict'
        return word
    try:
        normalized_alternatives = []
        for option in TWITTER_MODEL.most_similar(word):
            if option[0] in PHONE_DICT:
                normalized_alternatives.add(option[0])
        ranked_alts = sorted([(alt, edit_distance(word,alt)) for alt in normalized_alternatives], key=lambda x:x[1])
        # print 'twitter model used'
        return ranked_alts[0][0]
    except:
        pass
    try:
        # print 'spell checker used'
        return ENGLISH_DICT.suggest(word)[0]
    except:
        return word

# ----------------------------------------------- SIMILARITY OF STRINGS --------------------------------------------------
def easy_string_similarity(tweet1, tweet2):
    ''' old function, computed string similarity based on the number of overlaping words 
        SHOULD NOT BE USED '''
    overlap = 0
    for word in tweet1:
        if word in tweet2: 
            overlap += 1
    return overlap / float(len(tweet1) + len(tweet2))

def hard_string_similarity(tweet1, tweet2):
    ''' the similarity of tweet1 to tweet2 is defined as the average cosine similarity of each word in tweet1
        with every word in tweet2 '''
    tot_average = 0
    for w1 in tweet1:
        word_average = 0
        for w2 in tweet2:
            word_average += word_similarity(w1, w2)
        word_average /= float(len(tweet2))
        tot_average += word_average
    tot_average /= float(len(tweet1))
    return tot_average

def word_similarity(word1, word2):
    ''' get the similarity of 2 words - if they are the same, use the sameness penalty to discourage tweets from being identical
        otherwise use TWITTER_MODEL.similarity
        TWITTER_MODEL.similarity will fail if word1 or word2 is not in the corpus, in which case return 0 
        REMEMBER FOR OTHER FUNCTIONS - A HIGH COSINE SIMILARITY IS BETTER THAN A LOW ONE '''
    if word1 == word2:
        return 0
    try:
        return TWITTER_MODEL.similarity(word1, word2)
    except:
        return 0

# ---------------------------------------------------- GET PHONEMES ---------------------------------------------------
def get_phonemes(word):
    if word in PHONE_DICT:
        return PHONE_DICT[word][0]
    else:
        ''' due to extreme difficulties installing a grapheme to phoneme converter, this will settle '''
        result = []
        for i in range(len(word)):
            if word[i] in 'aeiouy':
                result.append(word[i].upper() + '0')
            else:
                result.append(word[i].upper())
        return result

# ------------------------------------------------- GET SYNONYMS -----------------------------------------------------
def get_synonyms(word):
    synonyms = set()
    for synset in wordnet.synsets(word):
        for superset in synset.hypernyms():
            for lem in superset.lemma_names:
                if not '_' in lem:
                    synonyms.add(lem)
            for subset in superset.hyponyms():
                for lem in subset.lemma_names:
                    if not '_' in lem:
                        synonyms.add(lem)
    return synonyms

# ------------------------------------------------- OTHER ------------------------------------------------------------
def remove_punctuation(string):
    # print 'i got ' + string
    s = string
    for punc in ''',":-/!#|\~`<>][}{$%^&*()-_=+@';?.''':
        s = s.replace(punc, '')
    # print 'i return ' + s
    return s.encode('ascii','ignore')

# -------------------------------------------------- LEXICAL GLOBALS --------------------------------------------------
# Just use this gensim model made with word2vec for context vector similarity of words!!!
print 'loading twitter word corpus ...'
TWITTER_MODEL = gensim.models.Word2Vec.load_word2vec_format('../corpus preparation/prof_corpus.bin', binary=True)
print '...loaded'
print 'loading english dictionary...'
ENGLISH_DICT = enchant.Dict('en_US')
print '...loaded'
print 'loading phonology dictionary...'
PHONE_DICT = cmudict.dict()
print '...loaded'