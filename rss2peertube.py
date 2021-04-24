#!/usr/bin/python3

import os
import sys
import getopt
import pafy
import feedparser as fp
from urllib.request import urlretrieve
import requests
import json
from time import sleep
from os import mkdir, path
from shutil import rmtree
import mimetypes
from datetime import datetime
from requests_toolbelt.multipart.encoder import MultipartEncoder
import utils









def pt_http_import(dl_dir, channel_conf, queue_item, access_token, thumb_extension, yt_lang):
    # Adapted from Prismedia https://git.lecygnenoir.info/LecygneNoir/prismedia
    pt_api = channel_conf["peertube_instance"] + "/api/v1"
    yt_video_url = queue_item["link"]
    # TODO: use the alternate link if video not found error occurs
    alternate_link = queue_item["links"][0]["href"]
    thumb_file = dl_dir + channel_conf["name"] + "/" + queue_item["yt_videoid"] + "." + thumb_extension
    description = channel_conf["description_prefix"] + "\n\n" + queue_item["summary"] + "\n\n" + channel_conf["description_suffix"]
    channel_id = str(get_pt_channel_id(channel_conf))
    language = utils.set_pt_lang(yt_lang, channel_conf["default_lang"])
    category = utils.set_pt_category(channel_conf["pt_channel_category"])
    # We need to transform fields into tuple to deal with tags as
    # MultipartEncoder does not support list refer
    # https://github.com/requests/toolbelt/issues/190 and
    # https://github.com/requests/toolbelt/issues/205
    fields = [
        ("name", queue_item["title"]),
        ("licence", "1"),
        ("description", description),
        ("nsfw", channel_conf["nsfw"]),
        ("channelId", channel_id),
        ("originallyPublishedAt", queue_item["published"]),
        ("category", category),
        ("language", language),
        ("privacy", str(channel_conf["pt_privacy"])),
        ("commentsEnabled", channel_conf["comments_enabled"]),
        ("targetUrl", yt_video_url),
        ("thumbnailfile", get_file(thumb_file)),
        ("previewfile", get_file(thumb_file)),
        ("waitTranscoding", 'false')
    ]
    if channel_conf["pt_tags"] != "":
        fields.append(("tags[]", channel_conf["pt_tags"]))
    else:
        print("you have no tags in your configuration file for this channel")
    multipart_data = MultipartEncoder(fields)
    headers = {
        'Content-Type': multipart_data.content_type,
        'Authorization': "Bearer " + access_token
    }

    return handle_peertube_result(requests.post(pt_api + "/videos/imports", data=multipart_data, headers=headers))













def get_video_data(channel_url,channel_name):
    #print ("getting video for "+channel_name+" at "+channel_url)
    #o_rss_url = "https://lbryfeed.melroy.org/channel/odysee/" + channel_id
    feed = fp.parse(channel_url)
    #print (len(feed))
    #channel_lang = feed["feed"]["title_detail"]["language"]
    #print(feed["feed"])
    entries = feed["entries"]

    channels_timestamps = "channels_timestamps.csv"
    # clear any existing queue before start
    queue = []
    # read contents of channels_timestamps.csv, create list object of contents
    ct = open(channels_timestamps, "r")
    ctr = ct.read().split("\n")
    ct.close()
    ctr_line = []
    channel_found = False
    # check if channel ID is found in channels_timestamps.csv
    for line in ctr:
        line_list = line.split(',')
        if channel_name == line_list[0]:
            channel_found = True
            ctr_line = line
            break
    if not channel_found:
        print("new channel added to config: " + channel_name)
    print(str(datetime.now().strftime("%m/%d %H:%M:%S"))+" : checking "+str(len(entries))+" in "+channel_name+"          ")
    #print ("\033[2A")
    # iterate through video entries for channel, parse data into objects for use
    for pos, i in enumerate(reversed(entries)):
        #print(i["title"])
        published = i["published"]
        updated = i["updated"]
        parsed=published
        if "odysee" in channel_url:
            p = i["updated_parsed"]
            parsed = str(p.tm_year)+str(p.tm_mon).zfill(2)+str(p.tm_mday).zfill(2)+str(p.tm_hour).zfill(2)+str(p.tm_min).zfill(2)+str(p.tm_sec).zfill(2)
            published_int = int(parsed)
            #print(parsed+" converts to "+ str(published_int))
        if "bitchute" in channel_url:
            p = i["updated_parsed"]
            parsed = str(p.tm_year)+str(p.tm_mon).zfill(2)+str(p.tm_mday).zfill(2)+str(p.tm_hour).zfill(2)+str(p.tm_min).zfill(2)+str(p.tm_sec).zfill(2)
            published_int = int(parsed)
            #print(parsed+" converts to "+ str(published_int))
        if "youtube" in channel_url:
            parsed = published
            #published_list = published.split(",")
            #print(published_list[1])
            published_int = utils.convert_timestamp(published)
        #print(parsed+" converts to "+ str(published_int))
        if not channel_found:
            # add the video to the queue
            queue.append(i)
            ctr_line = str(channel_name + "," + parsed + "," + parsed + '\n')
            # add the new line to ctr for adding to channels_timestamps later
            ctr.append(ctr_line)
            print ("channel not found, adding "+ctr_line)
            channel_found = True
        # if the channel exists in channels_timestamps, update "published" time in the channel line
        else:
            #print(ctr_line)
            ctr_line_list = ctr_line.split(",")
            if "youtube" in channel_url:
                line_published_int = utils.convert_timestamp(ctr_line_list[1])
            else:
                line_published_int = int(ctr_line_list[1])
            #print(parsed+" ("+str(published_int - line_published_int)+") comparing "+ctr_line_list[1])
            #rint (str(published_int)+" - "+str(line_published_int)+" = "+str(published_int-line_published_int))
            if published_int > line_published_int:
                # update the timestamp in the line for the channel in channels_timestamps,
                ctr.remove(ctr_line)
                ctr_line = str(channel_name + "," + parsed + "," + parsed + '\n')
                ctr.append(ctr_line)
                # and add current videos to queue.
                queue.append(i)
    # write the new channels and timestamps line to channels_timestamps.csv
    ct = open(channels_timestamps, "w")
    for line in ctr:
        if line != '':
            ct.write(line + "\n")
            #print ("writing line "+line)
    ct.close()
    return queue, "en"

