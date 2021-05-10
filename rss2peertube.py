#!/usr/bin/python3

import os
import sys
import getopt
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
import logging

def get_video_data(channel_url,channel_name,dupe_setting):
    feed = fp.parse(channel_url)
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
    # check if channel name is found in channels_timestamps.csv
    for line in ctr:
        line_list = line.split(',')
        if channel_name == line_list[0]:
            channel_found = True
            ctr_line = line
            break
    if not channel_found:
        print("new channel added to config: " + channel_name)
    print(str(datetime.now().strftime("%m/%d %H:%M:%S"))+" : checking "+str(len(entries))+" in "+channel_name+"          ")
    # iterate through video entries for channel, parse data into objects for use
    for pos, i in enumerate(reversed(entries)):
        published = i["published"]
        title = i["title"]
        #updated = i["updated"]
        parsed=published
        if "podbean" in channel_url:
            print(i.get('enclosures', [])[0])
        if ("odysee" in channel_url) or ("bitchute" in channel_url) or ("podbean"):
            p = i["updated_parsed"]
            parsed = str(p.tm_year)+str(p.tm_mon).zfill(2)+str(p.tm_mday).zfill(2)+str(p.tm_hour).zfill(2)+str(p.tm_min).zfill(2)+str(p.tm_sec).zfill(2)
            published_int = int(parsed)

        if "https://youtube" in channel_url:
            published_int = utils.convert_timestamp(published)
            parsed = str(published_int)
        if dupe_setting >0 and utils.dupe_check(published_int,title,dupe_setting):
            #go to next entry if already imported
            continue
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
            ctr_line_list = ctr_line.split(",")
            line_published_int = int(ctr_line_list[1])
            if published_int > line_published_int:
                # update the timestamp in the line for the channel in channels_timestamps,
                ctr.remove(ctr_line)
                ctr_line = str(channel_name + "," + parsed + "," + parsed + '\n')
                ctr.append(ctr_line)
                # and add current videos to queue.
                queue.append(i)
        #fix some of the typical differences in title text betwixt sites and comma induced errors in the csv
        title = title.replace(",",".")
        title = title.replace("&#x27;","'")
        title = title.replace("&quot;","'")
        title = title.replace("(video)","")
        #print("title:"+title)
        file = open ("videos.log.csv","a+")
        file.write(channel_name+","+parsed+","+title+"\n")
        file.close
    # write the new channels and timestamps line to channels_timestamps.csv
    ct = open(channels_timestamps, "w")
    for line in ctr:
        if line != '':
            ct.write(line + "\n")
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

def pt_cli_import(queue_item,channel_conf,cli_dir,dl_dir,parallel_import):
    video_url = queue_item["link"]
    pt_instance=channel_conf["peertube_instance"]
    hack = pt_instance.split("/")
    server_url=hack[2]
    video_url = video_url.replace("embed","video")
    pt_uname = channel_conf["peertube_username"]
    pt_passwd = channel_conf["peertube_password"]
    cline = "cd "+ cli_dir +" && node dist/server/tools/peertube-import-videos.js -u '"
    cline = cline +server_url+"' -U '"+pt_uname+"' --password '"+pt_passwd+"' --target-url '"+video_url+"'"
    cline = cline + " --tmpdir '"+ dl_dir+"'"
    if parallel_import == "true":
        cline=cline+"&"
    print(cline)
    os.system(cline)
    return True

def log_video(line):
    log_file = open("error.log.csv", "a")
    log_file.write(channel_conf['name']+","+yt_url+"\n")
    log_file.close()
    print("error !")

def run_steps(conf):
    # TODO: logging
    channel = conf["channel"]
    # run loop for every channel in the configuration file
    global_conf = conf["global"]
    dl_dir = global_conf["video_download_dir"]
    cli_dir = global_conf["cli_dir"]
    dupe_setting = global_conf["dupe_setting"]
    parallel_import = global_conf["parallel_import"]
    if not path.exists(dl_dir):
        mkdir(dl_dir)
    if not path.exists(cli_dir):
        print("either the CLI tools aren't installed, or the path isn't configured in config.toml")
    channel_counter = 0
    for c in channel:
        channel_url = channel[c]["channel_url"]
        channel_name = channel[c]["name"]
        parts=channel_url.split("/")
        channel_service="unknown"
        if "bitchute" in parts[2]:
            channel_service = "bitchute"
        if "youtube" in parts[2]:
            channel_service = "youtube"
        if "odysee" in parts[2]:
            channel_service = "odysee"
        channel_id = parts[-1]
        channel_conf = channel[str(channel_counter)]
        video_data = get_video_data(channel_url,channel_name,dupe_setting)
        queue = video_data[0]
        if len(queue) > 0:
            for queue_item in queue:
                print("mirroring " + queue_item["title"])
                pt_result = pt_cli_import(queue_item,channel_conf,cli_dir,dl_dir,parallel_import)
                if not pt_result:
                    print("error importing video")
                    log_upload_error(queue_item["link"],channel_conf)
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
    opts, args = getopt.getopt(argv,"horc",["help","once","reset","clear"])
  except:
    print("youtube2peertube.py [-o|--once]")
    sys(exit(2))

  for opt, arg in opts:
    if opt == '-h':
      print("youtube2peertube.py [-o|--once] [-r|--reset] [-c|--clear]")
      print("reset will reset channels_timestamps.csv and force videos to be rechecked")
      print("clear will clear videos.log.csv so nothing will marked duplicate")
      sys.exit()
    elif opt in ("-o", "--once"):
      run_once = True
    elif opt in ("-r", "--reset"):
      file = open("channels_timestamps.csv","r+")
      file. truncate(0)
      file. close()
    elif opt in ("-R", "--Reset"):
      file = open("videos.log.csv","r+")
      file. truncate(0)
      file. close()
  run(run_once)


if __name__ == "__main__":
  main(sys.argv[1:])
