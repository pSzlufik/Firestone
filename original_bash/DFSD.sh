#!/bin/bash
run () {
SECONDS=0
     echo "run: $SECONDS" #debug
xdotool search --name 'Firestone' windowactivate sleep 0.155
WID=$(xdotool getactivewindow)
     #echo "window: $WID"
reps=$1
     #echo "Running loop for: $reps"
startingServer=$2
     #echo "Starting on server: $startingServer"
lvl=$3
     #echo "with lvl: $lvl"
guardianNo=$4
     #echo "training guardian: $guardianNo"
swServer=$7
     #echo "then swapping to: $swServer"
IFS=';' read -r alchemyDB alchemyDust alchemyCoins <<< "$5"
     #echo "DB: $alchemyDB" ", dust: $alchemyDust"  ", coins: $alchemyCoins" #debug
IFS=';' read -r fsTree fs1 fs2 <<< "$6"
     #echo "Tree: $fsTree" ", 1st node: $fs1" ", 2nd node: $fs2" #debug
  
for (( i=1; i<=reps; i++ ))
do
	reset
	xdotool sleep 0.1
	     #echo "guardian: $SECONDS" #debug
	guardian "$guardianNo"
	     #echo "Guardian finished: $SECONDS" #debug
	xdotool sleep 0.1
	if [ "$lvl" -ge 10 ]; then
		     #echo "exped: $SECONDS" #debug
		exped
		     #echo "exped finished: $SECONDS" #debug
		xdotool sleep 0.1
		if [ "$fsTree" -ne 0 ]; then
 			     #echo "lib: $SECONDS" #debug
			lib "$fsTree" "$fs1" "$fs2"
 			     #echo "lib finished: $SECONDS" #debug
			xdotool sleep 0.1
		fi
		if [ "$lvl" -ge 15 ]; then
			     #echo "Tavern: $SECONDS" #debug
			tavern
			     #echo "Tavern collected: $SECONDS" #debug
			xdotool sleep 0.1
			if [ "$lvl" -ge 50 ]; then
				xdotool sleep 0.1
				     #echo "Campaign Loot: $SECONDS" #debug
				campaignLoot
				     #echo "Campaign Loot collected: $SECONDS" #debug
				xdotool sleep 0.1
				     #echo "Engi: $SECONDS" #debug
				engi
				     #echo "Engi collected: $SECONDS" #debug
				if [ "$lvl" -ge 120 ]; then
					xdotool sleep 0.1
					    #echo "Alchemy: $SECONDS" #debug
					alchemy "$alchemyDB" "$alchemyDust" "$alchemyCoins"
					    #echo "Alchemy finished: $SECONDS" #debug
					xdotool sleep 0.1
					if [ "$lvl" -ge 200 ]; then
						xdotool sleep 0.1
						     #echo "Oracle: $SECONDS" #debug
						oracle
						     #echo "Oracle finished: $SECONDS" #debug
						xdotool sleep 0.1
					fi
				fi
			fi
		fi
	fi
	
	xdotool sleep 0.1

	if [ "$((i%3))" -eq 0 ]; then
 		     #echo "mapCollect: $SECONDS" #debug
		mapCollect
 		     #echo "mapCollect finished: $SECONDS" #debug
		xdotool sleep 0.1
 		     #echo "mapStart: $SECONDS" #debug
		mapStart
 		     #echo "mapStart finished: $SECONDS" #debug
	fi
	if [ "$swServer" -ne 0 ]; then
		swLvl=$8		   
		swGuardian=$9   

		IFS=';' read -r swAlchemyDB swAlchemyDust swAlchemyCoins <<< "${10}"
		    #echo "DB: $swAlchemyDB" ", dust: $swAlchemyDust"  ", coins: $swAlchemyCoins" #debug
		IFS=';' read -r swFsTree swFs1 swFs2 <<< "${11}"
		     #echo "Tree: $swFsTree" ", 1st node: $swFs1" ", 2nd node: $swFs2" #debug
		     #echo "swServer: $SECONDS" #debug
		serverSwap "$swServer"
		     #echo "swServer finished: $SECONDS" #debug

		reset
		xdotool sleep 0.1
		     #echo "swGuardian: $SECONDS" #debug
		guardian "$swGuardian"
		     #echo "swGuardian finished: $SECONDS" #debug
		xdotool sleep 0.1
	
		if [ "$lvl" -ge 10 ]; then
			     #echo "swExped: $SECONDS" #debug
			exped
			     #echo "swExped finished: $SECONDS" #debug
			xdotool sleep 0.1
			if [ "$swFsTree" -ne 0 ]; then
	 			     #echo "swLib: $SECONDS" #debug
				lib "$swFsTree" "$swFs1" "$swFs2"
	 			     #echo "swLib finished: $SECONDS" #debug
				xdotool sleep 0.1
			fi
			if [ "$swLvl" -ge 15 ]; then
				     #echo "swTavern: $SECONDS" #debug
				tavern
				     #echo "swTavern collected: $SECONDS" #debug
				xdotool sleep 0.1
				if [ "$swLvl" -ge 50 ]; then
					xdotool sleep 0.15
					     #echo "swCampaignLoot: $SECONDS" #debug
					campaignLoot
					     #echo "swCampaignLoot collected: $SECONDS" #debug
					xdotool sleep 0.15
					     #echo "swEngi: $SECONDS" #debug
					engi
					     #echo "swEngi collected: $SECONDS" #debug
					if [ "$swLvl" -ge 120 ]; then
						xdotool sleep 0.1
						    #echo "swAlchemy: $SECONDS" #debug
						alchemy "$swAlchemyDB" "$swAlchemyDust" "$swAlchemyCoins"
						    #echo "swAlchemy finished: $SECONDS" #debug
						xdotool sleep 0.15
						if [ "$swLvl" -ge 200 ]; then
							xdotool sleep 0.15
							     #echo "swOracle: $SECONDS" #debug
							oracle
							     #echo "swOracle finished: $SECONDS" #debug
							xdotool sleep 0.15
						fi
					fi
				fi
			fi
		fi
	
		xdotool sleep 0.1
		if [ "$((i%3))" -eq 0 ]; then
	 		     #echo "swMapCollect: $SECONDS" #debug
			mapCollect
	 		     #echo "swMapCollect finished: $SECONDS" #debug
			xdotool sleep 0.1
	 		     #echo "swMapStart: $SECONDS" #debug
			mapStart
	 		     #echo "swMapStart finished: $SECONDS" #debug
		fi
		serverSwap "$startingServer"
		xdotool sleep 0.1
	fi
done

echo "$SECONDS"

}