def get_file(file_path):
    mimetypes.init()
    return (path.basename(file_path), open(path.abspath(file_path), 'rb'),
            mimetypes.types_map[path.splitext(file_path)[1]])

def log_upload_error(yt_url,channel_conf):
    error_file = open("video_errors.csv", "a")
    error_file.write(channel_conf['name']+","+yt_url+"\n")
    error_file.close()
    print("error !")

def run_steps(conf):
    # TODO: logging
    channel = conf["channel"]
    # run loop for every channel in the configuration file
    global_conf = conf["global"]
    dl_dir = global_conf["video_download_dir"]
    if not path.exists(dl_dir):
        mkdir(dl_dir)
    channel_counter = 0
    for c in channel:
        #print("\n")
        channel_url = channel[c]["channel_url"]
        channel_name = channel[c]["name"]
        #print (channel_url+" is "+channel_name)
        parts=channel_url.split("/")
        channel_service="unknown"
        if "bitchute" in parts[2]:
            channel_service = "bitchute"
        if "youtube" in parts[2]:
            channel_service = "youtube"
        if "odysee" in parts[2]:
            channel_service = "odysee"
        for part in parts:
            print(part)
        channel_id = parts[-1]
        channel_conf = channel[str(channel_counter)]
        video_data = get_video_data(channel_url,channel_name)
        queue = video_data[0]
        if len(queue) > 0:
            for queue_item in queue:
                print("mirroring " + queue_item["link"] + " to Peertube using HTTP import...")
                video_url = queue_item["link"]
                print (video_url)
                pt_instance=channel_conf["peertube_instance"]
                print (pt_instance)
                hack = pt_instance.split("/")
                print(hack)
                server_url=hack[2]
                video_url = video_url.replace("embed","video")
                print (video_url)
                pt_uname = channel_conf["peertube_username"]
                pt_passwd = channel_conf["peertube_password"]
                # server_url = "based.directory"
                if channel_service == "youtube":
                    pt_result = pt_http_import(dl_dir, channel_conf, queue_item, access_token, thumb_extension, yt_lang)
                else:
                    cline = "cd /home/marc/PeerTube/ && node dist/server/tools/peertube-import-videos.js -u '"
                    cline = cline +server_url+"' -U '"+pt_uname+"' --password '"+pt_passwd+"' --target-url '"+video_url+"'"
                    cline = cline + " --tmpdir '/home/marc/Downloads'"
                    print (cline)
                    os.system(cline)
        channel_counter += 1

def run(run_once=True):
    #TODO: turn this into a daemon
    conf = utils.read_conf("config.toml")
    if run_once:
        run_steps(conf)
    else:
        while True:
            poll_frequency = int(conf["global"]["poll_frequency"]) * 60
            run_steps(conf)
            sleep(poll_frequency)


def main(argv):
  run_once=False
  try:
    opts, args = getopt.getopt(argv,"ho",["help","once"])
  except:
    print("youtube2peertube.py [-o|--once]")
    sys(exit(2))

  for opt, arg in opts:
    if opt == '-h':
      print("youtube2peertube.py [-o|--once]")
      sys.exit()
    elif opt in ("-o", "--once"):
      run_once = True
    elif op int ("-r", "--reset")
      file = open("channels_timestamps.csv","r+")
      file. truncate(0)
      file. close()

  run(run_once)


if __name__ == "__main__":
  main(sys.argv[1:])
