# rss2peertube
Python script to automatically publish a media RSS feed to a PeerTube Channel

Based on https://github.com/mister-monster/YouTube2PeerTube

Works with BitChute and Odysee now, allows for multiple sources for redundancy. cross platform duplicate matching works best if video titles are identical across services.

In addition to the setup for https://github.com/mister-monster/YouTube2PeerTube you will also need to install the CLI tools from https://docs.joinpeertube.org/maintain-tools, Make sure to update the clie_dir in config.toml with the directory you install to.

After adding the third provider it became clear this would be better done with a Typescript plug-in and best to invest further effort toward developing that.