alchemy () {
xdotool search --name 'Firestone' windowactivate sleep 0.15
WID=$(xdotool getactivewindow)
db=$1
dust=$2
ec=$3
let sum=db+dust+ec
if [ "$sum" -ne 0 ]; then
	xdotool key --window "$WID" a sleep 0.4
	if [ "$1" -eq 1 ]; then
 		    #echo "Conducting DB experiment" #debug
		xdotool mousemove --window "$WID" 950 800 sleep 0.25 click --window "$WID" --repeat 2 --delay 25 1 sleep 0.15
	fi
	if [ "$2" -eq 1 ]; then
 		    #echo "Conducting dust experiment" #debug
		xdotool mousemove --window "$WID" 1300 800 sleep 0.25 click --window "$WID" --repeat 2 --delay 25 1 sleep 0.15
	fi
	if [ "$3" -eq 1 ]; then
 		    #echo "Conducting ec experiment" #debug
		xdotool mousemove --window "$WID" 1650 800 sleep 0.25 click --window "$WID" --repeat 2 --delay 25 1 sleep 0.15
	fi
#else
	     #echo "No alchemy experiments conducted" #debug
fi

reset
}

campaignFight () {
xdotool search --name 'Firestone' windowactivate sleep 0.2
WID=$(xdotool getactivewindow)
xdotool key --window "$WID" m sleep 0.4
xdotool mousemove --window "$WID" 1840 610 sleep 0.25 click --window "$WID" 1 sleep 0.15
xdotool mousemove --window "$WID" 1020 630 sleep 0.25 click --window "$WID" 1 sleep 0.15
xdotool mousemove --window "$WID" 600 950 sleep 0.25 click --window "$WID" 1 sleep 0.15
xdotool sleep 50
xdotool mousemove --window "$WID" 25 160 sleep 0.25 click --window "$WID" --repeat 3 --delay 10 1 sleep 0.15
xdotool mousemove --window "$WID" 500 790 sleep 0.25 click --window "$WID" 1 sleep 0.2
xdotool mousemove --window "$WID" 960 950 sleep 0.25 click --window "$WID" 1 sleep 0.2
xdotool mousemove --window "$WID" 25 160 sleep 0.25 click --window "$WID" --repeat 3 --delay 10 1 sleep 0.15
reset
}

