import toml
from difflib import SequenceMatcher

def read_conf(conf_file):
    conf_file = open(conf_file)
    conf = conf_file.read()
    conf = toml.loads(conf)
    conf_file.close()
    return conf

def convert_timestamp(timestamp):
    timestamp = timestamp.split('T')
    date = timestamp[0].split('-')
    time = timestamp[1].split('+')
    time = time[0].split(':')
    timestamp = int(date[0] + date[1] + date[2] + time[0] + time[1] + time[2])
    return timestamp

def dupe_check(published,title,dupe_setting):
        title = title.replace(",",".")
        title = title.replace("&#x27;","'")
        title = title.replace("&quot;","'")
        title = title.replace("(video)","")
        ct = open("videos.log.csv", "r")
        ctr = ct.read().split("\n")
        ct.close()
        ctr_line = []
        video_found = False
        # check if channel name is found in channels_timestamps.csv
        #print ("checking ("+title+") against "+str(len(ctr))+" videos")
        best_match =0
        duplicate = ""
        for line in ctr:
            line_list = line.split(',')
            #ignore blank lines
            if len(line_list) > 1:
                match = SequenceMatcher(a=title,b=line_list[2]).ratio()
                diff = abs(int(line_list[1])-published)
                if diff < 1000 and match>.98:
                    #print ("easy match: "+str(match)+": "+str(diff))
                    return True
                if diff == 0:
                    #print ("exact time: "+str(match)+": "+str(diff))
                    return True
                if match >dupe_setting:
                    #print ("title close enough: "+str(match)+": "+str(diff))
                    return True
        return False
def set_pt_lang(yt_lang, conf_lang):
    YOUTUBE_LANGUAGE = {
        "arabic": 'ar',
        "english": 'en',
        "french": 'fr',
        "german": 'de',
        "hindi": 'hi',
        "italian": 'it',
        "japanese": 'ja',
        "korean": 'ko',
        "mandarin": 'zh-CN',
        "portuguese": 'pt-PT',
        "punjabi": 'pa',
        "russian": 'ru',
        "spanish": 'es'
    }
    PEERTUBE_LANGUAGE = {
        "arabic": "ar",
        "english": "en",
        "french": "fr",
        "german": "de",
        "hindi": "hi",
        "italian": "it",
        "japanese": "ja",
        "korean": "ko",
        "mandarin": "zh",
        "portuguese": "pt",
        "punjabi": "pa",
        "russian": "ru",
        "spanish": "es"
    }
    # if youtube provides a language value
    if yt_lang != None:
        # if the language value is a value and not a key
        if len((yt_lang).split("-")[0]) < 3:
            key_list = list(YOUTUBE_LANGUAGE.keys())
            val_list =list(YOUTUBE_LANGUAGE.values())
            yt_lang = key_list[val_list.index(yt_lang)]
        else:
            pass
        # now set the language to the peertube value using the key
        try:
            lang = PEERTUBE_LANGUAGE[yt_lang]
        except:
            # in the event that no key exists for the youtube language, use the conf value
            if len(conf_lang) > 2:
                conf_lang = PEERTUBE_LANGUAGE[conf_lang]
            lang = conf_lang
    else:
        if len(conf_lang) > 2:
            conf_lang = PEERTUBE_LANGUAGE[conf_lang]
        lang = conf_lang
    return lang

def set_pt_category(category_str):
    print(category_str)
    PEERTUBE_CATEGORY = {
        "music": 1,
        "films": 2,
        "vehicles": 3,
        "sport": 5,
        "travels": 6,
        "gaming": 7,
        "people": 8,
        "comedy": 9,
        "entertainment": 10,
        "news": 11,
        "how to": 12,
        "education": 13,
        "activism": 14,
        "science & technology": 15,
        "science": 15,
        "technology": 15,
        "animals": 16
    }
    category = str(PEERTUBE_CATEGORY[category_str])
    return category
