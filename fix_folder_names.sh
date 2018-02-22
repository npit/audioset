#!/usr/bin/env bash
folder="$1"
for vidfolder in $(ls $folder); do
	mv "$folder/$vidfolder" "$folder/$( echo $vidfolder | sed 's<\_[0-9]*\_[0-9]*\.mp4<<g')"
done