campaignLoot () {
xdotool search --name 'Firestone' windowactivate sleep 0.15
WID=$(xdotool getactivewindow)
xdotool key --window "$WID" m sleep 0.4
xdotool mousemove --window "$WID" 1840 610 sleep 0.25 click --window "$WID" 1 sleep 0.15
xdotool mousemove --window "$WID" 160 1000 sleep 0.25 click --window "$WID" 1 sleep 0.15
xdotool sleep 0.25
reset
}

engi () {
xdotool search --name 'Firestone' windowactivate sleep 0.15
WID=$(xdotool getactivewindow)
	xdotool mousemove --window "$WID" 1860 212 sleep 0.25 click --window "$WID" 1 sleep 0.15
	xdotool mousemove --window "$WID" 1280 830 sleep 0.25 click --window "$WID" 1 sleep 0.15
	xdotool mousemove --window "$WID" 580 539 sleep 0.25 click --window "$WID" 1 sleep 0.15
	xdotool mousemove --window "$WID" 1625 720 sleep 0.25 click --window "$WID" 1 sleep 0.15
xdotool sleep 0.25
reset
}

exped () {
xdotool search --name 'Firestone' windowactivate sleep 0.15
WID=$(xdotool getactivewindow)
xdotool mousemove --window "$WID" 1856 469 sleep 0.25 click --window "$WID" 1 sleep 0.15
xdotool mousemove --window "$WID" 334 376 sleep 0.25 click --window "$WID" 1 sleep 0.15
xdotool mousemove --window "$WID" 1325 317 sleep 0.25 click --window "$WID" --repeat 2 --delay 250 1 sleep 0.15
xdotool sleep 0.25
reset
}

guardian () {
xdotool search --name 'Firestone' windowactivate sleep 0.15
WID=$(xdotool getactivewindow)
xdotool key --window "$WID" g sleep 0.4
let gindex=$1-1
temp=$(getSingleRowElement "$gindex" "${guardianPos[@]}")
IFS=';' read -r guardianX guardianY <<< "$temp"

xdotool mousemove --window "$WID" "$guardianX" "$guardianY" sleep 0.25 click --window "$WID" 1 sleep 0.15
xdotool mousemove --window "$WID" 1160 800 sleep 0.25 click --window "$WID" 1 sleep 0.15
xdotool sleep 0.25

reset
}

