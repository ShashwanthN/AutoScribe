# Obsidian : My Second Brain

Obsidian can be a second brain , an extended memory or just another note taking app its all based on how you use it.

I started out using it as “just note taking app” , then it became my “extended memory” and now , its basically my “second brain”.

### “Second Brain” huh what?

Yeah i get it - the term can sound flashy , futuristic , or something i try to hype it , but once you start using Obsidian or any digital note taking app or even the traditional pen and paper and structure it up to your likings or setup , you will understand that its a good candidate for that Title.

### Why do you need a note taking app? (in my POV)

- Because You dont forget things you care about when you write it down.
- You can offload your thoughts and process it clearly.
- You put your brain to good use (like jack harlow says “put my shrooms to good use” in the song) , yeah he is definitely talking about the Brain and thinking) by focusing on thinking rather than remembering it.
- It has a faster search bar and our brain has one too , but the one i have is slow Af so i prefer this.

### What Is Obsidian ?

- Its a Markdown-based note-taking app .
- It saves your notes as `.md` files — readable, portable, future-proof.
- It supports graph view , templates , hotkeys , image embeds , internal linking , and a community plugin ecosystem.
- You can customize it with themes , CSS snippets, and useful extensions.
- It works across devices — but syncing isnt free. Obsidian Sync is a paid feature.

### Privacy - I want it i got it

- I didnt want my notes to live in a cloud server , so i found a perfect workaround what works flawless for me and maybe for you too , using Syncthing Which lets me to sync my Obsidian vault across phone and my Arch linux seamlessly.

### Why i like it

- Its now my go-to Digital jotting tool and one of my favourite pieces of software.
- I use it daily whether its for Journaling , Writing thoughts , or just dumping whats in my mind that i feel like to note down.

TL;DR: If you write, think, or build — Obsidian can help you do it better.

## Thats it Cya.

# obs-sync

## Obsidian

A simple, free, and private way to keep your Obsidian vault in sync between Android and Linux using Syncthing.

### Why I Wanted This

- I dont wanna pay for Obsidian Sync Subscription
- My notes is not staying in cloud , Nope.
- Or setting up something complex with script
- Works offline
- Reliable On Android and Linux

### Solution : Syncthing — Obsidian Sync

Syncthing is an open-source tool that syncs folders between devices over local network or internet — privately and securely.

It doesn’t upload your data anywhere. Your files stay on your devices, synced in real time.

---

## Setup Guide

Works on any Linux distro (Windows too) and any Android phone. Tested on Arch Linux + Android 15.

### Step 1: Install Syncthing

#### On Android:

- Download **Syncthing-Fork** from F-Droid (Recommended over Play Store version)
- Allow necessary permissions for file access

#### On Linux:

```bash
# For Arch-based distros
sudo pacman -S syncthing

# Start Syncthing
systemctl --user enable syncthing.service
systemctl --user start syncthing.service

```

### Step 2: Open the UI

On your Linux system, open a browser and go to:
http://localhost:8384

This is the Syncthing control panel.

### Step 3: Pair Devices

1. Open Syncthing on both Android and Linux
2. Add device on either side (QR or Device ID)
3. Accept the pairing request on the other device

> **NOTE :** Both devices needs to be connected on same network in order to show up in the devices list

### Step 4: Share Your Obsidian Vault

#### On Android:

1. In Syncthing-Fork, go to **Folders** → **Add Folder**
2. Select your Obsidian vault (usually in `/storage/emulated/0/Documents/Obsidian/`)
3. Share it with your Linux device

#### On Linux:

1. Accept the shared folder
2. Choose a destination path (like `~/Documents/Obsidian/`)

Thats it.

Now whenever you write or edit notes, they sync automatically in both directions.

---

## Note

- **Android:** Enable background sync in Syncthing-Fork settings
- **Linux:** Already enabled via `systemctl`
- Syncthing handles versioning if you edit the same file from both sides
- Both devices needs to be connected on same network
