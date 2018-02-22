#!/usr/bin/env bash
folder="$1"
suff="$2"
simulate=0
[ $# -gt 2 ] && [ "$3" == "simulate" ] && simulate=1
for vidfolder in $(ls $folder); do
	if [ $simulate -eq 1 ]; then
		echo "(simulating)"
		echo "$folder/$vidfolder" 
		echo "$folder/$( echo $vidfolder | sed 's<\_[0-9]*\_[0-9]*<<g')"
	else
		mv "$folder/$vidfolder" "$folder/$( echo $vidfolder | sed 's<\_[0-9]*\_[0-9]*<<g')"
	fi
done