lib () {
	xdotool search --name 'Firestone' windowactivate sleep 0.15
	WID=$(xdotool getactivewindow)
	xdotool key --window "$WID" L sleep 0.4
	xdotool mousemove --window "$WID" 1800 630 sleep 0.25 click --window "$WID" 1 sleep 0.15
	xdotool mousemove --window "$WID" 1 1 sleep 0.25 click --window "$WID" --repeat 2 --delay 10 1
	xdotool mousemove --window "$WID" 1130 80 sleep 0.25 click --window "$WID" 1 sleep 0.15
	xdotool mousemove --window "$WID" 1 1 sleep 0.25 click --window "$WID" --repeat 2 --delay 10 1
	xdotool mousemove --window "$WID" 1270 990 sleep 0.25 click --window "$WID" 1 sleep 0.15
	xdotool mousemove --window "$WID" 1 1 sleep 0.25 click --window "$WID" --repeat 2 --delay 10 1
	xdotool mousemove --window "$WID" 590 990 sleep 0.25 click --window "$WID" 1 sleep 0.15
	xdotool mousemove --window "$WID" 1 1 sleep 0.25 click --window "$WID" --repeat 2 --delay 10 1

	# echo "lib Input: $1 $2 $3" #debug
	fsPattern=$(($1 % 3))
	# echo "Tree pattern: $fsPattern" #debug
	let fsNode1=$2-1
	let fsNode2=$3-1
	# echo "lib Upgrade indexes: $fsNode1 $fsNode2" #debug
	temp=$(getMatrixElement "$fsPattern" "$fsNode1" 16 "${fsTreePatterns[@]}")
	# echo "lib First matrix value: $temp" #debug
	IFS=';' read -r fsCol1 fsRow1 <<< "$temp"
	fsCol1Index=$((fsCol1-1))
	fsRow1Index=$((fsRow1-1))
	# echo "lib Col/Row for first upagrde: $fsCol1 / $fsRow1" #debug
	temp=$(getMatrixElement "$fsPattern" "$fsNode2" 16 "${fsTreePatterns[@]}")
	IFS=';' read -r fsCol2 fsRow2 <<< "$temp"
	fsCol2Index=$((fsCol2-1))
	fsRow2Index=$((fsRow2-1))
	     #echo "lib Col/Row for second upagrde: $fsCol2 / $fsRow2" #debug
	node1Y=$(getSingleRowElement "$fsRow1Index" "${fsRows[@]}")
	node2Y=$(getSingleRowElement "$fsRow2Index" "${fsRows[@]}")
	if [[ "$fsCol1" -le 4 ]]; then
 		     #echo "Early parts of the fs tree for the first upgrade!" #debug
   		node1X=$(getSingleRowElement "$fsCol1Index" "${fsColsLeft[@]}")

		  #  echo "X coordinate of the first node: $node1X" #debug
		xdotool mousemove --window "$WID" 1 1 sleep 0.25 click --window "$WID" --repeat 150 --delay 1 4 sleep 0.1
		xdotool mousemove --window "$WID" "$node1X" "$node1Y" sleep 0.25 click --window "$WID" 1 sleep 0.15
		xdotool mousemove --window "$WID" 750 790 sleep 0.25 click --window "$WID" 1 sleep 0.15
		xdotool mousemove --window "$WID" 20 20 sleep 0.25 click --window "$WID" --repeat 2 --delay 10 1 sleep 0.15
	elif [[ "$fsCol1" -ge 6 ]]; then
 		     #echo "Late parts of the fs tree for the first upgrade!" #debug
		fsCol1Index=$((fsCol1-6))
   		node1X=$(getSingleRowElement "$fsCol1Index" "${fsColsRight[@]}")

		  #  echo "X coordinate of the first node: $node1X" #debug
		xdotool mousemove --window "$WID" 1 1 sleep 0.25 click --window "$WID" --repeat 150 --delay 1 5 sleep 0.1
		xdotool mousemove --window "$WID" "$node1X" "$node1Y" sleep 0.25 click --window "$WID" 1 sleep 0.15
		xdotool mousemove --window "$WID" 750 790 sleep 0.25 click --window "$WID" 1 sleep 0.15
		xdotool mousemove --window "$WID" 20 20 sleep 0.25 click --window "$WID" --repeat 2 --delay 10 1 sleep 0.15
  	else
		     #echo "Middle part of the fs tree for the first upgrade!" #debug
		     #echo "X coordinate of the first node: 650" #debug
		xdotool mousemove --window "$WID" 1 1 sleep 0.25 click --window "$WID" --repeat 150 --delay 1 4 sleep 0.1
		xdotool mousemove --window "$WID" 1 1 sleep 0.25 click --window "$WID" --repeat 50 --delay 1 5 sleep 0.15
		xdotool mousemove --window "$WID" 650 "$node1Y" sleep 0.25 click --window "$WID" 1 sleep 0.15
		xdotool mousemove --window "$WID" 750 790 sleep 0.25 click --window "$WID" 1 sleep 0.15
		xdotool mousemove --window "$WID" 20 20 sleep 0.25 click --window "$WID" --repeat 2 --delay 10 1 sleep 0.15
   	fi
		     #echo "Y coordinate of first node: $node1Y" #debug
	if [[ "$fsCol2" -le 4 ]]; then
 		     #echo "Early parts of the fs tree for the second upgrade!" #debug
   		node2X=$(getSingleRowElement "$fsCol2Index" "${fsColsLeft[@]}")
		  #  echo "X coordinate of first node: $node2X" #debug
		xdotool mousemove --window "$WID" 1 1 sleep 0.25 click --window "$WID" --repeat 150 --delay 1 4 sleep 0.1
		xdotool mousemove --window "$WID" "$node2X" "$node2Y" sleep 0.25 click --window "$WID" 1 sleep 0.15
		xdotool mousemove --window "$WID" 750 790 sleep 0.25 click --window "$WID" 1 sleep 0.15
		xdotool mousemove --window "$WID" 20 20 sleep 0.25 click --window "$WID" --repeat 2 --delay 10 1 sleep 0.15
	elif [[ "$fsCol2" -ge 6 ]]; then
 		     #echo "Late parts of the fs tree for the second upgrade!" #debug
		fsCol2Index=$((fsCol2-6))
   		node2X=$(getSingleRowElement "$fsCol2Index" "${fsColsRight[@]}")

		  #  echo "X coordinate of the second node: $node2X" #debug
		xdotool mousemove --window "$WID" 1 1 sleep 0.25 click --window "$WID" --repeat 1200 --delay 1 5 sleep 0.15
		xdotool mousemove --window "$WID" "$node2X" "$node2Y" sleep 0.25 click --window "$WID" 1 sleep 0.15
		xdotool mousemove --window "$WID" 750 790 sleep 0.25 click --window "$WID" 1 sleep 0.15
		xdotool mousemove --window "$WID" 20 20 sleep 0.25 click --window "$WID" --repeat 2 --delay 10 1 sleep 0.15
  	else
		     #echo "Middle part of the fs tree for the second upgrade!" #debug
		     #echo "X coordinate of the second node: 650" #debug
		xdotool mousemove --window "$WID" 1 1 sleep 0.25 click --window "$WID" --repeat 120 --delay 1 4 sleep 0.15
		xdotool mousemove --window "$WID" 1 1 sleep 0.25 click --window "$WID" --repeat 50 --delay 1 5 sleep 0.15
		xdotool mousemove --window "$WID" 650 "$node2Y" sleep 0.25 click --window "$WID" 1 sleep 0.15
		xdotool mousemove --window "$WID" 750 790 sleep 0.25 click --window "$WID" 1 sleep 0.15
		xdotool mousemove --window "$WID" 20 20 sleep 0.25 click --window "$WID" --repeat 2 --delay 10 1 sleep 0.15
   	fi
		     #echo "Y coordinate of the second node: $node2Y" #debug
	reset
}


