#!/bin/bash
# Usage: ./to_instagram.sh renders/neuron_ig.1.mov  -> renders/neuron_ig.1_ig.mp4 (H.264 + AAC)
in="$1"; out="${in%.*}_ig.mp4"
avconvert -s "$in" -p PresetHighestQuality -o "$out" --replace && echo "OK -> $out"
