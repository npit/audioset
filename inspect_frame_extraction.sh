#!/usr/bin/env bash
folder="$1"
tfolder="$folder/audio"
echo "Empty folders in [$tfolder] subdirectory:"
find $folder/audio -depth -empty
tfolder="$folder/frames"
echo "Empty folders in [$tfolder]subdirectory:"
find $folder/frames -depth -empty