mapCollect () {
xdotool search --name 'Firestone' windowactivate sleep 0.15
WID=$(xdotool getactivewindow)
xdotool key --window "$WID" M sleep 0.4
xdotool mousemove --window "$WID" 1900 1 sleep 0.251 mousedown --window "$WID" 1 sleep 0.251
xdotool mousemove --window "$WID" 1 1080 sleep 0.251 mouseup --window "$WID" 1 sleep 0.151
xdotool mousemove --window "$WID" 1 1080 sleep 0.251 mousedown --window "$WID" 1 sleep 0.251
xdotool mousemove_relative 790 -840 sleep 0.251 mouseup --window "$WID" 1 sleep 0.151
for k in {1..8};
do
	     #echo "$k -th collection of map missions: $SECONDS"
	xdotool mousemove --window "$WID" 150 290 sleep 0.1 click --window "$WID" 1
	xdotool mousemove --window "$WID" 1410 800 sleep 0.1 click --window "$WID" 1
	xdotool mousemove --window "$WID" 1 1070 sleep 0.1 click --window "$WID" --repeat 3 --delay 10 1
	     #echo "$k -th collection of map missions finished: $SECONDS"
done
}



mapStart () {
xdotool search --name 'Firestone' windowactivate sleep 0.15
WID=$(xdotool getactivewindow)
p=370
t=140
for k in {1..9};
do
	xdotool mousemove --window "$WID" "$p" "$t" sleep 0.1 click --window "$WID" 1 
	xdotool mousemove --window "$WID" 1070 900 sleep 0.1 click --window "$WID" 1 
	xdotool mousemove --window "$WID" 1920 10 sleep 0.05 click --window "$WID" 1
	s=t
	let t=s+96
done
s=t
let t=s-12
xdotool mousemove --window "$WID" "$p" "$t" sleep 0.1 click --window "$WID" 1 
xdotool mousemove --window "$WID" 1070 900 sleep 0.1 click --window "$WID" 1 
xdotool mousemove --window "$WID" 1920 10 sleep 0.05 click --window "$WID" 1
f=p
let p=f+96
for z in {1..8};
do
	t=150
	for k in {1..9};
	do
		xdotool mousemove --window "$WID" "$p" "$t" sleep 0.1 click --window "$WID" 1 
		xdotool mousemove --window "$WID" 1070 900 sleep 0.1 click --window "$WID" 1
		xdotool mousemove --window "$WID" 1920 10 sleep 0.05 click --window "$WID" 1
		s=t
		let t=s+96
	done
	s=t
	let t=s-48
	xdotool mousemove --window "$WID" "$p" "$t" sleep 0.1 click --window "$WID" 1 
	xdotool mousemove --window "$WID" 1070 900 sleep 0.1 click --window "$WID" 1 
	xdotool mousemove --window "$WID" 1920 10 sleep 0.05 click --window "$WID" 1
	f=p
	let p=f+98
done
for z in {1..5};
do
	t=150
	for k in {1..9};
	do
		xdotool mousemove --window "$WID" "$p" "$t" sleep 0.1 click --window "$WID" 1 
		xdotool mousemove --window "$WID" 1070 900 sleep 0.1 click --window "$WID" 1
		xdotool mousemove --window "$WID" 1920 10 sleep 0.05 click --window "$WID" 1
		s=t
		let t=s+96
	done
	f=p
	let p=f+96
done
reset
}
oracle () {
	xdotool search --name 'Firestone' windowactivate sleep 0.15
	WID=$(xdotool getactivewindow)
	xdotool key --window "$WID" o sleep 0.3
	xdotool mousemove --window "$WID" 820 430 sleep 0.2 click --window "$WID" 1 sleep 0.15
	     #echo "Solar chests: $SECONDS" #debug
	xdotool mousemove --window "$WID" 1170 880 sleep 0.2 click --window "$WID" --repeat 2 --delay 200 1
	     #echo "Lunar chests: $SECONDS" #debug
	xdotool mousemove --window "$WID" 1620 510 sleep 0.2 click --window "$WID" --repeat 2 --delay 200 1
	     #echo "Comet chests: $SECONDS" #debug
	xdotool mousemove --window "$WID" 1170 510 sleep 0.2 click --window "$WID" --repeat 2 --delay 200 1
 	     #echo "Oracle's gifts: $SECONDS" #debug
	xdotool mousemove --window "$WID" 1620 880 sleep 0.2 click --window "$WID" --repeat 2 --delay 200 1
	reset
}

serverSwap () {
xdotool search --name 'Firestone' windowactivate sleep 0.15
WID=$(xdotool getactivewindow)
xdotool mousemove --window "$WID" 1840 50 sleep 0.25 click --window "$WID" 1
xdotool mousemove --window "$WID" 1500 620 sleep 0.25 click --window "$WID" 1
xdotool mousemove --window "$WID" 1300 170 sleep 0.25 click --window "$WID" 1
xdotool mousemove --window "$WID" 1180 160 sleep 0.2 click --window "$WID" 1

if [ "$1" -eq 1 ]; then
	     #echo "First favorite" #debug
	xdotool mousemove 520 330 sleep 0.2 click --window "$WID" 1
elif [ "$1" -eq 2 ]; then
	     #echo "Second favorite" #debug
	xdotool mousemove 1300 330 sleep 0.2 click --window "$WID" 1
elif [ "$1" -eq 3 ]; then
	     #echo "Third favorite" #debug
	xdotool mousemove 520 520 sleep 0.2 click --window "$WID" 1
elif [ "$1" -eq 4 ]; then
	     #echo "Fourth favorite" #debug
	xdotool mousemove 1300 520 sleep 0.2 click --window "$WID" 1
elif [ "$1" -eq 5 ]; then
	     #echo "Fifth favorite" #debug
	xdotool mousemove 520 700 sleep 0.2 click --window "$WID" 1
elif [ "$1" -eq 6 ]; then
	     #echo "Sixth favorite" #debug
	xdotool mousemove 1300 700 sleep 0.2 click --window "$WID" 1
fi
	xdotool mousemove 1110 720 sleep 0.2 click --window "$WID" 1
xdotool sleep 90
}


tavern () {
xdotool search --name 'Firestone' windowactivate sleep 0.15
WID=$(xdotool getactivewindow)
	xdotool mousemove --window "$WID" 1860 212 sleep 0.2 click --window "$WID" 1
	xdotool mousemove --window "$WID" 700 960 sleep 0.2 click --window "$WID" 1
	xdotool mousemove --window "$WID" 1720 50 sleep 0.2 click --window "$WID" 1
	xdotool mousemove --window "$WID" 500 570 sleep 0.2 click --window "$WID" 1
	reset
}


getMatrixElement () {
	local row=$1		# Expecting the first argument to be row index
	local col=$2		# Expecting the second argument to be column index
	local cols=$3	   # Expecting the third argument to be number of columns
	shift 3			 # Shift off the first three parameters to get the matrix
	local matrix=("$@") # Remaining arguments are the matrix elements
	local index=$((row * cols + col))
	#echo "matrix element row / col / cols / index: $row / $col / $cols / $index" #debug
	echo "${matrix[$index]}"
}

getSingleRowElement () {
	local col=$1			# Expecting the first argument to be column index
	shift					# Shift to drop the column index from parameters
	local matrix=("$@")	 # The remaining arguments are the matrix elements
	echo "${matrix[$col]}"  # Output the element at the specified column index
}

															  
declare -a fsRows=(
	"260" "400" "520" "640" "780"
 )
declare -a fsColsLeft=(
	"220" "700" "1200" "1690"
)									  
declare -a fsColsRight=(
	"20" "520" "990"
)

declare -a fsTreePatterns=(
"1;2" "1;4" "2;1" "2;3" "2;5" "3;2" "3;4" "4;3" "5;2" "5;4" "6;3" "7;1" "7;3" "7;5" "8;2" "8;4" "1;3" "2;2" "2;4" "3;1" "3;3" "3;5" "4;3" "5;2" "5;4" "6;2" "6;4" "7;2" "7;4" "8;1" "8;3" "8;5" "1;1" "1;3" "1;5" "2;2" "2;4" "3;3" "4;3" "5;2" "5;4" "6;2" "6;4" "7;2" "7;4" "8;1" "8;3" "8;5"
)

declare -a guardianPos=(
	"750;1000" "900;1000" "1050;1000" "1200;1000"  
)

reset () {
xdotool mousemove --window "$WID" 1840 50 sleep 0.2 click --window "$WID" --repeat 4 --delay 200 1
xdotool mousemove --window "$WID" 10 160 sleep 0.2 click --window "$WID" 1
}


max () {
	if [ "$1" -gt "$2" ]; then
		echo "$1"
	else
		echo "$2"
	fi
}
min () {
	if [ "$1" -gt "$2" ]; then
		echo "$2"
	else
		echo "$1"
	fi
}